import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock

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
    
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=[])
    mock_db.repositories.find = MagicMock(return_value=mock_cursor)
    
    response = await client.get("/api/v1/repos")
    assert response.status_code == 200
    assert response.json() == []
