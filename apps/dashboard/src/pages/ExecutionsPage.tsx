import { useState, useEffect, useCallback, useMemo } from "react"
import {
  RefreshCw,
  Activity,
  ChevronRight,
  ChevronLeft,
  Search,
  X,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Zap,
  Filter,
} from "lucide-react"
import { PageHeader, PageContainer } from "../components/ui/PageHeader"
import { Button } from "../components/ui/Button"
import { Badge } from "../components/ui/Badge"
import { Dialog } from "../components/ui/Dialog"
import { EmptyState } from "../components/ui/EmptyState"
import { ErrorState } from "../components/ui/ErrorState"
import { Skeleton } from "../components/ui/Loading"
import { useOrganization } from "../providers/useOrganization"
import { api } from "../services/api"
import { showToast } from "../components/ui/toast-fn"
import type { ExecutionLogResponse } from "../types/api"

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const PAGE_SIZE = 50

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  })
}

function fmtDateTimeShort(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  })
}

function fmtLatency(ms: number | null | undefined): string {
  if (ms == null) return "—"
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`
  return `${ms}ms`
}

function fmtTokens(n: number | null | undefined): string {
  if (n == null) return "—"
  return n.toLocaleString()
}

function isSuccess(statusCode: number): boolean {
  return statusCode < 400
}

function statusBadgeVariant(
  statusCode: number
): "success" | "error" | "warning" | "neutral" {
  if (statusCode < 400) return "success"
  if (statusCode === 429) return "warning"
  return "error"
}

function statusLabel(statusCode: number): string {
  const labels: Record<number, string> = {
    200: "200 OK",
    201: "201 Created",
    400: "400 Bad Request",
    401: "401 Unauthorized",
    403: "403 Forbidden",
    404: "404 Not Found",
    422: "422 Unprocessable",
    429: "429 Rate Limited",
    500: "500 Server Error",
    502: "502 Bad Gateway",
    503: "503 Unavailable",
  }
  return labels[statusCode] ?? String(statusCode)
}

// ─────────────────────────────────────────────────────────────────────────────
// Row skeleton
// ─────────────────────────────────────────────────────────────────────────────

function TableSkeleton() {
  return (
    <div className="divide-y divide-border/50">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 px-4 py-3">
          <Skeleton className="h-5 w-14 rounded" />
          <Skeleton className="h-4 w-32 rounded" />
          <Skeleton className="h-4 flex-1 rounded" />
          <Skeleton className="h-4 w-16 rounded" />
          <Skeleton className="h-4 w-16 rounded" />
          <Skeleton className="h-4 w-28 rounded" />
        </div>
      ))}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Detail panel
// ─────────────────────────────────────────────────────────────────────────────

function DetailRow({
  label,
  value,
  mono = false,
  className = "",
}: {
  label: string
  value: React.ReactNode
  mono?: boolean
  className?: string
}) {
  return (
    <div className={`flex flex-col gap-0.5 ${className}`}>
      <span className="text-[10px] font-mono font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span
        className={`text-sm text-foreground break-all ${mono ? "font-mono" : ""}`}
      >
        {value ?? "—"}
      </span>
    </div>
  )
}

interface DetailDialogProps {
  executionId: string
  onClose: () => void
}

function DetailDialog({ executionId, onClose }: DetailDialogProps) {
  const [exec, setExec] = useState<ExecutionLogResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const data = await api.getExecution(executionId)
        if (!cancelled) setExec(data)
      } catch (err: unknown) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Failed to load execution.")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [executionId])

  const succeeded = exec ? isSuccess(exec.status_code) : false

  return (
    <Dialog
      isOpen
      onClose={onClose}
      title="Execution Detail"
      maxWidth="lg"
    >
      {loading ? (
        <div className="space-y-3 py-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full rounded" />
          ))}
        </div>
      ) : error ? (
        <ErrorState
          title="Could not load execution"
          message={error}
          className="my-0 border-0 p-4"
        />
      ) : exec ? (
        <div className="space-y-5">
          {/* Status row */}
          <div className="flex items-center gap-3">
            <Badge variant={statusBadgeVariant(exec.status_code)} withDot size="md">
              {statusLabel(exec.status_code)}
            </Badge>
            <span className="text-xs text-muted-foreground font-mono">
              {fmtDateTime(exec.created_at)}
            </span>
          </div>

          {/* Core fields */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-4">
            <DetailRow label="Execution ID" value={exec.id} mono />
            <DetailRow label="Organization" value={exec.organization_id} mono />
            <DetailRow label="Model name" value={exec.model_name} mono />
            <DetailRow label="Latency" value={fmtLatency(exec.latency_ms)} mono />
            <DetailRow
              label="Prompt tokens"
              value={fmtTokens(exec.prompt_tokens)}
              mono
            />
            <DetailRow
              label="Completion tokens"
              value={fmtTokens(exec.completion_tokens)}
              mono
            />
            <DetailRow
              label="Total tokens"
              value={fmtTokens(exec.total_tokens)}
              mono
            />
            <DetailRow
              label="Provider ID"
              value={exec.provider_id ?? "—"}
              mono
            />
            <DetailRow
              label="Model ID"
              value={exec.model_id ?? "—"}
              mono
            />
            <DetailRow
              label="API Key ID"
              value={exec.api_key_id ?? "—"}
              mono
            />
          </div>

          {/* Error detail — only for failed executions */}
          {!succeeded && exec.error_message && (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 space-y-1">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-destructive">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                Error detail
              </div>
              <pre className="text-[11px] font-mono text-destructive/80 whitespace-pre-wrap break-all leading-relaxed">
                {exec.error_message}
              </pre>
            </div>
          )}

          {/* Closed successfully — no error */}
          {succeeded && (
            <div className="flex items-center gap-1.5 text-xs text-status-success">
              <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
              Request completed successfully
            </div>
          )}
        </div>
      ) : null}
    </Dialog>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Filter bar
// ─────────────────────────────────────────────────────────────────────────────

type StatusFilter = "all" | "success" | "error"

interface FilterBarProps {
  searchQuery: string
  onSearchChange: (v: string) => void
  statusFilter: StatusFilter
  onStatusChange: (v: StatusFilter) => void
  total: number
  filtered: number
}

function FilterBar({
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusChange,
  total,
  filtered,
}: FilterBarProps) {
  const filters: { value: StatusFilter; label: string }[] = [
    { value: "all", label: "All" },
    { value: "success", label: "Success" },
    { value: "error", label: "Error" },
  ]

  return (
    <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
      {/* Search */}
      <div className="flex flex-col gap-1 w-full sm:w-72">
        <div className="relative w-full">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Filter by model name…"
            className="w-full rounded-md border border-border bg-surface-2 pl-8 pr-8 py-1.5 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 focus:border-primary/50 transition-colors"
          />
          {searchQuery && (
            <button
              onClick={() => onSearchChange("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        <span className="text-[10px] text-muted-foreground/70 pl-0.5">
          Applies to loaded page only
        </span>
      </div>

      <div className="flex items-center gap-3">
        {/* Status filter pills */}
        <div className="flex items-center gap-1 rounded-md border border-border bg-surface-2 p-0.5">
          <Filter className="h-3.5 w-3.5 text-muted-foreground ml-1.5" />
          {filters.map((f) => (
            <button
              key={f.value}
              onClick={() => onStatusChange(f.value)}
              className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                statusFilter === f.value
                  ? "bg-surface-3 text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Count */}
        <span className="text-xs text-muted-foreground whitespace-nowrap">
          {filtered === total ? `${total}` : `${filtered} / ${total}`} records
        </span>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Table row
// ─────────────────────────────────────────────────────────────────────────────

interface ExecRowProps {
  exec: ExecutionLogResponse
  onClick: () => void
}

function ExecRow({ exec, onClick }: ExecRowProps) {
  const success = isSuccess(exec.status_code)
  return (
    <tr
      className="border-t border-border/50 group cursor-pointer hover:bg-surface-2/60 transition-colors"
      onClick={onClick}
    >
      <td className="px-4 py-3">
        <Badge variant={statusBadgeVariant(exec.status_code)} withDot size="sm">
          {exec.status_code}
        </Badge>
      </td>
      <td className="px-4 py-3">
        <span className="font-mono text-xs text-foreground">{exec.model_name}</span>
      </td>
      <td className="px-4 py-3 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <Zap className="h-3 w-3 shrink-0" />
          {fmtLatency(exec.latency_ms)}
        </div>
      </td>
      <td className="px-4 py-3 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <Activity className="h-3 w-3 shrink-0" />
          {fmtTokens(exec.total_tokens)}
        </div>
      </td>
      <td className="px-4 py-3">
        {!success && exec.error_message ? (
          <span className="text-xs text-destructive/80 truncate max-w-[220px] block" title={exec.error_message}>
            {exec.error_message.length > 60
              ? exec.error_message.slice(0, 57) + "…"
              : exec.error_message}
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )}
      </td>
      <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
        <div className="flex items-center gap-1">
          <Clock className="h-3 w-3 shrink-0" />
          {fmtDateTimeShort(exec.created_at)}
        </div>
      </td>
      <td className="px-4 py-3 text-right">
        <ChevronRight className="h-4 w-4 text-muted-foreground/50 group-hover:text-muted-foreground transition-colors inline-block" />
      </td>
    </tr>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Pagination
// ─────────────────────────────────────────────────────────────────────────────

interface PaginationProps {
  page: number
  pageSize: number
  total: number
  onPrev: () => void
  onNext: () => void
  hasMore: boolean
}

function Pagination({ page, pageSize, total, onPrev, onNext, hasMore }: PaginationProps) {
  const start = page * pageSize + 1
  const end = Math.min((page + 1) * pageSize, page * pageSize + total)

  return (
    <div className="flex items-center justify-between pt-4 border-t border-border/50">
      <span className="text-xs text-muted-foreground">
        Showing {start}–{end} of this page
      </span>
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={onPrev}
          disabled={page === 0}
          leftIcon={<ChevronLeft className="h-3.5 w-3.5" />}
        >
          Previous
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onNext}
          disabled={!hasMore}
          rightIcon={<ChevronRight className="h-3.5 w-3.5" />}
        >
          Next
        </Button>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────────────

export function ExecutionsPage() {
  const { currentOrg, isLoading: orgLoading } = useOrganization()

  const [executions, setExecutions] = useState<ExecutionLogResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(0)
  const [hasMore, setHasMore] = useState(false)

  // Filters (client-side — backend only supports skip/limit)
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all")

  // Detail dialog
  const [detailId, setDetailId] = useState<string | null>(null)

  // ── fetch ────────────────────────────────────────────────────────────────

  const fetchPage = useCallback(
    async (pg: number, signal?: AbortSignal) => {
      if (!currentOrg) return
      setLoading(true)
      setError(null)
      try {
        const skip = pg * PAGE_SIZE
        // Fetch PAGE_SIZE + 1 to determine if there is a next page
        const data = await api.listOrganizationExecutions(
          currentOrg.id,
          skip,
          PAGE_SIZE + 1
        )
        if (signal?.aborted) return
        if (data.length > PAGE_SIZE) {
          setHasMore(true)
          setExecutions(data.slice(0, PAGE_SIZE))
        } else {
          setHasMore(false)
          setExecutions(data)
        }
      } catch (err: unknown) {
        if (signal?.aborted) return
        const msg = err instanceof Error ? err.message : "Failed to load executions."
        setError(msg)
        showToast(msg, "error")
      } finally {
        if (!signal?.aborted) setLoading(false)
      }
    },
    [currentOrg]
  )

  useEffect(() => {
    const ctrl = new AbortController()
    setPage(0)
    fetchPage(0, ctrl.signal)
    return () => ctrl.abort()
  }, [fetchPage])

  function handleRefresh() {
    fetchPage(page)
  }

  function handlePrev() {
    const prev = page - 1
    setPage(prev)
    fetchPage(prev)
  }

  function handleNext() {
    const next = page + 1
    setPage(next)
    fetchPage(next)
  }

  // ── client-side filtering ────────────────────────────────────────────────

  const filtered = useMemo(() => {
    let result = executions
    if (statusFilter === "success") {
      result = result.filter((e) => isSuccess(e.status_code))
    } else if (statusFilter === "error") {
      result = result.filter((e) => !isSuccess(e.status_code))
    }
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase()
      result = result.filter((e) => e.model_name.toLowerCase().includes(q))
    }
    return result
  }, [executions, statusFilter, searchQuery])

  // ── render ────────────────────────────────────────────────────────────────

  if (orgLoading) {
    return (
      <PageContainer>
        <TableSkeleton />
      </PageContainer>
    )
  }

  if (!currentOrg) {
    return (
      <PageContainer>
        <EmptyState
          title="No organization selected"
          description="Select an organization from the header to view execution logs."
        />
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <PageHeader
        eyebrow="Observability"
        title="Executions"
        description="Audit log of every LLM request routed through the gateway."
        actions={
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            disabled={loading}
            leftIcon={
              <RefreshCw
                className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}
              />
            }
          >
            Refresh
          </Button>
        }
      />

      {/* Filter bar — always visible when not in error */}
      {!error && (
        <FilterBar
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          statusFilter={statusFilter}
          onStatusChange={setStatusFilter}
          total={executions.length}
          filtered={filtered.length}
        />
      )}

      {/* Content */}
      {loading ? (
        <div className="rounded-lg border border-border bg-surface-card overflow-hidden">
          <TableSkeleton />
        </div>
      ) : error ? (
        <ErrorState
          title="Could not load executions"
          message={error}
          onRetry={handleRefresh}
        />
      ) : executions.length === 0 ? (
        <EmptyState
          icon={<Activity className="h-6 w-6" />}
          title="No executions yet"
          description="Execution logs will appear here once requests are routed through the gateway."
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<Search className="h-6 w-6" />}
          title="No results match your filters"
          description="Try adjusting the status filter or search query."
          action={
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSearchQuery("")
                setStatusFilter("all")
              }}
            >
              Clear filters
            </Button>
          }
        />
      ) : (
        <div className="rounded-lg border border-border bg-surface-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left min-w-[640px]">
              <thead>
                <tr className="border-b border-border/70 bg-surface-2/50">
                  <th className="px-4 py-3 text-[10px] font-mono font-medium uppercase tracking-wider text-muted-foreground">
                    Status
                  </th>
                  <th className="px-4 py-3 text-[10px] font-mono font-medium uppercase tracking-wider text-muted-foreground">
                    Model
                  </th>
                  <th className="px-4 py-3 text-[10px] font-mono font-medium uppercase tracking-wider text-muted-foreground">
                    Latency
                  </th>
                  <th className="px-4 py-3 text-[10px] font-mono font-medium uppercase tracking-wider text-muted-foreground">
                    Tokens
                  </th>
                  <th className="px-4 py-3 text-[10px] font-mono font-medium uppercase tracking-wider text-muted-foreground">
                    Error
                  </th>
                  <th className="px-4 py-3 text-[10px] font-mono font-medium uppercase tracking-wider text-muted-foreground">
                    Timestamp
                  </th>
                  <th className="px-4 py-3 w-8" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((exec) => (
                  <ExecRow
                    key={exec.id}
                    exec={exec}
                    onClick={() => setDetailId(exec.id)}
                  />
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="px-4 pb-4">
            <Pagination
              page={page}
              pageSize={PAGE_SIZE}
              total={filtered.length}
              onPrev={handlePrev}
              onNext={handleNext}
              hasMore={hasMore}
            />
          </div>
        </div>
      )}

      {/* Detail dialog */}
      {detailId && (
        <DetailDialog
          executionId={detailId}
          onClose={() => setDetailId(null)}
        />
      )}
    </PageContainer>
  )
}
