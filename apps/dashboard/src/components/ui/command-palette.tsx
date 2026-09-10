import * as React from "react"
import { Search } from "lucide-react"
import { Dialog } from "./Dialog"
import { useNavigate } from "react-router-dom"

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
}

interface CommandItem {
  name: string
  path: string
  category: string
}

const COMMAND_ITEMS: CommandItem[] = [
  { name: "Overview", path: "/", category: "Core" },
  { name: "Playground", path: "/playground", category: "Core" },
  { name: "Models", path: "/models", category: "Infrastructure" },
  { name: "Providers", path: "/providers", category: "Infrastructure" },
  { name: "API Keys", path: "/api-keys", category: "Infrastructure" },
  { name: "Executions", path: "/executions", category: "Observability" },
  { name: "Usage Analytics", path: "/usage", category: "Observability" },
  { name: "Quotas", path: "/quotas", category: "Observability" },
  { name: "Organization Settings", path: "/settings", category: "System" },
]

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [query, setQuery] = React.useState("")
  const navigate = useNavigate()

  const filtered = React.useMemo(() => {
    if (!query.trim()) return COMMAND_ITEMS
    const q = query.toLowerCase()
    return COMMAND_ITEMS.filter(
      (item) =>
        item.name.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q)
    )
  }, [query])

  const handleSelect = (path: string) => {
    navigate(path)
    onClose()
    setQuery("")
  }

  return (
    <Dialog isOpen={isOpen} onClose={onClose} maxWidth="lg">
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-3 border-b border-border pb-3 px-1">
          <Search className="h-4 w-4 text-muted-foreground shrink-0" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none font-sans"
            placeholder="Search navigation or commands..."
            autoFocus
          />
          <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-2 border border-border text-muted-foreground">
            ESC
          </kbd>
        </div>

        <div className="max-h-72 overflow-y-auto space-y-1 custom-scrollbar py-1">
          {filtered.length === 0 ? (
            <div className="py-8 text-center text-xs text-muted-foreground font-mono">
              No matching commands or navigation paths found.
            </div>
          ) : (
            filtered.map((item) => (
              <button
                key={item.path}
                onClick={() => handleSelect(item.path)}
                className="w-full flex items-center justify-between px-3 py-2 rounded text-xs text-left hover:bg-surface-2 transition-colors group cursor-pointer"
              >
                <span className="font-medium text-foreground group-hover:text-primary transition-colors">
                  {item.name}
                </span>
                <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">
                  {item.category}
                </span>
              </button>
            ))
          )}
        </div>
      </div>
    </Dialog>
  )
}
