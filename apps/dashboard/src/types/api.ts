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

export interface ProviderResponse {
  id: string
  organization_id: string
  name: string
  provider_type: string
  base_url?: string | null
  default_model?: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ProviderModelResponse {
  id: string
  provider_id: string
  name: string
  model_identifier: string
  context_window?: number | null
  max_output_tokens?: number | null
  supports_streaming: boolean
  supports_tools: boolean
  supports_vision: boolean
  supports_reasoning: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ApiKeyCreateRequest {
  name: string
  expires_at?: string | null
}

export interface ApiKeyResponse {
  id: string
  organization_id: string
  name: string
  key_prefix: string
  expires_at?: string | null
  is_active: boolean
  created_by?: string | null
  created_at: string
  updated_at: string
}

export interface ApiKeyCreateResponse extends ApiKeyResponse {
  key: string
}
