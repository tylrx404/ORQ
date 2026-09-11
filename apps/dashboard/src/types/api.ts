/**
 * Standard API schemas for the ORQ Control Plane dashboard.
 * Anchored directly to existing FastAPI endpoints.
 */

export interface Organization {
  id: string
  name: string
  slug: string
  description?: string | null
  created_at: string
  updated_at: string
}

export interface UsageSummaryResponse {
  organization_id: string
  start: string
  end: string
  total_requests: number
  successful_requests: number
  failed_requests: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  average_latency_ms: number | null
}

export interface OrganizationQuotaResponse {
  id: string
  organization_id: string
  request_limit: number | null
  token_limit: number | null
  requests_used: number
  tokens_used: number
  reset_at: string
  created_at: string
  updated_at: string
}

export interface ExecutionLogResponse {
  id: string
  organization_id: string
  api_key_id?: string | null
  provider_id?: string | null
  model_id?: string | null
  model_name: string
  status_code: number
  prompt_tokens?: number | null
  completion_tokens?: number | null
  total_tokens?: number | null
  latency_ms?: number | null
  error_message?: string | null
  created_at: string
}

export interface ApiError {
  status: number
  message: string
  detail?: string
}
