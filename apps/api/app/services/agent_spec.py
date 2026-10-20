import uuid
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.models.agent_spec import AgentSpec
from app.repositories.agent_spec_repository import AgentSpecRepository
from app.repositories.prompt_repository import PromptRepository, PromptVersionRepository
from app.repositories.provider_model_repository import ProviderModelRepository
from app.repositories.provider_repository import ProviderRepository


class AgentSpecException(Exception):
    """Base exception for agent specification domain operations."""
    pass


class AgentSpecNotFoundError(AgentSpecException):
    """Raised when an agent spec does not exist or does not belong to the organization."""
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


class AgentSpecService:
    """Business logic for AgentSpec entities."""

    def __init__(
        self,
        agent_spec_repository: AgentSpecRepository,
        prompt_repository: PromptRepository,
        prompt_version_repository: PromptVersionRepository,
        provider_repository: ProviderRepository,
        provider_model_repository: ProviderModelRepository,
    ):
        self._agent_spec_repo = agent_spec_repository
        self._prompt_repo = prompt_repository
        self._prompt_version_repo = prompt_version_repository
        self._provider_repo = provider_repository
        self._model_repo = provider_model_repository

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

        if prompt_id is not None:
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
    ) -> AgentSpec:
        """Create a new AgentSpec after validating unique name and entity references."""
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

        agent_spec = AgentSpec(
            id=uuid.uuid4(),
            organization_id=organization_id,
            name=name,
            description=description,
            prompt_id=resolved_prompt_id,
            prompt_version_id=resolved_version_id,
            provider_id=resolved_provider_id,
            model_id=resolved_model_id,
            tool_identifiers=tool_identifiers if tool_identifiers is not None else [],
            memory_policy=memory_policy if memory_policy is not None else {},
            is_active=is_active,
        )

        try:
            return await self._agent_spec_repo.create(agent_spec)
        except IntegrityError as e:
            await self._agent_spec_repo.db.rollback()
            if "uq_agent_specs_organization_id_name" in str(e).lower():
                raise DuplicateAgentSpecError(
                    f"An agent specification named '{name}' already exists in this organization."
                ) from e
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
        """Apply partial updates to an AgentSpec, validating final effective references."""
        agent_spec = await self.get_agent_spec(organization_id, agent_id)

        # 1. Name uniqueness validation
        if "name" in update_data and update_data["name"] is not None and update_data["name"] != agent_spec.name:
            new_name = update_data["name"]
            existing = await self._agent_spec_repo.get_by_name_and_org(organization_id, new_name)
            if existing and existing.id != agent_spec.id:
                raise DuplicateAgentSpecError(
                    f"An agent specification named '{new_name}' already exists in this organization."
                )
            agent_spec.name = new_name

        # 2. Determine effective relational references
        if "prompt_id" in update_data:
            effective_prompt_id = update_data["prompt_id"]
        else:
            effective_prompt_id = agent_spec.prompt_id

        if "prompt_version_id" in update_data:
            effective_prompt_version_id = update_data["prompt_version_id"]
        else:
            effective_prompt_version_id = agent_spec.prompt_version_id

        # If prompt_id was explicitly cleared to None and version wasn't updated, clear version too
        if "prompt_id" in update_data and update_data["prompt_id"] is None and "prompt_version_id" not in update_data:
            effective_prompt_version_id = None

        if "provider_id" in update_data:
            effective_provider_id = update_data["provider_id"]
        else:
            effective_provider_id = agent_spec.provider_id

        if "model_id" in update_data:
            effective_model_id = update_data["model_id"]
        else:
            effective_model_id = agent_spec.model_id

        # If provider_id was explicitly cleared to None and model wasn't updated, clear model too
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

        agent_spec.prompt_id = resolved_prompt_id
        agent_spec.prompt_version_id = resolved_version_id
        agent_spec.provider_id = resolved_provider_id
        agent_spec.model_id = resolved_model_id

        # 3. Apply other metadata updates
        if "description" in update_data:
            agent_spec.description = update_data["description"]
        if "tool_identifiers" in update_data and update_data["tool_identifiers"] is not None:
            agent_spec.tool_identifiers = update_data["tool_identifiers"]
        if "memory_policy" in update_data and update_data["memory_policy"] is not None:
            agent_spec.memory_policy = update_data["memory_policy"]
        if "is_active" in update_data and update_data["is_active"] is not None:
            agent_spec.is_active = update_data["is_active"]

        try:
            return await self._agent_spec_repo.update(agent_spec)
        except IntegrityError as e:
            await self._agent_spec_repo.db.rollback()
            if "uq_agent_specs_organization_id_name" in str(e).lower():
                raise DuplicateAgentSpecError(
                    f"An agent specification named '{agent_spec.name}' already exists in this organization."
                ) from e
            raise

    async def delete_agent_spec(self, organization_id: UUID, agent_id: UUID) -> None:
        """Delete an AgentSpec scoped to an organization."""
        agent_spec = await self.get_agent_spec(organization_id, agent_id)
        await self._agent_spec_repo.delete(agent_spec)
