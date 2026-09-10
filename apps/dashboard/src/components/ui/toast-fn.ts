export interface ToastData {
  id: string
  message: string
  type?: "default" | "error" | "success" | "info"
}

type ToastListener = (toast: ToastData) => void
export const _toastListeners = new Set<ToastListener>()

export function showToast(message: string, type: ToastData["type"] = "default") {
  const t: ToastData = { id: Math.random().toString(36).slice(2), message, type }
  _toastListeners.forEach((listener) => listener(t))
}

/** Alias kept for ergonomics — prefer showToast for clarity. */
export const toast = showToast
