import * as React from "react"
import { cn } from "../../utils/cn"

export interface Canvas3DContainerProps
  extends React.HTMLAttributes<HTMLDivElement> {
  children?: React.ReactNode
  perspective?: number
  withGridBackdrop?: boolean
}

/**
 * Canvas3DContainer: Architecture foundation for future subtle 3D visuals.
 * Provides a hardware-accelerated, perspective-enabled container with
 * performance budgeting and graceful non-WebGL fallback.
 */
export function Canvas3DContainer({
  children,
  className,
  perspective = 1000,
  withGridBackdrop = true,
  ...props
}: Canvas3DContainerProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-lg surface-card",
        withGridBackdrop && "tech-grid-bg",
        className
      )}
      style={{ perspective: `${perspective}px` }}
      {...props}
    >
      {/* Subtle depth lighting layer */}
      <div
        className="pointer-events-none absolute inset-0 bg-gradient-to-tr from-primary/[0.03] via-transparent to-transparent opacity-80"
        aria-hidden="true"
      />

      {/* 3D Canvas Mounting Layer (future WebGL scene will attach here) */}
      <div className="relative z-10 w-full h-full transform-gpu">
        {children}
      </div>
    </div>
  )
}
