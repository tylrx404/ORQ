import { ListTree, ArrowRight } from "lucide-react"
import { Link } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "../ui/Card"
import { Badge } from "../ui/Badge"
import { EmptyState } from "../ui/EmptyState"
import { ErrorState } from "../ui/ErrorState"
import { Skeleton } from "../ui/Loading"
import type { ExecutionLogResponse } from "../../types/api"

interface OverviewRecentExecutionsProps {
  executions: ExecutionLogResponse[] | null
  isLoading: boolean
  error: string | null
  onRetry: () => void
}

function statusVariant(code: number): "success" | "warning" | "error" | "neutral" {
  if (code >= 200 && code < 300) return "success"
  if (code >= 400 && code < 500) return "warning"
  if (code >= 500) return "error"
  return "neutral"
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const s = Math.floor(diff / 1000)
  if (s < 60) return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export function OverviewRecentExecutions({
  executions,
  isLoading,
  error,
  onRetry,
}: OverviewRecentExecutionsProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-sm font-mono font-medium text-muted-foreground tracking-wider uppercase">
          Recent Executions
        </CardTitle>
        <Link
          to="/app/executions"
          className="flex items-center gap-1 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors"
        >
          All executions
          <ArrowRight className="h-3 w-3" />
        </Link>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading && (
          <div className="divide-y divide-border">
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className="px-5 py-3 flex items-center gap-3"
              >
                <Skeleton className="h-4 w-16 shrink-0" />
                <Skeleton className="h-4 flex-1" />
                <Skeleton className="h-5 w-12 rounded-full shrink-0" />
                <Skeleton className="h-4 w-14 shrink-0" />
                <Skeleton className="h-4 w-14 shrink-0" />
              </div>
            ))}
          </div>
        )}

        {!isLoading && error && (
          <div className="px-5 py-6">
            <ErrorState
              title="Failed to load executions"
              message={error}
              onRetry={onRetry}
            />
          </div>
        )}

        {!isLoading && !error && executions && executions.length === 0 && (
          <div className="px-5 py-8">
            <EmptyState
              icon={<ListTree className="h-7 w-7" />}
              title="No executions recorded yet"
              description="Executions appear here once your integration sends requests through the gateway."
            />
          </div>
        )}

        {!isLoading && !error && executions && executions.length > 0 && (
          <div className="divide-y divide-border">
            {/* Column header */}
            <div className="px-5 py-2 grid grid-cols-[5rem_1fr_5rem_5rem_5rem] gap-3 text-[10px] font-mono font-medium text-muted-foreground/60 uppercase tracking-wider">
              <span>Time</span>
              <span>Model</span>
              <span className="text-center">Status</span>
              <span className="text-right">Tokens</span>
              <span className="text-right">Latency</span>
            </div>
            {executions.map((ex) => (
              <div
                key={ex.id}
                className="px-5 py-2.5 grid grid-cols-[5rem_1fr_5rem_5rem_5rem] gap-3 items-center hover:bg-surface-2/50 transition-colors"
              >
                {/* Time */}
                <span className="text-[11px] font-mono text-muted-foreground shrink-0">
                  {relativeTime(ex.created_at)}
                </span>

                {/* Model */}
                <span
                  className="text-[12px] font-mono text-foreground truncate"
                  title={ex.model_name}
                >
                  {ex.model_name}
                </span>

                {/* Status badge */}
                <div className="flex justify-center">
                  <Badge
                    variant={statusVariant(ex.status_code)}
                    size="sm"
                  >
                    {ex.status_code}
                  </Badge>
                </div>

                {/* Tokens */}
                <span className="text-[11px] font-mono text-muted-foreground text-right">
                  {ex.total_tokens != null
                    ? ex.total_tokens >= 1000
                      ? `${(ex.total_tokens / 1000).toFixed(1)}k`
                      : String(ex.total_tokens)
                    : "—"}
                </span>

                {/* Latency */}
                <span className="text-[11px] font-mono text-muted-foreground text-right">
                  {ex.latency_ms != null ? `${Math.round(ex.latency_ms)} ms` : "—"}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
