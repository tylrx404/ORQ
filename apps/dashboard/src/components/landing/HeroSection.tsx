import { motion } from "framer-motion"
import { ArrowUpRight, Check, Play } from "lucide-react"
import { Link } from "react-router-dom"
import { Button } from "../ui/Button"
import { Badge } from "../ui/Badge"
import { AbstractControlPlane3D } from "./AbstractControlPlane3D"

export function HeroSection() {
  return (
    <section className="relative overflow-hidden pt-12 pb-20 md:pt-20 md:pb-32 border-b border-border/60">
      {/* Background radial accent - very subtle */}
      <div
        className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 h-[500px] w-[800px] bg-gradient-to-b from-primary/[0.07] via-transparent to-transparent blur-3xl opacity-70"
        aria-hidden="true"
      />

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          {/* Left Editorial Copy (7 cols) */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="lg:col-span-7 space-y-6"
          >
            {/* Status Pill */}
            <div className="inline-flex items-center gap-2">
              <Badge variant="primary" size="md" withDot pulse>
                ORQ CONTROL PLANE v1.0
              </Badge>
              <span className="text-xs font-mono text-muted-foreground hidden sm:inline-block">
                OpenAI-Compatible Gateway
              </span>
            </div>

            {/* Editorial Headline */}
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-tight text-foreground leading-[1.08] font-sans">
              AI infrastructure,{" "}
              <span className="text-muted-foreground block sm:inline font-normal">
                without the complexity.
              </span>
            </h1>

            {/* Concise Product Value Statement */}
            <p className="text-base sm:text-lg text-muted-foreground max-w-2xl font-normal leading-relaxed">
              One unified control plane for multi-provider routing, atomic quota enforcement,
              real-time SSE streaming, and granular token telemetry across all your LLM workloads.
            </p>

            {/* Call to Actions */}
            <div className="pt-2 flex flex-wrap items-center gap-3.5">
              <Link to="/app">
                <Button size="lg" variant="primary" rightIcon={<ArrowUpRight className="h-4 w-4" />}>
                  Explore Control Plane
                </Button>
              </Link>
              <Link to="/app/playground">
                <Button size="lg" variant="secondary" leftIcon={<Play className="h-3.5 w-3.5 text-primary" />}>
                  Live Playground
                </Button>
              </Link>
            </div>

            {/* Quick architectural guarantees */}
            <div className="pt-6 border-t border-border/60 grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs font-mono text-muted-foreground">
              <div className="flex items-center gap-2">
                <Check className="h-3.5 w-3.5 text-status-success shrink-0" />
                <span>Zero-loss quota rollback</span>
              </div>
              <div className="flex items-center gap-2">
                <Check className="h-3.5 w-3.5 text-status-success shrink-0" />
                <span>Encrypted AES-256 keys</span>
              </div>
              <div className="flex items-center gap-2">
                <Check className="h-3.5 w-3.5 text-status-success shrink-0" />
                <span>Low-overhead gateway</span>
              </div>
            </div>
          </motion.div>

          {/* Right 3D Visual Column (5 cols) */}
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.15, ease: "easeOut" }}
            className="lg:col-span-5"
          >
            <AbstractControlPlane3D />
          </motion.div>
        </div>
      </div>
    </section>
  )
}
