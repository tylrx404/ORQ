import { motion } from "framer-motion"
import { Cpu, Server, Zap, LineChart, Gauge, Key } from "lucide-react"

const CAPABILITIES = [
  {
    icon: Cpu,
    category: "Infrastructure",
    title: "Model Catalog & Dynamic Mapping",
    description:
      "Map internal model aliases (e.g. `gpt-4o`, `claude-3-5-sonnet`) to provider-specific IDs with designated context window ceilings and default fallbacks.",
    endpoint: "GET /api/v1/organizations/{id}/providers/{pid}/models",
    status: "Production Ready",
  },
  {
    icon: Server,
    category: "Infrastructure",
    title: "Multi-Provider Credential Vault",
    description:
      "Register upstream providers (OpenAI, Anthropic, or OpenAI-compatible custom endpoints) with AES-256 encrypted credentials and toggle active states instantly.",
    endpoint: "GET /api/v1/organizations/{id}/providers",
    status: "Encrypted Storage",
  },
  {
    icon: Zap,
    category: "Core Gateway",
    title: "Streaming SSE Gateway & Protocol Translation",
    description:
      "Unified `POST /api/v1/chat/completions` handling Server-Sent Events (SSE) streaming, parameter tuning, error normalisation, and zero-payload latency.",
    endpoint: "POST /api/v1/chat/completions",
    status: "SSE Streaming",
  },
  {
    icon: LineChart,
    category: "Observability",
    title: "Execution Traces & Latency Telemetry",
    description:
      "Full audit trail recording every transaction: HTTP status codes (200, 429, 502), prompt/completion token consumption, and millisecond latency timers.",
    endpoint: "GET /api/v1/organizations/{id}/executions",
    status: "Per-Request Audit",
  },
  {
    icon: Gauge,
    category: "Observability",
    title: "Monthly Quotas & Budget Ceilings",
    description:
      "Enforce hard monthly request limits and token consumption thresholds with atomic incrementation and transactional rollback upon upstream failure.",
    endpoint: "GET /api/v1/organizations/{id}/quota",
    status: "Zero-Loss Rollback",
  },
  {
    icon: Key,
    category: "Security",
    title: "High-Entropy API Keys & Isolation",
    description:
      "Cryptographically hashed machine-to-machine keys (`SHA-256`) with one-time raw secret generation, immediate revocation, and organization isolation.",
    endpoint: "GET /api/v1/organizations/{id}/api-keys",
    status: "SHA-256 Hashed",
  },
]

export function CapabilitiesSection() {
  return (
    <section id="product" className="py-20 md:py-28 border-b border-border/60">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="max-w-3xl mb-16">
          <span className="text-xs font-mono uppercase tracking-widest text-primary font-medium">
            Core Capabilities
          </span>
          <h2 className="mt-2 text-3xl sm:text-4xl font-semibold tracking-tight text-foreground font-sans">
            Engineered strictly from production control plane specifications.
          </h2>
          <p className="mt-3 text-base text-muted-foreground leading-relaxed font-normal">
            Every capability in ORQ is anchored in our real backend REST APIs, PostgreSQL data models,
            and distributed Redis rate limiting.
          </p>
        </div>

        {/* 6 Capabilities Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {CAPABILITIES.map((cap, idx) => {
            const Icon = cap.icon
            return (
              <motion.div
                key={cap.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.35, delay: idx * 0.05 }}
                className="rounded-lg border border-border bg-surface-base p-6 flex flex-col justify-between hover:border-border-strong hover:bg-surface-1/60 transition-all duration-150"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="h-8 w-8 rounded bg-surface-2 border border-border flex items-center justify-center text-primary">
                      <Icon className="h-4 w-4" />
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-2 border border-border text-muted-foreground uppercase">
                      {cap.category}
                    </span>
                  </div>

                  <h3 className="text-sm font-semibold text-foreground tracking-tight font-sans">
                    {cap.title}
                  </h3>
                  <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                    {cap.description}
                  </p>
                </div>

                <div className="mt-6 pt-4 border-t border-border/40 space-y-2">
                  <div className="flex items-center justify-between text-[10px] font-mono">
                    <span className="text-muted-foreground truncate max-w-[200px]">
                      {cap.endpoint}
                    </span>
                    <span className="text-primary/90 font-medium shrink-0">{cap.status}</span>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
