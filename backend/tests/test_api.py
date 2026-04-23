import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "reposcope-ai"}

@pytest.mark.asyncio
async def test_list_repos_empty(client: AsyncClient, mock_db):
    # Mocking list_repositories (which is called by list_repos)
    # The actual controller calls list_repositories() in repo_controller.py
    # For simplicity, we just mock the DB find result if the controller uses it.
    
    # In list_repositories:
    # async for doc in db.repositories.find({}): ...
    
    mock_db.repositories.find.return_value.__aiter__.return_value = []
    
    response = await client.get("/api/v1/repos")
    assert response.status_code == 200
    assert response.json() == []
