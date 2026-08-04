from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider_model import ProviderModel


class ProviderModelRepository:
    """Repository for provider model database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, model_id: UUID) -> ProviderModel | None:
        """Fetch a provider model by ID."""
        result = await self.db.execute(
            select(ProviderModel).where(ProviderModel.id == model_id)
        )
        return result.scalar_one_or_none()

    async def get_duplicate(
        self, provider_id: UUID, model_identifier: str
    ) -> ProviderModel | None:
        """Check if a model with the same identifier already exists for the provider."""
        result = await self.db.execute(
            select(ProviderModel).where(
                ProviderModel.provider_id == provider_id,
                ProviderModel.model_identifier == model_identifier,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_provider(
        self, provider_id: UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[ProviderModel]:
        """List all models for a provider."""
        result = await self.db.execute(
            select(ProviderModel)
            .where(ProviderModel.provider_id == provider_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def create(self, model: ProviderModel) -> ProviderModel:
        """Persist a new provider model."""
        self.db.add(model)
        await self.db.commit()
        await self.db.refresh(model)
        return model

    async def update(self, model: ProviderModel) -> ProviderModel:
        """Persist updates to an existing provider model."""
        await self.db.commit()
        await self.db.refresh(model)
        return model

    async def delete(self, model: ProviderModel) -> None:
        """Delete a provider model."""
        await self.db.delete(model)
        await self.db.commit()
