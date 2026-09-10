import * as React from "react"
import { cn } from "../../utils/cn"

export interface EmptyStateProps {
  icon?: React.ReactNode
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-12 text-center rounded-lg surface-card border border-dashed border-border/70 max-w-lg mx-auto my-8",
        className
      )}
    >
      {icon && (
        <div className="flex h-12 w-12 items-center justify-center rounded-md bg-surface-2 border border-border text-muted-foreground mb-4">
          {icon}
        </div>
      )}
      <h3 className="text-sm font-semibold tracking-tight text-foreground">
        {title}
      </h3>
      {description && (
        <p className="text-xs text-muted-foreground mt-1.5 max-w-sm leading-relaxed">
          {description}
        </p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
