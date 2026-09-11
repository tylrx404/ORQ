import { Activity, CheckCircle2, XCircle, Clock, Zap } from "lucide-react"
import { Card } from "../ui/Card"
import type { UsageSummaryResponse } from "../../types/api"

interface OverviewKpiSectionProps {
  usage: UsageSummaryResponse | null
  isLoading: boolean
}

export function OverviewKpiSection({ usage, isLoading }: OverviewKpiSectionProps) {
  const formatNumber = (val: number | undefined | null) => {
    if (val === undefined || val === null) return "0"
    return new Intl.NumberFormat().format(val)
  }

  const formatTokens = (val: number | undefined | null) => {
    if (val === undefined || val === null) return "0"
    if (val >= 1_000_000) return `${(val / 1_000_000).toFixed(2)}M`
    if (val >= 1_000) return `${(val / 1_000).toFixed(1)}k`
    return formatNumber(val)
  }

  const successRate =
    usage && usage.total_requests > 0
      ? ((usage.successful_requests / usage.total_requests) * 100).toFixed(1)
      : null

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5 sm:gap-4">
      {/* 1. Total Requests */}
      <Card className="p-4 flex flex-col justify-between">
        <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
          <span>Total Requests</span>
          <Activity className="h-3.5 w-3.5 text-primary" />
        </div>
        <div className="mt-3">
          {isLoading ? (
            <div className="h-7 w-20 bg-surface-2 rounded animate-pulse" />
          ) : (
            <div className="text-xl sm:text-2xl font-bold font-mono text-foreground tracking-tight">
              {formatNumber(usage?.total_requests)}
            </div>
          )}
          <p className="mt-1 text-[11px] font-mono text-muted-foreground">
            30-day window
          </p>
        </div>
      </Card>

      {/* 2. Total Tokens */}
      <Card className="p-4 flex flex-col justify-between">
        <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
          <span>Total Tokens</span>
          <Zap className="h-3.5 w-3.5 text-primary" />
        </div>
        <div className="mt-3">
          {isLoading ? (
            <div className="h-7 w-20 bg-surface-2 rounded animate-pulse" />
          ) : (
            <div className="text-xl sm:text-2xl font-bold font-mono text-foreground tracking-tight">
              {formatTokens(usage?.total_tokens)}
            </div>
          )}
          <p className="mt-1 text-[11px] font-mono text-muted-foreground truncate">
            {formatTokens(usage?.prompt_tokens)} in / {formatTokens(usage?.completion_tokens)} out
          </p>
        </div>
      </Card>

      {/* 3. Successful Requests */}
      <Card className="p-4 flex flex-col justify-between">
        <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
          <span>Successful</span>
          <CheckCircle2 className="h-3.5 w-3.5 text-status-success" />
        </div>
        <div className="mt-3">
          {isLoading ? (
            <div className="h-7 w-20 bg-surface-2 rounded animate-pulse" />
          ) : (
            <div className="text-xl sm:text-2xl font-bold font-mono text-foreground tracking-tight">
              {formatNumber(usage?.successful_requests)}
            </div>
          )}
          <p className="mt-1 text-[11px] font-mono text-status-success">
            {successRate !== null ? `${successRate}% success rate` : "No requests"}
          </p>
        </div>
      </Card>

      {/* 4. Failed Requests */}
      <Card className="p-4 flex flex-col justify-between">
        <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
          <span>Failed</span>
          <XCircle className="h-3.5 w-3.5 text-status-error" />
        </div>
        <div className="mt-3">
          {isLoading ? (
            <div className="h-7 w-20 bg-surface-2 rounded animate-pulse" />
          ) : (
            <div className="text-xl sm:text-2xl font-bold font-mono text-foreground tracking-tight">
              {formatNumber(usage?.failed_requests)}
            </div>
          )}
          <p className="mt-1 text-[11px] font-mono text-muted-foreground">
            Upstream or quota errors
          </p>
        </div>
      </Card>

      {/* 5. Average Latency */}
      <Card className="col-span-2 sm:col-span-1 p-4 flex flex-col justify-between">
        <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
          <span>Avg Latency</span>
          <Clock className="h-3.5 w-3.5 text-primary" />
        </div>
        <div className="mt-3">
          {isLoading ? (
            <div className="h-7 w-20 bg-surface-2 rounded animate-pulse" />
          ) : (
            <div className="text-xl sm:text-2xl font-bold font-mono text-foreground tracking-tight">
              {usage?.average_latency_ms !== null && usage?.average_latency_ms !== undefined
                ? `${Math.round(usage.average_latency_ms)} ms`
                : "—"}
            </div>
          )}
          <p className="mt-1 text-[11px] font-mono text-muted-foreground">
            End-to-end gateway
          </p>
        </div>
      </Card>
    </div>
  )
}
