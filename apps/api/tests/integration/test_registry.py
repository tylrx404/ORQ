import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient
from fastapi import HTTPException, status

from app.main import app
from app.api.dependencies import (
    get_current_user,
    get_organization_membership_repository,
    get_prompt_repository,
    get_prompt_version_repository,
    get_prompt_service,
    require_prompt_admin,
    require_prompt_member,
)
from app.core.permissions import Permission
from app.models.organization_membership import MembershipRole, OrganizationMembership
from app.models.prompt import Prompt, PromptVersion
from app.models.user import User
from app.services.prompt import (
    DuplicatePromptError,
    PromptNotFoundError,
    PromptService,
    PromptVersionNotFoundError,
)
from sqlalchemy.exc import IntegrityError


class MockPromptRepository:
    def __init__(self):
        self.prompts: dict[UUID, Prompt] = {}
        self.locked_ids: list[UUID] = []

        class MockDB:
            def __init__(self, repo):
                self.repo = repo
                self.rolled_back = False

            def add(self, obj):
                if isinstance(obj, Prompt):
                    if getattr(obj, "created_at", None) is None:
                        obj.created_at = datetime.now(timezone.utc)
                    if getattr(obj, "updated_at", None) is None:
                        obj.updated_at = datetime.now(timezone.utc)
                    self.repo.prompts[obj.id] = obj

            async def flush(self):
                pass

            async def commit(self):
                pass

            async def refresh(self, obj):
                pass

            async def rollback(self):
                self.rolled_back = True

        self.db = MockDB(self)

    async def get_by_id(self, prompt_id: UUID) -> Prompt | None:
        return self.prompts.get(prompt_id)

    async def get_by_id_and_org(self, organization_id: UUID, prompt_id: UUID) -> Prompt | None:
        prompt = self.prompts.get(prompt_id)
        if prompt and prompt.organization_id == organization_id:
            return prompt
        return None

    async def get_by_name_and_org(self, organization_id: UUID, name: str) -> Prompt | None:
        for p in self.prompts.values():
            if p.organization_id == organization_id and p.name == name:
                return p
        return None

    async def list_by_organization(self, organization_id: UUID, skip: int = 0, limit: int = 100):
        items = [p for p in self.prompts.values() if p.organization_id == organization_id]
        return items[skip : skip + limit]

    async def get_for_update(self, prompt_id: UUID) -> Prompt | None:
        self.locked_ids.append(prompt_id)
        return self.prompts.get(prompt_id)

    async def create(self, prompt: Prompt) -> Prompt:
        if getattr(prompt, "created_at", None) is None:
            prompt.created_at = datetime.now(timezone.utc)
        if getattr(prompt, "updated_at", None) is None:
            prompt.updated_at = datetime.now(timezone.utc)
        self.prompts[prompt.id] = prompt
        return prompt

    async def update(self, prompt: Prompt) -> Prompt:
        prompt.updated_at = datetime.now(timezone.utc)
        self.prompts[prompt.id] = prompt
        return prompt

    async def delete(self, prompt: Prompt) -> None:
        self.prompts.pop(prompt.id, None)


class MockPromptVersionRepository:
    def __init__(self):
        self.versions: dict[UUID, PromptVersion] = {}

        class MockDB:
            def __init__(self, repo):
                self.repo = repo
                self.rolled_back = False

            def add(self, obj):
                if isinstance(obj, PromptVersion):
                    if getattr(obj, "created_at", None) is None:
                        obj.created_at = datetime.now(timezone.utc)
                    self.repo.versions[obj.id] = obj

            async def flush(self):
                pass

            async def commit(self):
                pass

            async def refresh(self, obj):
                pass

            async def rollback(self):
                self.rolled_back = True

        self.db = MockDB(self)

    async def get_by_id(self, version_id: UUID) -> PromptVersion | None:
        return self.versions.get(version_id)

    async def get_by_prompt_and_id(self, prompt_id: UUID, version_id: UUID) -> PromptVersion | None:
        version = self.versions.get(version_id)
        if version and version.prompt_id == prompt_id:
            return version
        return None

    async def get_latest_version_number(self, prompt_id: UUID) -> int:
        versions = [v.version_number for v in self.versions.values() if v.prompt_id == prompt_id]
        return max(versions) if versions else 0

    async def list_by_prompt(self, prompt_id: UUID, skip: int = 0, limit: int = 100):
        items = [v for v in self.versions.values() if v.prompt_id == prompt_id]
        items.sort(key=lambda x: x.version_number, reverse=True)
        return items[skip : skip + limit]

    async def create(self, version: PromptVersion) -> PromptVersion:
        version.created_at = datetime.now(timezone.utc)
        self.versions[version.id] = version
        return version


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


