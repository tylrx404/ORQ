import { Card, CardHeader, CardTitle, CardContent } from "../ui/Card"
import { Skeleton } from "../ui/Loading"
import type { UsageSummaryResponse } from "../../types/api"

interface OverviewActivitySectionProps {
  usage: UsageSummaryResponse | null
  isLoading: boolean
}

interface BarRowProps {
  label: string
  value: number
  total: number
  color: string
  formatted: string
}

function BarRow({ label, value, total, color, formatted }: BarRowProps) {
  // Never force non-zero width for truly zero values
  const pct = total > 0 && value > 0 ? Math.round((value / total) * 100) : 0
  return (
    <div className="flex items-center gap-3">
      <span className="text-[11px] font-mono text-muted-foreground w-28 shrink-0 truncate">
        {label}
      </span>
      <div className="flex-1 h-1.5 bg-surface-2 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[11px] font-mono text-foreground w-16 text-right shrink-0">
        {formatted}
      </span>
    </div>
  )
}

function formatN(n: number | null | undefined): string {
  if (n == null) return "0"
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`
  return String(n)
}

export function OverviewActivitySection({ usage, isLoading }: OverviewActivitySectionProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-mono font-medium text-muted-foreground tracking-wider uppercase">
            Activity Breakdown
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3">
              <Skeleton className="h-3 w-28 shrink-0" />
              <Skeleton className="h-1.5 flex-1 rounded-full" />
              <Skeleton className="h-3 w-16 shrink-0" />
            </div>
          ))}
        </CardContent>
      </Card>
    )
  }

  if (!usage) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-mono font-medium text-muted-foreground tracking-wider uppercase">
            Activity Breakdown
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs font-mono text-muted-foreground py-4 text-center">
            Usage data unavailable.
          </p>
        </CardContent>
      </Card>
    )
  }

  const totalReq = usage.total_requests ?? 0
  const totalTok = usage.total_tokens ?? 0
  const promptTok = usage.prompt_tokens ?? 0
  const completionTok = usage.completion_tokens ?? 0

  // Date range label
  const start = usage.start ? new Date(usage.start).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : null
  const end = usage.end ? new Date(usage.end).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : null
  const rangeLabel = start && end ? `${start} – ${end}` : "Last 30 days"

  return (
    <Card>
      <CardHeader className="pb-1 flex flex-row items-start justify-between">
        <CardTitle className="text-sm font-mono font-medium text-muted-foreground tracking-wider uppercase">
          Activity Breakdown
        </CardTitle>
        <span className="text-[10px] font-mono text-muted-foreground/60 shrink-0 ml-2">
          {rangeLabel}
        </span>
      </CardHeader>

      <CardContent className="space-y-5 pt-4">
        {/* === Request distribution === */}
        <div className="space-y-2">
          <p className="text-[10px] font-mono text-muted-foreground/60 uppercase tracking-widest mb-3">
            Requests
          </p>
          <BarRow
            label="Successful"
            value={usage.successful_requests ?? 0}
            total={totalReq}
            color="bg-status-success"
            formatted={formatN(usage.successful_requests)}
          />
          <BarRow
            label="Failed"
            value={usage.failed_requests ?? 0}
            total={totalReq}
            color="bg-status-error"
            formatted={formatN(usage.failed_requests)}
          />
        </div>

        {/* Divider */}
        <div className="border-t border-border" />

        {/* === Token distribution === */}
        <div className="space-y-2">
          <p className="text-[10px] font-mono text-muted-foreground/60 uppercase tracking-widest mb-3">
            Tokens
          </p>
          <BarRow
            label="Prompt (in)"
            value={promptTok}
            total={totalTok}
            color="bg-primary/70"
            formatted={formatN(promptTok)}
          />
          <BarRow
            label="Completion (out)"
            value={completionTok}
            total={totalTok}
            color="bg-primary"
            formatted={formatN(completionTok)}
          />
        </div>

        {/* Footer totals */}
        <div className="pt-1 flex justify-between text-[10px] font-mono text-muted-foreground/50 border-t border-border">
          <span>Total: {formatN(totalReq)} requests</span>
          <span>{formatN(totalTok)} tokens</span>
        </div>
      </CardContent>
    </Card>
  )
}
