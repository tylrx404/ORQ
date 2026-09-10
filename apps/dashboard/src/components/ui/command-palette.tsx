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
  { name: "Overview", path: "/app", category: "Core" },
  { name: "Playground", path: "/app/playground", category: "Core" },
  { name: "Models", path: "/app/models", category: "Infrastructure" },
  { name: "Providers", path: "/app/providers", category: "Infrastructure" },
  { name: "API Keys", path: "/app/api-keys", category: "Infrastructure" },
  { name: "Executions", path: "/app/executions", category: "Observability" },
  { name: "Usage Analytics", path: "/app/usage", category: "Observability" },
  { name: "Quotas", path: "/app/quotas", category: "Observability" },
  { name: "Organization Settings", path: "/app/settings", category: "System" },
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
  }

  // Reset search when dialog opens/closes
  React.useEffect(() => {
    if (!isOpen) setQuery("")
  }, [isOpen])

  return (
    <Dialog isOpen={isOpen} onClose={onClose} maxWidth="lg" className="overflow-hidden" contentClassName="p-0">
      {/* Search Bar Input */}
      <div className="flex items-center px-4 border-b border-border/80 bg-surface-1">
        <Search className="h-4 w-4 text-muted-foreground shrink-0 mr-3" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Type a command or search sections..."
          className="w-full py-3.5 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none font-sans"
          autoFocus
        />
        <kbd className="hidden sm:inline-block text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-2 border border-border-strong text-muted-foreground select-none">
          ESC
        </kbd>
      </div>

      {/* Results List */}
      <div className="max-h-80 overflow-y-auto custom-scrollbar p-2 space-y-1">
        {filtered.length === 0 ? (
          <div className="py-8 text-center text-xs text-muted-foreground font-mono">
            No matching navigation items found.
          </div>
        ) : (
          filtered.map((item) => (
            <button
              key={item.path}
              onClick={() => handleSelect(item.path)}
              className="w-full flex items-center justify-between px-3 py-2.5 rounded-md hover:bg-surface-2 text-left transition-colors cursor-pointer group select-none"
            >
              <span className="text-xs font-medium text-foreground group-hover:text-primary transition-colors">
                {item.name}
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-1 border border-border text-muted-foreground">
                {item.category}
              </span>
            </button>
          ))
        )}
      </div>
    </Dialog>
  )
}
