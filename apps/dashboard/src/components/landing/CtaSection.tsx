import { motion } from "framer-motion"
import { ArrowUpRight, ShieldCheck, Terminal, Layers } from "lucide-react"
import { Link } from "react-router-dom"
import { Button } from "../ui/Button"

export function CtaSection() {
  return (
    <section className="py-20 md:py-32 relative overflow-hidden border-b border-border/60 bg-surface-1/40">
      {/* Background subtle radial lighting */}
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(243,138,54,0.06),transparent_65%)]"
        aria-hidden="true"
      />

      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 relative z-10 text-center space-y-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-2 border border-border text-xs font-mono text-muted-foreground">
          <Layers className="h-3.5 w-3.5 text-primary" />
          <span>High-Throughput Production Ready</span>
        </div>

        <motion.h2
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-3xl sm:text-5xl font-semibold tracking-tight text-foreground font-sans max-w-3xl mx-auto leading-tight"
        >
          Unify your AI infrastructure with the ORQ control plane.
        </motion.h2>

        <p className="text-base sm:text-lg text-muted-foreground max-w-2xl mx-auto font-normal leading-relaxed">
          Zero vendor lock-in. Full transactional visibility. Deploy locally with Docker or scale
          seamlessly across your enterprise clusters.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
          <Link to="/app">
            <Button size="lg" variant="primary" rightIcon={<ArrowUpRight className="h-4 w-4" />}>
              Get started now
            </Button>
          </Link>
          <Link to="/app/playground">
            <Button size="lg" variant="secondary" leftIcon={<Terminal className="h-3.5 w-3.5 text-primary" />}>
              Open Playground
            </Button>
          </Link>
        </div>

        <div className="pt-10 flex items-center justify-center gap-8 text-xs font-mono text-muted-foreground">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-primary" />
            <span>Open Source Backend</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-status-success" />
            <span>PostgreSQL + Redis Core</span>
          </div>
        </div>
      </div>
    </section>
  )
}
