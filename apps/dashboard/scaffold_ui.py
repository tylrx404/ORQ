import os

files = {}

files["tailwind.config.js"] = """/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        aurora: {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
      },
      animation: {
        aurora: "aurora 15s ease infinite",
      },
    },
  },
  plugins: [],
}
"""

files["postcss.config.js"] = """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
"""

files["src/utils/cn.ts"] = """import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
"""

files["src/styles/index.css"] = """@tailwind base;
@tailwind components;
@tailwind utilities;
 
@layer base {
  :root {
    --background: 240 10% 3.9%;
    --foreground: 0 0% 98%;
    --card: 240 10% 3.9%;
    --card-foreground: 0 0% 98%;
    --popover: 240 10% 3.9%;
    --popover-foreground: 0 0% 98%;
    --primary: 0 0% 98%;
    --primary-foreground: 240 5.9% 10%;
    --secondary: 240 3.7% 15.9%;
    --secondary-foreground: 0 0% 98%;
    --muted: 240 3.7% 15.9%;
    --muted-foreground: 240 5% 64.9%;
    --accent: 240 3.7% 15.9%;
    --accent-foreground: 0 0% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 0 0% 98%;
    --border: 240 3.7% 15.9%;
    --input: 240 3.7% 15.9%;
    --ring: 240 4.9% 83.9%;
    --radius: 1rem;
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
    #0f172a,
    #31103c,
    #0b213b,
    #0f172a
  );
  background-size: 400% 400%;
  animation: aurora 15s ease infinite;
}

.glass-panel {
  @apply bg-white/5 backdrop-blur-xl border border-white/10 shadow-[0_4px_24px_-8px_rgba(0,0,0,0.5)];
}
"""

files["src/providers/ThemeProvider.tsx"] = """import React, { createContext, useContext, useEffect } from "react"

type Theme = "dark"

const ThemeContext = createContext<{ theme: Theme }>({ theme: "dark" })

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const root = window.document.documentElement
    root.classList.add("dark")
  }, [])

  return (
    <ThemeContext.Provider value={{ theme: "dark" }}>
      {children}
    </ThemeContext.Provider>
  )
}

export const useTheme = () => useContext(ThemeContext)
"""

files["src/components/ui/glass-card.tsx"] = """import * as React from "react"
import { cn } from "../../utils/cn"

const GlassCard = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "rounded-2xl glass-panel text-card-foreground p-6",
        className
      )}
      {...props}
    />
  )
)
GlassCard.displayName = "GlassCard"

export { GlassCard }
"""

files["src/components/ui/glass-button.tsx"] = """import * as React from "react"
import { cn } from "../../utils/cn"
import { motion } from "framer-motion"

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {}

const GlassButton = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, ...props }, ref) => {
    return (
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center whitespace-nowrap rounded-xl text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
          "glass-panel hover:bg-white/10 h-10 px-6 py-2",
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

files["src/components/ui/glass-input.tsx"] = """import * as React from "react"
import { cn } from "../../utils/cn"

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

const GlassInput = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-10 w-full rounded-xl glass-panel bg-transparent px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-transparent disabled:cursor-not-allowed disabled:opacity-50 transition-all",
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

files["src/components/ui/modal.tsx"] = """import * as React from "react"
import { motion, AnimatePresence } from "framer-motion"
import { X } from "lucide-react"
import { GlassCard } from "./glass-card"

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  children: React.ReactNode
}

export function Modal({ isOpen, onClose, children }: ModalProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ duration: 0.2 }}
              className="pointer-events-auto w-full max-w-lg p-4"
            >
              <GlassCard className="relative overflow-hidden p-0">
                <button
                  onClick={onClose}
                  className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none"
                >
                  <X className="h-4 w-4" />
                </button>
                <div className="p-6">{children}</div>
              </GlassCard>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  )
}
"""

files["src/components/ui/command-palette.tsx"] = """import * as React from "react"
import { Search } from "lucide-react"
import { Modal } from "./modal"

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <div className="flex items-center gap-3 border-b border-white/10 pb-4">
        <Search className="h-5 w-5 text-muted-foreground" />
        <input
          className="flex h-10 w-full rounded-md bg-transparent text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
          placeholder="Type a command or search..."
          autoFocus
        />
      </div>
      <div className="py-4 text-center text-sm text-muted-foreground">
        No results found.
      </div>
    </Modal>
  )
}
"""

files["src/components/ui/toast.tsx"] = """import * as React from "react"
import { motion, AnimatePresence } from "framer-motion"
import { GlassCard } from "./glass-card"

export interface ToastProps {
  id: string
  message: string
  type?: "default" | "error" | "success"
  onClose: (id: string) => void
}

export function Toast({ id, message, type = "default", onClose }: ToastProps) {
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
      <GlassCard className="px-6 py-4 rounded-xl flex items-center gap-3 shadow-xl">
        <span className={type === "error" ? "text-red-400" : type === "success" ? "text-emerald-400" : ""}>
          {message}
        </span>
      </GlassCard>
    </motion.div>
  )
}

export function ToastContainer({ toasts, removeToast }: { toasts: any[], removeToast: any }) {
  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3">
      <AnimatePresence>
        {toasts.map((toast) => (
          <Toast key={toast.id} {...toast} onClose={removeToast} />
        ))}
      </AnimatePresence>
    </div>
  )
}
"""

files["src/components/ui/skeleton.tsx"] = """import * as React from "react"
import { cn } from "../../utils/cn"

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-white/10", className)}
      {...props}
    />
  )
}

export { Skeleton }
"""

