"""
app/repositories/organization_quota_repository.py
--------------------------------------------------
Repository for OrganizationQuota database operations.
"""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization_quota import OrganizationQuota


class OrganizationQuotaRepository:
    """Repository for OrganizationQuota database operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_organization(self, organization_id: UUID) -> OrganizationQuota | None:
        """Return the quota record for an organization, or None if not set."""
        result = await self.db.execute(
            select(OrganizationQuota).where(
                OrganizationQuota.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    async def create(self, quota: OrganizationQuota) -> OrganizationQuota:
        """Persist a new quota record and return the refreshed instance."""
        self.db.add(quota)
        await self.db.commit()
        await self.db.refresh(quota)
        return quota

    async def update(self, quota: OrganizationQuota) -> OrganizationQuota:
        """Flush all pending changes and return the refreshed quota."""
        await self.db.commit()
        await self.db.refresh(quota)
        return quota

    async def try_increment_request(
        self,
        organization_id: UUID,
        cycle_days: int = 30,
    ) -> bool:
        """Atomically check request quota and increment by 1 request if allowed.

        Uses SELECT ... FOR UPDATE to lock the organization's quota row, ensuring
        concurrent requests cannot bypass the request limit.
        If the billing cycle has expired (now >= reset_at), counters are reset
        and reset_at is advanced before checking limits.

        Returns True if request is allowed (or no quota/unlimited), False if exceeded.
        """
        result = await self.db.execute(
            select(OrganizationQuota)
            .where(OrganizationQuota.organization_id == organization_id)
            .with_for_update()
        )
        quota = result.scalar_one_or_none()
        if quota is None:
            # No quota configured means unlimited
            return True

        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        reset_at = quota.reset_at
        if reset_at.tzinfo is None:
            reset_at = reset_at.replace(tzinfo=timezone.utc)

        if now >= reset_at:
            while now >= reset_at:
                reset_at = reset_at + timedelta(days=cycle_days)
            quota.reset_at = reset_at
            quota.requests_used = 0
            quota.tokens_used = 0

        if quota.request_limit is not None and quota.requests_used >= quota.request_limit:
            await self.db.commit()
            return False

        quota.requests_used = OrganizationQuota.requests_used + 1
        await self.db.commit()
        return True

    async def try_increment_tokens(
        self,
        organization_id: UUID,
        tokens: int,
        cycle_days: int = 30,
    ) -> bool:
        """Atomically check token quota and increment by `tokens` if allowed.

        Uses SELECT ... FOR UPDATE to lock the organization's quota row, ensuring
        concurrent requests cannot bypass the token limit.
        If the billing cycle has expired (now >= reset_at), counters are reset
        and reset_at is advanced before checking limits.

        Returns True if tokens are allowed and incremented (or no quota/unlimited),
        False if adding the tokens would exceed token_limit (quota remains unchanged).
        """
        if tokens <= 0:
            return True

        result = await self.db.execute(
            select(OrganizationQuota)
            .where(OrganizationQuota.organization_id == organization_id)
            .with_for_update()
        )
        quota = result.scalar_one_or_none()
        if quota is None:
            # No quota configured means unlimited
            return True

        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        reset_at = quota.reset_at
        if reset_at.tzinfo is None:
            reset_at = reset_at.replace(tzinfo=timezone.utc)

        if now >= reset_at:
            while now >= reset_at:
                reset_at = reset_at + timedelta(days=cycle_days)
            quota.reset_at = reset_at
            quota.requests_used = 0
            quota.tokens_used = 0

        if quota.token_limit is not None and (quota.tokens_used + tokens) > quota.token_limit:
            await self.db.commit()
            return False

        quota.tokens_used = OrganizationQuota.tokens_used + tokens
        await self.db.commit()
        return True

    async def increment_usage(
        self,
        organization_id: UUID,
        requests_delta: int = 1,
        tokens_delta: int = 0,
    ) -> None:
        """Atomically increment usage counters in the database."""
        await self.db.execute(
            update(OrganizationQuota)
            .where(OrganizationQuota.organization_id == organization_id)
            .values(
                requests_used=OrganizationQuota.requests_used + requests_delta,
                tokens_used=OrganizationQuota.tokens_used + tokens_delta,
            )
        )
        await self.db.commit()

    async def reset_counters(self, organization_id: UUID) -> None:
        """Reset usage counters to zero (called when reset_at is passed)."""
        await self.db.execute(
            update(OrganizationQuota)
            .where(OrganizationQuota.organization_id == organization_id)
            .values(requests_used=0, tokens_used=0)
        )
        await self.db.commit()

    async def delete(self, quota: OrganizationQuota) -> None:
        """Delete a quota record."""
        await self.db.delete(quota)
        await self.db.commit()
