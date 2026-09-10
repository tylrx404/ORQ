import * as React from "react"
import { NavLink, Link } from "react-router-dom"
import {
  LayoutDashboard,
  Terminal,
  Cpu,
  Server,
  Key,
  ListTree,
  BarChart3,
  Gauge,
  Settings,
  X,
  Layers,
} from "lucide-react"
import { cn } from "../../utils/cn"

interface NavItemConfig {
  name: string
  to: string
  icon: React.ComponentType<{ className?: string }>
}

interface NavGroupConfig {
  title: string
  items: NavItemConfig[]
}

const NAVIGATION_GROUPS: NavGroupConfig[] = [
  {
    title: "Core",
    items: [
      { name: "Overview", to: "/app", icon: LayoutDashboard },
      { name: "Playground", to: "/app/playground", icon: Terminal },
    ],
  },
  {
    title: "Infrastructure",
    items: [
      { name: "Models", to: "/app/models", icon: Cpu },
      { name: "Providers", to: "/app/providers", icon: Server },
      { name: "API Keys", to: "/app/api-keys", icon: Key },
    ],
  },
  {
    title: "Observability",
    items: [
      { name: "Executions", to: "/app/executions", icon: ListTree },
      { name: "Usage", to: "/app/usage", icon: BarChart3 },
      { name: "Quotas", to: "/app/quotas", icon: Gauge },
    ],
  },
  {
    title: "System",
    items: [{ name: "Settings", to: "/app/settings", icon: Settings }],
  },
]

export interface SidebarProps {
  isOpen?: boolean
  onClose?: () => void
}

export function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-xs md:hidden"
          aria-hidden="true"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={cn(
          "fixed top-0 bottom-0 left-0 z-40 w-64 surface-card border-r border-border flex flex-col transition-transform duration-200 ease-in-out md:translate-x-0 md:static",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Brand Header */}
        <div className="h-14 flex items-center justify-between px-5 border-b border-border/60">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="flex h-7 w-7 items-center justify-center rounded bg-primary/10 border border-primary/30 text-primary group-hover:border-primary/60 transition-colors">
              <Layers className="h-4 w-4" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5">
                <span className="font-mono font-bold tracking-tight text-sm text-foreground">
                  ORQ
                </span>
                <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-surface-2 border border-border text-muted-foreground uppercase">
                  v1.0
                </span>
              </div>
              <span className="text-[10px] font-mono text-muted-foreground tracking-wider uppercase">
                Control Plane
              </span>
            </div>
          </Link>

          {onClose && (
            <button
              onClick={onClose}
              className="p-1 rounded text-muted-foreground hover:text-foreground md:hidden"
              aria-label="Close navigation"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Navigation Items */}
        <div className="flex-1 py-4 px-3 overflow-y-auto custom-scrollbar space-y-6">
          {NAVIGATION_GROUPS.map((group) => (
            <div key={group.title} className="space-y-1">
              <div className="px-3 pb-1 text-[10px] font-mono font-medium text-muted-foreground uppercase tracking-widest select-none">
                {group.title}
              </div>
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      onClick={onClose}
                      end={item.to === "/app"}
                      className={({ isActive }) =>
                        cn(
                          "relative flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors select-none group",
                          isActive
                            ? "bg-surface-2 text-foreground font-semibold"
                            : "text-muted-foreground hover:bg-surface-2/60 hover:text-foreground"
                        )
                      }
                    >
                      {({ isActive }) => (
                        <>
                          {isActive && (
                            <span
                              className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-r bg-primary"
                              aria-hidden="true"
                            />
                          )}
                          <Icon
                            className={cn(
                              "h-4 w-4 shrink-0 transition-colors",
                              isActive
                                ? "text-primary"
                                : "text-muted-foreground group-hover:text-foreground"
                            )}
                          />
                          <span>{item.name}</span>
                        </>
                      )}
                    </NavLink>
                  )
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Sidebar Footer / System Badge */}
        <div className="p-3 border-t border-border/60">
          <div className="flex items-center justify-between px-3 py-2 rounded bg-surface-base border border-border/40 text-[11px] font-mono">
            <span className="text-muted-foreground">Engine</span>
            <div className="flex items-center gap-1.5 text-status-success">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-status-success" />
              <span>Active</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}
