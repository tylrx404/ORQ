import * as React from "react"
import { cn } from "../../utils/cn"

export interface PageHeaderProps {
  eyebrow?: string
  title: string
  description?: string
  actions?: React.ReactNode
  className?: string
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        "flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-border/60",
        className
      )}
    >
      <div className="space-y-1">
        {eyebrow && (
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono font-medium text-primary uppercase tracking-widest">
              {eyebrow}
            </span>
          </div>
        )}
        <h1 className="text-xl font-bold tracking-tight text-foreground">
          {title}
        </h1>
        {description && (
          <p className="text-xs text-muted-foreground max-w-2xl leading-relaxed">
            {description}
          </p>
        )}
      </div>

      {actions && (
        <div className="flex items-center gap-2 shrink-0">{actions}</div>
      )}
    </div>
  )
}

export function PageContainer({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        "w-full max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-8 space-y-8",
        className
      )}
    >
      {children}
    </div>
  )
}
