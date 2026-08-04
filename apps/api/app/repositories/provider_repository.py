from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider import Provider


class ProviderRepository:
    """Repository for provider database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, provider_id: UUID) -> Provider | None:
        """Fetch a provider by ID."""
        result = await self.db.execute(
            select(Provider).where(Provider.id == provider_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name_and_org(
        self, organization_id: UUID, name: str
    ) -> Provider | None:
        """Fetch a provider by name within an organization."""
        result = await self.db.execute(
            select(Provider).where(
                Provider.organization_id == organization_id,
                Provider.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_organization(
        self, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[Provider]:
        """List all providers for an organization."""
        result = await self.db.execute(
            select(Provider)
            .where(Provider.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def create(self, provider: Provider) -> Provider:
        """Create a new provider."""
        self.db.add(provider)
        await self.db.commit()
        await self.db.refresh(provider)
        return provider

    async def update(self, provider: Provider) -> Provider:
        """Update an existing provider."""
        await self.db.commit()
        await self.db.refresh(provider)
        return provider

    async def delete(self, provider: Provider) -> None:
        """Delete a provider."""
        await self.db.delete(provider)
        await self.db.commit()
