import * as React from "react"
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
