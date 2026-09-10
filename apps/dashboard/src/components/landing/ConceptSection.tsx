import { motion } from "framer-motion"
import { Layers, ShieldCheck, Gauge, ArrowRight } from "lucide-react"

const ARCHITECTURE_PILLARS = [
  {
    icon: Layers,
    title: "Unified Gateway Decoupling",
    badge: "API Routing",
    description:
      "Client applications speak standard OpenAI-compatible REST schemas. ORQ dynamically resolves active organizations, validates cryptographic API keys, and routes payloads to registered upstream providers without breaking client code.",
  },
  {
    icon: ShieldCheck,
    title: "Atomic Transactional Integrity",
    badge: "Zero-Loss Quota",
    description:
      "Request ceilings and token allowances are tracked in ACID-compliant PostgreSQL transactions. If an upstream provider fails or disconnects mid-stream, allocated usage quotas roll back immediately to protect customer budgets.",
  },
  {
    icon: Gauge,
    title: "Deterministic Rate Limiting",
    badge: "Redis Slotted Counters",
    description:
      "High-throughput token bucket algorithms protect infrastructure from cascading overload. Rate limits evaluate before upstream network hops, rejecting bursts at 429 without consuming billable organization quota.",
  },
]

export function ConceptSection() {
  return (
    <section id="architecture" className="py-20 md:py-28 border-b border-border/60 bg-surface-1/40">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="max-w-2xl mb-16">
          <span className="text-xs font-mono uppercase tracking-widest text-primary font-medium">
            Architectural Concept
          </span>
          <h2 className="mt-2 text-3xl sm:text-4xl font-semibold tracking-tight text-foreground font-sans">
            Built for resilient, multi-tenant AI operations.
          </h2>
          <p className="mt-3 text-base text-muted-foreground leading-relaxed font-normal">
            Modern AI workflows require more than simple proxying. ORQ sits between client applications
            and upstream model APIs as an authoritative enterprise control plane.
          </p>
        </div>

        {/* 3 Conceptual Pillars */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {ARCHITECTURE_PILLARS.map((pillar, idx) => {
            const Icon = pillar.icon
            return (
              <motion.div
                key={pillar.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: idx * 0.1 }}
                className="rounded-lg border border-border bg-surface-base p-6 flex flex-col justify-between hover:border-border-strong transition-colors"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="h-9 w-9 rounded-md bg-surface-2 border border-border flex items-center justify-center text-primary">
                      <Icon className="h-4 w-4" />
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-2 border border-border text-muted-foreground">
                      {pillar.badge}
                    </span>
                  </div>

                  <h3 className="text-base font-semibold text-foreground tracking-tight font-sans">
                    {pillar.title}
                  </h3>
                  <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                    {pillar.description}
                  </p>
                </div>

                <div className="mt-6 pt-4 border-t border-border/50 flex items-center text-[11px] font-mono text-primary font-medium">
                  <span>Architecture Specification</span>
                  <ArrowRight className="h-3 w-3 ml-1.5" />
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
