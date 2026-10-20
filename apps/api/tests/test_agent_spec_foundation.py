import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.models.agent_spec import AgentSpec, AgentSpecVersion
from app.schemas.agent_spec import (
    AgentSpecCreateRequest,
    AgentSpecResponse,
    AgentSpecUpdateRequest,
    AgentSpecVersionCreateRequest,
    AgentSpecVersionResponse,
)
from app.repositories.agent_spec_repository import AgentSpecRepository
from app.repositories.agent_spec_version_repository import AgentSpecVersionRepository


# ---------------------------------------------------------------------------
# 1. Model Structure & Metadata Tests
# ---------------------------------------------------------------------------

def test_agent_spec_model_metadata():
    """Verify AgentSpec ORM table name, columns, constraints, and indices."""
    assert AgentSpec.__tablename__ == "agent_specs"

    table = AgentSpec.__table__
    col_names = {col.name for col in table.columns}
    expected_cols = {
        "id",
        "organization_id",
        "name",
        "description",
        "current_version_id",
        "prompt_id",
        "prompt_version_id",
        "provider_id",
        "model_id",
        "tool_identifiers",
        "memory_policy",
        "is_active",
        "created_at",
        "updated_at",
    }
    assert expected_cols.issubset(col_names)

    # Check unique constraint on (organization_id, name)
    unique_constraints = {
        uc.name: {col.name for col in uc.columns}
        for uc in table.constraints
        if hasattr(uc, "columns") and uc.name and "uq_" in uc.name
    }
    assert "uq_agent_specs_organization_id_name" in unique_constraints
    assert unique_constraints["uq_agent_specs_organization_id_name"] == {"organization_id", "name"}

    # Check index on organization_id
    index_names = {idx.name for idx in table.indexes}
    assert "ix_agent_specs_organization_id" in index_names

    # Check foreign keys
    fk_targets = {fk.target_fullname for fk in table.foreign_keys}
    assert "organizations.id" in fk_targets
    assert "prompts.id" in fk_targets
    assert "prompt_versions.id" in fk_targets
    assert "providers.id" in fk_targets
    assert "models.id" in fk_targets
    assert "agent_spec_versions.id" in fk_targets


def test_agent_spec_model_instantiation():
    """Verify AgentSpec instantiates with proper attributes and __repr__."""
    agent_id = uuid4()
    org_id = uuid4()
    spec = AgentSpec(
        id=agent_id,
        organization_id=org_id,
        name="Support Triage Agent",
        description="Triages incoming support tickets",
        tool_identifiers=["search_docs", "escalate_ticket"],
        memory_policy={"type": "summary", "max_entries": 10},
    )

    assert spec.id == agent_id
    assert spec.organization_id == org_id
    assert spec.name == "Support Triage Agent"
    assert spec.tool_identifiers == ["search_docs", "escalate_ticket"]
    assert spec.memory_policy == {"type": "summary", "max_entries": 10}
    assert "<AgentSpec" in repr(spec)
    assert "Support Triage Agent" in repr(spec)


def test_agent_spec_version_model_metadata():
    """Verify AgentSpecVersion ORM table name, columns, constraints, and indices."""
    assert AgentSpecVersion.__tablename__ == "agent_spec_versions"

    table = AgentSpecVersion.__table__
    col_names = {col.name for col in table.columns}
    expected_cols = {
        "id",
        "agent_spec_id",
        "version_number",
        "description",
        "prompt_id",
        "prompt_version_id",
        "provider_id",
        "model_id",
        "tool_identifiers",
        "memory_policy",
        "created_at",
    }
    assert expected_cols.issubset(col_names)

    # Check unique constraint on (agent_spec_id, version_number)
    unique_constraints = {
        uc.name: {col.name for col in uc.columns}
        for uc in table.constraints
        if hasattr(uc, "columns") and uc.name and "uq_" in uc.name
    }
    assert "uq_agent_spec_versions_agent_spec_id_version_number" in unique_constraints
    assert unique_constraints["uq_agent_spec_versions_agent_spec_id_version_number"] == {
        "agent_spec_id",
        "version_number",
    }

    # Check index on agent_spec_id
    index_names = {idx.name for idx in table.indexes}
    assert "ix_agent_spec_versions_agent_spec_id" in index_names

    # Check foreign keys
    fk_targets = {fk.target_fullname for fk in table.foreign_keys}
    assert "agent_specs.id" in fk_targets
    assert "prompts.id" in fk_targets
    assert "prompt_versions.id" in fk_targets
    assert "providers.id" in fk_targets
    assert "models.id" in fk_targets


