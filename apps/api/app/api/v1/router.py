from fastapi import APIRouter

from app.api.v1.endpoints import (
    api_keys,
    auth,
    chat_completions,
    execution,
    health,
    invitations,
    organization_api_keys,
    organization_executions,
    organization_invitations,
    organization_memberships,
    organization_provider_models,
    organization_providers,
    organization_quota,
    organization_usage,
    organizations,
    provider_models,
    providers,
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
api_router.include_router(
    organization_api_keys.router,
    prefix="/organizations/{organization_id}/api-keys",
    tags=["organization api keys"],
)
api_router.include_router(
    organization_executions.router,
    prefix="/organizations/{organization_id}/executions",
    tags=["organization executions"],
)
api_router.include_router(
    organization_usage.router,
    prefix="/organizations/{organization_id}",
    tags=["organization usage"],
)
api_router.include_router(
    organization_quota.router,
    prefix="/organizations/{organization_id}",
    tags=["organization quota"],
)
api_router.include_router(
    api_keys.router, prefix="/api-keys", tags=["api keys"]
)
api_router.include_router(
    execution.router, prefix="/executions", tags=["executions"]
)
api_router.include_router(
    chat_completions.router, prefix="/chat/completions", tags=["chat completions"]
)
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(health.router, prefix="/health", tags=["system"])
api_router.include_router(ready.router, prefix="/ready", tags=["system"])
api_router.include_router(version.router, prefix="/version", tags=["system"])
