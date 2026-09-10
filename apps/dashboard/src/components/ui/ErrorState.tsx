import * as React from "react"
import { AlertTriangle, RefreshCw } from "lucide-react"
import { Button } from "./Button"
import { cn } from "../../utils/cn"

export interface ErrorStateProps {
  title?: string
  message?: string
  errorDetails?: string
  onRetry?: () => void
  className?: string
}

export function ErrorState({
  title = "An unexpected error occurred",
  message = "Failed to load the requested resource. Check your network connection or verify configuration.",
  errorDetails,
  onRetry,
  className,
}: ErrorStateProps) {
  const [showDetails, setShowDetails] = React.useState(false)

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-8 text-center rounded-lg surface-card border border-destructive/30 max-w-lg mx-auto my-8",
        className
      )}
    >
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-destructive/10 text-destructive mb-4 border border-destructive/20">
        <AlertTriangle className="h-5 w-5" />
      </div>
      <h3 className="text-sm font-semibold tracking-tight text-foreground">
        {title}
      </h3>
      <p className="text-xs text-muted-foreground mt-1.5 max-w-sm leading-relaxed">
        {message}
      </p>

      {errorDetails && (
        <div className="w-full mt-4 text-left">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-[11px] text-muted-foreground hover:text-foreground font-mono transition-colors underline cursor-pointer"
          >
            {showDetails ? "Hide technical details" : "View technical details"}
          </button>
          {showDetails && (
            <pre className="mt-2 p-3 rounded bg-surface-base border border-border text-[11px] font-mono text-destructive/80 overflow-x-auto whitespace-pre-wrap break-all">
              {errorDetails}
            </pre>
          )}
        </div>
      )}

      {onRetry && (
        <div className="mt-6">
          <Button
            variant="secondary"
            size="sm"
            onClick={onRetry}
            leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
          >
            Retry request
          </Button>
        </div>
      )}
    </div>
  )
}