def test_agent_spec_version_model_instantiation_and_relationships():
    """Verify AgentSpecVersion instantiation and AgentSpec relationships."""
    agent_id = uuid4()
    version_id = uuid4()
    org_id = uuid4()

    agent = AgentSpec(
        id=agent_id,
        organization_id=org_id,
        name="Versioned Agent",
    )

    version = AgentSpecVersion(
        id=version_id,
        agent_spec_id=agent_id,
        version_number=1,
        description="Initial version",
        tool_identifiers=["calculator"],
        memory_policy={"type": "buffer"},
    )

    assert version.id == version_id
    assert version.agent_spec_id == agent_id
    assert version.version_number == 1
    assert version.description == "Initial version"
    assert version.tool_identifiers == ["calculator"]
    assert "v=1" in repr(version)

    # Relationship connection
    agent.current_version = version
    agent.current_version_id = version.id
    assert agent.current_version_number == 1

    # If current_version_id is None, current_version_number returns None safely
    agent.current_version_id = None
    assert agent.current_version_number is None

    # Manual property override
    agent.current_version_id = version_id
    agent.current_version = None
    agent.current_version_number = 3
    assert agent.current_version_number == 3


# ---------------------------------------------------------------------------
# 2. Schema Validation & Serialization Tests
# ---------------------------------------------------------------------------

def test_agent_spec_create_request_minimal_defaults():
    req = AgentSpecCreateRequest(name="Minimal Agent")
    assert req.name == "Minimal Agent"
    assert req.description is None
    assert req.organization_id is None
    assert req.prompt_id is None
    assert req.prompt_version_id is None
    assert req.provider_id is None
    assert req.model_id is None
    assert req.tool_identifiers == []
    assert req.memory_policy == {}
    assert req.is_active is True


def test_agent_spec_create_request_full():
    org_id = uuid4()
    p_id = uuid4()
    pv_id = uuid4()
    pr_id = uuid4()
    m_id = uuid4()

    req = AgentSpecCreateRequest(
        name="Full Agent",
        description="Comprehensive configuration",
        organization_id=org_id,
        prompt_id=p_id,
        prompt_version_id=pv_id,
        provider_id=pr_id,
        model_id=m_id,
        tool_identifiers=["bash", "python"],
        memory_policy={"max_tokens": 4096},
        is_active=False,
    )

    assert req.name == "Full Agent"
    assert req.description == "Comprehensive configuration"
    assert req.organization_id == org_id
    assert req.prompt_id == p_id
    assert req.prompt_version_id == pv_id
    assert req.provider_id == pr_id
    assert req.model_id == m_id
    assert req.tool_identifiers == ["bash", "python"]
    assert req.memory_policy == {"max_tokens": 4096}
    assert req.is_active is False


def test_agent_spec_create_request_validation():
    with pytest.raises(ValidationError):
        AgentSpecCreateRequest(name="")

    with pytest.raises(ValidationError):
        AgentSpecCreateRequest(name="a" * 256)


def test_agent_spec_update_request_omitted_fields():
    req = AgentSpecUpdateRequest()
    dumped = req.model_dump(exclude_unset=True)
    assert dumped == {}


def test_agent_spec_update_request_valid_partial():
    req = AgentSpecUpdateRequest(name="Updated Name", is_active=False)
    dumped = req.model_dump(exclude_unset=True)
    assert dumped == {"name": "Updated Name", "is_active": False}


