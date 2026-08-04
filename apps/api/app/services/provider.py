from typing import Any, Dict, Sequence
from uuid import UUID

from app.models.provider import Provider, ProviderType
from app.repositories.provider_repository import ProviderRepository


class ProviderException(Exception):
    pass


class ProviderNotFoundError(ProviderException):
    pass


class DuplicateProviderError(ProviderException):
    pass


class ProviderService:
    def __init__(self, provider_repository: ProviderRepository):
        self._provider_repo = provider_repository

    async def create_provider(
        self,
        organization_id: UUID,
        name: str,
        provider_type: ProviderType,
        api_key: str,
        base_url: str | None = None,
        default_model: str | None = None,
    ) -> Provider:
        existing = await self._provider_repo.get_by_name_and_org(organization_id, name)
        if existing:
            raise DuplicateProviderError(f"A provider named '{name}' already exists in this organization.")

        provider = Provider(
            organization_id=organization_id,
            name=name,
            provider_type=provider_type,
            api_key=api_key,
            base_url=base_url,
            default_model=default_model,
        )
        return await self._provider_repo.create(provider)

    async def get_provider(self, provider_id: UUID) -> Provider:
        provider = await self._provider_repo.get_by_id(provider_id)
        if not provider:
            raise ProviderNotFoundError("Provider not found.")
        return provider

    async def update_provider(
        self,
        provider_id: UUID,
        update_data: Dict[str, Any],
    ) -> Provider:
        provider = await self.get_provider(provider_id)

        if "name" in update_data and update_data["name"] != provider.name:
            existing = await self._provider_repo.get_by_name_and_org(
                provider.organization_id, update_data["name"]
            )
            if existing:
                raise DuplicateProviderError(f"A provider named '{update_data['name']}' already exists.")

        if "name" in update_data:
            provider.name = update_data["name"]
        if "provider_type" in update_data:
            provider.provider_type = update_data["provider_type"]
        if "api_key" in update_data:
            provider.api_key = update_data["api_key"]
        if "base_url" in update_data:
            provider.base_url = update_data["base_url"]
        if "default_model" in update_data:
            provider.default_model = update_data["default_model"]
        if "is_active" in update_data:
            provider.is_active = update_data["is_active"]

        return await self._provider_repo.update(provider)

    async def delete_provider(self, provider_id: UUID) -> None:
        provider = await self.get_provider(provider_id)
        await self._provider_repo.delete(provider)

    async def list_providers(
        self,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Provider]:
        return await self._provider_repo.list_by_organization(
            organization_id=organization_id, skip=skip, limit=limit
        )
