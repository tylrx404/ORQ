import uuid
from datetime import datetime, timezone
from typing import Sequence
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.agent_spec import AgentSpec
from app.models.prompt import Prompt, PromptVersion
from app.models.provider import Provider, ProviderType
from app.models.provider_model import ProviderModel
from app.services.agent_spec import (
    AgentSpecNotFoundError,
    AgentSpecService,
    DuplicateAgentSpecError,
    InvalidModelReferenceError,
    InvalidPromptReferenceError,
    InvalidPromptVersionReferenceError,
    InvalidProviderReferenceError,
)


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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repos():
    return {
        "agent_spec": MockAgentSpecRepository(),
        "prompt": MockPromptRepository(),
        "prompt_version": MockPromptVersionRepository(),
        "provider": MockProviderRepository(),
        "model": MockProviderModelRepository(),
    }


@pytest.fixture
def service(repos):
    return AgentSpecService(
        agent_spec_repository=repos["agent_spec"],
        prompt_repository=repos["prompt"],
        prompt_version_repository=repos["prompt_version"],
        provider_repository=repos["provider"],
        provider_model_repository=repos["model"],
    )


# ---------------------------------------------------------------------------
# 1. Create AgentSpec Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_agent_spec_minimal(service):
    """Verify minimal agent creation with defaults."""
    org_id = uuid4()
    agent = await service.create_agent_spec(
        organization_id=org_id,
        name="Support Agent",
    )

    assert agent.id is not None
    assert agent.organization_id == org_id
    assert agent.name == "Support Agent"
    assert agent.tool_identifiers == []
    assert agent.memory_policy == {}
    assert agent.is_active is True
    assert agent.prompt_id is None
    assert agent.prompt_version_id is None
    assert agent.provider_id is None
    assert agent.model_id is None


@pytest.mark.asyncio
async def test_create_agent_spec_with_valid_references(service, repos):
    """Verify agent creation referencing valid prompt, version, provider, and model."""
    org_id = uuid4()

    # Setup Prompt & Version
    prompt_id = uuid4()
    prompt = Prompt(id=prompt_id, organization_id=org_id, name="Test Prompt")
    repos["prompt"].prompts[prompt_id] = prompt

    version_id = uuid4()
    version = PromptVersion(id=version_id, prompt_id=prompt_id, version_number=1, content="System prompt")
    repos["prompt_version"].versions[version_id] = version

    # Setup Provider & Model
    provider_id = uuid4()
    provider = Provider(
        id=provider_id,
        organization_id=org_id,
        name="OpenAI Provider",
        provider_type=ProviderType.openai,
        api_key="encrypted_key",
    )
    repos["provider"].providers[provider_id] = provider

    model_id = uuid4()
    model = ProviderModel(
        id=model_id,
        provider_id=provider_id,
        name="GPT-4o",
        model_identifier="gpt-4o",
    )
    repos["model"].models[model_id] = model

    agent = await service.create_agent_spec(
        organization_id=org_id,
        name="Full Agent",
        description="Comprehensive agent",
        prompt_id=prompt_id,
        prompt_version_id=version_id,
        provider_id=provider_id,
        model_id=model_id,
        tool_identifiers=["web_search"],
        memory_policy={"type": "summary"},
        is_active=True,
    )

    assert agent.prompt_id == prompt_id
    assert agent.prompt_version_id == version_id
    assert agent.provider_id == provider_id
    assert agent.model_id == model_id
    assert agent.tool_identifiers == ["web_search"]


