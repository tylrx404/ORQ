from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt import Prompt, PromptVersion


class PromptRepository:
    """Repository for Prompt entity database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, prompt_id: UUID) -> Prompt | None:
        """Fetch a prompt by ID."""
        result = await self.db.execute(
            select(Prompt).where(Prompt.id == prompt_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_org(
        self, organization_id: UUID, prompt_id: UUID
    ) -> Prompt | None:
        """Fetch a prompt by ID scoped to an organization."""
        result = await self.db.execute(
            select(Prompt).where(
                Prompt.id == prompt_id,
                Prompt.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_name_and_org(
        self, organization_id: UUID, name: str
    ) -> Prompt | None:
        """Fetch a prompt by unique name within an organization."""
        result = await self.db.execute(
            select(Prompt).where(
                Prompt.organization_id == organization_id,
                Prompt.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_organization(
        self, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[Prompt]:
        """List all prompts for an organization ordered by creation time."""
        result = await self.db.execute(
            select(Prompt)
            .where(Prompt.organization_id == organization_id)
            .order_by(Prompt.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_for_update(self, prompt_id: UUID) -> Prompt | None:
        """Fetch a prompt locking the row for concurrent version updates."""
        result = await self.db.execute(
            select(Prompt).where(Prompt.id == prompt_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def create(self, prompt: Prompt) -> Prompt:
        """Persist a new prompt."""
        self.db.add(prompt)
        await self.db.commit()
        await self.db.refresh(prompt)
        return prompt

    async def update(self, prompt: Prompt) -> Prompt:
        """Persist updates to an existing prompt."""
        await self.db.commit()
        await self.db.refresh(prompt)
        return prompt

    async def delete(self, prompt: Prompt) -> None:
        """Delete a prompt."""
        await self.db.delete(prompt)
        await self.db.commit()


class PromptVersionRepository:
    """Repository for immutable PromptVersion entity database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, version_id: UUID) -> PromptVersion | None:
        """Fetch a prompt version by ID."""
        result = await self.db.execute(
            select(PromptVersion).where(PromptVersion.id == version_id)
        )
        return result.scalar_one_or_none()

    async def get_by_prompt_and_id(
        self, prompt_id: UUID, version_id: UUID
    ) -> PromptVersion | None:
        """Fetch a version scoped to a prompt ID."""
        result = await self.db.execute(
            select(PromptVersion).where(
                PromptVersion.id == version_id,
                PromptVersion.prompt_id == prompt_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_version_number(self, prompt_id: UUID) -> int:
        """Get the current maximum version number for a prompt."""
        result = await self.db.execute(
            select(func.coalesce(func.max(PromptVersion.version_number), 0)).where(
                PromptVersion.prompt_id == prompt_id
            )
        )
        return result.scalar() or 0

    async def list_by_prompt(
        self, prompt_id: UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[PromptVersion]:
        """List all versions for a prompt ordered by version number descending."""
        result = await self.db.execute(
            select(PromptVersion)
            .where(PromptVersion.prompt_id == prompt_id)
            .order_by(PromptVersion.version_number.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def create(self, version: PromptVersion) -> PromptVersion:
        """Persist an immutable prompt version."""
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        return version
