from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey


class ApiKeyRepository:
    """Repository for API key database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, key_id: UUID) -> ApiKey | None:
        """Fetch an API key by ID."""
        result = await self.db.execute(
            select(ApiKey).where(ApiKey.id == key_id)
        )
        return result.scalar_one_or_none()

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        """Fetch an API key by its hash."""
        result = await self.db.execute(
            select(ApiKey).where(ApiKey.key_hash == key_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_name_and_org(
        self, organization_id: UUID, name: str
    ) -> ApiKey | None:
        """Fetch an API key by name within an organization."""
        result = await self.db.execute(
            select(ApiKey).where(
                ApiKey.organization_id == organization_id,
                ApiKey.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_organization(
        self, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[ApiKey]:
        """List all API keys for an organization."""
        result = await self.db.execute(
            select(ApiKey)
            .where(ApiKey.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def create(self, api_key: ApiKey) -> ApiKey:
        """Create a new API key."""
        self.db.add(api_key)
        await self.db.commit()
        await self.db.refresh(api_key)
        return api_key

    async def update(self, api_key: ApiKey) -> ApiKey:
        """Update an existing API key."""
        await self.db.commit()
        await self.db.refresh(api_key)
        return api_key

    async def delete(self, api_key: ApiKey) -> None:
        """Delete an API key."""
        await self.db.delete(api_key)
        await self.db.commit()
