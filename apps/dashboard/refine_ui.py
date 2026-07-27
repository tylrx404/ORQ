import os

files = {}

files["src/styles/index.css"] = """@import "tailwindcss";

@custom-variant dark (&:is(.dark *));

@theme {
  --color-border: hsl(240 3.7% 15.9%);
  --color-input: hsl(240 3.7% 15.9%);
  --color-ring: hsl(199 89% 48%);
  --color-background: hsl(240 10% 3.9%);
  --color-foreground: hsl(0 0% 98%);
  --color-primary: hsl(199 89% 48%);
  --color-primary-foreground: hsl(0 0% 100%);
  --color-secondary: hsl(240 3.7% 15.9%);
  --color-secondary-foreground: hsl(0 0% 98%);
  --color-destructive: hsl(0 62.8% 30.6%);
  --color-destructive-foreground: hsl(0 0% 98%);
  --color-muted: hsl(240 3.7% 15.9%);
  --color-muted-foreground: hsl(240 5% 64.9%);
  --color-accent: hsl(199 89% 48% / 0.1);
  --color-accent-foreground: hsl(199 89% 48%);
  --color-card: hsl(240 10% 3.9%);
  --color-card-foreground: hsl(0 0% 98%);

  --radius-lg: 1rem;
  --radius-md: calc(1rem - 2px);
  --radius-sm: calc(1rem - 4px);

  --animate-aurora: aurora 20s ease infinite;

  @keyframes aurora {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground antialiased;
    font-feature-settings: "rlig" 1, "calt" 1;
  }
}

.aurora-bg {
  background: linear-gradient(
    -45deg,
    #09090b,
    #0f172a,
    #082f49,
    #09090b
  );
  background-size: 400% 400%;
  animation: aurora 20s ease infinite;
}

.glass-panel {
  @apply bg-zinc-950/40 backdrop-blur-2xl border border-white/10 shadow-[0_8px_32px_-8px_rgba(0,0,0,0.5)];
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  @apply bg-white/10 rounded-full hover:bg-white/20 transition-colors;
}
"""

files["src/components/ui/toast.tsx"] = """import * as React from "react"
import { motion, AnimatePresence } from "framer-motion"
import { GlassCard } from "./glass-card"

export interface ToastData {
  id: string
  message: string
  type?: "default" | "error" | "success"
}

let toastListener: ((toast: ToastData) => void) | null = null

export function toast(message: string, type: ToastData["type"] = "default") {
  if (toastListener) {
    toastListener({ id: Math.random().toString(36).slice(2), message, type })
  }
}

function ToastItem({ id, message, type = "default", onClose }: ToastData & { onClose: (id: string) => void }) {
  React.useEffect(() => {
    const timer = setTimeout(() => onClose(id), 5000)
    return () => clearTimeout(timer)
  }, [id, onClose])

  return (
    <motion.div
      initial={{ opacity: 0, y: 50, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
      layout
    >
      <GlassCard className="px-6 py-4 rounded-xl flex items-center gap-3 shadow-2xl border-white/20 bg-black/40">
        <span className={type === "error" ? "text-red-400" : type === "success" ? "text-cyan-400" : "text-white"}>
          {message}
        </span>
      </GlassCard>
    </motion.div>
  )
}

export function Toaster() {
  const [toasts, setToasts] = React.useState<ToastData[]>([])

  React.useEffect(() => {
    toastListener = (t) => setToasts((prev) => [...prev, t])
    return () => { toastListener = null }
  }, [])

  const removeToast = (id: string) => setToasts((prev) => prev.filter((t) => t.id !== id))

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 pointer-events-none">
      <AnimatePresence>
        {toasts.map((t) => (
          <div key={t.id} className="pointer-events-auto">
            <ToastItem {...t} onClose={removeToast} />
          </div>
        ))}
      </AnimatePresence>
    </div>
  )
}
"""

files["src/layouts/GlobalLayout.tsx"] = """import * as React from "react"
import { Sidebar } from "../components/layout/Sidebar"
import { TopNav } from "../components/layout/TopNav"
import { Toaster } from "../components/ui/toast"

export function GlobalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen w-full overflow-hidden aurora-bg text-foreground">
      <Sidebar />
      <div className="flex flex-col flex-1 h-full relative">
        <TopNav />
        <main className="flex-1 overflow-y-auto p-8 relative z-0 custom-scrollbar">
          {children}
        </main>
      </div>
      <Toaster />
    </div>
  )
}
"""

