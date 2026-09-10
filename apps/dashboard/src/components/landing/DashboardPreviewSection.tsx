import * as React from "react"
import { motion } from "framer-motion"
import { LayoutDashboard, Terminal, ListTree, Gauge, CheckCircle2, ArrowRight } from "lucide-react"
import { Link } from "react-router-dom"
import { Button } from "../ui/Button"
import { Badge } from "../ui/Badge"

export function DashboardPreviewSection() {
  const [activeTab, setActiveTab] = React.useState<"telemetry" | "executions" | "routing">("telemetry")

  return (
    <section id="platform" className="py-20 md:py-28 border-b border-border/60 bg-surface-1/30">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-6">
          <div>
            <span className="text-xs font-mono uppercase tracking-widest text-primary font-medium">
              Control Console
            </span>
            <h2 className="mt-2 text-3xl sm:text-4xl font-semibold tracking-tight text-foreground font-sans">
              Precision interface for technical operators.
            </h2>
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed max-w-xl">
              Preview the planned operator control console: telemetry histograms, execution audit logs, and
              provider routing topologies with responsive zero-downtime controls.
            </p>
          </div>
          <Link to="/app">
            <Button variant="outline" size="sm" rightIcon={<ArrowRight className="h-3.5 w-3.5" />}>
              Launch Console
            </Button>
          </Link>
        </div>

        {/* Dashboard Shell Mockup Container */}
        <div className="rounded-xl border border-border-strong bg-surface-base shadow-2xl overflow-hidden">
          {/* Top Mock Window Bar */}
          <div className="h-11 border-b border-border/80 bg-surface-1/80 px-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-2.5 w-2.5 rounded-full bg-border-strong" />
              <div className="h-2.5 w-2.5 rounded-full bg-border-strong" />
              <div className="h-2.5 w-2.5 rounded-full bg-border-strong" />
              <span className="ml-3 text-[11px] font-mono text-muted-foreground">
                https://console.orq.ai/overview
              </span>
            </div>

            {/* Mock Tabs */}
            <div className="flex items-center gap-1">
              <button
                onClick={() => setActiveTab("telemetry")}
                className={`px-3 py-1 rounded text-xs font-mono transition-colors ${
                  activeTab === "telemetry"
                    ? "bg-surface-2 text-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Telemetry
              </button>
              <button
                onClick={() => setActiveTab("executions")}
                className={`px-3 py-1 rounded text-xs font-mono transition-colors ${
                  activeTab === "executions"
                    ? "bg-surface-2 text-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Executions
              </button>
              <button
                onClick={() => setActiveTab("routing")}
                className={`px-3 py-1 rounded text-xs font-mono transition-colors ${
                  activeTab === "routing"
                    ? "bg-surface-2 text-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Topology
              </button>
            </div>
          </div>

          {/* Console Content Preview */}
          <div className="p-6 sm:p-8 space-y-6">
            {/* Top Stat Ribbon */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-4 rounded-lg bg-surface-1 border border-border/60">
                <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
                  <span>Gateway Throughput</span>
                  <Gauge className="h-3.5 w-3.5 text-primary" />
                </div>
                <div className="mt-2 text-xl sm:text-2xl font-semibold font-mono text-foreground">
                  2,840 <span className="text-xs font-normal text-muted-foreground">req/min</span>
                </div>
                <div className="mt-1 text-[11px] font-mono text-status-success flex items-center gap-1">
                  <span>↑ 14.2%</span>
                  <span className="text-muted-foreground">vs last hour</span>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-surface-1 border border-border/60">
                <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
                  <span>P95 Latency</span>
                  <Terminal className="h-3.5 w-3.5 text-primary" />
                </div>
                <div className="mt-2 text-xl sm:text-2xl font-semibold font-mono text-foreground">
                  312 <span className="text-xs font-normal text-muted-foreground">ms</span>
                </div>
                <div className="mt-1 text-[11px] font-mono text-status-success flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" />
                  <span>SLA Nominal</span>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-surface-1 border border-border/60">
                <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
                  <span>Monthly Quota</span>
                  <LayoutDashboard className="h-3.5 w-3.5 text-primary" />
                </div>
                <div className="mt-2 text-xl sm:text-2xl font-semibold font-mono text-foreground">
                  64.2% <span className="text-xs font-normal text-muted-foreground">used</span>
                </div>
                <div className="mt-1 text-[11px] font-mono text-muted-foreground">
                  642k / 1,000k requests
                </div>
              </div>

              <div className="p-4 rounded-lg bg-surface-1 border border-border/60">
                <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
                  <span>Active Routing</span>
                  <ListTree className="h-3.5 w-3.5 text-primary" />
                </div>
                <div className="mt-2 text-xl sm:text-2xl font-semibold font-mono text-foreground">
                  4 <span className="text-xs font-normal text-muted-foreground">Providers</span>
                </div>
                <div className="mt-1 text-[11px] font-mono text-primary flex items-center gap-1">
                  <span>100% Health Score</span>
                </div>
              </div>
            </div>

            {/* Interactive Tab Visual Area */}
            {activeTab === "telemetry" && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="rounded-lg border border-border/80 bg-surface-1 p-5 space-y-4"
              >
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-foreground font-medium">Gateway Activity Profile</span>
                  <Badge variant="neutral" size="sm" withDot>
                    Simulated Telemetry Stream
                  </Badge>
                </div>
                {/* Simulated Telemetry Bars */}
                <div className="h-28 flex items-end gap-1.5 pt-4">
                  {[45, 60, 52, 70, 65, 88, 76, 92, 85, 78, 95, 82, 90, 74, 88, 94, 89, 72, 84, 91].map(
                    (val, i) => (
                      <div
                        key={i}
                        className="flex-1 bg-surface-2 rounded-xs hover:bg-primary/80 transition-colors relative group"
                        style={{ height: `${val}%` }}
                      >
                        <div className="opacity-0 group-hover:opacity-100 absolute -top-7 left-1/2 -translate-x-1/2 px-1.5 py-0.5 rounded bg-surface-elevated border border-border text-[9px] font-mono pointer-events-none transition-opacity">
                          {val * 12}req
                        </div>
                      </div>
                    )
                  )}
                </div>
                <div className="flex items-center justify-between text-[10px] font-mono text-muted-foreground pt-1 border-t border-border/40">
                  <span>10 minutes ago</span>
                  <span>Now (Realtime)</span>
                </div>
              </motion.div>
            )}

            {activeTab === "executions" && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="rounded-lg border border-border/80 bg-surface-1 overflow-hidden"
              >
                <div className="p-3 border-b border-border/60 text-xs font-mono font-medium text-foreground">
                  Recent Gateway Transactions
                </div>
                <div className="divide-y divide-border/40 text-xs font-mono">
                  {[
                    { id: "exec_9a2f1b", model: "gpt-4o-mini", status: 200, tokens: 412, latency: "184ms" },
                    { id: "exec_8c4d2e", model: "claude-3-5-sonnet", status: 200, tokens: 1240, latency: "420ms" },
                    { id: "exec_7b1a9c", model: "text-embedding-3", status: 200, tokens: 94, latency: "82ms" },
                    { id: "exec_6e9f3a", model: "gpt-4o", status: 429, tokens: 0, latency: "4ms", reason: "Rate Limit Exceeded" },
                  ].map((row) => (
                    <div key={row.id} className="p-3 flex items-center justify-between hover:bg-surface-2/40">
                      <div className="flex items-center gap-3">
                        <span className="text-muted-foreground">{row.id}</span>
                        <span className="text-foreground font-semibold">{row.model}</span>
                      </div>
                      <div className="flex items-center gap-4 text-[11px]">
                        <span
                          className={`px-1.5 py-0.5 rounded ${
                            row.status === 200
                              ? "bg-status-success/15 text-status-success border border-status-success/30"
                              : "bg-status-error/15 text-status-error border border-status-error/30"
                          }`}
                        >
                          {row.status}
                        </span>
                        <span className="text-muted-foreground hidden sm:inline">{row.tokens} tokens</span>
                        <span className="text-muted-foreground">{row.latency}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {activeTab === "routing" && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="rounded-lg border border-border/80 bg-surface-1 p-5 space-y-3"
              >
                <div className="text-xs font-mono font-medium text-foreground">
                  Configured Upstream Route Policies
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
                  <div className="p-3 rounded bg-surface-base border border-border/60 flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-foreground">Primary: OpenAI Production</div>
                      <div className="text-[10px] text-muted-foreground mt-0.5">Base URL: api.openai.com/v1</div>
                    </div>
                    <Badge variant="success" size="sm">Active</Badge>
                  </div>
                  <div className="p-3 rounded bg-surface-base border border-border/60 flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-foreground">Failover: Anthropic Bedrock</div>
                      <div className="text-[10px] text-muted-foreground mt-0.5">Base URL: api.anthropic.com/v1</div>
                    </div>
                    <Badge variant="neutral" size="sm">Standby</Badge>
                  </div>
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
