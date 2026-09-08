
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


@pytest.fixture(autouse=True)
def mock_quota_limiter():
    from app.api.dependencies import get_organization_quota_service
    class MockQuotaService:
        async def check_and_increment_request_quota(self, *args, **kwargs):
            return True
    app.dependency_overrides[get_organization_quota_service] = lambda: MockQuotaService()
    yield
    if get_organization_quota_service in app.dependency_overrides:
        del app.dependency_overrides[get_organization_quota_service]
