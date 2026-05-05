import pytest
from app.services.neo4j_rbac import RBACGraph
from app.core.config import settings
from app.core.exceptions import AppError

@pytest.mark.asyncio
async def test_rbac_fail_closed(monkeypatch):
    monkeypatch.setattr(settings, "neo4j_uri", "bolt://127.0.0.1:1")
    g = RBACGraph()
    with pytest.raises(AppError) as e:
        await g.allowed_doc_ids(user_id="u1", roles=["auditor"])
    assert e.value.code == "RBAC_UNAVAILABLE"

@pytest.mark.asyncio
async def test_audit_logging_failure_rejects_request(monkeypatch):
    # If the database fails to write the audit log, the system must bubble up the error and reject the request.
    from app.services.audit_log import write_audit_log
    
    async def mock_write_audit_log(*args, **kwargs):
        raise Exception("Database disconnected during audit logging")
    
    monkeypatch.setattr("app.api.routes_query.write_audit_log", mock_write_audit_log)
    
    # Mock all the retrieval dependencies so we actually reach the audit logging step
    class MockEmbedder:
        async def embed(self, texts): return [[0.1]*1536]
    monkeypatch.setattr("app.api.routes_query.get_embedding_provider", lambda: MockEmbedder())
    
    class MockChroma:
        async def query(self, *args, **kwargs): return [{"id": "chunk1", "document": "test", "metadata": {"doc_id": "d1"}}]
    monkeypatch.setattr("app.api.routes_query.ChromaHttpClient", MockChroma)
    
    async def mock_bm25(*args, **kwargs): return []
    monkeypatch.setattr("app.api.routes_query.bm25_keyword_search", mock_bm25)
    
    class MockRBAC:
        async def allowed_doc_ids(self, *args, **kwargs): return ["d1"]
    monkeypatch.setattr("app.api.routes_query.RBACGraph", MockRBAC)
    
    # Mocking dependencies for query_endpoint
    from app.api.routes_query import query_endpoint
    from app.schemas.query import QueryRequest
    from fastapi import Request
    
    class MockRequest:
        pass
        
    class MockAsyncSession:
        def add(self, *args, **kwargs): pass
        async def commit(self): pass
        async def flush(self): pass
        async def execute(self, *args, **kwargs):
            class MockResult:
                def all(self): return []
                def scalars(self):
                    class MockScalars:
                        def all(self): return []
                        def first(self): return None
                    return MockScalars()
                def scalar_one_or_none(self): return None
            return MockResult()
        
    req = QueryRequest(query="Show me the documents", session_id="sess_1")
    user = {"user_id": "u1", "roles": ["auditor"]}
    db = MockAsyncSession()
    
    with pytest.raises(Exception) as e:
        await query_endpoint(req=req, request=MockRequest(), db=db, user=user, client_ip="127.0.0.1")
        
    assert "Database disconnected during audit logging" in str(e.value)
