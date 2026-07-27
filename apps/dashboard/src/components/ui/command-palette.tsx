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
