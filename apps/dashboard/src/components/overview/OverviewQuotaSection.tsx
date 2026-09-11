import { Gauge, ArrowRight, ShieldCheck, AlertCircle } from "lucide-react"
import { Link } from "react-router-dom"
import { Card, CardHeader, CardTitle, CardContent } from "../ui/Card"
import { Badge } from "../ui/Badge"
import type { OrganizationQuotaResponse } from "../../types/api"

interface OverviewQuotaSectionProps {
  quota: OrganizationQuotaResponse | null
  isLoading: boolean
  error?: string | null
}

export function OverviewQuotaSection({ quota, isLoading, error }: OverviewQuotaSectionProps) {
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

  const formatResetDate = (isoString?: string) => {
    if (!isoString) return "—"
    try {
      const d = new Date(isoString)
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    } catch {
      return isoString
    }
  }

  // Request percentage
  const requestPct =
    quota && quota.request_limit && quota.request_limit > 0
      ? Math.min(100, Math.round((quota.requests_used / quota.request_limit) * 100))
      : null

  // Token percentage
  const tokenPct =
    quota && quota.token_limit && quota.token_limit > 0
      ? Math.min(100, Math.round((quota.tokens_used / quota.token_limit) * 100))
      : null

  const getProgressColor = (pct: number | null) => {
    if (pct === null) return "bg-primary"
    if (pct >= 90) return "bg-status-error"
    if (pct >= 75) return "bg-status-warning"
    return "bg-primary"
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Gauge className="h-4 w-4 text-primary" />
            <CardTitle>Organization Quota & Limits</CardTitle>
          </div>
          <Link
            to="/app/quotas"
            className="flex items-center gap-1 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors"
          >
            <span>Manage Limits</span>
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="h-20 bg-surface-2 rounded animate-pulse" />
            <div className="h-20 bg-surface-2 rounded animate-pulse" />
          </div>
        ) : error ? (
          <div className="p-3 rounded-md bg-surface-base border border-status-error/30 text-xs font-mono text-status-error">
            {error}
          </div>
        ) : !quota ? (
          <div className="p-4 rounded-md bg-surface-base border border-border text-center text-xs text-muted-foreground font-mono">
            No quota policy configured for this organization. Unlimited requests enabled.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Request Ceiling */}
            <div className="space-y-2.5 p-4 rounded-lg bg-surface-base border border-border/70">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-foreground font-medium">Monthly Requests</span>
                {requestPct !== null ? (
                  <span className="text-muted-foreground">{requestPct}% consumed</span>
                ) : (
                  <Badge variant="neutral" size="sm">
                    Unlimited
                  </Badge>
                )}
              </div>

              {/* Progress Bar */}
              <div className="h-2 w-full rounded-full bg-surface-2 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${getProgressColor(
                    requestPct
                  )}`}
                  style={{ width: `${requestPct ?? 0}%` }}
                />
              </div>

              <div className="flex items-center justify-between text-[11px] font-mono text-muted-foreground pt-1">
                <span>{formatNumber(quota.requests_used)} used</span>
                <span>
                  {quota.request_limit ? `${formatNumber(quota.request_limit)} limit` : "No limit"}
                </span>
              </div>
            </div>

            {/* Token Ceiling */}
            <div className="space-y-2.5 p-4 rounded-lg bg-surface-base border border-border/70">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-foreground font-medium">Monthly Token Budget</span>
                {tokenPct !== null ? (
                  <span className="text-muted-foreground">{tokenPct}% consumed</span>
                ) : (
                  <Badge variant="neutral" size="sm">
                    Unlimited
                  </Badge>
                )}
              </div>

              {/* Progress Bar */}
              <div className="h-2 w-full rounded-full bg-surface-2 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${getProgressColor(
                    tokenPct
                  )}`}
                  style={{ width: `${tokenPct ?? 0}%` }}
                />
              </div>

              <div className="flex items-center justify-between text-[11px] font-mono text-muted-foreground pt-1">
                <span>{formatTokens(quota.tokens_used)} tokens used</span>
                <span>
                  {quota.token_limit ? `${formatTokens(quota.token_limit)} limit` : "No limit"}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Quota Guarantee Footer */}
        {quota && (
          <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono text-muted-foreground border-t border-border/50">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-3.5 w-3.5 text-status-success shrink-0" />
              <span>Zero-loss transactional rollback active on provider errors</span>
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              <AlertCircle className="h-3.5 w-3.5 text-primary shrink-0" />
              <span>Billing cycle resets: {formatResetDate(quota.reset_at)}</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
