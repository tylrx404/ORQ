import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_spec import AgentSpec, AgentSpecVersion
from app.repositories.agent_spec_repository import AgentSpecRepository
from app.repositories.agent_spec_version_repository import AgentSpecVersionRepository
from app.repositories.prompt_repository import PromptRepository, PromptVersionRepository
from app.repositories.provider_model_repository import ProviderModelRepository
from app.repositories.provider_repository import ProviderRepository

logger = logging.getLogger(__name__)


class AgentSpecException(Exception):
    """Base exception for agent specification domain operations."""
    pass


class AgentSpecNotFoundError(AgentSpecException):
    """Raised when an agent spec does not exist or does not belong to the organization."""
    pass


class AgentSpecVersionNotFoundError(AgentSpecException):
    """Raised when an agent spec version does not exist or does not belong to the agent spec."""
    pass


class DuplicateAgentSpecError(AgentSpecException):
    """Raised when an agent spec with the same name already exists in the organization."""
    pass


class InvalidPromptReferenceError(AgentSpecException):
    """Raised when a referenced prompt does not exist or does not belong to the organization."""
    pass


class InvalidPromptVersionReferenceError(AgentSpecException):
    """Raised when a referenced prompt version does not exist or does not belong to the prompt/organization."""
    pass


class InvalidProviderReferenceError(AgentSpecException):
    """Raised when a referenced provider does not exist or does not belong to the organization."""
    pass


class InvalidModelReferenceError(AgentSpecException):
    """Raised when a referenced model does not exist or does not belong to the provider/organization."""
    pass


_UNSET: Any = object()


