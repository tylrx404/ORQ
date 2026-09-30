import type {
  Organization,
  OrganizationUpdateRequest,
  MembershipResponse,
  MembershipCreateRequest,
  MembershipUpdateRequest,
  OrganizationInvitationCreateRequest,
  OrganizationInvitationResponse,
  UsageSummaryResponse,
  OrganizationQuotaResponse,
  ExecutionLogResponse,
  ProviderResponse,
  ProviderCreateRequest,
  ProviderUpdateRequest,
  ProviderModelResponse,
  ProviderModelCreateRequest,
  ProviderModelUpdateRequest,
  ApiKeyCreateRequest,
  ApiKeyCreateResponse,
  ApiKeyResponse,
  ApiKeyUpdateRequest,
} from "../types/api"

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api/v1"

class ApiClientError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = "ApiClientError"
    this.status = status
    this.detail = detail
  }
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem("orq_access_token")
  const headers = new Headers(options?.headers)

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`)
  }

  if (!headers.has("Content-Type") && options?.method && options.method !== "GET") {
    headers.set("Content-Type", "application/json")
  }

  const res = await fetch(url, {
    ...options,
    headers,
  })

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}: ${res.statusText}`
    try {
      const data = await res.json()
      if (data?.detail) {
        errorDetail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)
      } else if (data?.message) {
        errorDetail = data.message
      }
    } catch {
      // Body was not JSON, fallback to status text
    }
    throw new ApiClientError(res.status, errorDetail)
  }

  return res.json() as Promise<T>
}