files["src/components/ui/empty-state.tsx"] = """import * as React from "react"
import { Box } from "lucide-react"

export function EmptyState({ title = "No data found", description = "Get started by creating a new resource." }: { title?: string, description?: string }) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      <div className="flex h-20 w-20 items-center justify-center rounded-full bg-white/5 mb-6">
        <Box className="h-10 w-10 text-muted-foreground" />
      </div>
      <h3 className="text-xl font-semibold tracking-tight">{title}</h3>
      <p className="text-sm text-muted-foreground mt-2 max-w-sm">{description}</p>
    </div>
  )
}
"""

files["src/components/ui/error-state.tsx"] = """import * as React from "react"
import { AlertCircle } from "lucide-react"
import { GlassButton } from "./glass-button"

export function ErrorState({ title = "Something went wrong", onRetry }: { title?: string, onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      <div className="flex h-20 w-20 items-center justify-center rounded-full bg-red-500/10 mb-6 text-red-500">
        <AlertCircle className="h-10 w-10" />
      </div>
      <h3 className="text-xl font-semibold tracking-tight">{title}</h3>
      {onRetry && (
        <GlassButton className="mt-6" onClick={onRetry}>
          Try again
        </GlassButton>
      )}
    </div>
  )
}
"""

files["src/components/layout/Sidebar.tsx"] = """import * as React from "react"
import { Activity, Box, Settings, Cpu } from "lucide-react"
import { cn } from "../../utils/cn"

export function Sidebar() {
  return (
    <aside className="w-64 flex-col hidden md:flex glass-panel border-r-0 rounded-none border-r border-white/5 relative z-10">
      <div className="h-16 flex items-center px-6 border-b border-white/5">
        <div className="flex items-center gap-2 font-bold tracking-widest text-lg">
          <Cpu className="w-5 h-5 text-indigo-400" />
          <span>ORQ</span>
        </div>
      </div>
      <div className="flex-1 py-6 flex flex-col gap-2 px-3">
        <NavItem icon={<Activity className="w-4 h-4" />} label="Control Plane" active />
        <NavItem icon={<Box className="w-4 h-4" />} label="Agents" />
        <NavItem icon={<Settings className="w-4 h-4" />} label="Settings" />
      </div>
    </aside>
  )
}

function NavItem({ icon, label, active }: { icon: React.ReactNode, label: string, active?: boolean }) {
  return (
    <button className={cn(
      "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all text-left",
      active ? "bg-white/10 text-white" : "text-muted-foreground hover:bg-white/5 hover:text-white"
    )}>
      {icon}
      {label}
    </button>
  )
}
"""

files["src/components/layout/TopNav.tsx"] = """import * as React from "react"
import { Bell, Search } from "lucide-react"

export function TopNav() {
  return (
    <header className="h-16 glass-panel border-b-0 rounded-none border-b border-white/5 flex items-center justify-between px-6 relative z-10">
      <div className="flex items-center gap-4 flex-1">
        <button className="flex items-center gap-2 text-sm text-muted-foreground bg-white/5 hover:bg-white/10 transition-colors px-3 py-1.5 rounded-md border border-white/5">
          <Search className="w-4 h-4" />
          <span>Search...</span>
          <kbd className="ml-4 text-[10px] px-1.5 py-0.5 rounded bg-white/10 font-mono">⌘K</kbd>
        </button>
      </div>
      <div className="flex items-center gap-4">
        <button className="text-muted-foreground hover:text-white transition-colors relative">
          <Bell className="w-5 h-5" />
          <span className="absolute top-0 right-0 w-2 h-2 bg-indigo-500 rounded-full border border-background"></span>
        </button>
        <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center text-xs font-bold shadow-lg">
          US
        </div>
      </div>
    </header>
  )
}
"""

files["src/layouts/GlobalLayout.tsx"] = """import * as React from "react"
import { Sidebar } from "../components/layout/Sidebar"
import { TopNav } from "../components/layout/TopNav"

export function GlobalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen w-full overflow-hidden aurora-bg text-foreground">
      <Sidebar />
      <div className="flex flex-col flex-1 h-full relative">
        <TopNav />
        <main className="flex-1 overflow-y-auto p-8 relative z-0">
          {children}
        </main>
      </div>
    </div>
  )
}
"""

files["src/App.tsx"] = """import * as React from "react"
import { GlobalLayout } from "./layouts/GlobalLayout"
import { GlassCard } from "./components/ui/glass-card"
import { Cpu } from "lucide-react"

export default function App() {
  return (
    <GlobalLayout>
      <div className="h-full flex items-center justify-center min-h-[500px]">
        <GlassCard className="max-w-md w-full p-12 text-center shadow-2xl relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 to-purple-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
          <div className="mx-auto w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mb-8 border border-white/10 shadow-inner">
            <Cpu className="w-8 h-8 text-indigo-400" />
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight mb-2 bg-gradient-to-br from-white to-white/50 bg-clip-text text-transparent">
            ORQ
          </h1>
          <h2 className="text-xl font-medium text-white/80 mb-4 tracking-wide">
            AI Agent Control Plane
          </h2>
          <p className="text-sm tracking-widest text-muted-foreground uppercase font-semibold">
            Engineering Foundation
          </p>
        </GlassCard>
      </div>
    </GlobalLayout>
  )
}
"""

files["src/main.tsx"] = """import React from "react"
import ReactDOM from "react-dom/client"
import App from "./App.tsx"
import { ThemeProvider } from "./providers/ThemeProvider.tsx"
import "./styles/index.css"

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </React.StrictMode>
)
"""

files["index.html"] = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>ORQ - AI Agent Control Plane</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""

for path, content in files.items():
    full_path = os.path.join("c:/Users/Lenovo/OneDrive/Desktop/ORQ/apps/dashboard", path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("UI components generated successfully.")