files["src/components/layout/TopNav.tsx"] = """import * as React from "react"
import { Bell, Search, User, Settings, LogOut, ChevronDown } from "lucide-react"
import { toast } from "../ui/toast"
import { motion, AnimatePresence } from "framer-motion"

export function TopNav() {
  const [isAvatarOpen, setIsAvatarOpen] = React.useState(false)

  return (
    <header className="h-16 glass-panel border-b-0 border-x-0 rounded-none border-t-0 border-b border-white/10 flex items-center justify-between px-6 relative z-30 shadow-sm">
      <div className="flex items-center gap-4 flex-1">
        <div className="relative group">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-cyan-400 transition-colors" />
          <input 
            type="text" 
            placeholder="Search..." 
            className="h-9 w-64 bg-white/5 border border-white/10 rounded-lg pl-9 pr-12 text-sm text-white placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all shadow-inner"
          />
          <kbd className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] px-1.5 py-0.5 rounded bg-white/10 font-mono text-muted-foreground pointer-events-none">⌘K</kbd>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <button 
          onClick={() => toast("No new notifications.", "default")}
          className="w-9 h-9 flex items-center justify-center rounded-full text-muted-foreground hover:text-white hover:bg-white/10 transition-colors relative"
        >
          <Bell className="w-5 h-5" />
          <span className="absolute top-2 right-2 w-1.5 h-1.5 bg-cyan-500 rounded-full shadow-[0_0_8px_rgba(6,182,212,0.8)]"></span>
        </button>
        
        <div className="relative">
          <button 
            onClick={() => setIsAvatarOpen(!isAvatarOpen)}
            className="flex items-center gap-2 hover:opacity-80 transition-opacity focus:outline-none"
          >
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-xs font-bold text-white shadow-lg ring-2 ring-white/10">
              OR
            </div>
            <ChevronDown className="w-3 h-3 text-muted-foreground" />
          </button>
          
          <AnimatePresence>
            {isAvatarOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setIsAvatarOpen(false)} />
                <motion.div 
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  transition={{ duration: 0.15 }}
                  className="absolute right-0 top-full mt-2 w-48 glass-panel border border-white/10 shadow-2xl rounded-xl overflow-hidden z-50 py-1"
                >
                  <div className="px-4 py-2 border-b border-white/10 mb-1">
                    <p className="text-sm font-medium text-white">Admin User</p>
                    <p className="text-xs text-muted-foreground">admin@orq.ai</p>
                  </div>
                  <button onClick={() => { toast("Profile: Coming Soon"); setIsAvatarOpen(false) }} className="w-full text-left px-4 py-2 text-sm text-white hover:bg-white/10 transition-colors flex items-center gap-2">
                    <User className="w-4 h-4" /> Profile
                  </button>
                  <button onClick={() => { toast("Settings: Coming Soon"); setIsAvatarOpen(false) }} className="w-full text-left px-4 py-2 text-sm text-white hover:bg-white/10 transition-colors flex items-center gap-2">
                    <Settings className="w-4 h-4" /> Settings
                  </button>
                  <div className="h-px bg-white/10 my-1" />
                  <button disabled className="w-full text-left px-4 py-2 text-sm text-muted-foreground flex items-center gap-2 opacity-50 cursor-not-allowed">
                    <LogOut className="w-4 h-4" /> Logout
                  </button>
                </motion.div>
              </>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  )
}
"""

files["src/components/layout/Sidebar.tsx"] = """import * as React from "react"
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
"""

files["src/components/ui/glass-button.tsx"] = """import * as React from "react"
import { cn } from "../../utils/cn"
import { motion, type HTMLMotionProps } from "framer-motion"

export interface ButtonProps extends HTMLMotionProps<"button"> {}

const GlassButton = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, ...props }, ref) => {
    return (
      <motion.button
        whileHover={{ scale: 1.02, y: -1 }}
        whileTap={{ scale: 0.97 }}
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center whitespace-nowrap rounded-xl text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 disabled:pointer-events-none disabled:opacity-50",
          "bg-white/5 border border-white/10 shadow-lg hover:bg-white/10 hover:border-white/20 hover:shadow-cyan-500/10 h-10 px-6 py-2 text-white",
          className
        )}
        {...props}
      />
    )
  }
)
GlassButton.displayName = "GlassButton"

export { GlassButton }
"""

files["src/components/ui/glass-card.tsx"] = """import * as React from "react"
import { cn } from "../../utils/cn"

const GlassCard = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "rounded-2xl glass-panel text-card-foreground p-6 transition-all duration-300",
        className
      )}
      {...props}
    />
  )
)
GlassCard.displayName = "GlassCard"

export { GlassCard }
"""

files["src/components/ui/glass-input.tsx"] = """import * as React from "react"
import { cn } from "../../utils/cn"

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

const GlassInput = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-10 w-full rounded-xl bg-black/20 border border-white/10 px-3 py-2 text-sm text-white shadow-inner ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-zinc-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50 focus-visible:border-cyan-500/50 disabled:cursor-not-allowed disabled:opacity-50 transition-all hover:bg-black/30",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
GlassInput.displayName = "GlassInput"

export { GlassInput }
"""

files["src/App.tsx"] = """import { GlobalLayout } from "./layouts/GlobalLayout"
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
"""

for path, content in files.items():
    full_path = os.path.join("c:/Users/Lenovo/OneDrive/Desktop/ORQ/apps/dashboard", path)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
