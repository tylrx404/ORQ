from datetime import datetime, timezone
from typing import Sequence
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import (
    get_agent_spec_repository,
    get_agent_spec_service,
    get_current_user,
    get_organization_membership_repository,
    get_prompt_repository,
    get_prompt_version_repository,
    get_provider_model_repository,
    get_provider_repository,
)
from app.core.permissions import Permission
from app.main import app
from app.models.agent_spec import AgentSpec
from app.models.organization_membership import MembershipRole, OrganizationMembership
from app.models.prompt import Prompt, PromptVersion
from app.models.provider import Provider, ProviderType
from app.models.provider_model import ProviderModel
from app.models.user import User
from app.services.agent_spec import AgentSpecService


# ---------------------------------------------------------------------------
# Mock Repositories
# ---------------------------------------------------------------------------

class MockDB:
    def __init__(self):
        self.rolled_back = False

    async def rollback(self):
        self.rolled_back = True


class MockAgentSpecRepository:
    def __init__(self):
        self.items: dict[UUID, AgentSpec] = {}
        self.db = MockDB()

    async def get_by_id(self, agent_id: UUID) -> AgentSpec | None:
        return self.items.get(agent_id)

    async def get_by_id_and_org(self, organization_id: UUID, agent_id: UUID) -> AgentSpec | None:
        item = self.items.get(agent_id)
        if item and item.organization_id == organization_id:
            return item
        return None

    async def get_by_name_and_org(self, organization_id: UUID, name: str) -> AgentSpec | None:
        for item in self.items.values():
            if item.organization_id == organization_id and item.name == name:
                return item
        return None

    async def list_by_organization(
        self,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
    ) -> Sequence[AgentSpec]:
        matched = [
            item for item in self.items.values()
            if item.organization_id == organization_id
            and (is_active is None or item.is_active == is_active)
        ]
        matched.sort(key=lambda x: x.created_at, reverse=True)
        return matched[skip : skip + limit]

    async def create(self, agent_spec: AgentSpec) -> AgentSpec:
        if getattr(agent_spec, "created_at", None) is None:
            agent_spec.created_at = datetime.now(timezone.utc)
        if getattr(agent_spec, "updated_at", None) is None:
            agent_spec.updated_at = datetime.now(timezone.utc)
        self.items[agent_spec.id] = agent_spec
        return agent_spec

    async def update(self, agent_spec: AgentSpec) -> AgentSpec:
        agent_spec.updated_at = datetime.now(timezone.utc)
        self.items[agent_spec.id] = agent_spec
        return agent_spec

    async def delete(self, agent_spec: AgentSpec) -> None:
        self.items.pop(agent_spec.id, None)


class MockPromptRepository:
    def __init__(self):
        self.prompts: dict[UUID, Prompt] = {}

    async def get_by_id(self, prompt_id: UUID) -> Prompt | None:
        return self.prompts.get(prompt_id)

    async def get_by_id_and_org(self, organization_id: UUID, prompt_id: UUID) -> Prompt | None:
        prompt = self.prompts.get(prompt_id)
        if prompt and prompt.organization_id == organization_id:
            return prompt
        return None


class MockPromptVersionRepository:
    def __init__(self):
        self.versions: dict[UUID, PromptVersion] = {}

    async def get_by_id(self, version_id: UUID) -> PromptVersion | None:
        return self.versions.get(version_id)

    async def get_by_prompt_and_id(self, prompt_id: UUID, version_id: UUID) -> PromptVersion | None:
        version = self.versions.get(version_id)
        if version and version.prompt_id == prompt_id:
            return version
        return None


class MockProviderRepository:
    def __init__(self):
        self.providers: dict[UUID, Provider] = {}

    async def get_by_id(self, provider_id: UUID) -> Provider | None:
        return self.providers.get(provider_id)


class MockProviderModelRepository:
    def __init__(self):
        self.models: dict[UUID, ProviderModel] = {}

    async def get_by_id(self, model_id: UUID) -> ProviderModel | None:
        return self.models.get(model_id)


