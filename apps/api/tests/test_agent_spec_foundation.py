import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.models.agent_spec import AgentSpec
from app.schemas.agent_spec import (
    AgentSpecCreateRequest,
    AgentSpecResponse,
    AgentSpecUpdateRequest,
)
from app.repositories.agent_spec_repository import AgentSpecRepository


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


# ---------------------------------------------------------------------------
# 2. Pydantic Schemas Tests
# ---------------------------------------------------------------------------

def test_agent_spec_create_request_minimal_defaults():
    """Verify create request defaults for tools, memory, and active status."""
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
    """Verify create request with explicit values for all fields."""
    org_id = uuid4()
    prompt_id = uuid4()
    version_id = uuid4()
    provider_id = uuid4()
    model_id = uuid4()

    req = AgentSpecCreateRequest(
        name="Full Agent",
        description="Comprehensive agent configuration",
        organization_id=org_id,
        prompt_id=prompt_id,
        prompt_version_id=version_id,
        provider_id=provider_id,
        model_id=model_id,
        tool_identifiers=["web_search", "calculator"],
        memory_policy={"type": "sliding_window", "window_size": 20},
        is_active=False,
    )
    assert req.name == "Full Agent"
    assert req.organization_id == org_id
    assert req.prompt_id == prompt_id
    assert req.prompt_version_id == version_id
    assert req.provider_id == provider_id
    assert req.model_id == model_id
    assert req.tool_identifiers == ["web_search", "calculator"]
    assert req.memory_policy["type"] == "sliding_window"
    assert req.is_active is False


def test_agent_spec_create_request_validation():
    """Verify name is required and cannot be empty."""
    with pytest.raises(ValidationError):
        AgentSpecCreateRequest(name="")


def test_agent_spec_update_request_omitted_fields():
    """Verify omitted fields are excluded when dumping with exclude_unset=True."""
    update_req = AgentSpecUpdateRequest()
    dumped = update_req.model_dump(exclude_unset=True)
    assert dumped == {}


def test_agent_spec_update_request_valid_partial():
    """Verify update request allows partial updates and excludes unset fields."""
    update_req = AgentSpecUpdateRequest(
        name="Updated Name",
        tool_identifiers=["new_tool"],
        memory_policy={"type": "summary"},
        is_active=False,
    )
    dumped = update_req.model_dump(exclude_unset=True)
    assert dumped == {
        "name": "Updated Name",
        "tool_identifiers": ["new_tool"],
        "memory_policy": {"type": "summary"},
        "is_active": False,
    }
    assert "description" not in dumped
    assert "prompt_id" not in dumped


@pytest.mark.parametrize("field_name", ["name", "tool_identifiers", "memory_policy", "is_active"])
def test_agent_spec_update_request_rejects_null_for_non_nullable_fields(field_name):
    """Verify explicitly supplied null is rejected for non-nullable fields."""
    with pytest.raises(ValidationError) as exc_info:
        AgentSpecUpdateRequest(**{field_name: None})
    errors = exc_info.value.errors()
    assert any(field_name in err["loc"] for err in errors)


def test_agent_spec_update_request_accepts_null_for_nullable_fields():
    """Verify explicit null is accepted for nullable database fields and captured in dumped dict."""
    update_req = AgentSpecUpdateRequest(
        description=None,
        prompt_id=None,
        prompt_version_id=None,
        provider_id=None,
        model_id=None,
    )
    dumped = update_req.model_dump(exclude_unset=True)
    assert dumped == {
        "description": None,
        "prompt_id": None,
        "prompt_version_id": None,
        "provider_id": None,
        "model_id": None,
    }
    assert "name" not in dumped
    assert "tool_identifiers" not in dumped
    assert "memory_policy" not in dumped
    assert "is_active" not in dumped


def test_agent_spec_response_serialization():
    """Verify response model serialization from ORM attributes."""
    agent_id = uuid4()
    org_id = uuid4()
    now = datetime.now(timezone.utc)

    spec = AgentSpec(
        id=agent_id,
        organization_id=org_id,
        name="Serialized Agent",
        description="Test desc",
        prompt_id=None,
        prompt_version_id=None,
        provider_id=None,
        model_id=None,
        tool_identifiers=["bash"],
        memory_policy={"max_tokens": 2000},
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    resp = AgentSpecResponse.model_validate(spec)
    assert resp.id == agent_id
    assert resp.organization_id == org_id
    assert resp.name == "Serialized Agent"
    assert resp.tool_identifiers == ["bash"]
    assert resp.memory_policy == {"max_tokens": 2000}
    assert resp.created_at == now


# ---------------------------------------------------------------------------
# 3. Repository CRUD Operations with Mock AsyncSession
# ---------------------------------------------------------------------------

class MockAsyncSession:
    """In-memory mock session implementing the AsyncSession subset used by repositories."""

    def __init__(self):
        self.items: dict[UUID, AgentSpec] = {}

    def add(self, obj: AgentSpec):
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(timezone.utc)
        if getattr(obj, "updated_at", None) is None:
            obj.updated_at = datetime.now(timezone.utc)
        self.items[obj.id] = obj

    async def commit(self):
        pass

    async def refresh(self, obj: Any):
        pass

    async def delete(self, obj: AgentSpec):
        self.items.pop(obj.id, None)

    async def execute(self, statement):
        class MockResult:
            def __init__(self, data):
                self._data = data

            def scalar_one_or_none(self):
                return self._data[0] if self._data else None

            def scalars(self):
                class MockScalars:
                    def __init__(self, items):
                        self._items = items

                    def all(self):
                        return list(self._items)

                return MockScalars(self._data)

        # Basic query inspection for the mock
        stmt_str = str(statement)
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

    # 3. Delete
    await repo.delete(updated)
    assert agent_id not in session.items


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
