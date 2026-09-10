import * as React from "react"
import {
  Menu,
  Search,
  User,
  Settings,
  LogOut,
  ChevronDown,
  Activity,
} from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { CommandPalette } from "../ui/command-palette"
import { showToast } from "../ui/toast-fn"
import { useLocation } from "react-router-dom"

export interface TopNavProps {
  onOpenMobileMenu?: () => void
}

const ROUTE_NAMES: Record<string, string> = {
  "/": "Overview",
  "/playground": "Playground",
  "/models": "Models",
  "/providers": "Providers",
  "/api-keys": "API Keys",
  "/executions": "Executions",
  "/usage": "Usage Analytics",
  "/quotas": "Quotas & Limits",
  "/settings": "Settings",
}

export function TopNav({ onOpenMobileMenu }: TopNavProps) {
  const [isUserMenuOpen, setIsUserMenuOpen] = React.useState(false)
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = React.useState(false)
  const location = useLocation()

  // Listen for Cmd+K or Ctrl+K shortcut
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        setIsCommandPaletteOpen((prev) => !prev)
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [])

  const currentRouteName = ROUTE_NAMES[location.pathname] || "Control Plane"

  return (
    <>
      <header className="h-14 surface-card border-b border-border flex items-center justify-between px-4 sm:px-6 relative z-30 shrink-0">
        {/* Left: Mobile Toggle & Route Breadcrumb */}
        <div className="flex items-center gap-3">
          {onOpenMobileMenu && (
            <button
              onClick={onOpenMobileMenu}
              className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-surface-2 md:hidden"
              aria-label="Open navigation menu"
            >
              <Menu className="h-5 w-5" />
            </button>
          )}

          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-muted-foreground hidden sm:inline">ORQ</span>
            <span className="text-border-strong hidden sm:inline">/</span>
            <span className="text-foreground font-medium font-sans text-sm">
              {currentRouteName}
            </span>
          </div>
        </div>

        {/* Center/Right Actions */}
        <div className="flex items-center gap-3">
          {/* Quick Search Button */}
          <button
            onClick={() => setIsCommandPaletteOpen(true)}
            className="flex items-center gap-2.5 h-8 px-2.5 rounded-md bg-surface-base border border-border text-muted-foreground hover:text-foreground hover:border-border-strong transition-colors cursor-pointer text-xs select-none"
            aria-label="Search or run command"
          >
            <Search className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Quick search...</span>
            <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-2 border border-border-strong text-muted-foreground">
              ⌘K
            </kbd>
          </button>

          {/* System Health Beacon */}
          <div className="hidden lg:flex items-center gap-2 px-2.5 py-1 rounded-md bg-surface-base border border-border text-xs font-mono">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-status-success opacity-40" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-status-success" />
            </span>
            <span className="text-muted-foreground text-[11px]">System Online</span>
          </div>

          {/* User Menu Dropdown */}
          <div className="relative">
            <button
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              className="flex items-center gap-2 p-1 rounded-md hover:bg-surface-2 transition-colors cursor-pointer select-none"
              aria-expanded={isUserMenuOpen}
              aria-label="User profile menu"
            >
              <div className="h-7 w-7 rounded bg-surface-2 border border-border flex items-center justify-center text-xs font-mono font-semibold text-primary">
                OP
              </div>
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground hidden sm:block" />
            </button>

            <AnimatePresence>
              {isUserMenuOpen && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setIsUserMenuOpen(false)}
                  />
                  <motion.div
                    initial={{ opacity: 0, y: 6, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 6, scale: 0.98 }}
                    transition={{ duration: 0.12, ease: "easeOut" }}
                    className="absolute right-0 top-full mt-2 w-52 rounded-md surface-elevated border border-border shadow-xl z-50 py-1"
                  >
                    <div className="px-3 py-2 border-b border-border/60">
                      <p className="text-xs font-semibold text-foreground">
                        Operator
                      </p>
                      <p className="text-[11px] font-mono text-muted-foreground truncate">
                        admin@orq.ai
                      </p>
                    </div>

                    <div className="py-1">
                      <button
                        onClick={() => {
                          showToast("Profile settings: Ready in dashboard phase", "info")
                          setIsUserMenuOpen(false)
                        }}
                        className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-foreground hover:bg-surface-2 transition-colors cursor-pointer"
                      >
                        <User className="h-3.5 w-3.5 text-muted-foreground" />
                        <span>Profile</span>
                      </button>

                      <button
                        onClick={() => {
                          showToast("Gateway health: 200 OK (Postgres + Redis connected)", "success")
                          setIsUserMenuOpen(false)
                        }}
                        className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-foreground hover:bg-surface-2 transition-colors cursor-pointer"
                      >
                        <Activity className="h-3.5 w-3.5 text-muted-foreground" />
                        <span>Gateway Status</span>
                      </button>

                      <button
                        onClick={() => {
                          showToast("Settings: Ready in dashboard phase", "info")
                          setIsUserMenuOpen(false)
                        }}
                        className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-foreground hover:bg-surface-2 transition-colors cursor-pointer"
                      >
                        <Settings className="h-3.5 w-3.5 text-muted-foreground" />
                        <span>Settings</span>
                      </button>
                    </div>

                    <div className="border-t border-border/60 my-1" />

                    <div className="px-1">
                      <button
                        disabled
                        className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-muted-foreground/50 cursor-not-allowed select-none"
                      >
                        <LogOut className="h-3.5 w-3.5" />
                        <span>Sign Out</span>
                      </button>
                    </div>
                  </motion.div>
                </>
              )}
            </AnimatePresence>
          </div>
        </div>
      </header>

      {/* Global Command Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
      />
    </>
  )
}
