import * as React from "react"
import { Activity, Box, Settings, Cpu } from "lucide-react"
import { cn } from "../../utils/cn"
import { toast } from "../ui/toast"

export function Sidebar() {
  return (
    <aside className="w-64 flex-col hidden md:flex glass-panel border-y-0 border-l-0 rounded-none border-r border-white/10 relative z-20 shadow-xl bg-zinc-950/60 backdrop-blur-2xl">
      <div className="h-16 flex items-center px-6 border-b border-white/10">
        <div className="flex items-center gap-3 font-bold tracking-widest text-lg text-white">
          <div className="p-1.5 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 shadow-[0_0_15px_rgba(6,182,212,0.2)]">
            <Cpu className="w-5 h-5 text-cyan-400" />
          </div>
          <span>ORQ</span>
        </div>
      </div>
      <div className="flex-1 py-6 flex flex-col gap-1.5 px-3 custom-scrollbar overflow-y-auto">
        <div className="px-3 pb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Platform</div>
        <NavItem icon={<Activity className="w-4 h-4" />} label="Control Plane" active onClick={() => toast("Already on Control Plane")} />
        <NavItem icon={<Box className="w-4 h-4" />} label="Agents" onClick={() => toast("Coming Soon — Available in a future phase.")} />
        <NavItem icon={<Settings className="w-4 h-4" />} label="Settings" onClick={() => toast("Coming Soon — Available in a future phase.")} />
      </div>
    </aside>
  )
}

function NavItem({ icon, label, active, onClick }: { icon: React.ReactNode, label: string, active?: boolean, onClick?: () => void }) {
  return (
    <button 
      onClick={onClick}
      className={cn(
        "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all text-left group relative outline-none focus-visible:ring-2 focus-visible:ring-cyan-500",
        active ? "bg-cyan-500/10 text-cyan-400" : "text-zinc-400 hover:bg-white/5 hover:text-white"
      )}
    >
      {active && <span className="absolute left-0 w-1 h-5 bg-cyan-400 rounded-r-full shadow-[0_0_8px_rgba(6,182,212,0.8)]" />}
      <span className={cn("transition-colors", active ? "text-cyan-400" : "text-zinc-500 group-hover:text-zinc-300")}>
        {icon}
      </span>
      {label}
    </button>
  )
}
