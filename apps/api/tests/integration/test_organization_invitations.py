import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from uuid import uuid4

from app.main import app
from app.api.dependencies import (
    get_current_user,
    require_admin,
    get_organization_invitation_repository,
    get_organization_membership_service,
)
from app.models.user import User
from app.models.organization_membership import MembershipRole
from app.models.organization_invitation import OrganizationInvitation, InvitationStatus


class MockInvitationRepository:
    def __init__(self):
        self.invitations = {}

    async def get_by_id(self, invitation_id):
        return self.invitations.get(invitation_id)

    async def get_by_token(self, token):
        for inv in self.invitations.values():
            if inv.token == token:
                return inv
        return None

    async def get_pending_by_email_and_org(self, organization_id, email):
        for inv in self.invitations.values():
            if (
                inv.organization_id == organization_id
                and inv.email == email
                and inv.status == InvitationStatus.pending
            ):
                return inv
        return None

    async def list_by_organization(self, organization_id, skip=0, limit=100):
        return [
            inv
            for inv in self.invitations.values()
            if inv.organization_id == organization_id
        ]

    async def create(self, invitation):
        invitation.id = uuid4()
        invitation.created_at = datetime.now(timezone.utc)
        invitation.updated_at = datetime.now(timezone.utc)
        self.invitations[invitation.id] = invitation
        return invitation

    async def update(self, invitation):
        invitation.updated_at = datetime.now(timezone.utc)
        self.invitations[invitation.id] = invitation
        return invitation

    async def delete(self, invitation):
        if invitation.id in self.invitations:
            del self.invitations[invitation.id]


class MockMembershipService:
    def __init__(self):
        self.memberships = []

    async def add_member(self, organization_id, user_id, role):
        self.memberships.append((organization_id, user_id, role))


@pytest.fixture
def mock_dependencies():
    repo = MockInvitationRepository()
    membership_svc = MockMembershipService()

    mock_user = User(
        id=uuid4(),
        email="admin@example.com",
        is_active=True,
    )

    app.dependency_overrides[get_organization_invitation_repository] = lambda: repo
    app.dependency_overrides[get_organization_membership_service] = lambda: membership_svc
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_admin] = lambda: None

    yield repo, membership_svc, mock_user
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_invitation(mock_dependencies):
    repo, _, user = mock_dependencies
    org_id = str(uuid4())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            f"/api/v1/organizations/{org_id}/invitations",
            json={"email": "new@example.com", "role": "member"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert data["status"] == "pending"
    assert "token" in data


@pytest.mark.asyncio
async def test_duplicate_invitation(mock_dependencies):
    repo, _, user = mock_dependencies
    org_id = str(uuid4())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        await ac.post(
            f"/api/v1/organizations/{org_id}/invitations",
            json={"email": "new@example.com", "role": "member"},
        )
        response = await ac.post(
            f"/api/v1/organizations/{org_id}/invitations",
            json={"email": "new@example.com", "role": "member"},
        )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_accept_invitation(mock_dependencies):
    repo, membership_svc, user = mock_dependencies
    org_id = uuid4()

    # Create invitation manually in repo
    inv = OrganizationInvitation(
        organization_id=org_id,
        email="new@example.com",
        role=MembershipRole.member,
        token="valid_token",
        status=InvitationStatus.pending,
        created_by=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    await repo.create(inv)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/invitations/valid_token/accept")

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert len(membership_svc.memberships) == 1


@pytest.mark.asyncio
async def test_revoke_invitation(mock_dependencies):
    repo, _, user = mock_dependencies
    org_id = uuid4()

    inv = OrganizationInvitation(
        organization_id=org_id,
        email="new@example.com",
        role=MembershipRole.member,
        token="valid_token",
        status=InvitationStatus.pending,
        created_by=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    inv = await repo.create(inv)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.delete(
            f"/api/v1/organizations/{org_id}/invitations/{inv.id}"
        )

    assert response.status_code == 204

    updated_inv = await repo.get_by_id(inv.id)
    assert updated_inv.status == InvitationStatus.revoked
