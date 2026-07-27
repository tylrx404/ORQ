import { GlobalLayout } from "./layouts/GlobalLayout"
import { GlassCard } from "./components/ui/glass-card"
import { Cpu } from "lucide-react"

export default function App() {
  return (
    <GlobalLayout>
      <div className="h-full flex items-center justify-center min-h-[500px]">
        <GlassCard className="max-w-md w-full p-12 text-center shadow-2xl relative overflow-hidden group border-white/10 bg-zinc-950/50 backdrop-blur-2xl">
          <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/10 to-blue-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
          <div className="mx-auto w-16 h-16 rounded-2xl bg-zinc-900/50 flex items-center justify-center mb-8 border border-white/5 shadow-inner group-hover:border-cyan-500/30 group-hover:shadow-[0_0_30px_rgba(6,182,212,0.2)] transition-all duration-500">
            <Cpu className="w-8 h-8 text-cyan-400" />
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight mb-2 text-white">
            ORQ
          </h1>
          <h2 className="text-xl font-medium text-zinc-300 mb-4 tracking-wide">
            AI Agent Control Plane
          </h2>
          <p className="text-sm tracking-widest text-cyan-500/80 uppercase font-bold">
            Engineering Foundation
          </p>
        </GlassCard>
      </div>
    </GlobalLayout>
  )
}