@pytest.mark.asyncio
async def test_create_agent_spec_auto_aligns_provider_from_model(service, repos):
    """Verify provider_id is auto-aligned when model_id is given without provider_id."""
    org_id = uuid4()
    provider_id = uuid4()
    model_id = uuid4()

    provider = Provider(
        id=provider_id,
        organization_id=org_id,
        name="Anthropic Provider",
        provider_type=ProviderType.anthropic,
        api_key="encrypted_key",
    )
    repos["provider"].providers[provider_id] = provider

    model = ProviderModel(
        id=model_id,
        provider_id=provider_id,
        name="Claude 3.5 Sonnet",
        model_identifier="claude-3-5-sonnet",
    )
    repos["model"].models[model_id] = model

    agent = await service.create_agent_spec(
        organization_id=org_id,
        name="Auto Provider Agent",
        model_id=model_id,
    )

    assert agent.model_id == model_id
    assert agent.provider_id == provider_id


@pytest.mark.asyncio
async def test_create_agent_spec_auto_aligns_prompt_from_version(service, repos):
    """Verify prompt_id is auto-aligned when prompt_version_id is given without prompt_id."""
    org_id = uuid4()
    prompt_id = uuid4()
    version_id = uuid4()

    prompt = Prompt(id=prompt_id, organization_id=org_id, name="Auto Prompt")
    repos["prompt"].prompts[prompt_id] = prompt

    version = PromptVersion(id=version_id, prompt_id=prompt_id, version_number=1, content="Hello")
    repos["prompt_version"].versions[version_id] = version

    agent = await service.create_agent_spec(
        organization_id=org_id,
        name="Auto Prompt Agent",
        prompt_version_id=version_id,
    )

    assert agent.prompt_id == prompt_id
    assert agent.prompt_version_id == version_id


@pytest.mark.asyncio
async def test_create_agent_spec_duplicate_name_fails(service):
    """Verify creating duplicate agent name in same org raises DuplicateAgentSpecError."""
    org_id = uuid4()
    await service.create_agent_spec(organization_id=org_id, name="Billing Agent")

    with pytest.raises(DuplicateAgentSpecError) as exc_info:
        await service.create_agent_spec(organization_id=org_id, name="Billing Agent")
    assert "already exists in this organization" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_agent_spec_same_name_different_orgs_succeeds(service):
    """Verify same agent name in different organizations succeeds."""
    org1 = uuid4()
    org2 = uuid4()

    agent1 = await service.create_agent_spec(organization_id=org1, name="Triage Agent")
    agent2 = await service.create_agent_spec(organization_id=org2, name="Triage Agent")

    assert agent1.name == agent2.name
    assert agent1.organization_id != agent2.organization_id


