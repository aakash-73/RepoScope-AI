import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from database import get_db
from unittest.mock import AsyncMock

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture
def mock_db():
    db = AsyncMock()
    # Mock collections used in classifier_registry
    db.classifier_extensions = AsyncMock()
    db.classifier_named_files = AsyncMock()
    db.classifier_fingerprints = AsyncMock()
    db.classifier_path_patterns = AsyncMock()
    db.classifier_categories = AsyncMock()
    db.classifier_edge_colors = AsyncMock()
    return db

@pytest.fixture(autouse=True)
def override_get_db(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    yield
    app.dependency_overrides.clear()