class _InMemoryVersionRepo:
    """Fallback in-memory version repository when no database session or repo is provided."""

    def __init__(self):
        self.versions: dict[UUID, AgentSpecVersion] = {}

    async def get_by_id(self, version_id: UUID) -> AgentSpecVersion | None:
        return self.versions.get(version_id)

    async def get_by_agent_and_id(self, agent_spec_id: UUID, version_id: UUID) -> AgentSpecVersion | None:
        v = self.versions.get(version_id)
        if v and v.agent_spec_id == agent_spec_id:
            return v
        return None

    async def get_by_version_number(self, agent_spec_id: UUID, version_number: int) -> AgentSpecVersion | None:
        for v in self.versions.values():
            if v.agent_spec_id == agent_spec_id and v.version_number == version_number:
                return v
        return None

    async def get_latest_version_number(self, agent_spec_id: UUID) -> int:
        matching = [v.version_number for v in self.versions.values() if v.agent_spec_id == agent_spec_id]
        return max(matching) if matching else 0

    async def list_by_agent(
        self, agent_spec_id: UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[AgentSpecVersion]:
        matching = [v for v in self.versions.values() if v.agent_spec_id == agent_spec_id]
        matching.sort(key=lambda x: x.version_number, reverse=True)
        return matching[skip : skip + limit]

    async def create(self, version: AgentSpecVersion) -> AgentSpecVersion:
        if getattr(version, "created_at", None) is None:
            version.created_at = datetime.now(timezone.utc)
        self.versions[version.id] = version
        return version


class AgentSpecService:
    """Business logic for AgentSpec and AgentSpecVersion entities."""

    def __init__(
        self,
        agent_spec_repository: AgentSpecRepository,
        prompt_repository: PromptRepository,
        prompt_version_repository: PromptVersionRepository,
        provider_repository: ProviderRepository,
        provider_model_repository: ProviderModelRepository,
        agent_spec_version_repository: AgentSpecVersionRepository | None = None,
    ):
        self._agent_spec_repo = agent_spec_repository
        self._prompt_repo = prompt_repository
        self._prompt_version_repo = prompt_version_repository
        self._provider_repo = provider_repository
        self._model_repo = provider_model_repository
        self._version_repo = agent_spec_version_repository or (
            getattr(agent_spec_repository, "version_repo", None)
            or (
                AgentSpecVersionRepository(agent_spec_repository.db)
                if hasattr(agent_spec_repository, "db") and isinstance(agent_spec_repository.db, AsyncSession)
                else _InMemoryVersionRepo()
            )
        )

    def _db_add(self, obj: Any) -> None:
        now = datetime.now(timezone.utc)
        if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
            obj.created_at = now
        if hasattr(obj, "updated_at") and getattr(obj, "updated_at", None) is None:
            obj.updated_at = now
        if hasattr(self._agent_spec_repo, "db") and hasattr(self._agent_spec_repo.db, "add"):
            self._agent_spec_repo.db.add(obj)
        elif hasattr(self._agent_spec_repo, "items") and hasattr(obj, "id"):
            self._agent_spec_repo.items[obj.id] = obj

    async def _db_flush(self) -> None:
        if hasattr(self._agent_spec_repo, "db") and hasattr(self._agent_spec_repo.db, "flush"):
            res = self._agent_spec_repo.db.flush()
            if hasattr(res, "__await__"):
                await res

    async def _db_commit(self) -> None:
        if hasattr(self._agent_spec_repo, "db") and hasattr(self._agent_spec_repo.db, "commit"):
            res = self._agent_spec_repo.db.commit()
            if hasattr(res, "__await__"):
                await res

    async def _db_refresh(self, obj: Any) -> None:
        if hasattr(self._agent_spec_repo, "db") and hasattr(self._agent_spec_repo.db, "refresh"):
            res = self._agent_spec_repo.db.refresh(obj)
            if hasattr(res, "__await__"):
                await res

    async def _db_rollback(self) -> None:
        if hasattr(self._agent_spec_repo, "db") and hasattr(self._agent_spec_repo.db, "rollback"):
            try:
                res = self._agent_spec_repo.db.rollback()
                if hasattr(res, "__await__"):
                    await res
            except Exception as e:
                # Do not allow secondary rollback failures (e.g. broken connection) to mask the original exception
                logger.warning("Database rollback failed during exception handling: %s", e)

    async def _get_locked_agent(self, agent_id: UUID) -> AgentSpec | None:
        if hasattr(self._agent_spec_repo, "get_for_update"):
            return await self._agent_spec_repo.get_for_update(agent_id)
        return await self._agent_spec_repo.get_by_id(agent_id)

    async def _validate_references(
        self,
        organization_id: UUID,
        prompt_id: UUID | None,
        prompt_version_id: UUID | None,
        provider_id: UUID | None,
        model_id: UUID | None,
    ) -> tuple[UUID | None, UUID | None, UUID | None, UUID | None]:
        """Validate foreign entity references against organization tenancy and relational consistency."""
        # --- 1. Prompt & PromptVersion Validation ---
        if prompt_version_id is not None and prompt_id is None:
            version = await self._prompt_version_repo.get_by_id(prompt_version_id)
            if not version:
                raise InvalidPromptVersionReferenceError(
                    f"Prompt version with ID '{prompt_version_id}' was not found."
                )
            parent_prompt = await self._prompt_repo.get_by_id_and_org(organization_id, version.prompt_id)
            if not parent_prompt:
                raise InvalidPromptVersionReferenceError(
                    f"Prompt version with ID '{prompt_version_id}' does not belong to this organization."
                )
            prompt_id = version.prompt_id
        elif prompt_id is not None:
            prompt = await self._prompt_repo.get_by_id_and_org(organization_id, prompt_id)
            if not prompt:
                raise InvalidPromptReferenceError(
                    f"Prompt with ID '{prompt_id}' was not found in this organization."
                )
            if prompt_version_id is not None:
                version = await self._prompt_version_repo.get_by_prompt_and_id(prompt_id, prompt_version_id)
                if not version:
                    raise InvalidPromptVersionReferenceError(
                        f"Prompt version with ID '{prompt_version_id}' does not belong to prompt '{prompt_id}'."
                    )

        # --- 2. Provider & Model Validation ---
        if model_id is not None:
            model = await self._model_repo.get_by_id(model_id)
            if not model:
                raise InvalidModelReferenceError(f"Model with ID '{model_id}' was not found.")

            model_provider = await self._provider_repo.get_by_id(model.provider_id)
            if not model_provider or model_provider.organization_id != organization_id:
                raise InvalidModelReferenceError(
                    f"Model with ID '{model_id}' does not belong to this organization."
                )

            if provider_id is not None and provider_id != model.provider_id:
                raise InvalidModelReferenceError(
                    f"Model with ID '{model_id}' does not belong to provider '{provider_id}'."
                )
            provider_id = model.provider_id

        if provider_id is not None and model_id is None:
            provider = await self._provider_repo.get_by_id(provider_id)
            if not provider or provider.organization_id != organization_id:
                raise InvalidProviderReferenceError(
                    f"Provider with ID '{provider_id}' was not found in this organization."
                )

        return prompt_id, prompt_version_id, provider_id, model_id

    async def create_agent_spec(
        self,
        organization_id: UUID,
        name: str,
        description: str | None = None,
        prompt_id: UUID | None = None,
        prompt_version_id: UUID | None = None,
        provider_id: UUID | None = None,
        model_id: UUID | None = None,
        tool_identifiers: list[str] | None = None,
        memory_policy: dict[str, Any] | None = None,
        is_active: bool = True,
        version_description: str | None = None,
    ) -> AgentSpec:
        """Create a new AgentSpec after validating unique name and entity references, atomically generating Version 1."""
        try:
            existing = await self._agent_spec_repo.get_by_name_and_org(organization_id, name)
            if existing:
                raise DuplicateAgentSpecError(
                    f"An agent specification named '{name}' already exists in this organization."
                )

            resolved_prompt_id, resolved_version_id, resolved_provider_id, resolved_model_id = (
                await self._validate_references(
                    organization_id=organization_id,
                    prompt_id=prompt_id,
                    prompt_version_id=prompt_version_id,
                    provider_id=provider_id,
                    model_id=model_id,
                )
            )

            agent_id = uuid.uuid4()
            version_id = uuid.uuid4()
            now = datetime.now(timezone.utc)

            tools = list(tool_identifiers) if tool_identifiers is not None else []
            memory = dict(memory_policy) if memory_policy is not None else {}

            agent_spec = AgentSpec(
                id=agent_id,
                organization_id=organization_id,
                name=name,
                description=description,
                prompt_id=resolved_prompt_id,
                prompt_version_id=resolved_version_id,
                provider_id=resolved_provider_id,
                model_id=resolved_model_id,
                tool_identifiers=tools,
                memory_policy=memory,
                is_active=is_active,
                current_version_id=None,
                created_at=now,
                updated_at=now,
            )

            v1_desc = version_description if version_description is not None else "Initial version"
            version_1 = AgentSpecVersion(
                id=version_id,
                agent_spec_id=agent_id,
                version_number=1,
                description=v1_desc,
                prompt_id=resolved_prompt_id,
                prompt_version_id=resolved_version_id,
                provider_id=resolved_provider_id,
                model_id=resolved_model_id,
                tool_identifiers=list(tools),
                memory_policy=dict(memory),
                created_at=now,
            )

            self._db_add(agent_spec)
            await self._db_flush()

            await self._version_repo.create(version_1)

            agent_spec.current_version_id = version_1.id
            agent_spec.current_version = version_1
            agent_spec.current_version_number = 1

            await self._db_commit()
            await self._db_refresh(agent_spec)
            agent_spec.current_version = version_1
            agent_spec.current_version_number = 1
            return agent_spec
        except IntegrityError as e:
            await self._db_rollback()
            if "uq_agent_specs_organization_id_name" in str(e).lower():
                raise DuplicateAgentSpecError(
                    f"An agent specification named '{name}' already exists in this organization."
                ) from e
            raise
        except Exception:
            await self._db_rollback()
            raise

    async def get_agent_spec(self, organization_id: UUID, agent_id: UUID) -> AgentSpec:
        """Retrieve an AgentSpec scoped to an organization."""
        spec = await self._agent_spec_repo.get_by_id_and_org(organization_id, agent_id)
        if not spec:
            raise AgentSpecNotFoundError(
                f"Agent specification with ID '{agent_id}' not found."
            )
        return spec

    async def list_agent_specs(
        self,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
    ) -> Sequence[AgentSpec]:
        """List all agent specs for an organization with pagination and optional status filter."""
        return await self._agent_spec_repo.list_by_organization(
            organization_id=organization_id,
            skip=skip,
            limit=limit,
            is_active=is_active,
        )

    async def update_agent_spec(
        self,
        organization_id: UUID,
        agent_id: UUID,
        update_data: dict[str, Any],
    ) -> AgentSpec:
        """Apply partial updates to an AgentSpec.

        If execution-affecting configuration changes, generates the next sequential
        version atomically. If metadata-only changes occur, preserves the existing version.
        Handles legacy unversioned agents by creating Version 1 on their first configuration mutation.
        """
        try:
            locked_agent = await self._get_locked_agent(agent_id)
            if not locked_agent or locked_agent.organization_id != organization_id:
                raise AgentSpecNotFoundError(
                    f"Agent specification with ID '{agent_id}' not found."
                )

            # 1. Name uniqueness validation
            if "name" in update_data and update_data["name"] is not None and update_data["name"] != locked_agent.name:
                new_name = update_data["name"]
                existing = await self._agent_spec_repo.get_by_name_and_org(organization_id, new_name)
                if existing and existing.id != locked_agent.id:
                    raise DuplicateAgentSpecError(
                        f"An agent specification named '{new_name}' already exists in this organization."
                    )
                locked_agent.name = new_name

            # 2. Determine effective relational references
            if "prompt_id" in update_data:
                effective_prompt_id = update_data["prompt_id"]
            else:
                effective_prompt_id = locked_agent.prompt_id

            if "prompt_version_id" in update_data:
                effective_prompt_version_id = update_data["prompt_version_id"]
            else:
                effective_prompt_version_id = locked_agent.prompt_version_id

            # If prompt_id was explicitly cleared to None and version wasn't specified in update, clear version too
            if "prompt_id" in update_data and update_data["prompt_id"] is None and "prompt_version_id" not in update_data:
                effective_prompt_version_id = None

            if "provider_id" in update_data:
                effective_provider_id = update_data["provider_id"]
            else:
                effective_provider_id = locked_agent.provider_id

            if "model_id" in update_data:
                effective_model_id = update_data["model_id"]
            else:
                effective_model_id = locked_agent.model_id

            # If provider_id was explicitly cleared to None and model wasn't specified in update, clear model too
            if "provider_id" in update_data and update_data["provider_id"] is None and "model_id" not in update_data:
                effective_model_id = None

            resolved_prompt_id, resolved_version_id, resolved_provider_id, resolved_model_id = (
                await self._validate_references(
                    organization_id=organization_id,
                    prompt_id=effective_prompt_id,
                    prompt_version_id=effective_prompt_version_id,
                    provider_id=effective_provider_id,
                    model_id=effective_model_id,
                )
            )

            if "tool_identifiers" in update_data:
                effective_tools = list(update_data["tool_identifiers"] or [])
            else:
                effective_tools = list(locked_agent.tool_identifiers or [])

            if "memory_policy" in update_data:
                effective_memory = dict(update_data["memory_policy"] or {})
            else:
                effective_memory = dict(locked_agent.memory_policy or {})

            config_changed = (
                resolved_prompt_id != locked_agent.prompt_id
                or resolved_version_id != locked_agent.prompt_version_id
                or resolved_provider_id != locked_agent.provider_id
                or resolved_model_id != locked_agent.model_id
                or effective_tools != list(locked_agent.tool_identifiers or [])
                or effective_memory != dict(locked_agent.memory_policy or {})
            )

            now = datetime.now(timezone.utc)
            new_version = None
            next_version_num = None

            if config_changed:
                latest_v = await self._version_repo.get_latest_version_number(agent_id)
                if latest_v == 0 or locked_agent.current_version_id is None:
                    next_version_num = 1
                    v_desc = (
                        update_data.get("version_description")
                        or "Initial version from legacy configuration"
                    )
                else:
                    next_version_num = latest_v + 1
                    v_desc = (
                        update_data.get("version_description")
                        or f"Update to version {next_version_num}"
                    )

                new_version = AgentSpecVersion(
                    id=uuid.uuid4(),
                    agent_spec_id=locked_agent.id,
                    version_number=next_version_num,
                    description=v_desc,
                    prompt_id=resolved_prompt_id,
                    prompt_version_id=resolved_version_id,
                    provider_id=resolved_provider_id,
                    model_id=resolved_model_id,
                    tool_identifiers=list(effective_tools),
                    memory_policy=dict(effective_memory),
                    created_at=now,
                )

            # 3. Apply updates to entity
            locked_agent.prompt_id = resolved_prompt_id
            locked_agent.prompt_version_id = resolved_version_id
            locked_agent.provider_id = resolved_provider_id
            locked_agent.model_id = resolved_model_id
            locked_agent.tool_identifiers = effective_tools
            locked_agent.memory_policy = effective_memory
            locked_agent.updated_at = now

            if "description" in update_data:
                locked_agent.description = update_data["description"]
            if "is_active" in update_data and update_data["is_active"] is not None:
                locked_agent.is_active = update_data["is_active"]

            if config_changed and new_version is not None:
                await self._version_repo.create(new_version)

                locked_agent.current_version_id = new_version.id
                locked_agent.current_version = new_version
                locked_agent.current_version_number = next_version_num

            await self._db_commit()
            await self._db_refresh(locked_agent)
            if config_changed and new_version is not None:
                locked_agent.current_version = new_version
                locked_agent.current_version_number = next_version_num
            return locked_agent
        except IntegrityError as e:
            await self._db_rollback()
            if "uq_agent_specs_organization_id_name" in str(e).lower():
                raise DuplicateAgentSpecError(
                    f"An agent specification named '{locked_agent.name}' already exists in this organization."
                ) from e
            raise
        except Exception:
            await self._db_rollback()
            raise

    async def create_version(
        self,
        organization_id: UUID,
        agent_id: UUID,
        description: str | None = None,
        prompt_id: UUID | None | object = _UNSET,
        prompt_version_id: UUID | None | object = _UNSET,
        provider_id: UUID | None | object = _UNSET,
        model_id: UUID | None | object = _UNSET,
        tool_identifiers: list[str] | None | object = _UNSET,
        memory_policy: dict[str, Any] | None | object = _UNSET,
    ) -> AgentSpecVersion:
        """Create a new version explicitly from the agent's effective configuration or provided overrides.

        Locks the agent row, assigns the next sequential version number, and updates
        current_version_id atomically.
        """
        try:
            locked_agent = await self._get_locked_agent(agent_id)
            if not locked_agent or locked_agent.organization_id != organization_id:
                raise AgentSpecNotFoundError(
                    f"Agent specification with ID '{agent_id}' not found."
                )

            effective_prompt_id = locked_agent.prompt_id if prompt_id is _UNSET else prompt_id
            effective_prompt_version_id = (
                locked_agent.prompt_version_id if prompt_version_id is _UNSET else prompt_version_id
            )
            # If prompt_id was explicitly cleared to None and prompt_version_id was omitted, clear version too
            if prompt_id is None and prompt_version_id is _UNSET:
                effective_prompt_version_id = None

            effective_provider_id = (
                locked_agent.provider_id if provider_id is _UNSET else provider_id
            )
            effective_model_id = locked_agent.model_id if model_id is _UNSET else model_id
            # If provider_id was explicitly cleared to None and model_id was omitted, clear model too
            if provider_id is None and model_id is _UNSET:
                effective_model_id = None

            if tool_identifiers is _UNSET:
                target_tools = list(locked_agent.tool_identifiers or [])
            else:
                target_tools = list(tool_identifiers) if tool_identifiers is not None else []

            if memory_policy is _UNSET:
                target_memory = dict(locked_agent.memory_policy or {})
            else:
                target_memory = dict(memory_policy) if memory_policy is not None else {}

            resolved_prompt_id, resolved_version_id, resolved_provider_id, resolved_model_id = (
                await self._validate_references(
                    organization_id=organization_id,
                    prompt_id=effective_prompt_id,
                    prompt_version_id=effective_prompt_version_id,
                    provider_id=effective_provider_id,
                    model_id=effective_model_id,
                )
            )

            latest_v = await self._version_repo.get_latest_version_number(agent_id)
            if latest_v == 0 or locked_agent.current_version_id is None:
                next_version_num = 1
            else:
                next_version_num = latest_v + 1

            now = datetime.now(timezone.utc)
            v_desc = description if description is not None else f"Version {next_version_num}"
            version = AgentSpecVersion(
                id=uuid.uuid4(),
                agent_spec_id=agent_id,
                version_number=next_version_num,
                description=v_desc,
                prompt_id=resolved_prompt_id,
                prompt_version_id=resolved_version_id,
                provider_id=resolved_provider_id,
                model_id=resolved_model_id,
                tool_identifiers=list(target_tools),
                memory_policy=dict(target_memory),
                created_at=now,
            )

            await self._version_repo.create(version)

            locked_agent.prompt_id = resolved_prompt_id
            locked_agent.prompt_version_id = resolved_version_id
            locked_agent.provider_id = resolved_provider_id
            locked_agent.model_id = resolved_model_id
            locked_agent.tool_identifiers = target_tools
            locked_agent.memory_policy = target_memory
            locked_agent.current_version_id = version.id
            locked_agent.current_version = version
            locked_agent.current_version_number = next_version_num
            locked_agent.updated_at = now

            await self._db_commit()
            await self._db_refresh(locked_agent)
            locked_agent.current_version = version
            locked_agent.current_version_number = next_version_num
            return version
        except Exception:
            await self._db_rollback()
            raise

    async def list_versions(
        self,
        organization_id: UUID,
        agent_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[AgentSpecVersion]:
        """List all versions of an agent spec ordered by version number descending."""
        await self.get_agent_spec(organization_id, agent_id)
        return await self._version_repo.list_by_agent(agent_id, skip=skip, limit=limit)

    async def get_version(
        self,
        organization_id: UUID,
        agent_id: UUID,
        version_id: UUID,
    ) -> AgentSpecVersion:
        """Retrieve a specific version of an agent spec."""
        await self.get_agent_spec(organization_id, agent_id)
        version = await self._version_repo.get_by_agent_and_id(agent_id, version_id)
        if not version:
            raise AgentSpecVersionNotFoundError(
                f"Agent specification version '{version_id}' not found for agent '{agent_id}'."
            )
        return version

    async def rollback_version(
        self,
        organization_id: UUID,
        agent_id: UUID,
        target_version_id: UUID,
        description: str | None = None,
    ) -> AgentSpec:
        """Roll back an AgentSpec by creating a new sequential version containing the selected historical version's configuration.

        The historical version is never modified or deleted. Validates that the historical version
        belongs to this agent and that its referenced entities are still valid.
        """
        try:
            locked_agent = await self._get_locked_agent(agent_id)
            if not locked_agent or locked_agent.organization_id != organization_id:
                raise AgentSpecNotFoundError(
                    f"Agent specification with ID '{agent_id}' not found."
                )

            target_version = await self._version_repo.get_by_agent_and_id(agent_id, target_version_id)
            if not target_version:
                raise AgentSpecVersionNotFoundError(
                    f"Agent specification version '{target_version_id}' not found for agent '{agent_id}'."
                )

            resolved_prompt_id, resolved_version_id, resolved_provider_id, resolved_model_id = (
                await self._validate_references(
                    organization_id=organization_id,
                    prompt_id=target_version.prompt_id,
                    prompt_version_id=target_version.prompt_version_id,
                    provider_id=target_version.provider_id,
                    model_id=target_version.model_id,
                )
            )

            latest_v = await self._version_repo.get_latest_version_number(agent_id)
            next_version_num = latest_v + 1

            rollback_desc = (
                description
                if description is not None
                else f"Rollback to version {target_version.version_number}"
            )

            now = datetime.now(timezone.utc)
            new_version = AgentSpecVersion(
                id=uuid.uuid4(),
                agent_spec_id=agent_id,
                version_number=next_version_num,
                description=rollback_desc,
                prompt_id=resolved_prompt_id,
                prompt_version_id=resolved_version_id,
                provider_id=resolved_provider_id,
                model_id=resolved_model_id,
                tool_identifiers=list(target_version.tool_identifiers or []),
                memory_policy=dict(target_version.memory_policy or {}),
                created_at=now,
            )

            await self._version_repo.create(new_version)

            locked_agent.prompt_id = resolved_prompt_id
            locked_agent.prompt_version_id = resolved_version_id
            locked_agent.provider_id = resolved_provider_id
            locked_agent.model_id = resolved_model_id
            locked_agent.tool_identifiers = list(target_version.tool_identifiers or [])
            locked_agent.memory_policy = dict(target_version.memory_policy or {})
            locked_agent.current_version_id = new_version.id
            locked_agent.current_version = new_version
            locked_agent.current_version_number = next_version_num
            locked_agent.updated_at = now

            await self._db_commit()
            await self._db_refresh(locked_agent)
            locked_agent.current_version = new_version
            locked_agent.current_version_number = next_version_num
            return locked_agent
        except Exception:
            await self._db_rollback()
            raise

    # Convenience alias
    rollback_to_version = rollback_version

    async def delete_agent_spec(self, organization_id: UUID, agent_id: UUID) -> None:
        """Delete an AgentSpec scoped to an organization."""
        agent_spec = await self.get_agent_spec(organization_id, agent_id)
        await self._agent_spec_repo.delete(agent_spec)