# ---------------------------------------------------------------------------
# 2. Relational & Cross-Org Validation Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_agent_spec_cross_org_prompt_fails(service, repos):
    """Verify prompt from another organization is rejected."""
    org1 = uuid4()
    org2 = uuid4()

    # Prompt belongs to org2
    prompt_id = uuid4()
    repos["prompt"].prompts[prompt_id] = Prompt(id=prompt_id, organization_id=org2, name="Foreign Prompt")

    with pytest.raises(InvalidPromptReferenceError) as exc_info:
        await service.create_agent_spec(organization_id=org1, name="Agent", prompt_id=prompt_id)
    assert "not found in this organization" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_agent_spec_mismatched_prompt_version_fails(service, repos):
    """Verify prompt version belonging to another prompt is rejected."""
    org_id = uuid4()

    prompt1_id = uuid4()
    prompt2_id = uuid4()
    repos["prompt"].prompts[prompt1_id] = Prompt(id=prompt1_id, organization_id=org_id, name="Prompt 1")
    repos["prompt"].prompts[prompt2_id] = Prompt(id=prompt2_id, organization_id=org_id, name="Prompt 2")

    version_id = uuid4()
    # Version belongs to prompt2
    repos["prompt_version"].versions[version_id] = PromptVersion(
        id=version_id, prompt_id=prompt2_id, version_number=1, content="Content"
    )

    with pytest.raises(InvalidPromptVersionReferenceError) as exc_info:
        await service.create_agent_spec(
            organization_id=org_id,
            name="Agent",
            prompt_id=prompt1_id,
            prompt_version_id=version_id,
        )
    assert "does not belong to prompt" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_agent_spec_cross_org_provider_fails(service, repos):
    """Verify provider from another organization is rejected."""
    org1 = uuid4()
    org2 = uuid4()

    provider_id = uuid4()
    repos["provider"].providers[provider_id] = Provider(
        id=provider_id,
        organization_id=org2,
        name="Foreign Provider",
        provider_type=ProviderType.openai,
        api_key="key",
    )

    with pytest.raises(InvalidProviderReferenceError) as exc_info:
        await service.create_agent_spec(organization_id=org1, name="Agent", provider_id=provider_id)
    assert "not found in this organization" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_agent_spec_cross_org_model_fails(service, repos):
    """Verify model from another organization's provider is rejected."""
    org1 = uuid4()
    org2 = uuid4()

    provider_id = uuid4()
    repos["provider"].providers[provider_id] = Provider(
        id=provider_id,
        organization_id=org2,
        name="Org2 Provider",
        provider_type=ProviderType.openai,
        api_key="key",
    )

    model_id = uuid4()
    repos["model"].models[model_id] = ProviderModel(
        id=model_id,
        provider_id=provider_id,
        name="Org2 Model",
        model_identifier="gpt-4o",
    )

    with pytest.raises(InvalidModelReferenceError) as exc_info:
        await service.create_agent_spec(organization_id=org1, name="Agent", model_id=model_id)
    assert "does not belong to this organization" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_agent_spec_mismatched_model_provider_fails(service, repos):
    """Verify model belonging to provider A is rejected when provider B is passed."""
    org_id = uuid4()

    p1_id = uuid4()
    p2_id = uuid4()
    repos["provider"].providers[p1_id] = Provider(
        id=p1_id, organization_id=org_id, name="P1", provider_type=ProviderType.openai, api_key="k"
    )
    repos["provider"].providers[p2_id] = Provider(
        id=p2_id, organization_id=org_id, name="P2", provider_type=ProviderType.anthropic, api_key="k"
    )

    model_id = uuid4()
    # Model belongs to p1
    repos["model"].models[model_id] = ProviderModel(
        id=model_id, provider_id=p1_id, name="M1", model_identifier="m1"
    )

    with pytest.raises(InvalidModelReferenceError) as exc_info:
        await service.create_agent_spec(
            organization_id=org_id,
            name="Agent",
            provider_id=p2_id,
            model_id=model_id,
        )
    assert "does not belong to provider" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 3. Get, List, Update, and Delete Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_agent_spec_cross_org_raises_not_found(service):
    """Verify retrieving an agent with a mismatched organization raises AgentSpecNotFoundError."""
    org1 = uuid4()
    org2 = uuid4()

    agent = await service.create_agent_spec(organization_id=org1, name="Secret Agent")

    # Correct org succeeds
    found = await service.get_agent_spec(org1, agent.id)
    assert found.id == agent.id

    # Wrong org fails with 404
    with pytest.raises(AgentSpecNotFoundError):
        await service.get_agent_spec(org2, agent.id)


@pytest.mark.asyncio
async def test_list_agent_specs_scoped_and_filtered(service):
    """Verify listing agent specs scopes by organization and filters by is_active."""
    org1 = uuid4()
    org2 = uuid4()

    await service.create_agent_spec(organization_id=org1, name="Active 1", is_active=True)
    await service.create_agent_spec(organization_id=org1, name="Inactive 1", is_active=False)
    await service.create_agent_spec(organization_id=org2, name="Org2 Agent", is_active=True)

    all_org1 = await service.list_agent_specs(org1)
    assert len(all_org1) == 2

    active_org1 = await service.list_agent_specs(org1, is_active=True)
    assert len(active_org1) == 1
    assert active_org1[0].name == "Active 1"

    inactive_org1 = await service.list_agent_specs(org1, is_active=False)
    assert len(inactive_org1) == 1
    assert inactive_org1[0].name == "Inactive 1"


