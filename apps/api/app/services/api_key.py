import hashlib
import secrets
from datetime import datetime, timezone
from typing import Sequence
from uuid import UUID

from app.models.api_key import ApiKey
from app.repositories.api_key_repository import ApiKeyRepository


class ApiKeyException(Exception):
    pass


class ApiKeyNotFoundError(ApiKeyException):
    pass


class DuplicateApiKeyError(ApiKeyException):
    pass


class InvalidApiKeyError(ApiKeyException):
    pass


class ApiKeyService:
    def __init__(self, api_key_repository: ApiKeyRepository):
        self._repo = api_key_repository

    def _hash_key(self, raw_key: str) -> str:
        """Hash the raw key using SHA-256."""
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    async def create_key(
        self,
        organization_id: UUID,
        name: str,
        user_id: UUID | None,
        expires_at: datetime | None = None,
    ) -> tuple[ApiKey, str]:
        """Create a new API key, returning the metadata and the raw key."""
        existing = await self._repo.get_by_name_and_org(organization_id, name)
        if existing:
            raise DuplicateApiKeyError(
                f"An API key with the name '{name}' already exists in this organization."
            )

        # Generate a cryptographically secure random token (URL-safe)
        random_part = secrets.token_urlsafe(36)
        raw_key = f"orq_sk_{random_part}"

        # Display prefix is the fixed "orq_sk_" plus the first 8 characters of the random part
        key_prefix = raw_key[:15]
        
        # Hash the full raw key
        key_hash = self._hash_key(raw_key)

        api_key_record = ApiKey(
            organization_id=organization_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            expires_at=expires_at,
            created_by=user_id,
            is_active=True,
        )

        created_key = await self._repo.create(api_key_record)
        return created_key, raw_key

    async def list_keys(
        self,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[ApiKey]:
        """List all API keys for an organization."""
        return await self._repo.list_by_organization(
            organization_id=organization_id, skip=skip, limit=limit
        )

    async def get_key(self, key_id: UUID) -> ApiKey:
        """Fetch an API key by ID."""
        api_key = await self._repo.get_by_id(key_id)
        if not api_key:
            raise ApiKeyNotFoundError("API key not found.")
        return api_key

    async def update_key(
        self,
        key_id: UUID,
        name: str | None = None,
        is_active: bool | None = None,
    ) -> ApiKey:
        """Update an existing API key's metadata."""
        api_key = await self.get_key(key_id)

        if name is not None and name != api_key.name:
            existing = await self._repo.get_by_name_and_org(api_key.organization_id, name)
            if existing:
                raise DuplicateApiKeyError(
                    f"An API key with the name '{name}' already exists in this organization."
                )
            api_key.name = name

        if is_active is not None:
            api_key.is_active = is_active

        return await self._repo.update(api_key)

    async def delete_key(self, key_id: UUID) -> None:
        """Permanently delete an API key."""
        api_key = await self.get_key(key_id)
        await self._repo.delete(api_key)

    async def validate_key(self, raw_key: str) -> ApiKey:
        """Validate a raw API key and return its metadata."""
        if not raw_key or not raw_key.startswith("orq_sk_"):
            raise InvalidApiKeyError("Invalid API key format.")

        key_hash = self._hash_key(raw_key)
        api_key = await self._repo.get_by_hash(key_hash)

        if not api_key:
            raise InvalidApiKeyError("API key is invalid.")

        if not api_key.is_active:
            raise InvalidApiKeyError("API key has been disabled or revoked.")

        if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
            raise InvalidApiKeyError("API key has expired.")

        return api_key
