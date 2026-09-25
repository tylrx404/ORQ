import { useState, useEffect, useCallback, useId } from "react"
import {
  RefreshCw,
  BarChart3,
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  Zap,
  Gauge,
  Calendar,
  ShieldCheck,
  TrendingUp,
  AlertCircle,
} from "lucide-react"
import { PageHeader, PageContainer } from "../components/ui/PageHeader"
import { Button } from "../components/ui/Button"
import { Badge } from "../components/ui/Badge"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/Card"
import { EmptyState } from "../components/ui/EmptyState"
import { ErrorState } from "../components/ui/ErrorState"
import { Skeleton } from "../components/ui/Loading"
import { useOrganization } from "../providers/useOrganization"
import { api, ApiClientError } from "../services/api"
import { showToast } from "../components/ui/toast-fn"
import type { UsageSummaryResponse, OrganizationQuotaResponse } from "../types/api"

// ─────────────────────────────────────────────────────────────────────────────
// Formatters & Helpers
// ─────────────────────────────────────────────────────────────────────────────

function formatNumber(val: number | null | undefined): string {
  if (val === null || val === undefined) return "0"
  return new Intl.NumberFormat().format(val)
}

function formatTokens(val: number | null | undefined): string {
  if (val === null || val === undefined) return "0"
  if (val >= 1_000_000_000) return `${(val / 1_000_000_000).toFixed(2)}B`
  if (val >= 1_000_000) return `${(val / 1_000_000).toFixed(2)}M`
  if (val >= 1_000) return `${(val / 1_000).toFixed(1)}k`
  return formatNumber(val)
}

