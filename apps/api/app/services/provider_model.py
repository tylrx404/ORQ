from typing import Any, Dict, Sequence
from uuid import UUID

from app.models.provider_model import ProviderModel
from app.repositories.provider_model_repository import ProviderModelRepository


class ProviderModelException(Exception):
    pass


class ProviderModelNotFoundError(ProviderModelException):
    pass


class DuplicateProviderModelError(ProviderModelException):
    pass


class ProviderModelService:
    def __init__(self, provider_model_repository: ProviderModelRepository):
        self._repo = provider_model_repository

    async def create_model(
        self,
        provider_id: UUID,
        name: str,
        model_identifier: str,
        context_window: int | None = None,
        max_output_tokens: int | None = None,
        supports_streaming: bool = False,
        supports_tools: bool = False,
        supports_vision: bool = False,
        supports_reasoning: bool = False,
        is_active: bool = True,
    ) -> ProviderModel:
        """Create a new provider model, enforcing uniqueness of model_identifier per provider."""
        existing = await self._repo.get_duplicate(provider_id, model_identifier)
        if existing:
            raise DuplicateProviderModelError(
                f"A model with identifier '{model_identifier}' already exists for this provider."
            )

        model = ProviderModel(
            provider_id=provider_id,
            name=name,
            model_identifier=model_identifier,
            context_window=context_window,
            max_output_tokens=max_output_tokens,
            supports_streaming=supports_streaming,
            supports_tools=supports_tools,
            supports_vision=supports_vision,
            supports_reasoning=supports_reasoning,
            is_active=is_active,
        )
        return await self._repo.create(model)

    async def get_model(self, model_id: UUID) -> ProviderModel:
        """Fetch a provider model by ID, raising if not found."""
        model = await self._repo.get_by_id(model_id)
        if not model:
            raise ProviderModelNotFoundError("Provider model not found.")
        return model

    async def list_models(
        self,
        provider_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[ProviderModel]:
        """List all models for a provider."""
        return await self._repo.list_by_provider(
            provider_id=provider_id, skip=skip, limit=limit
        )

    async def update_model(
        self,
        model_id: UUID,
        update_data: Dict[str, Any],
    ) -> ProviderModel:
        """Apply partial updates to a provider model."""
        model = await self.get_model(model_id)

        # Guard against duplicate model_identifier within the same provider.
        new_identifier = update_data.get("model_identifier")
        if new_identifier and new_identifier != model.model_identifier:
            existing = await self._repo.get_duplicate(model.provider_id, new_identifier)
            if existing:
                raise DuplicateProviderModelError(
                    f"A model with identifier '{new_identifier}' already exists for this provider."
                )

        for field, value in update_data.items():
            setattr(model, field, value)

        return await self._repo.update(model)

    async def delete_model(self, model_id: UUID) -> None:
        """Delete a provider model by ID."""
        model = await self.get_model(model_id)
        await self._repo.delete(model)
