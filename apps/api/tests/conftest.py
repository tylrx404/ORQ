
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.fixture(autouse=True)
def mock_rate_limiter():
    from app.api.dependencies import get_rate_limit_service
    class MockRateLimit:
        async def check_rate_limit(self, *args, **kwargs):
            return True, {}, None
    app.dependency_overrides[get_rate_limit_service] = lambda: MockRateLimit()
    yield
    if get_rate_limit_service in app.dependency_overrides:
        del app.dependency_overrides[get_rate_limit_service]
