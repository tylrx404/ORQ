import uuid
from datetime import datetime, timezone
from typing import Sequence
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.agent_spec import AgentSpec, AgentSpecVersion
from app.models.prompt import Prompt, PromptVersion
from app.models.provider import Provider, ProviderType
from app.models.provider_model import ProviderModel
from app.services.agent_spec import (
    AgentSpecNotFoundError,
    AgentSpecService,
    AgentSpecVersionNotFoundError,
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
    def __init__(self, agent_repo=None, version_repo=None):
        self.agent_repo = agent_repo
        self.version_repo = version_repo
        self.rolled_back = False
        self.committed = False
        self.flushed = False
        self._uncommitted_agents: set[UUID] = set()
        self._uncommitted_versions: set[UUID] = set()

    def add(self, obj):
        now = datetime.now(timezone.utc)
        if isinstance(obj, AgentSpec) and self.agent_repo:
            if getattr(obj, "created_at", None) is None:
                obj.created_at = now
            if getattr(obj, "updated_at", None) is None:
                obj.updated_at = now
            self.agent_repo.items[obj.id] = obj
            self._uncommitted_agents.add(obj.id)
        elif isinstance(obj, AgentSpecVersion) and self.version_repo:
            if getattr(obj, "created_at", None) is None:
                obj.created_at = now
            self.version_repo.versions[obj.id] = obj
            self._uncommitted_versions.add(obj.id)

    async def flush(self):
        self.flushed = True
        if self.agent_repo and hasattr(self.agent_repo, "create"):
            if self.agent_repo.create.__code__ != MockAgentSpecRepository.create.__code__:
                await self.agent_repo.create(None)

    async def commit(self):
        self.committed = True
        if self.agent_repo and hasattr(self.agent_repo, "create"):
            if self.agent_repo.create.__code__ != MockAgentSpecRepository.create.__code__:
                await self.agent_repo.create(None)
        self._uncommitted_agents.clear()
        self._uncommitted_versions.clear()

    async def refresh(self, obj):
        pass

    async def rollback(self):
        self.rolled_back = True
        if self.agent_repo:
            for aid in list(self._uncommitted_agents):
                self.agent_repo.items.pop(aid, None)
        if self.version_repo:
            for vid in list(self._uncommitted_versions):
                self.version_repo.versions.pop(vid, None)
        self._uncommitted_agents.clear()
        self._uncommitted_versions.clear()


class MockAgentSpecRepository:
    def __init__(self):
        self.items: dict[UUID, AgentSpec] = {}
        self.locked_ids: list[UUID] = []
        self.db = MockDB(agent_repo=self)

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

    async def get_for_update(self, agent_id: UUID) -> AgentSpec | None:
        self.locked_ids.append(agent_id)
        return self.items.get(agent_id)

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


class MockAgentSpecVersionRepository:
    def __init__(self, db=None):
        self.versions: dict[UUID, AgentSpecVersion] = {}
        self.db = db

    async def get_by_id(self, version_id: UUID) -> AgentSpecVersion | None:
        return self.versions.get(version_id)

    async def get_by_agent_and_id(
        self, agent_spec_id: UUID, version_id: UUID
    ) -> AgentSpecVersion | None:
        v = self.versions.get(version_id)
        if v and v.agent_spec_id == agent_spec_id:
            return v
        return None

    async def get_by_version_number(
        self, agent_spec_id: UUID, version_number: int
    ) -> AgentSpecVersion | None:
        for v in self.versions.values():
            if v.agent_spec_id == agent_spec_id and v.version_number == version_number:
                return v
        return None

    async def get_latest_version_number(self, agent_spec_id: UUID) -> int:
        matching = [
            v.version_number
            for v in self.versions.values()
            if v.agent_spec_id == agent_spec_id
        ]
        return max(matching) if matching else 0

    async def list_by_agent(
        self, agent_spec_id: UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[AgentSpecVersion]:
        matching = [
            v for v in self.versions.values() if v.agent_spec_id == agent_spec_id
        ]
        matching.sort(key=lambda v: v.version_number, reverse=True)
        return matching[skip : skip + limit]

    async def create(self, version: AgentSpecVersion) -> AgentSpecVersion:
        if getattr(version, "created_at", None) is None:
            version.created_at = datetime.now(timezone.utc)
        if self.db:
            self.db.add(version)
            await self.db.flush()
        else:
            self.versions[version.id] = version
        return version


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
    agent_spec_repo = MockAgentSpecRepository()
    version_repo = MockAgentSpecVersionRepository(db=agent_spec_repo.db)
    agent_spec_repo.db.version_repo = version_repo
    agent_spec_repo.version_repo = version_repo

    return {
        "agent_spec": agent_spec_repo,
        "agent_spec_version": version_repo,
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
        agent_spec_version_repository=repos["agent_spec_version"],
    )

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
async def test_update_agent_spec_mismatched_model_provider_fails(service, repos):
    """Verify updating model_id to a model belonging to a different provider, while retaining existing provider, raises InvalidModelReferenceError."""
    org_id = uuid4()

    p1_id = uuid4()
    p2_id = uuid4()
    repos["provider"].providers[p1_id] = Provider(
        id=p1_id, organization_id=org_id, name="P1", provider_type=ProviderType.openai, api_key="k"
    )
    repos["provider"].providers[p2_id] = Provider(
        id=p2_id, organization_id=org_id, name="P2", provider_type=ProviderType.anthropic, api_key="k"
    )

    m1_id = uuid4()
    repos["model"].models[m1_id] = ProviderModel(
        id=m1_id, provider_id=p1_id, name="M1", model_identifier="m1"
    )

    m2_id = uuid4()
    repos["model"].models[m2_id] = ProviderModel(
        id=m2_id, provider_id=p2_id, name="M2", model_identifier="m2"
    )

    agent = await service.create_agent_spec(
        organization_id=org_id,
        name="Agent",
        provider_id=p1_id,
        model_id=m1_id,
    )

    with pytest.raises(InvalidModelReferenceError) as exc_info:
        await service.update_agent_spec(
            organization_id=org_id,
            agent_id=agent.id,
            update_data={"model_id": m2_id},
        )
    assert f"Model with ID '{m2_id}' does not belong to provider '{p1_id}'." in str(exc_info.value)


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


# ---------------------------------------------------------------------------
# 5. AgentSpec Versioning Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_agent_spec_creates_version_1_atomically(service, repos):
    """Verify creating an AgentSpec atomically creates Version 1 and links current_version_id."""
    org_id = uuid4()
    agent = await service.create_agent_spec(
        organization_id=org_id,
        name="Auto Version Agent",
        description="Testing initial versioning",
        tool_identifiers=["search", "bash"],
        memory_policy={"max_entries": 10},
    )

    assert agent.id is not None
    assert agent.current_version_id is not None
    assert agent.current_version_number == 1
    assert repos["agent_spec"].db.committed is True

    # Check version entity in version repo
    v1 = await repos["agent_spec_version"].get_by_id(agent.current_version_id)
    assert v1 is not None
    assert v1.agent_spec_id == agent.id
    assert v1.version_number == 1
    assert v1.description == "Initial version"
    assert v1.tool_identifiers == ["search", "bash"]
    assert v1.memory_policy == {"max_entries": 10}


@pytest.mark.asyncio
async def test_create_agent_spec_atomic_failure_rolls_back_all(service, repos):
    """Verify that if version creation fails during agent creation, the agent is not persisted."""
    org_id = uuid4()

    async def mock_fail_create(version):
        raise RuntimeError("Disk full / version insertion failure")

    repos["agent_spec_version"].create = mock_fail_create

    with pytest.raises(RuntimeError) as exc_info:
        await service.create_agent_spec(
            organization_id=org_id,
            name="Failing Agent",
        )
    assert "version insertion failure" in str(exc_info.value)
    assert repos["agent_spec"].db.rolled_back is True
    assert len(repos["agent_spec"].items) == 0
    assert len(repos["agent_spec_version"].versions) == 0


@pytest.mark.asyncio
async def test_update_agent_spec_metadata_only_does_not_create_version(service, repos):
    """Verify that metadata-only updates (name, description, is_active) do not create a new version."""
    org_id = uuid4()
    agent = await service.create_agent_spec(
        organization_id=org_id,
        name="Original Agent",
        description="Original Desc",
        tool_identifiers=["tool1"],
        is_active=True,
    )
    v1_id = agent.current_version_id
    assert agent.current_version_number == 1

    updated = await service.update_agent_spec(
        organization_id=org_id,
        agent_id=agent.id,
        update_data={
            "name": "Updated Agent Name",
            "description": "Updated Desc",
            "is_active": False,
        },
    )

    assert updated.name == "Updated Agent Name"
    assert updated.description == "Updated Desc"
    assert updated.is_active is False
    assert updated.current_version_id == v1_id
    assert updated.current_version_number == 1

    versions = await service.list_versions(org_id, agent.id)
    assert len(versions) == 1
    assert versions[0].version_number == 1


@pytest.mark.asyncio
async def test_update_agent_spec_configuration_change_creates_next_version(service, repos):
    """Verify that execution-affecting configuration changes generate the next sequential version."""
    org_id = uuid4()
    agent = await service.create_agent_spec(
        organization_id=org_id,
        name="Config Agent",
        tool_identifiers=["calculator"],
    )
    v1_id = agent.current_version_id

    # Update tool_identifiers (execution configuration)
    updated = await service.update_agent_spec(
        organization_id=org_id,
        agent_id=agent.id,
        update_data={"tool_identifiers": ["calculator", "web_search"]},
    )

    assert updated.current_version_id != v1_id
    assert updated.current_version_number == 2
    assert updated.tool_identifiers == ["calculator", "web_search"]

    versions = await service.list_versions(org_id, agent.id)
    assert len(versions) == 2
    assert [v.version_number for v in versions] == [2, 1]

    # Verify immutability of historical Version 1
    v1 = await service.get_version(org_id, agent.id, v1_id)
    assert v1.version_number == 1
    assert v1.tool_identifiers == ["calculator"]


@pytest.mark.asyncio
async def test_sequential_version_numbering_on_multiple_updates(service, repos):
    """Verify version numbers strictly increment sequentially across multiple configuration changes."""
    org_id = uuid4()
    agent = await service.create_agent_spec(organization_id=org_id, name="Multi-version Agent")
    assert agent.current_version_number == 1

    # v2: change tools
    agent = await service.update_agent_spec(
        org_id, agent.id, {"tool_identifiers": ["t1"]}
    )
    assert agent.current_version_number == 2

    # v3: change memory
    agent = await service.update_agent_spec(
        org_id, agent.id, {"memory_policy": {"type": "window", "size": 5}}
    )
    assert agent.current_version_number == 3

    # Metadata update should NOT bump version
    agent = await service.update_agent_spec(org_id, agent.id, {"name": "New Name"})
    assert agent.current_version_number == 3

    # v4: change tools again
    agent = await service.update_agent_spec(
        org_id, agent.id, {"tool_identifiers": ["t1", "t2"]}
    )
    assert agent.current_version_number == 4

    versions = await service.list_versions(org_id, agent.id)
    assert [v.version_number for v in versions] == [4, 3, 2, 1]


@pytest.mark.asyncio
async def test_explicit_version_creation_from_effective_config(service, repos):
    """Verify explicit version creation creates a new version from current effective configuration."""
    org_id = uuid4()
    agent = await service.create_agent_spec(
        organization_id=org_id,
        name="Snapshot Agent",
        tool_identifiers=["search"],
        memory_policy={"max": 5},
    )
    assert agent.current_version_number == 1

    v2 = await service.create_version(
        organization_id=org_id,
        agent_id=agent.id,
        description="Manual snapshot before release",
    )

    assert v2.version_number == 2
    assert v2.description == "Manual snapshot before release"
    assert v2.tool_identifiers == ["search"]
    assert v2.memory_policy == {"max": 5}

    refetched = await service.get_agent_spec(org_id, agent.id)
    assert refetched.current_version_id == v2.id
    assert refetched.current_version_number == 2


@pytest.mark.asyncio
async def test_explicit_version_creation_with_overrides(service, repos):
    """Verify explicit version creation with overridden configuration updates both version and agent."""
    org_id = uuid4()
    agent = await service.create_agent_spec(organization_id=org_id, name="Override Agent")
    assert agent.tool_identifiers == []

    v2 = await service.create_version(
        organization_id=org_id,
        agent_id=agent.id,
        description="With new tools",
        tool_identifiers=["browser", "bash"],
    )

    assert v2.version_number == 2
    assert v2.tool_identifiers == ["browser", "bash"]

    refetched = await service.get_agent_spec(org_id, agent.id)
    assert refetched.current_version_id == v2.id
    assert refetched.current_version_number == 2
    assert refetched.tool_identifiers == ["browser", "bash"]


@pytest.mark.asyncio
async def test_rollback_creates_new_version_and_preserves_history(service, repos):
    """Verify rolling back creates a NEW version with historical configuration without mutating history."""
    org_id = uuid4()
    agent = await service.create_agent_spec(
        organization_id=org_id,
        name="Rollback Agent",
        tool_identifiers=["v1_tool"],
    )
    v1_id = agent.current_version_id

    # Create v2
    agent = await service.update_agent_spec(
        org_id, agent.id, {"tool_identifiers": ["v2_tool"]}
    )
    v2_id = agent.current_version_id
    assert agent.current_version_number == 2

    # Create v3
    agent = await service.update_agent_spec(
        org_id, agent.id, {"tool_identifiers": ["v3_tool"]}
    )
    assert agent.current_version_number == 3

    # Roll back to v1
    rolled_back_agent = await service.rollback_version(
        organization_id=org_id,
        agent_id=agent.id,
        target_version_id=v1_id,
    )

    # Agent should now be at v4 with v1's tools
    assert rolled_back_agent.current_version_number == 4
    assert rolled_back_agent.tool_identifiers == ["v1_tool"]

    # History must contain all 4 versions intact
    versions = await service.list_versions(org_id, agent.id)
    assert len(versions) == 4
    assert [v.version_number for v in versions] == [4, 3, 2, 1]

    v4 = versions[0]
    assert v4.version_number == 4
    assert v4.description == "Rollback to version 1"
    assert v4.tool_identifiers == ["v1_tool"]

    # Historical versions are completely untouched
    v1 = await service.get_version(org_id, agent.id, v1_id)
    assert v1.version_number == 1
    assert v1.tool_identifiers == ["v1_tool"]

    v2 = await service.get_version(org_id, agent.id, v2_id)
    assert v2.version_number == 2
    assert v2.tool_identifiers == ["v2_tool"]


@pytest.mark.asyncio
async def test_legacy_agent_mutation_creates_version_1(service, repos):
    """Verify legacy agent with no versions creates Version 1 on first configuration mutation."""
    org_id = uuid4()
    legacy_agent_id = uuid4()

    legacy_agent = AgentSpec(
        id=legacy_agent_id,
        organization_id=org_id,
        name="Legacy Agent",
        description="Created before versioning",
        tool_identifiers=["legacy_tool"],
        memory_policy={},
        current_version_id=None,
    )
    repos["agent_spec"].items[legacy_agent_id] = legacy_agent
    assert await repos["agent_spec_version"].get_latest_version_number(legacy_agent_id) == 0

    # 1. Metadata-only update must NOT create a version
    updated_meta = await service.update_agent_spec(
        org_id, legacy_agent_id, {"description": "Updated legacy description"}
    )
    assert updated_meta.current_version_id is None
    assert updated_meta.current_version_number is None
    assert await repos["agent_spec_version"].get_latest_version_number(legacy_agent_id) == 0

    # 2. Configuration mutation must create Version 1
    updated_config = await service.update_agent_spec(
        org_id, legacy_agent_id, {"tool_identifiers": ["new_tool"]}
    )
    assert updated_config.current_version_id is not None
    assert updated_config.current_version_number == 1
    assert updated_config.tool_identifiers == ["new_tool"]

    versions = await service.list_versions(org_id, legacy_agent_id)
    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert versions[0].tool_identifiers == ["new_tool"]


@pytest.mark.asyncio
async def test_legacy_agent_explicit_version_creation(service, repos):
    """Verify legacy agent with no versions creates Version 1 on explicit create_version."""
    org_id = uuid4()
    legacy_agent_id = uuid4()

    legacy_agent = AgentSpec(
        id=legacy_agent_id,
        organization_id=org_id,
        name="Legacy Agent 2",
        tool_identifiers=["base_tool"],
        current_version_id=None,
    )
    repos["agent_spec"].items[legacy_agent_id] = legacy_agent

    v1 = await service.create_version(
        org_id, legacy_agent_id, description="First explicit version for legacy agent"
    )
    assert v1.version_number == 1
    assert v1.description == "First explicit version for legacy agent"
    assert v1.tool_identifiers == ["base_tool"]

    refetched = await service.get_agent_spec(org_id, legacy_agent_id)
    assert refetched.current_version_id == v1.id
    assert refetched.current_version_number == 1


@pytest.mark.asyncio
async def test_rollback_nonexistent_version_fails(service, repos):
    """Verify attempting to rollback to a nonexistent version raises AgentSpecVersionNotFoundError."""
    org_id = uuid4()
    agent = await service.create_agent_spec(organization_id=org_id, name="Rollback Missing")

    with pytest.raises(AgentSpecVersionNotFoundError):
        await service.rollback_version(
            organization_id=org_id,
            agent_id=agent.id,
            target_version_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_rollback_cross_agent_version_fails(service, repos):
    """Verify rolling back to a version belonging to another agent raises AgentSpecVersionNotFoundError."""
    org_id = uuid4()
    agent_a = await service.create_agent_spec(organization_id=org_id, name="Agent A")
    agent_b = await service.create_agent_spec(organization_id=org_id, name="Agent B")

    v1_b_id = agent_b.current_version_id

    # Attempt to rollback Agent A to Agent B's version
    with pytest.raises(AgentSpecVersionNotFoundError) as exc_info:
        await service.rollback_version(
            organization_id=org_id,
            agent_id=agent_a.id,
            target_version_id=v1_b_id,
        )
    assert f"version '{v1_b_id}' not found for agent '{agent_a.id}'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_rollback_with_stale_or_invalid_reference_fails(service, repos):
    """Verify rollback re-validates foreign references and fails if a referenced entity is missing."""
    org_id = uuid4()
    p_id = uuid4()
    m_id = uuid4()

    repos["provider"].providers[p_id] = Provider(
        id=p_id, organization_id=org_id, name="Provider", provider_type=ProviderType.openai, api_key="k"
    )
    repos["model"].models[m_id] = ProviderModel(
        id=m_id, provider_id=p_id, name="Model", model_identifier="m"
    )

    agent = await service.create_agent_spec(
        organization_id=org_id,
        name="Agent Valid Ref",
        provider_id=p_id,
        model_id=m_id,
    )
    v1_id = agent.current_version_id

    # Update to clear model
    await service.update_agent_spec(org_id, agent.id, {"model_id": None, "provider_id": None})

    # Now delete the model from repository to simulate external deletion
    del repos["model"].models[m_id]

    # Rollback to v1 should fail reference validation
    with pytest.raises(InvalidModelReferenceError):
        await service.rollback_version(
            organization_id=org_id,
            agent_id=agent.id,
            target_version_id=v1_id,
        )


@pytest.mark.asyncio
async def test_rollback_transaction_failure_rolls_back(service, repos):
    """Verify database errors during rollback trigger session rollback."""
    org_id = uuid4()
    agent = await service.create_agent_spec(organization_id=org_id, name="Failing Rollback")
    v1_id = agent.current_version_id

    # Update to v2
    await service.update_agent_spec(org_id, agent.id, {"tool_identifiers": ["t2"]})

    # Simulate error on commit
    async def mock_commit_failure():
        raise RuntimeError("Commit failed")

    repos["agent_spec"].db.commit = mock_commit_failure

    with pytest.raises(RuntimeError):
        await service.rollback_version(org_id, agent.id, v1_id)

    assert repos["agent_spec"].db.rolled_back is True


@pytest.mark.asyncio
async def test_row_locking_invoked_on_mutations(service, repos):
    """Verify get_for_update is called on mutations for concurrency safety."""
    org_id = uuid4()
    agent = await service.create_agent_spec(organization_id=org_id, name="Locking Test Agent")
    repos["agent_spec"].locked_ids.clear()

    # 1. update_agent_spec locks row
    await service.update_agent_spec(org_id, agent.id, {"description": "Updated"})
    assert agent.id in repos["agent_spec"].locked_ids

    # 2. create_version locks row
    repos["agent_spec"].locked_ids.clear()
    v2 = await service.create_version(org_id, agent.id)
    assert agent.id in repos["agent_spec"].locked_ids

    # 3. rollback_version locks row
    repos["agent_spec"].locked_ids.clear()
    await service.rollback_version(org_id, agent.id, v2.id)
    assert agent.id in repos["agent_spec"].locked_ids
