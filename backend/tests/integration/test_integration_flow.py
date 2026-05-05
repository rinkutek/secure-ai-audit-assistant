import pytest
from httpx import AsyncClient, ASGITransport
import asyncio
from app.main import app
from app.api.deps import get_current_user

# Mock the LLM so we don't spend real OpenAI credits during tests
class MockLLM:
    async def answer(self, question, context_chunks, past_messages):
        # We return a dummy answer that includes citations to whatever context was provided
        cits = "".join([f"[{c['citation'].split('#')[0]}]" for c in context_chunks])
        return f"This is a mock LLM answer. {cits}"

@pytest.mark.asyncio
async def test_full_pipeline_integration(monkeypatch):
    """
    This test hits the REAL Postgres, REAL Neo4j, and REAL ChromaDB databases.
    It verifies:
    1. Document Upload (Ingestion into all 3 DBs)
    2. RBAC Enforcement (Viewer cannot see Admin docs)
    3. Query Retrieval (Merged search results passed to LLM)
    """
    monkeypatch.setattr("app.api.routes_query.get_llm_provider", lambda: MockLLM())
    
    import tempfile
    temp_dir = tempfile.mkdtemp()
    monkeypatch.setattr("app.core.config.settings.doc_storage_dir", temp_dir)
    
    unique_string = "INTEGRATION_TEST_SECRET_KEYWORD_999123"
    
    # Get actual user IDs from db to avoid FK violations
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select
    from app.db.models import User
    
    async with AsyncSessionLocal() as db_session:
        res = await db_session.execute(select(User).where(User.email == "admin@example.com"))
        admin_id = res.scalar_one().id
        res = await db_session.execute(select(User).where(User.email == "viewer@example.com"))
        viewer_id = res.scalar_one().id
    
    # 1. Upload a Document as Admin
    app.dependency_overrides[get_current_user] = lambda: {"user_id": admin_id, "roles": ["admin"]}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a dummy text file
        files = {'file': ('testdoc.txt', f"The system architecture uses {unique_string} for scaling.", 'text/plain')}
        upload_resp = await ac.post("/documents/upload?title=TopSecret", files=files)
        
    assert upload_resp.status_code == 200
    doc_id = upload_resp.json()["doc_id"]
    
    # Give the async Chroma/Neo4j indexing time to settle (embedding model takes 1-2s)
    await asyncio.sleep(3)

    # 2. Query as Viewer (Should Fail / Be Denied)
    app.dependency_overrides[get_current_user] = lambda: {"user_id": viewer_id, "roles": ["viewer"]}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        viewer_query = await ac.post("/query", json={"query": f"What uses {unique_string}?"})
        
    assert viewer_query.status_code == 200
    # Viewer does not have access to the uploaded document, so they should not get any chunks from it.
    # They might get chunks from other documents they have access to (due to vector search returning closest matches).
    viewer_citations = viewer_query.json()["citations"]
    for c in viewer_citations:
        assert c["doc_id"] != doc_id
        assert "testdoc.txt" not in c["filename"]

    # 3. Query as Admin (Should Succeed)
    app.dependency_overrides[get_current_user] = lambda: {"user_id": admin_id, "roles": ["admin"]}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        admin_query = await ac.post("/query", json={"query": f"What uses {unique_string}?"})
        
    assert admin_query.status_code == 200
    data = admin_query.json()
    assert data["debug"]["authorized_total"] > 0
    assert len(data["citations"]) > 0
    assert any(c["doc_id"] == doc_id for c in data["citations"]), f"Document {doc_id} not in citations: {data['citations']}"
    assert "mock LLM answer" in data["answer"]
    
    # 4. Cleanup (Delete Document)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        del_resp = await ac.delete(f"/documents/{doc_id}")
    assert del_resp.status_code == 200
    
    app.dependency_overrides.clear()
