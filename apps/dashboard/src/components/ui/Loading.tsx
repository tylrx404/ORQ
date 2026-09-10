import * as React from "react"
import { cn } from "../../utils/cn"

export function Spinner({
  size = "md",
  className,
}: {
  size?: "sm" | "md" | "lg"
  className?: string
}) {
  const sizeClasses = {
    sm: "h-3.5 w-3.5 border-2",
    md: "h-5 w-5 border-2",
    lg: "h-8 w-8 border-3",
  }

  return (
    <div
      className={cn(
        "inline-block animate-spin rounded-full border-primary border-t-transparent",
        sizeClasses[size],
        className
      )}
      role="status"
      aria-label="loading"
    />
  )
}

export function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded bg-surface-2", className)}
      {...props}
    />
  )
}

export function LoadingOverlay({
  message = "Loading...",
}: {
  message?: string
}) {
  return (
    <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-background/60 backdrop-blur-xs gap-3">
      <Spinner size="md" />
      <p className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
        {message}
      </p>
    </div>
  )
}

export function PageLoading() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] w-full gap-4">
      <Spinner size="lg" />
      <p className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
        Initializing workspace...
      </p>
    </div>
  )
}