class MockMembershipRepository:
    def __init__(self):
        self.memberships: dict[tuple[UUID, UUID], OrganizationMembership] = {}

    def add_membership(self, org_id: UUID, user_id: UUID, role: MembershipRole = MembershipRole.member):
        membership = OrganizationMembership(
            id=uuid4(),
            organization_id=org_id,
            user_id=user_id,
            role=role,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.memberships[(org_id, user_id)] = membership
        return membership

    async def get_membership(self, organization_id: UUID, user_id: UUID) -> OrganizationMembership | None:
        return self.memberships.get((organization_id, user_id))


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_agent_api_deps():
    agent_spec_repo = MockAgentSpecRepository()
    prompt_repo = MockPromptRepository()
    version_repo = MockPromptVersionRepository()
    provider_repo = MockProviderRepository()
    model_repo = MockProviderModelRepository()
    membership_repo = MockMembershipRepository()

    service = AgentSpecService(
        agent_spec_repository=agent_spec_repo,
        prompt_repository=prompt_repo,
        prompt_version_repository=version_repo,
        provider_repository=provider_repo,
        provider_model_repository=model_repo,
    )

    org_a = uuid4()
    user_a = User(id=uuid4(), email="owner@orga.com", is_active=True)
    membership_repo.add_membership(org_a, user_a.id, MembershipRole.owner)

    user_a_member = User(id=uuid4(), email="member@orga.com", is_active=True)
    membership_repo.add_membership(org_a, user_a_member.id, MembershipRole.member)

    org_b = uuid4()
    user_b = User(id=uuid4(), email="user@orgb.com", is_active=True)
    membership_repo.add_membership(org_b, user_b.id, MembershipRole.member)

    app.dependency_overrides[get_agent_spec_repository] = lambda: agent_spec_repo
    app.dependency_overrides[get_prompt_repository] = lambda: prompt_repo
    app.dependency_overrides[get_prompt_version_repository] = lambda: version_repo
    app.dependency_overrides[get_provider_repository] = lambda: provider_repo
    app.dependency_overrides[get_provider_model_repository] = lambda: model_repo
    app.dependency_overrides[get_organization_membership_repository] = lambda: membership_repo
    app.dependency_overrides[get_agent_spec_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: user_a

    yield {
        "agent_spec_repo": agent_spec_repo,
        "prompt_repo": prompt_repo,
        "version_repo": version_repo,
        "provider_repo": provider_repo,
        "model_repo": model_repo,
        "membership_repo": membership_repo,
        "service": service,
        "org_a": org_a,
        "user_a": user_a,
        "user_a_member": user_a_member,
        "org_b": org_b,
        "user_b": user_b,
    }

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# API Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_agent_spec_minimal(mock_agent_api_deps):
    deps = mock_agent_api_deps
    org_id = str(deps["org_a"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/agents?organization_id={org_id}",
            json={"name": "Minimal Agent"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Minimal Agent"
        assert data["organization_id"] == org_id
        assert data["description"] is None
        assert data["prompt_id"] is None
        assert data["prompt_version_id"] is None
        assert data["provider_id"] is None
        assert data["model_id"] is None
        assert data["tool_identifiers"] == []
        assert data["memory_policy"] == {}
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_agent_spec_full(mock_agent_api_deps):
    deps = mock_agent_api_deps
    org_id = deps["org_a"]

    # Setup Prompt & Version
    p_id = uuid4()
    v_id = uuid4()
    deps["prompt_repo"].prompts[p_id] = Prompt(id=p_id, organization_id=org_id, name="Prompt 1")
    deps["version_repo"].versions[v_id] = PromptVersion(id=v_id, prompt_id=p_id, version_number=1, content="System")

    # Setup Provider & Model
    prov_id = uuid4()
    m_id = uuid4()
    deps["provider_repo"].providers[prov_id] = Provider(
        id=prov_id, organization_id=org_id, name="OpenAI", provider_type=ProviderType.openai, api_key="sk-test"
    )
    deps["model_repo"].models[m_id] = ProviderModel(
        id=m_id, provider_id=prov_id, name="GPT-4o", model_identifier="gpt-4o"
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/agents",
            json={
                "organization_id": str(org_id),
                "name": "Full Agent",
                "description": "Handles everything",
                "prompt_id": str(p_id),
                "prompt_version_id": str(v_id),
                "provider_id": str(prov_id),
                "model_id": str(m_id),
                "tool_identifiers": ["web_search", "calculator"],
                "memory_policy": {"window_size": 10},
                "is_active": False,
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Full Agent"
        assert data["prompt_id"] == str(p_id)
        assert data["prompt_version_id"] == str(v_id)
        assert data["provider_id"] == str(prov_id)
        assert data["model_id"] == str(m_id)
        assert data["tool_identifiers"] == ["web_search", "calculator"]
        assert data["memory_policy"] == {"window_size": 10}
        assert data["is_active"] is False


@pytest.mark.asyncio
async def test_create_agent_spec_organization_resolution(mock_agent_api_deps):
    """Test organization resolution from body, query parameter, and X-Organization-Id header."""
    deps = mock_agent_api_deps
    org_id = str(deps["org_a"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. From body
        res1 = await ac.post("/api/v1/agents", json={"organization_id": org_id, "name": "Agent Body"})
        assert res1.status_code == 201
        assert res1.json()["organization_id"] == org_id

        # 2. From query
        res2 = await ac.post(f"/api/v1/agents?organization_id={org_id}", json={"name": "Agent Query"})
        assert res2.status_code == 201
        assert res2.json()["organization_id"] == org_id

        # 3. From header
        res3 = await ac.post(
            "/api/v1/agents",
            headers={"X-Organization-Id": org_id},
            json={"name": "Agent Header"},
        )
        assert res3.status_code == 201
        assert res3.json()["organization_id"] == org_id


@pytest.mark.asyncio
async def test_create_agent_spec_missing_organization_id_returns_400(mock_agent_api_deps):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/agents", json={"name": "No Org Agent"})
        assert res.status_code == 400
        assert "organization_id is required" in res.json()["detail"]


@pytest.mark.asyncio
async def test_create_agent_spec_duplicate_name_returns_409(mock_agent_api_deps):
    deps = mock_agent_api_deps
    org_id = str(deps["org_a"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res1 = await ac.post(f"/api/v1/agents?organization_id={org_id}", json={"name": "Triage Agent"})
        assert res1.status_code == 201

        res2 = await ac.post(f"/api/v1/agents?organization_id={org_id}", json={"name": "Triage Agent"})
        assert res2.status_code == 409
        assert "already exists in this organization" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_create_agent_spec_same_name_different_orgs_succeeds(mock_agent_api_deps):
    deps = mock_agent_api_deps
    user_a = deps["user_a"]
    user_b = deps["user_b"]
    org_a = str(deps["org_a"])
    org_b = str(deps["org_b"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create in Org A
        res_a = await ac.post(f"/api/v1/agents?organization_id={org_a}", json={"name": "Common Name"})
        assert res_a.status_code == 201

        # Switch user to User B in Org B
        app.dependency_overrides[get_current_user] = lambda: user_b
        res_b = await ac.post(f"/api/v1/agents?organization_id={org_b}", json={"name": "Common Name"})
        assert res_b.status_code == 201
        assert res_a.json()["id"] != res_b.json()["id"]


@pytest.mark.asyncio
async def test_create_agent_spec_invalid_references_return_400(mock_agent_api_deps):
    deps = mock_agent_api_deps
    org_a = deps["org_a"]
    org_b = deps["org_b"]

    # Prompt in Org B
    p_b_id = uuid4()
    deps["prompt_repo"].prompts[p_b_id] = Prompt(id=p_b_id, organization_id=org_b, name="Foreign Prompt")

    # Provider & Model in Org A
    prov_a_id = uuid4()
    deps["provider_repo"].providers[prov_a_id] = Provider(
        id=prov_a_id, organization_id=org_a, name="Prov A", provider_type=ProviderType.openai, api_key="k"
    )
    prov_b_id = uuid4()
    deps["provider_repo"].providers[prov_b_id] = Provider(
        id=prov_b_id, organization_id=org_b, name="Prov B", provider_type=ProviderType.openai, api_key="k"
    )

    m_a_id = uuid4()
    deps["model_repo"].models[m_a_id] = ProviderModel(
        id=m_a_id, provider_id=prov_a_id, name="Model A", model_identifier="m-a"
    )
    m_b_id = uuid4()
    deps["model_repo"].models[m_b_id] = ProviderModel(
        id=m_b_id, provider_id=prov_b_id, name="Model B", model_identifier="m-b"
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Foreign prompt
        res1 = await ac.post(
            f"/api/v1/agents?organization_id={str(org_a)}",
            json={"name": "Agent 1", "prompt_id": str(p_b_id)},
        )
        assert res1.status_code == 400

        # 2. Foreign provider
        res2 = await ac.post(
            f"/api/v1/agents?organization_id={str(org_a)}",
            json={"name": "Agent 2", "provider_id": str(prov_b_id)},
        )
        assert res2.status_code == 400

        # 3. Foreign model
        res3 = await ac.post(
            f"/api/v1/agents?organization_id={str(org_a)}",
            json={"name": "Agent 3", "model_id": str(m_b_id)},
        )
        assert res3.status_code == 400

        # 4. Mismatched provider & model (Prov A passed with Model B)
        res4 = await ac.post(
            f"/api/v1/agents?organization_id={str(org_a)}",
            json={"name": "Agent 4", "provider_id": str(prov_a_id), "model_id": str(m_b_id)},
        )
        assert res4.status_code == 400


@pytest.mark.asyncio
async def test_list_agent_specs(mock_agent_api_deps):
    deps = mock_agent_api_deps
    org_a = str(deps["org_a"])
    org_b = str(deps["org_b"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post(f"/api/v1/agents?organization_id={org_a}", json={"name": "Agent A1", "is_active": True})
        await ac.post(f"/api/v1/agents?organization_id={org_a}", json={"name": "Agent A2", "is_active": True})
        await ac.post(f"/api/v1/agents?organization_id={org_a}", json={"name": "Agent A3 Inactive", "is_active": False})

        # Switch to User B in Org B
        app.dependency_overrides[get_current_user] = lambda: deps["user_b"]
        await ac.post(f"/api/v1/agents?organization_id={org_b}", json={"name": "Agent B1", "is_active": True})

        # Switch back to User A in Org A
        app.dependency_overrides[get_current_user] = lambda: deps["user_a"]

        # List all in Org A
        res_all = await ac.get(f"/api/v1/agents?organization_id={org_a}")
        assert res_all.status_code == 200
        assert len(res_all.json()) == 3

        # Filter active
        res_active = await ac.get(f"/api/v1/agents?organization_id={org_a}&is_active=true")
        assert res_active.status_code == 200
        assert len(res_active.json()) == 2

        # Filter inactive
        res_inactive = await ac.get(f"/api/v1/agents?organization_id={org_a}&is_active=false")
        assert res_inactive.status_code == 200
        assert len(res_inactive.json()) == 1

        # Pagination: limit=1
        res_limit = await ac.get(f"/api/v1/agents?organization_id={org_a}&limit=1")
        assert res_limit.status_code == 200
        assert len(res_limit.json()) == 1


@pytest.mark.asyncio
async def test_get_agent_spec_by_id(mock_agent_api_deps):
    deps = mock_agent_api_deps
    org_id = str(deps["org_a"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_res = await ac.post(f"/api/v1/agents?organization_id={org_id}", json={"name": "Get Me"})
        agent_id = create_res.json()["id"]

        get_res = await ac.get(f"/api/v1/agents/{agent_id}")
        assert get_res.status_code == 200
        assert get_res.json()["name"] == "Get Me"
        assert get_res.json()["id"] == agent_id


@pytest.mark.asyncio
async def test_get_agent_spec_not_found(mock_agent_api_deps):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/agents/{uuid4()}")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_patch_agent_spec_partial_update(mock_agent_api_deps):
    deps = mock_agent_api_deps
    org_id = str(deps["org_a"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_res = await ac.post(
            f"/api/v1/agents?organization_id={org_id}",
            json={
                "name": "Original Name",
                "description": "Original Description",
                "tool_identifiers": ["tool1"],
                "is_active": True,
            },
        )
        agent_id = create_res.json()["id"]

        # Partial update
        patch_res = await ac.patch(
            f"/api/v1/agents/{agent_id}",
            json={"name": "Renamed Agent", "is_active": False},
        )
        assert patch_res.status_code == 200
        data = patch_res.json()
        assert data["name"] == "Renamed Agent"
        assert data["is_active"] is False
        assert data["description"] == "Original Description"
        assert data["tool_identifiers"] == ["tool1"]


@pytest.mark.asyncio
async def test_patch_agent_spec_clearing_references(mock_agent_api_deps):
    deps = mock_agent_api_deps
    org_id = deps["org_a"]

    p_id = uuid4()
    v_id = uuid4()
    deps["prompt_repo"].prompts[p_id] = Prompt(id=p_id, organization_id=org_id, name="Prompt Clear")
    deps["version_repo"].versions[v_id] = PromptVersion(id=v_id, prompt_id=p_id, version_number=1, content="C")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_res = await ac.post(
            f"/api/v1/agents?organization_id={str(org_id)}",
            json={"name": "Agent With Prompt", "prompt_id": str(p_id), "prompt_version_id": str(v_id)},
        )
        agent_id = create_res.json()["id"]
        assert create_res.json()["prompt_id"] == str(p_id)

        # Clear prompt_id with explicit null
        patch_res = await ac.patch(
            f"/api/v1/agents/{agent_id}",
            json={"prompt_id": None},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["prompt_id"] is None
        assert patch_res.json()["prompt_version_id"] is None


@pytest.mark.asyncio
async def test_patch_agent_spec_mismatched_model_provider_fails(mock_agent_api_deps):
    deps = mock_agent_api_deps
    org_id = deps["org_a"]

    p1_id = uuid4()
    p2_id = uuid4()
    deps["provider_repo"].providers[p1_id] = Provider(
        id=p1_id, organization_id=org_id, name="P1", provider_type=ProviderType.openai, api_key="k"
    )
    deps["provider_repo"].providers[p2_id] = Provider(
        id=p2_id, organization_id=org_id, name="P2", provider_type=ProviderType.anthropic, api_key="k"
    )

    m1_id = uuid4()
    m2_id = uuid4()
    deps["model_repo"].models[m1_id] = ProviderModel(id=m1_id, provider_id=p1_id, name="M1", model_identifier="m1")
    deps["model_repo"].models[m2_id] = ProviderModel(id=m2_id, provider_id=p2_id, name="M2", model_identifier="m2")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_res = await ac.post(
            f"/api/v1/agents?organization_id={str(org_id)}",
            json={"name": "Agent Mismatch", "provider_id": str(p1_id), "model_id": str(m1_id)},
        )
        agent_id = create_res.json()["id"]

        # Attempt to update model_id to M2 (which belongs to P2) while retaining P1
        patch_res = await ac.patch(
            f"/api/v1/agents/{agent_id}",
            json={"model_id": str(m2_id)},
        )
        assert patch_res.status_code == 400
        assert f"does not belong to provider '{p1_id}'" in patch_res.json()["detail"]


@pytest.mark.asyncio
async def test_patch_agent_spec_duplicate_name_fails(mock_agent_api_deps):
    deps = mock_agent_api_deps
    org_id = str(deps["org_a"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post(f"/api/v1/agents?organization_id={org_id}", json={"name": "Agent One"})
        res2 = await ac.post(f"/api/v1/agents?organization_id={org_id}", json={"name": "Agent Two"})
        agent_two_id = res2.json()["id"]

        # Rename Agent Two to Agent One
        patch_res = await ac.patch(
            f"/api/v1/agents/{agent_two_id}",
            json={"name": "Agent One"},
        )
        assert patch_res.status_code == 409
        assert "already exists in this organization" in patch_res.json()["detail"]


@pytest.mark.asyncio
async def test_delete_agent_spec_as_admin_succeeds(mock_agent_api_deps):
    deps = mock_agent_api_deps
    org_id = str(deps["org_a"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Created by Owner (User A)
        create_res = await ac.post(f"/api/v1/agents?organization_id={org_id}", json={"name": "To Delete"})
        agent_id = create_res.json()["id"]

        # Owner deletes
        delete_res = await ac.delete(f"/api/v1/agents/{agent_id}")
        assert delete_res.status_code == 204

        # Subsequent GET is 404
        get_res = await ac.get(f"/api/v1/agents/{agent_id}")
        assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_delete_agent_spec_as_member_returns_403(mock_agent_api_deps):
    deps = mock_agent_api_deps
    org_id = str(deps["org_a"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Created by Owner
        create_res = await ac.post(f"/api/v1/agents?organization_id={org_id}", json={"name": "Admin Protected"})
        agent_id = create_res.json()["id"]

        # Switch user to member-only user in Org A
        app.dependency_overrides[get_current_user] = lambda: deps["user_a_member"]

        # Member attempting to delete returns 403
        delete_res = await ac.delete(f"/api/v1/agents/{agent_id}")
        assert delete_res.status_code == 403
        assert "requires admin or owner role" in delete_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cross_organization_isolation(mock_agent_api_deps):
    deps = mock_agent_api_deps
    org_a = str(deps["org_a"])
    user_b = deps["user_b"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create agent in Org A
        create_res = await ac.post(f"/api/v1/agents?organization_id={org_a}", json={"name": "Org A Secret"})
        agent_id = create_res.json()["id"]

        # Switch current user to User B (member of Org B only)
        app.dependency_overrides[get_current_user] = lambda: user_b

        # 1. Attempt GET by ID -> 404 (detail matches missing agent to prevent ID oracle)
        get_res = await ac.get(f"/api/v1/agents/{agent_id}")
        assert get_res.status_code == 404
        assert get_res.json()["detail"] == "Agent specification not found."

        # 2. Attempt PATCH -> 404
        patch_res = await ac.patch(f"/api/v1/agents/{agent_id}", json={"name": "Hacked"})
        assert patch_res.status_code == 404
        assert patch_res.json()["detail"] == "Agent specification not found."

        # 3. Attempt DELETE -> 404
        del_res = await ac.delete(f"/api/v1/agents/{agent_id}")
        assert del_res.status_code == 404
        assert del_res.json()["detail"] == "Agent specification not found."

        # 4. Attempt list Org A -> 404 (no membership in Org A)
        list_res = await ac.get(f"/api/v1/agents?organization_id={org_a}")
        assert list_res.status_code == 404

        # 5. Attempt create in Org A -> 404 (no membership in Org A)
        post_res = await ac.post(f"/api/v1/agents?organization_id={org_a}", json={"name": "Injected"})
        assert post_res.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401():
    """Unauthenticated requests must be rejected with 401 Unauthorized without get_current_user override."""
    app.dependency_overrides.pop(get_current_user, None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/agents")
        assert res.status_code == 401
        assert res.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_list_agent_specs_without_organization_id_returns_400(mock_agent_api_deps):
    """GET /api/v1/agents without an organization ID in params or header must return 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/agents")
        assert res.status_code == 400
        assert "organization_id is required" in res.json()["detail"]


@pytest.mark.asyncio
async def test_invalid_payload_returns_422(mock_agent_api_deps):
    """Invalid request payloads violating schema validation must return 422."""
    deps = mock_agent_api_deps
    org_id = str(deps["org_a"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # POST with missing required 'name'
        res_missing = await ac.post(f"/api/v1/agents?organization_id={org_id}", json={})
        assert res_missing.status_code == 422

        # POST with empty string 'name' (min_length=1)
        res_empty = await ac.post(f"/api/v1/agents?organization_id={org_id}", json={"name": ""})
        assert res_empty.status_code == 422

        # POST with invalid UUID format
        res_bad_uuid = await ac.post(
            f"/api/v1/agents?organization_id={org_id}",
            json={"name": "Bad UUID", "model_id": "not-a-valid-uuid"},
        )
        assert res_bad_uuid.status_code == 422

        # Create valid agent for PATCH testing
        valid_res = await ac.post(f"/api/v1/agents?organization_id={org_id}", json={"name": "Valid Agent"})
        agent_id = valid_res.json()["id"]

        # PATCH with null for non-nullable field 'name'
        res_null_name = await ac.patch(f"/api/v1/agents/{agent_id}", json={"name": None})
        assert res_null_name.status_code == 422


@pytest.mark.asyncio
async def test_list_agent_specs_pagination_validation(mock_agent_api_deps):
    """Confirm negative skip, limit=0, and limit=101 return 422, while valid pagination works."""
    deps = mock_agent_api_deps
    org_id = str(deps["org_a"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Populate test agents
        await ac.post(f"/api/v1/agents?organization_id={org_id}", json={"name": "Agent Page 1"})
        await ac.post(f"/api/v1/agents?organization_id={org_id}", json={"name": "Agent Page 2"})

        # Negative skip -> 422
        res_neg_skip = await ac.get(f"/api/v1/agents?organization_id={org_id}&skip=-1")
        assert res_neg_skip.status_code == 422

        # limit=0 -> 422
        res_zero_limit = await ac.get(f"/api/v1/agents?organization_id={org_id}&limit=0")
        assert res_zero_limit.status_code == 422

        # limit=101 -> 422
        res_over_limit = await ac.get(f"/api/v1/agents?organization_id={org_id}&limit=101")
        assert res_over_limit.status_code == 422

        # Valid pagination: skip=1, limit=1
        res_valid = await ac.get(f"/api/v1/agents?organization_id={org_id}&skip=1&limit=1")
        assert res_valid.status_code == 200
        assert len(res_valid.json()) == 1

        # Valid pagination boundary: skip=0, limit=100
        res_boundary = await ac.get(f"/api/v1/agents?organization_id={org_id}&skip=0&limit=100")
        assert res_boundary.status_code == 200
        assert len(res_boundary.json()) >= 2
