import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { GlobalLayout } from "./layouts/GlobalLayout"
import { PlaceholderPage } from "./pages/PlaceholderPage"

export default function App() {
  return (
    <BrowserRouter>
      <GlobalLayout>
        <Routes>
          {/* 1. Overview */}
          <Route
            path="/"
            element={
              <PlaceholderPage
                eyebrow="Core"
                title="Overview"
                description="High-level telemetry, active providers, and platform throughput overview for the ORQ control plane."
                endpointHint="GET /api/v1/ready • GET /api/v1/organizations/{id}/usage"
                features={[
                  "System health monitoring",
                  "Execution volume summary",
                  "Active provider topology",
                  "Token quota consumption",
                ]}
              />
            }
          />

          {/* 2. Playground */}
          <Route
            path="/playground"
            element={
              <PlaceholderPage
                eyebrow="Core"
                title="Playground"
                description="Interactive test environment for experimenting with resolved models, system prompts, and streaming chat completions."
                endpointHint="POST /api/v1/chat/completions (SSE streaming supported)"
                features={[
                  "Real-time streaming generation",
                  "Model parameter tuning",
                  "Token count calculation",
                  "Latency metrics inspector",
                ]}
              />
            }
          />

          {/* 3. Models */}
          <Route
            path="/models"
            element={
              <PlaceholderPage
                eyebrow="Infrastructure"
                title="Models"
                description="Configure, catalog, and map models available to your organizations with designated aliases and routing parameters."
                endpointHint="GET /api/v1/organizations/{id}/providers/{pid}/models"
                features={[
                  "Model registry and routing",
                  "Context window limits",
                  "Default model designation",
                  "Provider association",
                ]}
              />
            }
          />

          {/* 4. Providers */}
          <Route
            path="/providers"
            element={
              <PlaceholderPage
                eyebrow="Infrastructure"
                title="Providers"
                description="Manage upstream LLM provider credentials, custom base URLs, and active routing status."
                endpointHint="GET /api/v1/organizations/{id}/providers"
                features={[
                  "Encrypted API key storage",
                  "Custom OpenAI-compatible base URLs",
                  "Active/inactive toggle",
                  "Provider failover health",
                ]}
              />
            }
          />

          {/* 5. API Keys */}
          <Route
            path="/api-keys"
            element={
              <PlaceholderPage
                eyebrow="Infrastructure"
                title="API Keys"
                description="Issue, inspect, and revoke machine-to-machine API keys for client integrations and gateway access."
                endpointHint="GET /api/v1/organizations/{id}/api-keys"
                features={[
                  "High-entropy SHA-256 key hashing",
                  "One-time display raw secret generation",
                  "Immediate revocation controls",
                  "Expiration policies",
                ]}
              />
            }
          />

          {/* 6. Executions */}
          <Route
            path="/executions"
            element={
              <PlaceholderPage
                eyebrow="Observability"
                title="Executions"
                description="Detailed audit logs of every gateway LLM execution, including status codes, token breakdown, and response latency."
                endpointHint="GET /api/v1/organizations/{id}/executions"
                features={[
                  "Status code filtering (200, 429, 502)",
                  "Token usage audit (prompt & completion)",
                  "Latency tracing (milliseconds)",
                  "Failure error message inspection",
                ]}
              />
            }
          />

          {/* 7. Usage */}
          <Route
            path="/usage"
            element={
              <PlaceholderPage
                eyebrow="Observability"
                title="Usage Analytics"
                description="Aggregated usage metrics across time intervals, breakdown by model identifier, and overall request volume."
                endpointHint="GET /api/v1/organizations/{id}/usage"
                features={[
                  "Time-bucketed request metrics",
                  "Cumulative token consumption",
                  "Success vs. error distribution",
                  "Per-model utilization breakdown",
                ]}
              />
            }
          />

          {/* 8. Quotas */}
          <Route
            path="/quotas"
            element={
              <PlaceholderPage
                eyebrow="Observability"
                title="Quotas & Limits"
                description="Manage organizational monthly request limits, token consumption budgets, and automatic billing cycle resets."
                endpointHint="GET /api/v1/organizations/{id}/quota"
                features={[
                  "Monthly request ceiling enforcement",
                  "Monthly token consumption ceiling",
                  "Atomic PostgreSQL quota incrementation",
                  "Transactional failure rollback verification",
                ]}
              />
            }
          />

          {/* 9. Settings */}
          <Route
            path="/settings"
            element={
              <PlaceholderPage
                eyebrow="System"
                title="Settings"
                description="Configure organization metadata, team member access roles, and platform notifications."
                endpointHint="GET /api/v1/organizations/{id}"
                features={[
                  "Organization slug and name management",
                  "Role-based access control (Admin / Member)",
                  "Invitation link generator",
                  "System connection diagnostics",
                ]}
              />
            }
          />

          {/* Catch-all fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </GlobalLayout>
    </BrowserRouter>
  )
}