@pytest.mark.parametrize("field_name", ["name", "tool_identifiers", "memory_policy", "is_active"])
def test_agent_spec_update_request_rejects_null_for_non_nullable_fields(field_name: str):
    with pytest.raises(ValidationError) as exc_info:
        AgentSpecUpdateRequest(**{field_name: None})
    err_str = str(exc_info.value)
    assert field_name in err_str
    assert "cannot be null" in err_str or "Input should be" in err_str


def test_agent_spec_update_request_accepts_null_for_nullable_fields():
    req = AgentSpecUpdateRequest(
        description=None,
        prompt_id=None,
        prompt_version_id=None,
        provider_id=None,
        model_id=None,
    )
    dumped = req.model_dump(exclude_unset=True)
    assert dumped == {
        "description": None,
        "prompt_id": None,
        "prompt_version_id": None,
        "provider_id": None,
        "model_id": None,
    }


def test_agent_spec_response_serialization():
    agent_id = uuid4()
    org_id = uuid4()
    version_id = uuid4()
    now = datetime.now(timezone.utc)

    resp = AgentSpecResponse(
        id=agent_id,
        organization_id=org_id,
        name="Serialized Agent",
        description="Testing response schema",
        current_version_id=version_id,
        current_version_number=1,
        prompt_id=None,
        prompt_version_id=None,
        provider_id=None,
        model_id=None,
        tool_identifiers=["web_search"],
        memory_policy={"max_tokens": 2000},
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    data = resp.model_dump()
    assert data["id"] == agent_id
    assert data["organization_id"] == org_id
    assert data["name"] == "Serialized Agent"
    assert data["current_version_id"] == version_id
    assert data["current_version_number"] == 1
    assert data["tool_identifiers"] == ["web_search"]
    assert data["memory_policy"] == {"max_tokens": 2000}
    assert data["created_at"] == now


def test_agent_spec_response_serialization_with_null_version():
    """Verify AgentSpecResponse serialization when current_version_id is None."""
    agent_id = uuid4()
    org_id = uuid4()
    now = datetime.now(timezone.utc)

    # 1. From schema instantiation
    resp = AgentSpecResponse(
        id=agent_id,
        organization_id=org_id,
        name="Unversioned Agent",
        description=None,
        current_version_id=None,
        current_version_number=None,
        prompt_id=None,
        prompt_version_id=None,
        provider_id=None,
        model_id=None,
        tool_identifiers=[],
        memory_policy={},
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    data = resp.model_dump()
    assert data["current_version_id"] is None
    assert data["current_version_number"] is None

    # 2. From ORM model instance with current_version_id=None
    orm_spec = AgentSpec(
        id=agent_id,
        organization_id=org_id,
        name="Unversioned ORM Agent",
        description=None,
        current_version_id=None,
        tool_identifiers=[],
        memory_policy={},
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    from_orm = AgentSpecResponse.model_validate(orm_spec)
    assert from_orm.current_version_id is None
    assert from_orm.current_version_number is None


def test_agent_spec_version_schemas():
    """Verify AgentSpecVersionCreateRequest and AgentSpecVersionResponse."""
    p_id = uuid4()
    m_id = uuid4()

    req = AgentSpecVersionCreateRequest(
        description="Version 2 update",
        prompt_id=p_id,
        model_id=m_id,
        tool_identifiers=["browser"],
    )
    assert req.description == "Version 2 update"
    assert req.prompt_id == p_id
    assert req.model_id == m_id
    assert req.tool_identifiers == ["browser"]
    assert req.memory_policy == {}

    v_id = uuid4()
    a_id = uuid4()
    now = datetime.now(timezone.utc)

    resp = AgentSpecVersionResponse(
        id=v_id,
        agent_spec_id=a_id,
        version_number=2,
        description="Version 2 update",
        prompt_id=p_id,
        model_id=m_id,
        tool_identifiers=["browser"],
        memory_policy={"type": "summary"},
        created_at=now,
    )
    assert resp.id == v_id
    assert resp.agent_spec_id == a_id
    assert resp.version_number == 2
    assert resp.description == "Version 2 update"
    assert resp.tool_identifiers == ["browser"]
    assert resp.created_at == now


# ---------------------------------------------------------------------------
# 3. Repository Operations with Mock AsyncSession
# ---------------------------------------------------------------------------

class MockAsyncSession:
    """In-memory mock session implementing the AsyncSession subset used by repositories."""

    def __init__(self):
        self.items: dict[UUID, AgentSpec] = {}
        self.versions: dict[UUID, AgentSpecVersion] = {}

    def add(self, obj: Any):
        if isinstance(obj, AgentSpecVersion):
            if getattr(obj, "created_at", None) is None:
                obj.created_at = datetime.now(timezone.utc)
            self.versions[obj.id] = obj
        else:
            if getattr(obj, "created_at", None) is None:
                obj.created_at = datetime.now(timezone.utc)
            if getattr(obj, "updated_at", None) is None:
                obj.updated_at = datetime.now(timezone.utc)
            self.items[obj.id] = obj

    async def commit(self):
        pass

    async def refresh(self, obj: Any):
        pass

    async def delete(self, obj: Any):
        if isinstance(obj, AgentSpecVersion):
            self.versions.pop(obj.id, None)
        else:
            self.items.pop(obj.id, None)

    async def execute(self, statement):
        class MockResult:
            def __init__(self, data, scalar_val=None):
                self._data = data
                self._scalar_val = scalar_val

            def scalar_one_or_none(self):
                return self._data[0] if self._data else None

            def scalar(self):
                return self._scalar_val

            def scalars(self):
                class MockScalars:
                    def __init__(self, items):
                        self._items = items

                    def all(self):
                        return list(self._items)

                return MockScalars(self._data)

        compiled = statement.compile()
        params = compiled.params
        stmt_str = str(statement)

        if "agent_spec_versions" in stmt_str and "max" in stmt_str.lower():
            target_agent_id = None
            for k, v in params.items():
                if "agent_spec_id" in k:
                    target_agent_id = v
                    break
            matching = [
                v.version_number
                for v in self.versions.values()
                if target_agent_id is None or v.agent_spec_id == target_agent_id
            ]
            max_v = max(matching, default=0)
            return MockResult([], scalar_val=max_v)
        elif "agent_spec_versions" in stmt_str:
            target_agent_id = None
            target_id = None
            for k, v in params.items():
                if "agent_spec_id" in k:
                    target_agent_id = v
                elif "id" in k:
                    target_id = v
            matched = [
                v for v in self.versions.values()
                if (target_agent_id is None or v.agent_spec_id == target_agent_id)
                and (target_id is None or v.id == target_id)
            ]
            if "desc" in stmt_str.lower():
                matched.sort(key=lambda x: x.version_number, reverse=True)
            offset_val = getattr(statement, "_offset", None) or 0
            limit_val = getattr(statement, "_limit", None)
            if limit_val is not None:
                matched = matched[offset_val : offset_val + limit_val]
            elif offset_val:
                matched = matched[offset_val:]
            return MockResult(matched)
        return MockResult(list(self.items.values()))


@pytest.mark.asyncio
async def test_agent_spec_repository_in_memory():
    """Verify AgentSpecRepository methods with a mock async session."""
    session = MockAsyncSession()
    repo = AgentSpecRepository(session)

    org_id = uuid4()
    agent_id = uuid4()
    spec = AgentSpec(
        id=agent_id,
        organization_id=org_id,
        name="Repo Test Agent",
        description="Testing repository",
        tool_identifiers=[],
        memory_policy={},
        is_active=True,
    )

    # 1. Create
    created = await repo.create(spec)
    assert created.id == agent_id
    assert agent_id in session.items

    # 2. Update
    created.name = "Repo Test Agent Updated"
    updated = await repo.update(created)
    assert updated.name == "Repo Test Agent Updated"

    # 3. get_for_update
    locked = await repo.get_for_update(agent_id)
    assert locked is not None
    assert locked.id == agent_id

    # 4. Delete
    await repo.delete(updated)
    assert agent_id not in session.items


@pytest.mark.asyncio
async def test_agent_spec_version_repository_in_memory():
    """Verify AgentSpecVersionRepository methods with a mock async session."""
    session = MockAsyncSession()
    repo = AgentSpecVersionRepository(session)

    agent_a = uuid4()
    agent_b = uuid4()

    # 1. Latest version number returns 0 when history is empty
    empty_v = await repo.get_latest_version_number(agent_a)
    assert empty_v == 0

    # 2. Create multiple versions for Agent A
    v1_a = AgentSpecVersion(
        id=uuid4(),
        agent_spec_id=agent_a,
        version_number=1,
        description="Version 1",
        tool_identifiers=["t1"],
        memory_policy={},
    )
    v2_a = AgentSpecVersion(
        id=uuid4(),
        agent_spec_id=agent_a,
        version_number=2,
        description="Version 2",
        tool_identifiers=["t1", "t2"],
        memory_policy={},
    )
    # Create single version for Agent B
    v1_b = AgentSpecVersion(
        id=uuid4(),
        agent_spec_id=agent_b,
        version_number=1,
        description="Agent B v1",
        tool_identifiers=[],
        memory_policy={},
    )

    await repo.create(v1_a)
    await repo.create(v2_a)
    await repo.create(v1_b)

    # 3. Latest version number per agent
    assert await repo.get_latest_version_number(agent_a) == 2
    assert await repo.get_latest_version_number(agent_b) == 1

    # 4. Get by ID and get by agent and ID
    fetched = await repo.get_by_id(v1_a.id)
    assert fetched is not None
    assert fetched.id == v1_a.id

    scoped = await repo.get_by_agent_and_id(agent_a, v2_a.id)
    assert scoped is not None
    assert scoped.version_number == 2

    # Cross-agent ID lookup returns None
    cross_lookup = await repo.get_by_agent_and_id(agent_b, v2_a.id)
    assert cross_lookup is None

    # 5. Descending version ordering and isolation by agent spec
    versions_a = await repo.list_by_agent(agent_a, skip=0, limit=10)
    assert len(versions_a) == 2
    assert [v.version_number for v in versions_a] == [2, 1]

    versions_b = await repo.list_by_agent(agent_b, skip=0, limit=10)
    assert len(versions_b) == 1
    assert versions_b[0].id == v1_b.id

    # Pagination: limit=1
    paginated_a = await repo.list_by_agent(agent_a, skip=1, limit=1)
    assert len(paginated_a) == 1
    assert paginated_a[0].version_number == 1


# ---------------------------------------------------------------------------
# 4. Optional Live Database Session Integration Test
# ---------------------------------------------------------------------------

@pytest.fixture
async def real_db_session():
    """Provides a real database session if available, otherwise skips."""
    from app.core.database import AsyncSessionLocal, engine
    await engine.dispose()
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("Real PostgreSQL database connection not configured/available")

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_agent_spec_persisted_in_real_sqlalchemy_session(real_db_session):
    """Verify persisting AgentSpec in a live PostgreSQL session if connected."""
    from app.models.organization import Organization

    session = real_db_session
    org = Organization(
        name=f"test-agent-org-{uuid4()}",
        slug=f"test-agent-slug-{uuid4()}",
    )
    session.add(org)
    await session.flush()

    spec = AgentSpec(
        organization_id=org.id,
        name=f"Agent-{uuid4()}",
        description="Live DB test",
        tool_identifiers=["search"],
        memory_policy={"type": "buffer"},
    )
    session.add(spec)
    await session.flush()

    assert spec.id is not None
    assert isinstance(spec.created_at, datetime)
    assert spec.created_at.tzinfo is not None
    assert spec.tool_identifiers == ["search"]
    assert spec.memory_policy == {"type": "buffer"}
