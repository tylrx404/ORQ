from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    health,
    invitations,
    organization_invitations,
    organization_memberships,
    organizations,
    organization_providers,
    organization_provider_models,
    providers,
    provider_models,
    ready,
    users,
    version,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(
    organization_memberships.router,
    prefix="/organizations/{organization_id}/members",
    tags=["organization memberships"],
)
api_router.include_router(
    organization_invitations.router,
    prefix="/organizations/{organization_id}/invitations",
    tags=["organization invitations"],
)
api_router.include_router(
    invitations.router, prefix="/invitations", tags=["invitations"]
)
api_router.include_router(
    organization_providers.router,
    prefix="/organizations/{organization_id}/providers",
    tags=["organization providers"],
)
api_router.include_router(
    providers.router, prefix="/providers", tags=["providers"]
)
api_router.include_router(
    organization_provider_models.router,
    prefix="/organizations/{organization_id}/providers/{provider_id}/models",
    tags=["provider models"],
)
api_router.include_router(
    provider_models.router,
    prefix="/providers/{provider_id}/models",
    tags=["provider models"],
)
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(health.router, prefix="/health", tags=["system"])
api_router.include_router(ready.router, prefix="/ready", tags=["system"])
api_router.include_router(version.router, prefix="/version", tags=["system"])
