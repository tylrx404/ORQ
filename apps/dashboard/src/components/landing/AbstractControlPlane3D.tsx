import { motion } from "framer-motion"
import { Cpu, Server, Shield, Activity, Database, Zap } from "lucide-react"

export function AbstractControlPlane3D() {
  return (
    <div className="relative w-full h-[380px] sm:h-[440px] flex items-center justify-center select-none overflow-hidden rounded-xl border border-border/70 bg-gradient-to-b from-surface-1/90 via-surface-base/80 to-surface-1/90 p-4">
      {/* Subtle depth lighting */}
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_30%,rgba(243,138,54,0.08),transparent_70%)]"
        aria-hidden="true"
      />

      {/* Grid Floor Perspective Plane */}
      <div
        className="absolute inset-x-0 bottom-0 h-44 opacity-25"
        style={{
          backgroundImage:
            "linear-gradient(to right, rgba(255,255,255,0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.06) 1px, transparent 1px)",
          backgroundSize: "28px 28px",
          transform: "perspective(500px) rotateX(60deg)",
          transformOrigin: "bottom center",
          maskImage: "linear-gradient(to top, black, transparent)",
          WebkitMaskImage: "linear-gradient(to top, black, transparent)",
        }}
      />

      {/* Isometric Layer Stack Container */}
      <div
        className="relative z-10 w-full max-w-[420px] flex flex-col items-center gap-3.5 transform-gpu"
        style={{
          transform: "perspective(1200px) rotateX(24deg) rotateY(-12deg) rotateZ(2deg)",
          transformStyle: "preserve-3d",
        }}
      >
        {/* Layer 1: Client Application Layer (Top) */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          whileHover={{ translateY: -4, translateZ: 10 }}
          className="w-full rounded-lg border border-border-strong bg-surface-elevated/95 p-3.5 shadow-xl backdrop-blur-sm"
        >
          <div className="flex items-center justify-between text-xs font-mono">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-status-success animate-pulse" />
              <span className="font-semibold text-foreground">API Consumers</span>
            </div>
            <span className="text-[11px] text-muted-foreground">POST /api/v1/chat/completions</span>
          </div>
          <div className="mt-2.5 flex items-center justify-between gap-2 text-[10px] font-mono text-muted-foreground">
            <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-surface-1 border border-border/50">
              <Shield className="h-3 w-3 text-primary" />
              <span>Bearer SHA-256</span>
            </div>
            <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-surface-1 border border-border/50">
              <Activity className="h-3 w-3 text-status-warning" />
              <span>Token Bucket Rate Limit</span>
            </div>
          </div>
        </motion.div>

        {/* Dynamic Data Transmission Beam 1 */}
        <div className="w-0.5 h-3 bg-gradient-to-b from-primary/80 to-primary/20 rounded-full" />

        {/* Layer 2: ORQ Core Gateway Control Plane (Centerpiece) */}
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          whileHover={{ translateY: -3, translateZ: 14 }}
          className="w-full rounded-lg border border-primary/40 bg-surface-2/95 p-4 shadow-2xl relative overflow-hidden"
        >
          {/* Subtle accent corner glow */}
          <div className="absolute -top-10 -right-10 w-24 h-24 bg-primary/10 rounded-full blur-xl pointer-events-none" />

          <div className="flex items-center justify-between text-xs font-mono mb-3">
            <div className="flex items-center gap-2">
              <div className="p-1 rounded bg-primary/10 border border-primary/30 text-primary">
                <Zap className="h-3.5 w-3.5" />
              </div>
              <div>
                <div className="font-semibold text-foreground">ORQ Gateway Engine</div>
                <div className="text-[10px] text-muted-foreground">Atomic Transaction Router</div>
              </div>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-primary/15 text-primary border border-primary/30">
              Zero-Loss Quota
            </span>
          </div>

          {/* Micro-metrics visual grid */}
          <div className="grid grid-cols-3 gap-2 text-[10px] font-mono">
            <div className="p-2 rounded bg-surface-1 border border-border/60 flex flex-col gap-0.5">
              <span className="text-muted-foreground text-[9px] uppercase">Routing</span>
              <span className="text-foreground font-semibold">Active Model</span>
            </div>
            <div className="p-2 rounded bg-surface-1 border border-border/60 flex flex-col gap-0.5">
              <span className="text-muted-foreground text-[9px] uppercase">Telemetry</span>
              <span className="text-foreground font-semibold">Live SSE</span>
            </div>
            <div className="p-2 rounded bg-surface-1 border border-border/60 flex flex-col gap-0.5">
              <span className="text-muted-foreground text-[9px] uppercase">Storage</span>
              <span className="text-foreground font-semibold">Postgres + Redis</span>
            </div>
          </div>
        </motion.div>

        {/* Dynamic Data Transmission Beam 2 */}
        <div className="w-0.5 h-3 bg-gradient-to-b from-primary/80 to-primary/20 rounded-full" />

        {/* Layer 3: Upstream Providers Topology (Bottom) */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          whileHover={{ translateY: -2, translateZ: 8 }}
          className="w-full rounded-lg border border-border bg-surface-1/90 p-3.5 shadow-lg backdrop-blur-sm"
        >
          <div className="flex items-center justify-between text-xs font-mono mb-2">
            <div className="flex items-center gap-2">
              <Database className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="font-semibold text-foreground">Upstream Providers</span>
            </div>
            <span className="text-[11px] text-muted-foreground font-mono flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-status-success" />
              Active Topology
            </span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-[10px] font-mono text-center">
            <div className="py-1.5 px-2 rounded bg-surface-base border border-border/60 text-muted-foreground flex items-center justify-center gap-1">
              <Server className="h-3 w-3 text-primary" />
              <span>OpenAI</span>
            </div>
            <div className="py-1.5 px-2 rounded bg-surface-base border border-border/60 text-muted-foreground flex items-center justify-center gap-1">
              <Cpu className="h-3 w-3 text-primary" />
              <span>Anthropic</span>
            </div>
            <div className="py-1.5 px-2 rounded bg-surface-base border border-border/60 text-muted-foreground flex items-center justify-center gap-1">
              <Server className="h-3 w-3 text-primary" />
              <span>Custom V1</span>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Decorative hairline corner markers */}
      <div className="absolute top-3 left-3 text-[9px] font-mono text-muted-foreground/60 select-none">
        PLANE: AXIS-Z
      </div>
      <div className="absolute bottom-3 right-3 text-[9px] font-mono text-muted-foreground/60 select-none">
        ORQ CORE v1.0
      </div>
    </div>
  )
}
