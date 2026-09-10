import * as React from "react"
import { cn } from "../../utils/cn"

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
  prefixIcon?: React.ReactNode
  suffixIcon?: React.ReactNode
  shortcut?: string
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      type,
      label,
      error,
      hint,
      prefixIcon,
      suffixIcon,
      shortcut,
      id,
      ...props
    },
    ref
  ) => {
    const inputId = id || (label ? `input-${label.toLowerCase().replace(/\s+/g, "-")}` : undefined)

    return (
      <div className="w-full flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="text-xs font-medium text-muted-foreground uppercase tracking-wider select-none"
          >
            {label}
          </label>
        )}
        <div className="relative flex items-center w-full">
          {prefixIcon && (
            <div className="absolute left-3 flex items-center pointer-events-none text-muted-foreground">
              {prefixIcon}
            </div>
          )}
          <input
            id={inputId}
            type={type}
            ref={ref}
            className={cn(
              "flex h-9 w-full rounded-md bg-surface-1 border border-border px-3 text-sm text-foreground placeholder:text-muted-foreground/60 transition-colors shadow-xs",
              "focus-visible:outline-none focus-visible:border-primary/60 focus-visible:ring-1 focus-visible:ring-primary/40",
              "disabled:cursor-not-allowed disabled:opacity-40",
              prefixIcon && "pl-9",
              (suffixIcon || shortcut) && "pr-12",
              error && "border-destructive focus-visible:border-destructive focus-visible:ring-destructive/30",
              className
            )}
            {...props}
          />
          {shortcut && !suffixIcon && (
            <div className="absolute right-2.5 flex items-center pointer-events-none">
              <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-3 border border-border text-muted-foreground">
                {shortcut}
              </kbd>
            </div>
          )}
          {suffixIcon && (
            <div className="absolute right-3 flex items-center text-muted-foreground">
              {suffixIcon}
            </div>
          )}
        </div>
        {error && (
          <p className="text-xs text-destructive mt-0.5">{error}</p>
        )}
        {hint && !error && (
          <p className="text-xs text-muted-foreground mt-0.5">{hint}</p>
        )}
      </div>
    )
  }
)

Input.displayName = "Input"
