"""
app/services/organization_quota.py
------------------------------------
Service layer for organization quota CRUD and cycle management.

Responsibilities:
- Create / read / update / delete quota records.
- Auto-reset usage counters when reset_at is in the past.
- Advance the reset_at timestamp by one cycle length on reset.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.models.organization_quota import OrganizationQuota
from app.repositories.organization_quota_repository import OrganizationQuotaRepository
from app.schemas.organization_quota import OrganizationQuotaCreate, OrganizationQuotaUpdate

_DEFAULT_CYCLE_DAYS = 30


class QuotaNotFoundError(Exception):
    """Raised when no quota record exists for the requested organization."""


class QuotaAlreadyExistsError(Exception):
    """Raised when a quota already exists for the organization."""


class OrganizationQuotaService:
    """Business logic for organization usage quotas."""

    def __init__(self, repo: OrganizationQuotaRepository) -> None:
        self._repo = repo

    async def get_quota(self, organization_id: UUID) -> OrganizationQuota:
        """Return the quota for an organization, auto-resetting if the cycle expired.

        Raises QuotaNotFoundError if no quota has been configured.
        """
        quota = await self._repo.get_by_organization(organization_id)
        if quota is None:
            raise QuotaNotFoundError(
                f"No quota configured for organization {organization_id}."
            )
        quota = await self._maybe_reset_cycle(quota)
        return quota

    async def create_quota(
        self, organization_id: UUID, data: OrganizationQuotaCreate
    ) -> OrganizationQuota:
        """Create a quota record for an organization.

        Raises QuotaAlreadyExistsError if one already exists.
        """
        existing = await self._repo.get_by_organization(organization_id)
        if existing is not None:
            raise QuotaAlreadyExistsError(
                f"A quota already exists for organization {organization_id}."
            )

        reset_at = data.reset_at
        if reset_at.tzinfo is None:
            reset_at = reset_at.replace(tzinfo=timezone.utc)

        quota = OrganizationQuota(
            organization_id=organization_id,
            request_limit=data.request_limit,
            token_limit=data.token_limit,
            reset_at=reset_at,
            requests_used=0,
            tokens_used=0,
        )
        return await self._repo.create(quota)

    async def update_quota(
        self, organization_id: UUID, data: OrganizationQuotaUpdate
    ) -> OrganizationQuota:
        """Update limits or reset_at for an existing quota.

        Raises QuotaNotFoundError if no quota exists.
        Only fields explicitly provided in data are changed.
        """
        quota = await self._repo.get_by_organization(organization_id)
        if quota is None:
            raise QuotaNotFoundError(
                f"No quota configured for organization {organization_id}."
            )

        if data.request_limit is not None:
            quota.request_limit = data.request_limit
        elif "request_limit" in data.model_fields_set:
            # Explicitly set to None -> remove limit
            quota.request_limit = None

        if data.token_limit is not None:
            quota.token_limit = data.token_limit
        elif "token_limit" in data.model_fields_set:
            quota.token_limit = None

        if data.reset_at is not None:
            reset_at = data.reset_at
            if reset_at.tzinfo is None:
                reset_at = reset_at.replace(tzinfo=timezone.utc)
            quota.reset_at = reset_at

        return await self._repo.update(quota)

    async def delete_quota(self, organization_id: UUID) -> None:
        """Remove the quota record for an organization.

        Raises QuotaNotFoundError if none exists.
        """
        quota = await self._repo.get_by_organization(organization_id)
        if quota is None:
            raise QuotaNotFoundError(
                f"No quota configured for organization {organization_id}."
            )
        await self._repo.delete(quota)

    async def check_and_increment_request_quota(self, organization_id: UUID) -> bool:
        """Atomically check if organization has available request quota and increment by 1.

        Returns True if allowed (or unlimited/no quota configured), False if quota exceeded.
        """
        return await self._repo.try_increment_request(
            organization_id=organization_id,
            cycle_days=_DEFAULT_CYCLE_DAYS,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _maybe_reset_cycle(self, quota: OrganizationQuota) -> OrganizationQuota:
        """If the billing cycle has expired, reset counters and advance reset_at."""
        now = datetime.now(timezone.utc)
        reset_at = quota.reset_at
        if reset_at.tzinfo is None:
            reset_at = reset_at.replace(tzinfo=timezone.utc)

        if now >= reset_at:
            # Advance reset_at by the default cycle length until it is in the future.
            while now >= reset_at:
                reset_at = reset_at + timedelta(days=_DEFAULT_CYCLE_DAYS)

            quota.reset_at = reset_at
            quota.requests_used = 0
            quota.tokens_used = 0
            await self._repo.update(quota)

        return quota