@pytest.mark.asyncio
async def test_update_agent_spec_partial(service):
    """Verify partial updates update specified fields and preserve omitted fields."""
    org_id = uuid4()
    agent = await service.create_agent_spec(
        organization_id=org_id,
        name="Original Name",
        description="Original Desc",
        tool_identifiers=["tool1"],
        is_active=True,
    )

    updated = await service.update_agent_spec(
        organization_id=org_id,
        agent_id=agent.id,
        update_data={"name": "New Name", "is_active": False},
    )

    assert updated.name == "New Name"
    assert updated.is_active is False
    assert updated.description == "Original Desc"
    assert updated.tool_identifiers == ["tool1"]


@pytest.mark.asyncio
async def test_update_agent_spec_clearing_references(service, repos):
    """Verify setting prompt_id to None clears both prompt and version references."""
    org_id = uuid4()
    prompt_id = uuid4()
    version_id = uuid4()

    repos["prompt"].prompts[prompt_id] = Prompt(id=prompt_id, organization_id=org_id, name="P")
    repos["prompt_version"].versions[version_id] = PromptVersion(
        id=version_id, prompt_id=prompt_id, version_number=1, content="C"
    )

    agent = await service.create_agent_spec(
        organization_id=org_id,
        name="Agent With Prompt",
        prompt_id=prompt_id,
        prompt_version_id=version_id,
    )

    # Clear prompt reference
    updated = await service.update_agent_spec(
        organization_id=org_id,
        agent_id=agent.id,
        update_data={"prompt_id": None},
    )

    assert updated.prompt_id is None
    assert updated.prompt_version_id is None


@pytest.mark.asyncio
async def test_update_agent_spec_duplicate_name_fails(service):
    """Verify updating to an existing name in the same org raises DuplicateAgentSpecError."""
    org_id = uuid4()
    await service.create_agent_spec(organization_id=org_id, name="Agent A")
    agent_b = await service.create_agent_spec(organization_id=org_id, name="Agent B")

    with pytest.raises(DuplicateAgentSpecError):
        await service.update_agent_spec(
            organization_id=org_id,
            agent_id=agent_b.id,
            update_data={"name": "Agent A"},
        )


@pytest.mark.asyncio
async def test_delete_agent_spec(service):
    """Verify deleting agent spec removes it from organization."""
    org_id = uuid4()
    agent = await service.create_agent_spec(organization_id=org_id, name="To Delete")

    await service.delete_agent_spec(org_id, agent.id)

    with pytest.raises(AgentSpecNotFoundError):
        await service.get_agent_spec(org_id, agent.id)


# ---------------------------------------------------------------------------
# 4. Transaction Integrity Error & Rollback Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_agent_spec_concurrency_race_rollback(service, repos):
    """Verify session rollback on concurrent duplicate unique constraint collision."""
    org_id = uuid4()

    async def mock_create_integrity_error(obj):
        raise IntegrityError("INSERT", {}, Exception("uq_agent_specs_organization_id_name"))

    repos["agent_spec"].create = mock_create_integrity_error

    with pytest.raises(DuplicateAgentSpecError):
        await service.create_agent_spec(organization_id=org_id, name="Racing Agent")

    assert repos["agent_spec"].db.rolled_back is True


@pytest.mark.asyncio
async def test_create_agent_spec_unrelated_integrity_error_re_raised(service, repos):
    """Verify unrelated database integrity errors are rolled back and re-raised."""
    org_id = uuid4()

    async def mock_unrelated_error(obj):
        raise IntegrityError("INSERT", {}, Exception("foreign_key_violation_unknown"))

    repos["agent_spec"].create = mock_unrelated_error

    with pytest.raises(IntegrityError):
        await service.create_agent_spec(organization_id=org_id, name="Error Agent")

    assert repos["agent_spec"].db.rolled_back is True
