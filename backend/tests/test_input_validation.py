import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings

@pytest.mark.asyncio
async def test_query_length_restriction():
    # Attempt to send a query that exceeds the max length
    oversized_query = "A" * (settings.max_query_chars + 1)
    
    # We must provide an auth token because the route requires it.
    # We can mock get_current_user in fastapi dependency overrides
    from app.api.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: {"user_id": "u1", "roles": ["auditor"]}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/query",
            json={"query": oversized_query}
        )
        
    app.dependency_overrides.clear()
    
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_invalid_json_handling():
    from app.api.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: {"user_id": "u1", "roles": ["auditor"]}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Missing the required 'query' field in the JSON payload
        response = await ac.post(
            "/query",
            json={"wrong_field": "test"}
        )
        
    app.dependency_overrides.clear()
    
    # FastAPI's Pydantic validation automatically catches this and safely returns 422
    assert response.status_code == 422
