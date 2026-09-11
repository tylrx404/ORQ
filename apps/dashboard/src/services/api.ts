import type {
  Organization,
  UsageSummaryResponse,
  OrganizationQuotaResponse,
  ExecutionLogResponse,
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
   * List all available organizations.
   * Endpoint: GET /api/v1/organizations/
   */
  async listOrganizations(skip = 0, limit = 100): Promise<Organization[]> {
    return fetchJson<Organization[]>(
      `${API_BASE_URL}/organizations/?skip=${skip}&limit=${limit}`
    )
  },

  /**
   * Get an organization by ID.
   * Endpoint: GET /api/v1/organizations/{id}
   */
  async getOrganization(organizationId: string): Promise<Organization> {
    return fetchJson<Organization>(`${API_BASE_URL}/organizations/${organizationId}`)
  },

  /**
   * Get aggregated usage statistics for an organization.
   * Endpoint: GET /api/v1/organizations/{id}/usage
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
   * Endpoint: GET /api/v1/organizations/{id}/quota
   */
  async getOrganizationQuota(organizationId: string): Promise<OrganizationQuotaResponse> {
    return fetchJson<OrganizationQuotaResponse>(
      `${API_BASE_URL}/organizations/${organizationId}/quota`
    )
  },

  /**
   * List execution logs for an organization.
   * Endpoint: GET /api/v1/organizations/{id}/executions
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
}

export { ApiClientError }
