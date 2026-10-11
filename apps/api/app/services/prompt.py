import uuid
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.models.prompt import Prompt, PromptVersion
from app.repositories.prompt_repository import (
    PromptRepository,
    PromptVersionRepository,
)


class PromptException(Exception):
    """Base exception for prompt domain operations."""
    pass


class PromptNotFoundError(PromptException):
    """Raised when a prompt does not exist or does not belong to the organization."""
    pass


class PromptVersionNotFoundError(PromptException):
    """Raised when a prompt version does not exist or does not belong to the prompt."""
    pass


class DuplicatePromptError(PromptException):
    """Raised when a prompt with the same name already exists in the organization."""
    pass


class PromptService:
    """Business logic for Prompt and PromptVersion entities."""

    def __init__(
        self,
        prompt_repository: PromptRepository,
        prompt_version_repository: PromptVersionRepository,
    ):
        self._prompt_repo = prompt_repository
        self._version_repo = prompt_version_repository

    async def create_prompt(
        self,
        organization_id: UUID,
        name: str,
        initial_content: str,
        description: str | None = None,
    ) -> tuple[Prompt, PromptVersion]:
        """Create a new prompt and its initial version 1 transactionally.

        Automatically marks version 1 as the published version.
        """
        existing = await self._prompt_repo.get_by_name_and_org(organization_id, name)
        if existing:
            raise DuplicatePromptError(f"A prompt named '{name}' already exists in this organization.")

        prompt_id = uuid.uuid4()
        version_id = uuid.uuid4()

        prompt = Prompt(
            id=prompt_id,
            organization_id=organization_id,
            name=name,
            description=description,
            published_version_id=None,
        )
        try:
            self._prompt_repo.db.add(prompt)
            await self._prompt_repo.db.flush()

            version_1 = PromptVersion(
                id=version_id,
                prompt_id=prompt_id,
                version_number=1,
                content=initial_content,
            )
            self._version_repo.db.add(version_1)
            await self._version_repo.db.flush()

            prompt.published_version_id = version_id
            await self._prompt_repo.db.commit()
            await self._prompt_repo.db.refresh(prompt)
            await self._version_repo.db.refresh(version_1)

            return prompt, version_1
        except IntegrityError as e:
            await self._prompt_repo.db.rollback()
            if "uq_prompts_organization_id_name" in str(e).lower():
                raise DuplicatePromptError(f"A prompt named '{name}' already exists in this organization.") from e
            raise

    async def get_prompt(self, organization_id: UUID, prompt_id: UUID) -> Prompt:
        """Retrieve a prompt scoped to the organization."""
        prompt = await self._prompt_repo.get_by_id_and_org(organization_id, prompt_id)
        if not prompt:
            raise PromptNotFoundError("Prompt not found.")
        return prompt

    async def list_prompts(
        self, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[Prompt]:
        """List all prompts for an organization."""
        return await self._prompt_repo.list_by_organization(organization_id, skip=skip, limit=limit)

    async def update_prompt(
        self,
        organization_id: UUID,
        prompt_id: UUID,
        update_data: dict[str, Any],
    ) -> Prompt:
        """Update prompt metadata (name, description)."""
        prompt = await self.get_prompt(organization_id, prompt_id)

        if "name" in update_data and update_data["name"] is not None and update_data["name"] != prompt.name:
            new_name = update_data["name"]
            existing = await self._prompt_repo.get_by_name_and_org(organization_id, new_name)
            if existing and existing.id != prompt.id:
                raise DuplicatePromptError(f"A prompt named '{new_name}' already exists in this organization.")
            prompt.name = new_name

        if "description" in update_data:
            prompt.description = update_data["description"]

        try:
            return await self._prompt_repo.update(prompt)
        except IntegrityError as e:
            await self._prompt_repo.db.rollback()
            if "uq_prompts_organization_id_name" in str(e).lower():
                raise DuplicatePromptError(f"A prompt named '{prompt.name}' already exists in this organization.") from e
            raise

    async def delete_prompt(self, organization_id: UUID, prompt_id: UUID) -> None:
        """Delete a prompt."""
        prompt = await self.get_prompt(organization_id, prompt_id)
        await self._prompt_repo.delete(prompt)

    async def create_version(
        self,
        organization_id: UUID,
        prompt_id: UUID,
        content: str,
    ) -> PromptVersion:
        """Create a new subsequent version for a prompt.

        Locks the parent prompt row inside the transaction for concurrency safety.
        Does NOT automatically publish the new version.
        """
        # Ensure prompt exists within organization
        await self.get_prompt(organization_id, prompt_id)

        # Concurrency safety: lock the parent prompt row
        locked_prompt = await self._prompt_repo.get_for_update(prompt_id)
        if not locked_prompt:
            raise PromptNotFoundError("Prompt not found.")

        latest_version = await self._version_repo.get_latest_version_number(prompt_id)
        next_version = latest_version + 1

        new_version = PromptVersion(
            id=uuid.uuid4(),
            prompt_id=prompt_id,
            version_number=next_version,
            content=content,
        )
        return await self._version_repo.create(new_version)

    async def list_versions(
        self,
        organization_id: UUID,
        prompt_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[PromptVersion]:
        """List all versions of a prompt."""
        await self.get_prompt(organization_id, prompt_id)
        return await self._version_repo.list_by_prompt(prompt_id, skip=skip, limit=limit)

    async def get_version(
        self,
        organization_id: UUID,
        prompt_id: UUID,
        version_id: UUID,
    ) -> PromptVersion:
        """Retrieve a specific version of a prompt."""
        await self.get_prompt(organization_id, prompt_id)
        version = await self._version_repo.get_by_prompt_and_id(prompt_id, version_id)
        if not version:
            raise PromptVersionNotFoundError("Prompt version not found.")
        return version

    async def publish_version(
        self,
        organization_id: UUID,
        prompt_id: UUID,
        version_id: UUID,
    ) -> Prompt:
        """Set a specific version as the published version for a prompt."""
        prompt = await self.get_prompt(organization_id, prompt_id)
        version = await self._version_repo.get_by_prompt_and_id(prompt_id, version_id)
        if not version:
            raise PromptVersionNotFoundError("Prompt version not found for this prompt.")

        prompt.published_version_id = version.id
        return await self._prompt_repo.update(prompt)