@pytest.fixture
def mock_registry_deps():
    prompt_repo = MockPromptRepository()
    version_repo = MockPromptVersionRepository()
    membership_repo = MockMembershipRepository()

    user_a = User(id=uuid4(), email="user_a@example.com", is_active=True)
    org_a = uuid4()
    membership_repo.add_membership(org_a, user_a.id, MembershipRole.owner)

    user_b = User(id=uuid4(), email="user_b@example.com", is_active=True)
    org_b = uuid4()
    membership_repo.add_membership(org_b, user_b.id, MembershipRole.member)

    service = PromptService(prompt_repo, version_repo)

    app.dependency_overrides[get_prompt_repository] = lambda: prompt_repo
    app.dependency_overrides[get_prompt_version_repository] = lambda: version_repo
    app.dependency_overrides[get_organization_membership_repository] = lambda: membership_repo
    app.dependency_overrides[get_prompt_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: user_a

    yield {
        "prompt_repo": prompt_repo,
        "version_repo": version_repo,
        "membership_repo": membership_repo,
        "service": service,
        "org_a": org_a,
        "user_a": user_a,
        "org_b": org_b,
        "user_b": user_b,
    }
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Service & Repository Foundation Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_prompt_creates_version_1_and_publishes_it(mock_registry_deps):
    deps = mock_registry_deps
    service: PromptService = deps["service"]
    org_id = deps["org_a"]

    prompt, v1 = await service.create_prompt(
        organization_id=org_id,
        name="Customer Support Agent",
        initial_content="You are a helpful customer service representative.",
        description="Handles tier 1 support queries",
    )

    assert prompt.name == "Customer Support Agent"
    assert prompt.organization_id == org_id
    assert prompt.published_version_id == v1.id

    assert v1.prompt_id == prompt.id
    assert v1.version_number == 1
    assert v1.content == "You are a helpful customer service representative."


@pytest.mark.asyncio
async def test_create_subsequent_versions_increments_and_does_not_auto_publish(mock_registry_deps):
    deps = mock_registry_deps
    service: PromptService = deps["service"]
    org_id = deps["org_a"]

    prompt, v1 = await service.create_prompt(
        organization_id=org_id,
        name="Summarizer",
        initial_content="Summarize in 3 bullet points.",
    )
    assert prompt.published_version_id == v1.id

    # Create version 2
    v2 = await service.create_version(
        organization_id=org_id,
        prompt_id=prompt.id,
        content="Summarize in 5 bullet points with key metrics.",
    )
    assert v2.version_number == 2
    assert v2.content == "Summarize in 5 bullet points with key metrics."

    # Verify concurrency row lock was called
    assert prompt.id in deps["prompt_repo"].locked_ids

    # Re-fetch prompt to ensure published_version_id remains unchanged (still v1)
    refreshed_prompt = await service.get_prompt(org_id, prompt.id)
    assert refreshed_prompt.published_version_id == v1.id

    # Create version 3
    v3 = await service.create_version(
        organization_id=org_id,
        prompt_id=prompt.id,
        content="Summarize in an executive paragraph.",
    )
    assert v3.version_number == 3

    refreshed_prompt = await service.get_prompt(org_id, prompt.id)
    assert refreshed_prompt.published_version_id == v1.id


@pytest.mark.asyncio
async def test_publish_version_updates_active_version(mock_registry_deps):
    deps = mock_registry_deps
    service: PromptService = deps["service"]
    org_id = deps["org_a"]

    prompt, v1 = await service.create_prompt(
        organization_id=org_id,
        name="Code Reviewer",
        initial_content="Review code for style bugs.",
    )

    v2 = await service.create_version(
        organization_id=org_id,
        prompt_id=prompt.id,
        content="Review code for OWASP vulnerabilities.",
    )
    assert prompt.published_version_id == v1.id

    # Explicitly publish version 2
    published = await service.publish_version(
        organization_id=org_id,
        prompt_id=prompt.id,
        version_id=v2.id,
    )
    assert published.published_version_id == v2.id


@pytest.mark.asyncio
async def test_publish_version_from_another_prompt_fails(mock_registry_deps):
    deps = mock_registry_deps
    service: PromptService = deps["service"]
    org_id = deps["org_a"]

    prompt_1, _ = await service.create_prompt(
        organization_id=org_id,
        name="Prompt 1",
        initial_content="Content 1",
    )
    _, v2_of_prompt_2 = await service.create_prompt(
        organization_id=org_id,
        name="Prompt 2",
        initial_content="Content 2",
    )

    # Attempting to publish v2_of_prompt_2 for prompt_1 must fail
    with pytest.raises(PromptVersionNotFoundError):
        await service.publish_version(
            organization_id=org_id,
            prompt_id=prompt_1.id,
            version_id=v2_of_prompt_2.id,
        )


@pytest.mark.asyncio
async def test_duplicate_prompt_name_in_same_org_fails(mock_registry_deps):
    deps = mock_registry_deps
    service: PromptService = deps["service"]
    org_id = deps["org_a"]

    await service.create_prompt(
        organization_id=org_id,
        name="Unique Name",
        initial_content="Content A",
    )

    with pytest.raises(DuplicatePromptError):
        await service.create_prompt(
            organization_id=org_id,
            name="Unique Name",
            initial_content="Content B",
        )


@pytest.mark.asyncio
async def test_same_prompt_name_in_different_orgs_succeeds(mock_registry_deps):
    deps = mock_registry_deps
    service: PromptService = deps["service"]

    prompt_a, _ = await service.create_prompt(
        organization_id=deps["org_a"],
        name="Shared Name",
        initial_content="Content in Org A",
    )

    prompt_b, _ = await service.create_prompt(
        organization_id=deps["org_b"],
        name="Shared Name",
        initial_content="Content in Org B",
    )

    assert prompt_a.id != prompt_b.id
    assert prompt_a.organization_id == deps["org_a"]
    assert prompt_b.organization_id == deps["org_b"]


# ---------------------------------------------------------------------------
# HTTP Endpoints Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_http_create_and_get_prompt(mock_registry_deps):
    deps = mock_registry_deps
    org_id = str(deps["org_a"])

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.post(
            f"/api/v1/registry/prompts?organization_id={org_id}",
            json={
                "name": "SQL Generator",
                "description": "Translates plain text to PostgreSQL queries",
                "initial_content": "Generate strictly standard ANSI SQL.",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "SQL Generator"
        prompt_id = data["id"]
        published_v_id = data["published_version_id"]
        assert published_v_id is not None

        # Fetch prompt
        get_res = await ac.get(f"/api/v1/registry/prompts/{prompt_id}")
        assert get_res.status_code == 200
        assert get_res.json()["name"] == "SQL Generator"


@pytest.mark.asyncio
async def test_http_duplicate_prompt_returns_409(mock_registry_deps):
    deps = mock_registry_deps
    org_id = str(deps["org_a"])

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        await ac.post(
            f"/api/v1/registry/prompts?organization_id={org_id}",
            json={"name": "Translator", "initial_content": "Translate to Spanish."},
        )
        dup_res = await ac.post(
            f"/api/v1/registry/prompts?organization_id={org_id}",
            json={"name": "Translator", "initial_content": "Translate to French."},
        )
        assert dup_res.status_code == 409


@pytest.mark.asyncio
async def test_http_versions_lifecycle_and_publish(mock_registry_deps):
    deps = mock_registry_deps
    org_id = str(deps["org_a"])

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Create prompt
        create_res = await ac.post(
            f"/api/v1/registry/prompts?organization_id={org_id}",
            json={"name": "Grammar Checker", "initial_content": "Fix spelling and punctuation."},
        )
        prompt_id = create_res.json()["id"]
        v1_id = create_res.json()["published_version_id"]

        # 2. Add version 2
        v2_res = await ac.post(
            f"/api/v1/registry/prompts/{prompt_id}/versions",
            json={"content": "Fix spelling, punctuation, and style tone."},
        )
        assert v2_res.status_code == 201
        v2_data = v2_res.json()
        assert v2_data["version_number"] == 2
        v2_id = v2_data["id"]

        # Verify active version is still v1
        get_prompt = await ac.get(f"/api/v1/registry/prompts/{prompt_id}")
        assert get_prompt.json()["published_version_id"] == v1_id

        # 3. List versions
        versions_list_res = await ac.get(f"/api/v1/registry/prompts/{prompt_id}/versions")
        assert versions_list_res.status_code == 200
        versions = versions_list_res.json()
        assert len(versions) == 2

        # 4. Publish version 2 via dedicated endpoint
        publish_res = await ac.post(
            f"/api/v1/registry/prompts/{prompt_id}/versions/{v2_id}/publish"
        )
        assert publish_res.status_code == 200
        assert publish_res.json()["published_version_id"] == v2_id


@pytest.mark.asyncio
async def test_http_version_immutability(mock_registry_deps):
    deps = mock_registry_deps
    org_id = str(deps["org_a"])

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        create_res = await ac.post(
            f"/api/v1/registry/prompts?organization_id={org_id}",
            json={"name": "Immutable Test", "initial_content": "Original Content"},
        )
        prompt_id = create_res.json()["id"]
        v1_id = create_res.json()["published_version_id"]

        # PUT or PATCH on version endpoint must be 405 Method Not Allowed
        put_res = await ac.put(
            f"/api/v1/registry/prompts/{prompt_id}/versions/{v1_id}",
            json={"content": "Modified Content"},
        )
        assert put_res.status_code == 405

        patch_res = await ac.patch(
            f"/api/v1/registry/prompts/{prompt_id}/versions/{v1_id}",
            json={"content": "Modified Content"},
        )
        assert patch_res.status_code == 405


@pytest.mark.asyncio
async def test_http_cross_organization_isolation(mock_registry_deps):
    deps = mock_registry_deps
    user_b = deps["user_b"]
    org_a = deps["org_a"]

    # Create prompt in Org A by user A
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.post(
            f"/api/v1/registry/prompts?organization_id={str(org_a)}",
            json={"name": "Org A Confidential", "initial_content": "Internal secret prompt."},
        )
        prompt_id = res.json()["id"]

    # Switch current user to User B (who is only a member of Org B, NOT Org A)
    app.dependency_overrides[get_current_user] = lambda: user_b

    # User B attempting to read, update, delete, or create versions for Org A's prompt must fail with 404
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        get_res = await ac.get(f"/api/v1/registry/prompts/{prompt_id}")
        assert get_res.status_code == 404

        patch_res = await ac.patch(
            f"/api/v1/registry/prompts/{prompt_id}",
            json={"name": "Hacked"},
        )
        assert patch_res.status_code == 404

        delete_res = await ac.delete(f"/api/v1/registry/prompts/{prompt_id}")
        assert delete_res.status_code == 404

        post_version_res = await ac.post(
            f"/api/v1/registry/prompts/{prompt_id}/versions",
            json={"content": "Injected version"},
        )
        assert post_version_res.status_code == 404


@pytest.mark.asyncio
async def test_concurrent_duplicate_prompt_integrity_error_rollback(mock_registry_deps):
    """Simulate a concurrency race where unique constraint fails during DB commit."""
    deps = mock_registry_deps
    service: PromptService = deps["service"]
    org_id = deps["org_a"]
    prompt_repo = deps["prompt_repo"]

    # Mock commit to raise IntegrityError for uq_prompts_organization_id_name
    async def mock_commit_integrity_error():
        raise IntegrityError(
            "duplicate key value violates unique constraint \"uq_prompts_organization_id_name\"",
            params=None,
            orig=Exception("duplicate key"),
        )

    prompt_repo.db.commit = mock_commit_integrity_error

    with pytest.raises(DuplicatePromptError) as exc_info:
        await service.create_prompt(
            organization_id=org_id,
            name="Race Condition Prompt",
            initial_content="Content",
        )

    assert "already exists in this organization" in str(exc_info.value)
    assert prompt_repo.db.rolled_back is True


@pytest.mark.asyncio
async def test_unrelated_integrity_error_is_re_raised(mock_registry_deps):
    """Unrelated database IntegrityErrors must be re-raised and transaction rolled back."""
    deps = mock_registry_deps
    service: PromptService = deps["service"]
    org_id = deps["org_a"]
    prompt_repo = deps["prompt_repo"]

    # Mock commit to raise an unrelated IntegrityError
    async def mock_commit_unrelated_error():
        raise IntegrityError(
            "insert or update on table \"prompts\" violates foreign key constraint \"fk_some_other_table\"",
            params=None,
            orig=Exception("foreign key violation"),
        )

    prompt_repo.db.commit = mock_commit_unrelated_error

    with pytest.raises(IntegrityError):
        await service.create_prompt(
            organization_id=org_id,
            name="Unrelated Error Prompt",
            initial_content="Content",
        )

    assert prompt_repo.db.rolled_back is True


@pytest.mark.asyncio
async def test_update_prompt_race_condition_integrity_error_rollback(mock_registry_deps):
    """Updating a prompt name that collides in a concurrent race rolls back and raises DuplicatePromptError."""
    deps = mock_registry_deps
    service: PromptService = deps["service"]
    org_id = deps["org_a"]
    prompt_repo = deps["prompt_repo"]

    prompt, _ = await service.create_prompt(
        organization_id=org_id,
        name="Original Name",
        initial_content="Initial content",
    )

    # Mock update to raise IntegrityError for uq_prompts_organization_id_name
    async def mock_update_integrity_error(p):
        raise IntegrityError(
            "duplicate key value violates unique constraint \"uq_prompts_organization_id_name\"",
            params=None,
            orig=Exception("duplicate key"),
        )

    prompt_repo.update = mock_update_integrity_error

    with pytest.raises(DuplicatePromptError):
        await service.update_prompt(
            organization_id=org_id,
            prompt_id=prompt.id,
            update_data={"name": "Conflicting Name"},
        )

    assert prompt_repo.db.rolled_back is True


@pytest.mark.asyncio
async def test_invalid_x_organization_id_header_returns_422(mock_registry_deps):
    """Invalid X-Organization-Id header value must return FastAPI 422 Unprocessable Entity."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. POST /api/v1/registry/prompts with invalid header
        post_res = await ac.post(
            "/api/v1/registry/prompts",
            headers={"X-Organization-Id": "not-a-valid-uuid"},
            json={
                "name": "Invalid Header Prompt",
                "initial_content": "Content",
            },
        )
        assert post_res.status_code == 422

        # 2. GET /api/v1/registry/prompts with invalid header
        get_res = await ac.get(
            "/api/v1/registry/prompts",
            headers={"X-Organization-Id": "not-a-valid-uuid"},
        )
        assert get_res.status_code == 422


@pytest.mark.asyncio
async def test_valid_x_organization_id_header_succeeds(mock_registry_deps):
    """Valid X-Organization-Id header value is accepted and processed cleanly."""
    deps = mock_registry_deps
    org_id = deps["org_a"]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        post_res = await ac.post(
            "/api/v1/registry/prompts",
            headers={"X-Organization-Id": str(org_id)},
            json={
                "name": "Valid Header Prompt",
                "initial_content": "Content",
            },
        )
        assert post_res.status_code == 201
        assert post_res.json()["organization_id"] == str(org_id)

        get_res = await ac.get(
            "/api/v1/registry/prompts",
            headers={"X-Organization-Id": str(org_id)},
        )
        assert get_res.status_code == 200
        assert len(get_res.json()) >= 1


# ---------------------------------------------------------------------------
# Real SQLAlchemy Session Persistence & Model Default Tests
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
async def test_prompt_and_version_direct_persistence_evaluates_defaults(real_db_session):
    """Verify that persisting Prompt and PromptVersion evaluates timestamp defaults in a real session."""
    from app.models.organization import Organization

    session = real_db_session
    org = Organization(
        name=f"test-registry-org-{uuid4()}",
        slug=f"test-registry-slug-{uuid4()}",
    )
    session.add(org)
    await session.flush()

    # Insert Prompt without specifying created_at or updated_at
    prompt = Prompt(
        organization_id=org.id,
        name=f"Direct Model Prompt-{uuid4()}",
        description="Evaluating defaults",
    )
    session.add(prompt)
    await session.flush()

    assert prompt.id is not None
    assert isinstance(prompt.created_at, datetime)
    assert isinstance(prompt.updated_at, datetime)
    assert prompt.created_at.tzinfo is not None
    assert prompt.updated_at.tzinfo is not None

    # Insert PromptVersion without specifying created_at
    version = PromptVersion(
        prompt_id=prompt.id,
        version_number=1,
        content="Direct model version content",
    )
    session.add(version)
    await session.flush()

    assert version.id is not None
    assert isinstance(version.created_at, datetime)
    assert version.created_at.tzinfo is not None

    # Link published_version_id
    prompt.published_version_id = version.id
    await session.flush()
    assert prompt.published_version_id == version.id


@pytest.mark.asyncio
async def test_prompt_and_version_persisted_in_real_sqlalchemy_session(real_db_session):
    """Verify persisting Prompt and PromptVersion via a real SQLAlchemy AsyncSession against PostgreSQL.

    Evaluates server-side defaults, model-level defaults, unique constraints, and foreign key relations.
    """
    from app.models.organization import Organization
    from app.repositories.prompt_repository import PromptRepository, PromptVersionRepository

    session = real_db_session
    # 1. Create Organization
    org = Organization(
        name=f"test-registry-org-{uuid4()}",
        slug=f"test-registry-slug-{uuid4()}",
    )
    session.add(org)
    await session.flush()

    prompt_repo = PromptRepository(session)
    version_repo = PromptVersionRepository(session)
    real_service = PromptService(prompt_repo, version_repo)

    # 2. Persist Prompt and initial Version 1 via service
    prompt, v1 = await real_service.create_prompt(
        organization_id=org.id,
        name="Real DB Prompt",
        initial_content="Initial real DB content",
        description="Testing real DB defaults",
    )

    assert prompt.id is not None
    assert isinstance(prompt.created_at, datetime)
    assert isinstance(prompt.updated_at, datetime)
    assert prompt.created_at.tzinfo is not None
    assert prompt.published_version_id == v1.id

    assert v1.id is not None
    assert v1.version_number == 1
    assert isinstance(v1.created_at, datetime)
    assert v1.created_at.tzinfo is not None

    # 3. Create Version 2 with row lock
    v2 = await real_service.create_version(
        organization_id=org.id,
        prompt_id=prompt.id,
        content="Second real DB content",
    )
    assert v2.version_number == 2
    assert v2.id is not None
    assert isinstance(v2.created_at, datetime)

    # Verify published_version_id is still v1
    refreshed = await real_service.get_prompt(org.id, prompt.id)
    assert refreshed.published_version_id == v1.id

    # 4. Publish Version 2
    published = await real_service.publish_version(
        organization_id=org.id,
        prompt_id=prompt.id,
        version_id=v2.id,
    )
    assert published.published_version_id == v2.id
