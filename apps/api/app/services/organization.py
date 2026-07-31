"""
app/services/organization.py
----------------------------
Organization business logic.
"""

from typing import Any, Sequence
from uuid import UUID

from app.models.organization import Organization
from app.repositories.organization_repository import OrganizationRepository


class OrganizationException(Exception):
    """Base exception for organization service errors."""
    pass


class OrganizationAlreadyExistsError(OrganizationException):
    """Raised when attempting to create an organization that already exists."""
    pass


class OrganizationNotFoundError(OrganizationException):
    """Raised when an organization cannot be found."""
    pass


class OrganizationService:
    """Service layer for organization management."""

    def __init__(self, organization_repository: OrganizationRepository):
        """
        Initialize the OrganizationService.

        Args:
            organization_repository: Injected repository for organization data access.
        """
        self._org_repo = organization_repository

    async def create_organization(self, name: str, slug: str, description: str | None = None) -> Organization:
        """Create a new organization."""
        existing_by_slug = await self._org_repo.get_by_slug(slug)
        if existing_by_slug:
            raise OrganizationAlreadyExistsError(f"Organization slug already exists.")

        existing_by_name = await self._org_repo.get_by_name(name)
        if existing_by_name:
            raise OrganizationAlreadyExistsError(f"Organization name already exists.")

        org = Organization(
            name=name,
            slug=slug,
            description=description,
        )
        return await self._org_repo.create(org)

    async def get_by_id(self, org_id: UUID) -> Organization:
        """Retrieve an organization by its ID."""
        org = await self._org_repo.get_by_id(org_id)
        if not org:
            raise OrganizationNotFoundError(f"Organization with ID '{org_id}' not found.")
        return org

    async def get_by_slug(self, slug: str) -> Organization:
        """Retrieve an organization by its slug."""
        org = await self._org_repo.get_by_slug(slug)
        if not org:
            raise OrganizationNotFoundError(f"Organization with slug '{slug}' not found.")
        return org

    async def list_organizations(self, skip: int = 0, limit: int = 100) -> Sequence[Organization]:
        """List multiple organizations."""
        return await self._org_repo.list(skip=skip, limit=limit)

    async def update_organization(self, org_id: UUID, update_data: dict[str, Any]) -> Organization:
        """Update an existing organization."""
        org = await self.get_by_id(org_id)
        
        if "slug" in update_data and update_data["slug"] != org.slug:
            existing = await self._org_repo.get_by_slug(update_data["slug"])
            if existing:
                raise OrganizationAlreadyExistsError("Organization slug already exists.")
                
        if "name" in update_data and update_data["name"] != org.name:
            existing = await self._org_repo.get_by_name(update_data["name"])
            if existing:
                raise OrganizationAlreadyExistsError("Organization name already exists.")

        if "name" in update_data:
            org.name = update_data["name"]
        if "slug" in update_data:
            org.slug = update_data["slug"]
        if "description" in update_data:
            org.description = update_data["description"]
            
        return await self._org_repo.update(org)

    async def delete_organization(self, org_id: UUID) -> Organization:
        org = await self.get_by_id(org_id)
        await self._org_repo.delete(org)
        return org