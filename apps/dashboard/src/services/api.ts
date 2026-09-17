import type {
  Organization,
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
}

export { ApiClientError }