function formatLatency(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—"
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`
  return `${Math.round(ms)}ms`
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—"
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    })
  } catch {
    return String(iso)
  }
}

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—"
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })
  } catch {
    return String(iso)
  }
}

function toDateInputValue(d: Date): string {
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, "0")
  const dd = String(d.getDate()).padStart(2, "0")
  return `${yyyy}-${mm}-${dd}`
}

type PresetKey = "7d" | "30d" | "90d" | "custom"

interface DatePreset {
  label: string
  days: number
}

const PRESETS: Record<"7d" | "30d" | "90d", DatePreset> = {
  "7d": { label: "7 days", days: 7 },
  "30d": { label: "30 days", days: 30 },
  "90d": { label: "90 days", days: 90 },
}

// ─────────────────────────────────────────────────────────────────────────────
// Skeleton component
// ─────────────────────────────────────────────────────────────────────────────

function UsagePageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5 sm:gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <Card key={i} className="p-4 space-y-3">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-16" />
            <Skeleton className="h-3 w-32" />
          </Card>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6 space-y-4">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-20 w-full" />
        </Card>
        <Card className="p-6 space-y-4">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-20 w-full" />
        </Card>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Quota Progress Card
// ─────────────────────────────────────────────────────────────────────────────

interface QuotaCardProps {
  title: string
  used: number
  limit: number | null
  unit: "requests" | "tokens"
  resetAt: string
}

function QuotaCard({ title, used, limit, unit, resetAt }: QuotaCardProps) {
  const isUnlimited = limit === null || limit === undefined
  const pct = isUnlimited || limit <= 0 ? null : Math.min(100, Math.round((used / limit) * 100))

  const formattedUsed = unit === "tokens" ? formatTokens(used) : formatNumber(used)
  const formattedLimit = isUnlimited
    ? "Unlimited"
    : unit === "tokens"
    ? formatTokens(limit)
    : formatNumber(limit)

  const getProgressColor = (p: number | null) => {
    if (p === null) return "bg-primary"
    if (p >= 90) return "bg-status-error"
    if (p >= 75) return "bg-status-warning"
    return "bg-primary"
  }

  const getBadgeVariant = (p: number | null): "neutral" | "success" | "warning" | "error" => {
    if (p === null) return "neutral"
    if (p >= 90) return "error"
    if (p >= 75) return "warning"
    return "success"
  }

  return (
    <div className="p-5 rounded-lg bg-surface-card border border-border/80 flex flex-col justify-between space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="text-sm font-semibold text-foreground">{title}</h4>
          <p className="text-xs text-muted-foreground mt-0.5 font-mono">
            Billing cycle resets: {formatDateTime(resetAt)}
          </p>
        </div>
        {isUnlimited ? (
          <Badge variant="neutral" size="sm">
            Unlimited
          </Badge>
        ) : (
          <Badge variant={getBadgeVariant(pct)} withDot size="sm">
            {pct}% used
          </Badge>
        )}
      </div>

      <div className="space-y-2">
        <div className="flex items-baseline justify-between text-xs font-mono">
          <span className="text-xl sm:text-2xl font-bold font-mono text-foreground tracking-tight">
            {formattedUsed}
          </span>
          <span className="text-muted-foreground">
            of <span className="font-semibold text-foreground">{formattedLimit}</span>
          </span>
        </div>

        {/* Progress bar */}
        <div className="h-2 w-full bg-surface-2 rounded-full overflow-hidden border border-border/40">
          {isUnlimited ? (
            <div className="h-full bg-primary/40 rounded-full w-full" />
          ) : (
            <div
              className={`h-full rounded-full transition-all duration-500 ${getProgressColor(pct)}`}
              style={{ width: `${Math.max(pct ?? 0, 1)}%` }}
            />
          )}
        </div>
      </div>

      <div className="text-[11px] font-mono text-muted-foreground pt-1 flex items-center justify-between border-t border-border/50">
        <span>
          {isUnlimited
            ? "No limit enforced on this cycle"
            : limit - used > 0
            ? `${unit === "tokens" ? formatTokens(limit - used) : formatNumber(limit - used)} remaining`
            : "Quota limit reached"}
        </span>
        <span className="text-muted-foreground/70">Reset date: {formatDate(resetAt)}</span>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Main UsagePage Component
// ─────────────────────────────────────────────────────────────────────────────

export function UsagePage() {
  const { currentOrg, isLoading: orgLoading } = useOrganization()

  // Preset & custom date range
  const [preset, setPreset] = useState<PresetKey>("30d")
  const [startDate, setStartDate] = useState<string>(() => {
    const d = new Date()
    d.setDate(d.getDate() - 30)
    return toDateInputValue(d)
  })
  const [endDate, setEndDate] = useState<string>(() => toDateInputValue(new Date()))

  // Data states
  const [usage, setUsage] = useState<UsageSummaryResponse | null>(null)
  const [usageLoading, setUsageLoading] = useState(false)
  const [usageError, setUsageError] = useState<string | null>(null)

  const [quota, setQuota] = useState<OrganizationQuotaResponse | null>(null)
  const [quotaLoading, setQuotaLoading] = useState(false)
  const [quotaError, setQuotaError] = useState<string | null>(null)

  const [refreshing, setRefreshing] = useState(false)

  // IDs for accessibility
  const startInputId = useId()
  const endInputId = useId()

  // Handler for preset button clicks
  const handlePresetChange = (key: "7d" | "30d" | "90d") => {
    setPreset(key)
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - PRESETS[key].days)
    setStartDate(toDateInputValue(start))
    setEndDate(toDateInputValue(end))
  }

  // Validate custom date range
  const isRangeInvalid = Boolean(startDate && endDate && startDate > endDate)

  // Fetch Usage & Quota
  const fetchData = useCallback(
    async (isQuiet = false) => {
      if (!currentOrg) return
      const orgId = currentOrg.id

      // If custom date range is invalid (start > end), do not call usage API
      if (startDate && endDate && startDate > endDate) {
        setUsageLoading(false)
        return
      }

      if (!isQuiet) {
        setUsageLoading(true)
        setQuotaLoading(true)
      } else {
        setRefreshing(true)
      }

      // Build ISO parameters for usage
      let startIso: string | undefined
      let endIso: string | undefined

      if (startDate) {
        // Start of selected day in UTC
        startIso = new Date(`${startDate}T00:00:00Z`).toISOString()
      }
      if (endDate) {
        // End of selected day in UTC
        endIso = new Date(`${endDate}T23:59:59Z`).toISOString()
      }

      const [usageResult, quotaResult] = await Promise.allSettled([
        api.getOrganizationUsage(orgId, { start: startIso, end: endIso }),
        api.getOrganizationQuota(orgId),
      ])

      // Handle usage result
      if (usageResult.status === "fulfilled") {
        setUsage(usageResult.value)
        setUsageError(null)
      } else {
        const err = usageResult.reason
        const msg = err instanceof Error ? err.message : "Failed to load usage data."
        setUsageError(msg)
      }

      // Handle quota result (404 means no quota configured)
      if (quotaResult.status === "fulfilled") {
        setQuota(quotaResult.value)
        setQuotaError(null)
      } else {
        const err = quotaResult.reason
        if (err instanceof ApiClientError && err.status === 404) {
          setQuota(null)
          setQuotaError(null)
        } else {
          const msg = err instanceof Error ? err.message : "Failed to load quota record."
          setQuotaError(msg)
        }
      }

      setUsageLoading(false)
      setQuotaLoading(false)
      setRefreshing(false)
    },
    [currentOrg, startDate, endDate]
  )

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleRefresh = () => {
    fetchData(true)
    showToast("Refreshing usage and quota metrics...", "info")
  }

  if (orgLoading) {
    return (
      <PageContainer>
        <UsagePageSkeleton />
      </PageContainer>
    )
  }

  if (!currentOrg) {
    return (
      <PageContainer>
        <EmptyState
          title="No organization selected"
          description="Select an organization from the header to view usage metrics and quotas."
        />
      </PageContainer>
    )
  }

  const successRate =
    usage && usage.total_requests > 0
      ? ((usage.successful_requests / usage.total_requests) * 100).toFixed(1)
      : null

  const promptTokenPct =
    usage && usage.total_tokens > 0
      ? Math.round((usage.prompt_tokens / usage.total_tokens) * 100)
      : 0
  const completionTokenPct =
    usage && usage.total_tokens > 0
      ? Math.round((usage.completion_tokens / usage.total_tokens) * 100)
      : 0

  const hasNoActivity =
    usage !== null &&
    usage.total_requests === 0 &&
    usage.total_tokens === 0

  return (
    <PageContainer>
      <PageHeader
        eyebrow="Observability"
        title="Usage & Quotas"
        description="Comprehensive audit of LLM consumption, token throughput, and organizational quota ceilings."
        actions={
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            disabled={usageLoading || quotaLoading || refreshing}
            leftIcon={
              <RefreshCw
                className={`h-3.5 w-3.5 ${refreshing || usageLoading ? "animate-spin" : ""}`}
              />
            }
          >
            Refresh
          </Button>
        }
      />

      {/* Date Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between p-4 rounded-lg bg-surface-card border border-border/80">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs font-mono text-muted-foreground mr-1 flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5" />
            Range:
          </span>
          {(["7d", "30d", "90d"] as const).map((key) => (
            <button
              key={key}
              onClick={() => handlePresetChange(key)}
              className={`rounded px-2.5 py-1 text-xs font-mono font-medium transition-colors ${
                preset === key
                  ? "bg-surface-3 text-foreground shadow-sm border border-border-strong"
                  : "text-muted-foreground hover:text-foreground border border-transparent"
              }`}
            >
              {PRESETS[key].label}
            </button>
          ))}
        </div>

        {/* Custom Start/End Inputs */}
        <div className="flex flex-col items-start sm:items-end gap-1">
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
            <div className="flex items-center gap-1.5">
              <label htmlFor={startInputId} className="text-muted-foreground">
                From:
              </label>
              <input
                id={startInputId}
                type="date"
                value={startDate}
                onChange={(e) => {
                  setPreset("custom")
                  setStartDate(e.target.value)
                }}
                className={`rounded border bg-surface-2 px-2 py-1 text-foreground focus:outline-none focus:ring-1 text-xs font-mono ${
                  isRangeInvalid
                    ? "border-status-error focus:ring-status-error/50"
                    : "border-border focus:ring-primary/50"
                }`}
              />
            </div>
            <div className="flex items-center gap-1.5">
              <label htmlFor={endInputId} className="text-muted-foreground">
                To:
              </label>
              <input
                id={endInputId}
                type="date"
                value={endDate}
                onChange={(e) => {
                  setPreset("custom")
                  setEndDate(e.target.value)
                }}
                className={`rounded border bg-surface-2 px-2 py-1 text-foreground focus:outline-none focus:ring-1 text-xs font-mono ${
                  isRangeInvalid
                    ? "border-status-error focus:ring-status-error/50"
                    : "border-border focus:ring-primary/50"
                }`}
              />
            </div>
          </div>
          {isRangeInvalid && (
            <span className="text-[11px] font-mono text-status-error flex items-center gap-1 mt-0.5">
              <AlertCircle className="h-3 w-3 shrink-0" />
              Start date must be on or before end date
            </span>
          )}
        </div>
      </div>

      {/* Main Content States */}
      {usageLoading && !usage ? (
        <UsagePageSkeleton />
      ) : usageError ? (
        <ErrorState
          title="Could not load usage data"
          message={usageError}
          onRetry={() => fetchData()}
        />
      ) : (
        <div className="space-y-6">
          {/* Top 5 KPI Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5 sm:gap-4">
            {/* 1. Total Requests */}
            <Card className="p-4 flex flex-col justify-between">
              <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
                <span>Total Requests</span>
                <Activity className="h-3.5 w-3.5 text-primary" />
              </div>
              <div className="mt-3">
                <div className="text-xl sm:text-2xl font-bold font-mono text-foreground tracking-tight">
                  {formatNumber(usage?.total_requests)}
                </div>
                <p className="mt-1 text-[11px] font-mono text-muted-foreground truncate">
                  {formatDate(usage?.start)} – {formatDate(usage?.end)}
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
                <div className="text-xl sm:text-2xl font-bold font-mono text-foreground tracking-tight">
                  {formatTokens(usage?.total_tokens)}
                </div>
                <p className="mt-1 text-[11px] font-mono text-muted-foreground truncate">
                  Prompt + Completion
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
                <div className="text-xl sm:text-2xl font-bold font-mono text-foreground tracking-tight">
                  {formatNumber(usage?.successful_requests)}
                </div>
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
                <div className="text-xl sm:text-2xl font-bold font-mono text-foreground tracking-tight">
                  {formatNumber(usage?.failed_requests)}
                </div>
                <p className="mt-1 text-[11px] font-mono text-muted-foreground">
                  Status code ≥ 400
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
                <div className="text-xl sm:text-2xl font-bold font-mono text-foreground tracking-tight">
                  {formatLatency(usage?.average_latency_ms)}
                </div>
                <p className="mt-1 text-[11px] font-mono text-muted-foreground">
                  Gateway e2e latency
                </p>
              </div>
            </Card>
          </div>

          {/* Empty State Banner if 0 requests in time window */}
          {hasNoActivity && (
            <div className="p-6 rounded-lg border border-dashed border-border text-center space-y-2 bg-surface-card/50">
              <div className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-surface-2 text-muted-foreground mb-1">
                <BarChart3 className="h-4 w-4" />
              </div>
              <h4 className="text-sm font-semibold text-foreground">
                No activity recorded in this time range
              </h4>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                No LLM requests were processed between {formatDate(usage?.start)} and {formatDate(usage?.end)}. Try expanding the date range or sending test requests from the Playground.
              </p>
            </div>
          )}

          {/* Token Breakdown Section */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-primary" />
                    <CardTitle>Token Breakdown</CardTitle>
                  </div>
                  <span className="text-xs font-mono text-muted-foreground">
                    {formatTokens(usage?.total_tokens)} total
                  </span>
                </div>
                <CardDescription>
                  Ratio between input context prompts and generated completion output tokens.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Visual Ratio Bar */}
                <div className="space-y-2">
                  <div className="h-3 w-full bg-surface-2 rounded-full overflow-hidden flex border border-border/40">
                    <div
                      className="h-full bg-primary transition-all duration-500"
                      style={{ width: `${usage?.total_tokens ? promptTokenPct : 50}%` }}
                      title={`Prompt Tokens: ${promptTokenPct}%`}
                    />
                    <div
                      className="h-full bg-accent-blue transition-all duration-500"
                      style={{ width: `${usage?.total_tokens ? completionTokenPct : 50}%` }}
                      title={`Completion Tokens: ${completionTokenPct}%`}
                    />
                  </div>
                  <div className="flex justify-between text-xs font-mono text-muted-foreground">
                    <span className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-primary inline-block" />
                      Prompt: {promptTokenPct}%
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-accent-blue inline-block" />
                      Completion: {completionTokenPct}%
                    </span>
                  </div>
                </div>

                {/* Token Detail Rows */}
                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div className="p-3.5 rounded-lg bg-surface-base border border-border/60">
                    <span className="text-[10px] font-mono uppercase text-muted-foreground tracking-wider">
                      Input / Prompt Tokens
                    </span>
                    <div className="text-lg font-bold font-mono text-foreground mt-1">
                      {formatTokens(usage?.prompt_tokens)}
                    </div>
                    <span className="text-[11px] font-mono text-muted-foreground">
                      {formatNumber(usage?.prompt_tokens)} raw count
                    </span>
                  </div>

                  <div className="p-3.5 rounded-lg bg-surface-base border border-border/60">
                    <span className="text-[10px] font-mono uppercase text-muted-foreground tracking-wider">
                      Output / Completion Tokens
                    </span>
                    <div className="text-lg font-bold font-mono text-foreground mt-1">
                      {formatTokens(usage?.completion_tokens)}
                    </div>
                    <span className="text-[11px] font-mono text-muted-foreground">
                      {formatNumber(usage?.completion_tokens)} raw count
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Request Reliability Section */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-primary" />
                    <CardTitle>Request Reliability</CardTitle>
                  </div>
                  {successRate !== null && (
                    <Badge
                      variant={Number(successRate) >= 95 ? "success" : Number(successRate) >= 80 ? "warning" : "error"}
                      size="sm"
                    >
                      {successRate}% availability
                    </Badge>
                  )}
                </div>
                <CardDescription>
                  Operational health and request completion ratio over the selected window.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Visual Ratio Bar */}
                <div className="space-y-2">
                  <div className="h-3 w-full bg-surface-2 rounded-full overflow-hidden flex border border-border/40">
                    <div
                      className="h-full bg-status-success transition-all duration-500"
                      style={{
                        width: `${
                          usage?.total_requests
                            ? (usage.successful_requests / usage.total_requests) * 100
                            : 100
                        }%`,
                      }}
                      title="Successful requests"
                    />
                    <div
                      className="h-full bg-status-error transition-all duration-500"
                      style={{
                        width: `${
                          usage?.total_requests
                            ? (usage.failed_requests / usage.total_requests) * 100
                            : 0
                        }%`,
                      }}
                      title="Failed requests"
                    />
                  </div>
                  <div className="flex justify-between text-xs font-mono text-muted-foreground">
                    <span className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-status-success inline-block" />
                      Success: {usage?.successful_requests ? formatNumber(usage.successful_requests) : "0"}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-status-error inline-block" />
                      Errors: {usage?.failed_requests ? formatNumber(usage.failed_requests) : "0"}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div className="p-3.5 rounded-lg bg-surface-base border border-border/60">
                    <span className="text-[10px] font-mono uppercase text-muted-foreground tracking-wider">
                      Successful Executions
                    </span>
                    <div className="text-lg font-bold font-mono text-foreground mt-1">
                      {formatNumber(usage?.successful_requests)}
                    </div>
                    <span className="text-[11px] font-mono text-status-success">
                      HTTP status &lt; 400
                    </span>
                  </div>

                  <div className="p-3.5 rounded-lg bg-surface-base border border-border/60">
                    <span className="text-[10px] font-mono uppercase text-muted-foreground tracking-wider">
                      Failed Executions
                    </span>
                    <div className="text-lg font-bold font-mono text-foreground mt-1">
                      {formatNumber(usage?.failed_requests)}
                    </div>
                    <span className="text-[11px] font-mono text-status-error">
                      HTTP status ≥ 400
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Organizational Quotas Section */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Gauge className="h-4 w-4 text-primary" />
                  <CardTitle>Organizational Quotas & Limits</CardTitle>
                </div>
                {quota && (
                  <Badge variant="neutral" size="sm">
                    Cycle ending {formatDate(quota.reset_at)}
                  </Badge>
                )}
              </div>
              <CardDescription>
                Live usage counters and enforcement ceilings configured for this organization's billing cycle.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {quotaLoading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <Skeleton className="h-32 w-full rounded-lg" />
                  <Skeleton className="h-32 w-full rounded-lg" />
                </div>
              ) : quotaError ? (
                <div className="p-4 rounded-md bg-surface-base border border-status-error/30 text-xs font-mono text-status-error">
                  {quotaError}
                </div>
              ) : !quota ? (
                <div className="p-6 rounded-lg bg-surface-base border border-dashed border-border text-center space-y-2">
                  <div className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary mb-1">
                    <ShieldCheck className="h-4 w-4" />
                  </div>
                  <h4 className="text-sm font-semibold text-foreground">
                    No Quota Record Configured
                  </h4>
                  <p className="text-xs text-muted-foreground max-w-md mx-auto">
                    This organization does not have an active quota limit enforced. Both request volume and token consumption are currently unlimited.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <QuotaCard
                    title="Monthly Request Quota"
                    used={quota.requests_used}
                    limit={quota.request_limit}
                    unit="requests"
                    resetAt={quota.reset_at}
                  />
                  <QuotaCard
                    title="Monthly Token Quota"
                    used={quota.tokens_used}
                    limit={quota.token_limit}
                    unit="tokens"
                    resetAt={quota.reset_at}
                  />
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </PageContainer>
  )
}
