import { useState, useEffect, useCallback } from "react"
import { RefreshCw } from "lucide-react"
import { PageHeader, PageContainer } from "../components/ui/PageHeader"
import { Button } from "../components/ui/Button"
import { EmptyState } from "../components/ui/EmptyState"
import { OverviewKpiSection } from "../components/overview/OverviewKpiSection"
import { OverviewQuotaSection } from "../components/overview/OverviewQuotaSection"
import { OverviewRecentExecutions } from "../components/overview/OverviewRecentExecutions"
import { OverviewActivitySection } from "../components/overview/OverviewActivitySection"
import { OverviewQuickActions } from "../components/overview/OverviewQuickActions"
import { useOrganization } from "../providers/useOrganization"
import { api, ApiClientError } from "../services/api"
import type {
  UsageSummaryResponse,
  OrganizationQuotaResponse,
  ExecutionLogResponse,
} from "../types/api"

export function OverviewPage() {
  const { currentOrg, isLoading: orgLoading } = useOrganization()

  // --- Usage (KPI + Activity) ---
  const [usage, setUsage] = useState<UsageSummaryResponse | null>(null)
  const [usageLoading, setUsageLoading] = useState(false)
  const [_usageError, setUsageError] = useState<string | null>(null)

  // --- Quota ---
  const [quota, setQuota] = useState<OrganizationQuotaResponse | null>(null)
  const [quotaLoading, setQuotaLoading] = useState(false)
  const [quotaError, setQuotaError] = useState<string | null>(null)

  // --- Executions ---
  const [executions, setExecutions] = useState<ExecutionLogResponse[] | null>(null)
  const [execLoading, setExecLoading] = useState(false)
  const [execError, setExecError] = useState<string | null>(null)

  // --- Refresh timestamp ---
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const fetchAll = useCallback(
    async (quiet = false) => {
      if (!currentOrg) return
      const orgId = currentOrg.id

      if (!quiet) {
        setUsageLoading(true)
        setQuotaLoading(true)
        setExecLoading(true)
      } else {
        setRefreshing(true)
      }

      const [usageResult, quotaResult, execResult] = await Promise.allSettled([
        api.getOrganizationUsage(orgId),
        api.getOrganizationQuota(orgId),
        api.listOrganizationExecutions(orgId, 0, 10),
      ])

      // Usage
      if (usageResult.status === "fulfilled") {
        setUsage(usageResult.value)
        setUsageError(null)
      } else {
        setUsageError(
          usageResult.reason instanceof Error
            ? usageResult.reason.message
            : "Failed to load usage data."
        )
      }

      // Quota — 404 means "no quota configured" (treat as null, not error)
      if (quotaResult.status === "fulfilled") {
        setQuota(quotaResult.value)
        setQuotaError(null)
      } else {
        const err = quotaResult.reason
        if (err instanceof ApiClientError && err.status === 404) {
          setQuota(null)
          setQuotaError(null)
        } else {
          setQuotaError(
            err instanceof Error ? err.message : "Failed to load quota."
          )
        }
      }

      // Executions
      if (execResult.status === "fulfilled") {
        setExecutions(execResult.value)
        setExecError(null)
      } else {
        setExecError(
          execResult.reason instanceof Error
            ? execResult.reason.message
            : "Failed to load executions."
        )
      }

      setUsageLoading(false)
      setQuotaLoading(false)
      setExecLoading(false)
      setRefreshing(false)
      setLastRefresh(new Date())
    },
    [currentOrg]
  )

  // Fetch on org change
  useEffect(() => {
    if (currentOrg) {
      fetchAll()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentOrg?.id])

  const handleRefresh = () => fetchAll(true)

  // Format last-refresh label
  const refreshLabel = lastRefresh
    ? `Updated ${lastRefresh.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
    : null

  // --- No org state ---
  if (!orgLoading && !currentOrg) {
    return (
      <PageContainer>
        <div className="py-16">
          <EmptyState
            title="No organization found"
            description="Create or join an organization to start using the ORQ control plane."
          />
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      {/* ── Page Header ─────────────────────────────────────────── */}
      <PageHeader
        eyebrow="Core"
        title="Overview"
        description={
          currentOrg
            ? `${currentOrg.name} · ${currentOrg.slug}`
            : "ORQ control plane — organization telemetry at a glance."
        }
        actions={
          <div className="flex items-center gap-3">
            {refreshLabel && (
              <span className="text-[10px] font-mono text-muted-foreground/50 hidden sm:block">
                {refreshLabel}
              </span>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={refreshing || usageLoading}
              className="flex items-center gap-1.5 font-mono text-xs"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`}
              />
              Refresh
            </Button>
          </div>
        }
      />

      {/* ── KPI strip ───────────────────────────────────────────── */}
      <OverviewKpiSection
        usage={usage}
        isLoading={orgLoading || usageLoading}
      />

      {/* ── Two-column mid-section ──────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mt-5">
        {/* Activity breakdown — wider column */}
        <div className="lg:col-span-2">
          <OverviewActivitySection
            usage={usage}
            isLoading={orgLoading || usageLoading}
          />
        </div>

        {/* Quota summary — narrower column */}
        <div>
          <OverviewQuotaSection
            quota={quota}
            isLoading={orgLoading || quotaLoading}
            error={quotaError}
          />
        </div>
      </div>

      {/* ── Recent Executions ───────────────────────────────────── */}
      <div className="mt-5">
        <OverviewRecentExecutions
          executions={executions}
          isLoading={orgLoading || execLoading}
          error={execError}
          onRetry={() => fetchAll()}
        />
      </div>

      {/* ── Quick Actions ───────────────────────────────────────── */}
      <div className="mt-8">
        <OverviewQuickActions />
      </div>
    </PageContainer>
  )
}
