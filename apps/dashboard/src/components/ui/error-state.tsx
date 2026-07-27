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
