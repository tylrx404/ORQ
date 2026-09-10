import * as React from "react"
import { motion, AnimatePresence } from "framer-motion"
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react"
import { cn } from "../../utils/cn"
import { _toastListeners, type ToastData } from "./toast-fn"

export type { ToastData }

function ToastItem({
  id,
  message,
  type = "default",
  onClose,
}: ToastData & { onClose: (id: string) => void }) {
  React.useEffect(() => {
    const timer = setTimeout(() => onClose(id), 4000)
    return () => clearTimeout(timer)
  }, [id, onClose])

  const iconMap = {
    default: <Info className="h-4 w-4 text-muted-foreground shrink-0" />,
    info: <Info className="h-4 w-4 text-primary shrink-0" />,
    success: <CheckCircle2 className="h-4 w-4 text-status-success shrink-0" />,
    error: <AlertCircle className="h-4 w-4 text-status-error shrink-0" />,
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.96, transition: { duration: 0.15 } }}
      transition={{ duration: 0.15, ease: "easeOut" }}
      layout
      className={cn(
        "surface-elevated px-4 py-3 rounded-md flex items-center gap-3 shadow-lg border border-border-strong text-foreground text-xs font-medium max-w-sm"
      )}
    >
      {iconMap[type]}
      <span className="flex-1 text-foreground leading-normal">{message}</span>
      <button
        onClick={() => onClose(id)}
        className="text-muted-foreground hover:text-foreground p-0.5 rounded transition-colors"
        aria-label="Dismiss notification"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </motion.div>
  )
}

export function Toaster() {
  const [toasts, setToasts] = React.useState<ToastData[]>([])

  React.useEffect(() => {
    const listener = (t: ToastData) => setToasts((prev) => [...prev, t])
    _toastListeners.add(listener)
    return () => {
      _toastListeners.delete(listener)
    }
  }, [])

  const removeToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return (
    <div
      aria-live="polite"
      className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none"
    >
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
