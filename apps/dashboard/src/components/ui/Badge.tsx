import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "../../utils/cn"

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 font-medium border select-none transition-colors",
  {
    variants: {
      variant: {
        neutral:
          "bg-surface-2 text-muted-foreground border-border",
        default:
          "bg-surface-2 text-foreground border-border-strong",
        primary:
          "bg-primary/10 text-primary border-primary/30",
        success:
          "bg-status-success/10 text-status-success border-status-success/30",
        warning:
          "bg-status-warning/10 text-status-warning border-status-warning/30",
        error:
          "bg-status-error/10 text-status-error border-status-error/30",
        outline:
          "bg-transparent text-foreground border-border-strong",
      },
      size: {
        sm: "text-[11px] px-2 py-0.5 rounded font-mono tracking-tight",
        md: "text-xs px-2.5 py-1 rounded-md font-mono",
      },
    },
    defaultVariants: {
      variant: "neutral",
      size: "sm",
    },
  }
)

const dotColorMap = {
  neutral: "bg-muted-foreground",
  default: "bg-foreground",
  primary: "bg-primary",
  success: "bg-status-success",
  warning: "bg-status-warning",
  error: "bg-status-error",
  outline: "bg-muted-foreground",
}

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  withDot?: boolean
  pulse?: boolean
}

export function Badge({
  className,
  variant = "neutral",
  size,
  withDot = false,
  pulse = false,
  children,
  ...props
}: BadgeProps) {
  const dotColor = dotColorMap[variant || "neutral"]

  return (
    <span className={cn(badgeVariants({ variant, size, className }))} {...props}>
      {withDot && (
        <span className="relative flex h-1.5 w-1.5 shrink-0">
          {pulse && (
            <span
              className={cn(
                "absolute inline-flex h-full w-full animate-ping rounded-full opacity-75",
                dotColor
              )}
            />
          )}
          <span className={cn("relative inline-flex h-1.5 w-1.5 rounded-full", dotColor)} />
        </span>
      )}
      {children}
    </span>
  )
}