export const api = {
  /**
   * Get the current stored JWT auth token.
   */
  getAuthToken(): string | null {
    return localStorage.getItem("orq_access_token")
  },

  /**
   * List all available organizations.
   */
  async listOrganizations(skip = 0, limit = 100): Promise<Organization[]> {
    return fetchJson<Organization[]>(
      `${API_BASE_URL}/organizations/?skip=${skip}&limit=${limit}`
    )
  },

  /**
   * Get an organization by ID.
   */
  async getOrganization(organizationId: string): Promise<Organization> {
    return fetchJson<Organization>(`${API_BASE_URL}/organizations/${organizationId}`)
  },

  /**
   * Update an organization (requires admin or owner).
   */
  async updateOrganization(
    organizationId: string,
    data: OrganizationUpdateRequest
  ): Promise<Organization> {
    return fetchJson<Organization>(`${API_BASE_URL}/organizations/${organizationId}`, {
      method: "PATCH",
      headers: {
        "X-Organization-Id": organizationId,
      },
      body: JSON.stringify(data),
    })
  },

  /**
   * Delete an organization (requires owner).
   */
  async deleteOrganization(organizationId: string): Promise<void> {
    const token = localStorage.getItem("orq_access_token")
    const headers = new Headers()
    if (token) {
      headers.set("Authorization", `Bearer ${token}`)
    }
    headers.set("X-Organization-Id", organizationId)

    const res = await fetch(`${API_BASE_URL}/organizations/${organizationId}`, {
      method: "DELETE",
      headers,
    })

    if (!res.ok) {
      let errorDetail = `HTTP ${res.status}: ${res.statusText}`
      try {
        const data = await res.json()
        if (data?.detail) {
          errorDetail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)
        } else if (data?.message) {
          errorDetail = data.message
        }
      } catch {
        // Response was not JSON
      }
      throw new ApiClientError(res.status, errorDetail)
    }
  },

  /**
   * List members of an organization.
   */
  async listOrganizationMembers(
    organizationId: string,
    skip = 0,
    limit = 100
  ): Promise<MembershipResponse[]> {
    return fetchJson<MembershipResponse[]>(
      `${API_BASE_URL}/organizations/${organizationId}/members?skip=${skip}&limit=${limit}`,
      {
        headers: {
          "X-Organization-Id": organizationId,
        },
      }
    )
  },

  /**
   * Add a member to an organization (requires admin or owner).
   */
  async addOrganizationMember(
    organizationId: string,
    request: MembershipCreateRequest
  ): Promise<MembershipResponse> {
    return fetchJson<MembershipResponse>(
      `${API_BASE_URL}/organizations/${organizationId}/members`,
      {
        method: "POST",
        headers: {
          "X-Organization-Id": organizationId,
        },
        body: JSON.stringify(request),
      }
    )
  },

  /**
   * Update an organization member's role (requires owner).
   */
  async updateOrganizationMemberRole(
    organizationId: string,
    userId: string,
    request: MembershipUpdateRequest
  ): Promise<MembershipResponse> {
    return fetchJson<MembershipResponse>(
      `${API_BASE_URL}/organizations/${organizationId}/members/${userId}`,
      {
        method: "PATCH",
        headers: {
          "X-Organization-Id": organizationId,
        },
        body: JSON.stringify(request),
      }
    )
  },

  /**
   * Remove a member from an organization (requires admin or owner).
   */
  async removeOrganizationMember(
    organizationId: string,
    userId: string
  ): Promise<void> {
    const token = localStorage.getItem("orq_access_token")
    const headers = new Headers()
    if (token) {
      headers.set("Authorization", `Bearer ${token}`)
    }
    headers.set("X-Organization-Id", organizationId)

    const res = await fetch(
      `${API_BASE_URL}/organizations/${organizationId}/members/${userId}`,
      {
        method: "DELETE",
        headers,
      }
    )

    if (!res.ok) {
      let errorDetail = `HTTP ${res.status}: ${res.statusText}`
      try {
        const data = await res.json()
        if (data?.detail) {
          errorDetail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)
        } else if (data?.message) {
          errorDetail = data.message
        }
      } catch {
        // Response was not JSON
      }
      throw new ApiClientError(res.status, errorDetail)
    }
  },

  /**
   * List invitations for an organization (requires admin or owner).
   */
  async listOrganizationInvitations(
    organizationId: string,
    skip = 0,
    limit = 100
  ): Promise<OrganizationInvitationResponse[]> {
    return fetchJson<OrganizationInvitationResponse[]>(
      `${API_BASE_URL}/organizations/${organizationId}/invitations?skip=${skip}&limit=${limit}`,
      {
        headers: {
          "X-Organization-Id": organizationId,
        },
      }
    )
  },

  /**
   * Create an invitation to join an organization (requires admin or owner).
   */
  async createOrganizationInvitation(
    organizationId: string,
    request: OrganizationInvitationCreateRequest
  ): Promise<OrganizationInvitationResponse> {
    return fetchJson<OrganizationInvitationResponse>(
      `${API_BASE_URL}/organizations/${organizationId}/invitations`,
      {
        method: "POST",
        headers: {
          "X-Organization-Id": organizationId,
        },
        body: JSON.stringify(request),
      }
    )
  },

  /**
   * Revoke an organization invitation (requires admin or owner).
   */
  async revokeOrganizationInvitation(
    organizationId: string,
    invitationId: string
  ): Promise<void> {
    const token = localStorage.getItem("orq_access_token")
    const headers = new Headers()
    if (token) {
      headers.set("Authorization", `Bearer ${token}`)
    }
    headers.set("X-Organization-Id", organizationId)

    const res = await fetch(
      `${API_BASE_URL}/organizations/${organizationId}/invitations/${invitationId}`,
      {
        method: "DELETE",
        headers,
      }
    )

    if (!res.ok) {
      let errorDetail = `HTTP ${res.status}: ${res.statusText}`
      try {
        const data = await res.json()
        if (data?.detail) {
          errorDetail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)
        } else if (data?.message) {
          errorDetail = data.message
        }
      } catch {
        // Response was not JSON
      }
      throw new ApiClientError(res.status, errorDetail)
    }
  },

  /**
   * Get aggregated usage statistics for an organization.
   */
  async getOrganizationUsage(
    organizationId: string,
    params?: { start?: string; end?: string }
  ): Promise<UsageSummaryResponse> {
    const query = new URLSearchParams()
    if (params?.start) query.set("start", params.start)
    if (params?.end) query.set("end", params.end)
    const queryString = query.toString() ? `?${query.toString()}` : ""
    return fetchJson<UsageSummaryResponse>(
      `${API_BASE_URL}/organizations/${organizationId}/usage${queryString}`
    )
  },

  /**
   * Get quota record for an organization.
   */
  async getOrganizationQuota(organizationId: string): Promise<OrganizationQuotaResponse> {
    return fetchJson<OrganizationQuotaResponse>(
      `${API_BASE_URL}/organizations/${organizationId}/quota`
    )
  },

  /**
   * List execution logs for an organization.
   */
  async listOrganizationExecutions(
    organizationId: string,
    skip = 0,
    limit = 20
  ): Promise<ExecutionLogResponse[]> {
    return fetchJson<ExecutionLogResponse[]>(
      `${API_BASE_URL}/organizations/${organizationId}/executions?skip=${skip}&limit=${limit}`
    )
  },

  /**
   * Fetch a single execution log by ID.
   */
  async getExecution(executionId: string): Promise<ExecutionLogResponse> {
    return fetchJson<ExecutionLogResponse>(
      `${API_BASE_URL}/executions/${executionId}`
    )
  },

  /**
   * List providers for an organization.
   */
  async listProviders(organizationId: string, skip = 0, limit = 100): Promise<ProviderResponse[]> {
    return fetchJson<ProviderResponse[]>(
      `${API_BASE_URL}/organizations/${organizationId}/providers?skip=${skip}&limit=${limit}`
    )
  },

  /**
   * Create a provider in an organization.
   */
  async createProvider(organizationId: string, request: ProviderCreateRequest): Promise<ProviderResponse> {
    return fetchJson<ProviderResponse>(
      `${API_BASE_URL}/organizations/${organizationId}/providers`,
      {
        method: "POST",
        body: JSON.stringify(request),
      }
    )
  },

  /**
   * Update a provider by ID.
   */
  async updateProvider(providerId: string, request: ProviderUpdateRequest): Promise<ProviderResponse> {
    return fetchJson<ProviderResponse>(
      `${API_BASE_URL}/providers/${providerId}`,
      {
        method: "PATCH",
        body: JSON.stringify(request),
      }
    )
  },

  /**
   * Delete a provider by ID.
   */
  async deleteProvider(providerId: string): Promise<void> {
    const token = localStorage.getItem("orq_access_token")
    const headers = new Headers()
    if (token) {
      headers.set("Authorization", `Bearer ${token}`)
    }
    const res = await fetch(`${API_BASE_URL}/providers/${providerId}`, {
      method: "DELETE",
      headers,
    })
    if (!res.ok) {
      let errorDetail = `HTTP ${res.status}: ${res.statusText}`
      try {
        const data = await res.json()
        if (data?.detail) {
          errorDetail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)
        } else if (data?.message) {
          errorDetail = data.message
        }
      } catch {
        // Body was not JSON
      }
      throw new ApiClientError(res.status, errorDetail)
    }
  },

  /**
   * List models for a provider.
   */
  async listProviderModels(organizationId: string, providerId: string, skip = 0, limit = 100): Promise<ProviderModelResponse[]> {
    return fetchJson<ProviderModelResponse[]>(
      `${API_BASE_URL}/organizations/${organizationId}/providers/${providerId}/models?skip=${skip}&limit=${limit}`
    )
  },

  /**
   * Create a model for a provider within an organization.
   */
  async createProviderModel(
    organizationId: string,
    providerId: string,
    request: ProviderModelCreateRequest
  ): Promise<ProviderModelResponse> {
    return fetchJson<ProviderModelResponse>(
      `${API_BASE_URL}/organizations/${organizationId}/providers/${providerId}/models`,
      {
        method: "POST",
        body: JSON.stringify(request),
      }
    )
  },

  /**
   * Update a model for a provider.
   */
  async updateProviderModel(
    providerId: string,
    modelId: string,
    request: ProviderModelUpdateRequest
  ): Promise<ProviderModelResponse> {
    return fetchJson<ProviderModelResponse>(
      `${API_BASE_URL}/providers/${providerId}/models/${modelId}`,
      {
        method: "PATCH",
        body: JSON.stringify(request),
      }
    )
  },

  /**
   * Delete a model for a provider.
   */
  async deleteProviderModel(providerId: string, modelId: string): Promise<void> {
    const token = localStorage.getItem("orq_access_token")
    const headers = new Headers()
    if (token) {
      headers.set("Authorization", `Bearer ${token}`)
    }
    const res = await fetch(`${API_BASE_URL}/providers/${providerId}/models/${modelId}`, {
      method: "DELETE",
      headers,
    })
    if (!res.ok) {
      let errorDetail = `HTTP ${res.status}: ${res.statusText}`
      try {
        const data = await res.json()
        if (data?.detail) {
          errorDetail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)
        } else if (data?.message) {
          errorDetail = data.message
        }
      } catch {
        // Body was not JSON
      }
      throw new ApiClientError(res.status, errorDetail)
    }
  },

  /**
   * Create an API key for the organization.
   */
  async createApiKey(organizationId: string, request: ApiKeyCreateRequest): Promise<ApiKeyCreateResponse> {
    return fetchJson<ApiKeyCreateResponse>(
      `${API_BASE_URL}/organizations/${organizationId}/api-keys`,
      {
        method: "POST",
        body: JSON.stringify(request)
      }
    )
  },

  /**
   * List API keys for an organization.
   */
  async listApiKeys(organizationId: string, skip = 0, limit = 100): Promise<ApiKeyResponse[]> {
    return fetchJson<ApiKeyResponse[]>(
      `${API_BASE_URL}/organizations/${organizationId}/api-keys?skip=${skip}&limit=${limit}`
    )
  },

  /**
   * Update an API key (rename or activate/deactivate).
   */
  async updateApiKey(keyId: string, request: ApiKeyUpdateRequest): Promise<ApiKeyResponse> {
    return fetchJson<ApiKeyResponse>(
      `${API_BASE_URL}/api-keys/${keyId}`,
      {
        method: "PATCH",
        body: JSON.stringify(request),
      }
    )
  },

  /**
   * Delete an API key by ID (returns 204 No Content).
   */
  async deleteApiKey(keyId: string): Promise<void> {
    const token = localStorage.getItem("orq_access_token")
    const headers = new Headers()
    if (token) {
      headers.set("Authorization", `Bearer ${token}`)
    }
    const res = await fetch(`${API_BASE_URL}/api-keys/${keyId}`, {
      method: "DELETE",
      headers,
    })
    if (!res.ok) {
      let errorDetail = `HTTP ${res.status}: ${res.statusText}`
      try {
        const data = await res.json()
        if (data?.detail) {
          errorDetail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)
        } else if (data?.message) {
          errorDetail = data.message
        }
      } catch {
        // Body was not JSON
      }
      throw new ApiClientError(res.status, errorDetail)
    }
  },
}

export { ApiClientError }
