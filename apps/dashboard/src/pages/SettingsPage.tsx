import { useState, useEffect, useCallback, useId } from "react"
import {
  Building2,
  Edit3,
  X,
  Save,
  ShieldCheck,
  Calendar,
  Fingerprint,
  RefreshCw,
  Info,
} from "lucide-react"
import { PageHeader, PageContainer } from "../components/ui/PageHeader"
import { Button } from "../components/ui/Button"
import { Badge } from "../components/ui/Badge"
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "../components/ui/Card"
import { EmptyState } from "../components/ui/EmptyState"
import { ErrorState } from "../components/ui/ErrorState"
import { Skeleton } from "../components/ui/Loading"
import { useOrganization } from "../providers/useOrganization"
import { api, ApiClientError } from "../services/api"
import { showToast } from "../components/ui/toast-fn"
import type { Organization, MembershipRole } from "../types/api"

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—"
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    })
  } catch {
    return String(iso)
  }
}

function parseJwt(token: string): Record<string, unknown> | null {
  try {
    const base64Url = token.split(".")[1]
    if (!base64Url) return null
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/")
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    )
    return JSON.parse(jsonPayload)
  } catch {
    return null
  }
}

export function SettingsPage() {
  const { currentOrg, isLoading: orgLoading, reloadOrganizations } = useOrganization()

  const [org, setOrg] = useState<Organization | null>(currentOrg)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // RBAC resolution
  const [userRole, setUserRole] = useState<MembershipRole | null>(null)
  const [roleLoading, setRoleLoading] = useState(false)

  // Edit form state
  const [isEditing, setIsEditing] = useState(false)
  const [name, setName] = useState("")
  const [slug, setSlug] = useState("")
  const [description, setDescription] = useState("")
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  // Unique accessible IDs for inputs
  const nameInputId = useId()
  const slugInputId = useId()
  const descInputId = useId()

  // Determine user's role in this organization
  const resolveRole = useCallback(async (orgId: string) => {
    setRoleLoading(true)
    try {
      const token = api.getAuthToken()
      if (!token) {
        setUserRole(null)
        return
      }

      const payload = parseJwt(token)
      const currentUserId = payload?.sub as string | undefined

      const members = await api.listOrganizationMembers(orgId)
      if (currentUserId) {
        const myMembership = members.find((m) => m.user_id === currentUserId)
        if (myMembership) {
          setUserRole(myMembership.role)
          return
        }
      }
      
      // Fallback: If current user not found by ID, check if members list has owner/admin
      if (members.length > 0) {
        // If there's an owner, default conservatively to member unless matched
        setUserRole("member")
      } else {
        setUserRole(null)
      }
    } catch {
      // If fetching members fails (e.g. 403 or network), fallback to member (read-only)
      setUserRole("member")
    } finally {
      setRoleLoading(false)
    }
  }, [])

  // Sync state with currentOrg
  useEffect(() => {
    if (currentOrg) {
      setOrg(currentOrg)
      setName(currentOrg.name)
      setSlug(currentOrg.slug)
      setDescription(currentOrg.description || "")
      setIsEditing(false)
      setSaveError(null)
      setSaveSuccess(false)
      resolveRole(currentOrg.id)
    }
  }, [currentOrg, resolveRole])

  const canEdit = userRole === "admin" || userRole === "owner"

  const handleStartEdit = () => {
    if (!org) return
    setName(org.name)
    setSlug(org.slug)
    setDescription(org.description || "")
    setSaveError(null)
    setSaveSuccess(false)
    setIsEditing(true)
  }

  const handleCancel = () => {
    if (!org) return
    setName(org.name)
    setSlug(org.slug)
    setDescription(org.description || "")
    setSaveError(null)
    setIsEditing(false)
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!org) return

    const trimmedName = name.trim()
    const trimmedSlug = slug.trim()
    const trimmedDesc = description.trim()

    if (!trimmedName) {
      setSaveError("Organization name cannot be empty.")
      return
    }
    if (!trimmedSlug) {
      setSaveError("Organization slug cannot be empty.")
      return
    }

    setSaving(true)
    setSaveError(null)
    setSaveSuccess(false)

    try {
      const updated = await api.updateOrganization(org.id, {
        name: trimmedName,
        slug: trimmedSlug,
        description: trimmedDesc || null,
      })

      setOrg(updated)
      setIsEditing(false)
      setSaveSuccess(true)
      showToast("Organization updated successfully", "success")

      // Refresh global organization list so TopNav / selectors reflect new name/slug
      await reloadOrganizations()
    } catch (err: unknown) {
      const msg = err instanceof ApiClientError ? err.detail : err instanceof Error ? err.message : "Failed to update organization."
      setSaveError(msg)
      showToast(msg, "error")
    } finally {
      setSaving(false)
    }
  }

  const handleRefresh = async () => {
    if (!currentOrg) return
    setLoading(true)
    setError(null)
    try {
      const refreshed = await api.getOrganization(currentOrg.id)
      setOrg(refreshed)
      setName(refreshed.name)
      setSlug(refreshed.slug)
      setDescription(refreshed.description || "")
      await resolveRole(refreshed.id)
      showToast("Organization settings refreshed", "info")
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to refresh organization."
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  if (orgLoading) {
    return (
      <PageContainer>
        <div className="space-y-6 max-w-4xl">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-64 w-full rounded-lg" />
        </div>
      </PageContainer>
    )
  }

  if (!currentOrg) {
    return (
      <PageContainer>
        <EmptyState
          icon={<Building2 className="h-6 w-6" />}
          title="No organization selected"
          description="Select an organization from the workspace header to view and manage its settings."
        />
      </PageContainer>
    )
  }

  if (error) {
    return (
      <PageContainer>
        <ErrorState
          title="Could not load organization"
          message={error}
          onRetry={handleRefresh}
        />
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <PageHeader
        eyebrow="System"
        title="Settings"
        description="Manage organizational metadata, identifiers, and configuration parameters."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRefresh}
              disabled={loading || saving}
              leftIcon={<RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />}
            >
              Refresh
            </Button>
            {!isEditing && canEdit && (
              <Button
                variant="primary"
                size="sm"
                onClick={handleStartEdit}
                leftIcon={<Edit3 className="h-3.5 w-3.5" />}
              >
                Edit Settings
              </Button>
            )}
          </div>
        }
      />

      <div className="max-w-4xl space-y-6">
        {/* Organization Profile Card */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Building2 className="h-4 w-4 text-primary" />
                <CardTitle>Organization Profile</CardTitle>
              </div>
              <div className="flex items-center gap-2">
                {roleLoading ? (
                  <Skeleton className="h-5 w-20 rounded" />
                ) : userRole ? (
                  <Badge
                    variant={userRole === "owner" ? "primary" : userRole === "admin" ? "success" : "neutral"}
                    size="sm"
                  >
                    Role: {userRole}
                  </Badge>
                ) : null}
                {!canEdit && !roleLoading && (
                  <Badge variant="neutral" size="sm">
                    Read-only
                  </Badge>
                )}
              </div>
            </div>
            <CardDescription>
              Core entity metadata used for API routing, workspace segmentation, and gateway billing.
            </CardDescription>
          </CardHeader>

          {isEditing ? (
            /* Edit Mode Form */
            <form onSubmit={handleSave}>
              <CardContent className="space-y-5">
                {saveError && (
                  <div className="p-3 rounded-md bg-status-error/10 border border-status-error/30 text-xs font-mono text-status-error">
                    {saveError}
                  </div>
                )}

                <div className="space-y-4">
                  <div>
                    <label htmlFor={nameInputId} className="block text-xs font-mono font-medium text-foreground mb-1.5">
                      Organization Name <span className="text-status-error">*</span>
                    </label>
                    <input
                      id={nameInputId}
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                      placeholder="e.g. Acme Corporation"
                      className="w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 focus:border-primary/50 font-sans"
                    />
                    <p className="text-[11px] text-muted-foreground mt-1">
                      Display name for the organization across the control plane.
                    </p>
                  </div>

                  <div>
                    <label htmlFor={slugInputId} className="block text-xs font-mono font-medium text-foreground mb-1.5">
                      URL Slug <span className="text-status-error">*</span>
                    </label>
                    <input
                      id={slugInputId}
                      type="text"
                      value={slug}
                      onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ""))}
                      required
                      placeholder="e.g. acme-corp"
                      className="w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 focus:border-primary/50 font-mono"
                    />
                    <p className="text-[11px] text-muted-foreground mt-1 font-mono">
                      Unique identifier used in resource paths and CLI configuration.
                    </p>
                  </div>

                  <div>
                    <label htmlFor={descInputId} className="block text-xs font-mono font-medium text-foreground mb-1.5">
                      Description <span className="text-muted-foreground text-[10px]">(optional)</span>
                    </label>
                    <textarea
                      id={descInputId}
                      rows={3}
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Add an optional operational note or scope for this organization..."
                      className="w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 focus:border-primary/50 font-sans resize-none"
                    />
                  </div>
                </div>
              </CardContent>

              <CardFooter className="justify-end gap-2.5">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleCancel}
                  disabled={saving}
                  leftIcon={<X className="h-3.5 w-3.5" />}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  isLoading={saving}
                  leftIcon={<Save className="h-3.5 w-3.5" />}
                >
                  Save Changes
                </Button>
              </CardFooter>
            </form>
          ) : (
            /* Read-Only Display Mode */
            <div>
              <CardContent className="space-y-6">
                {saveSuccess && (
                  <div className="p-3 rounded-md bg-status-success/10 border border-status-success/30 text-xs font-mono text-status-success flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 shrink-0" />
                    Organization settings saved successfully.
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-5 gap-x-6">
                  {/* Name */}
                  <div className="space-y-1">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                      Organization Name
                    </span>
                    <p className="text-base font-semibold text-foreground">
                      {org?.name}
                    </p>
                  </div>

                  {/* Slug */}
                  <div className="space-y-1">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                      Slug
                    </span>
                    <div className="flex items-center gap-1.5">
                      <code className="text-sm font-mono text-foreground px-2 py-0.5 rounded bg-surface-2 border border-border/70">
                        {org?.slug}
                      </code>
                    </div>
                  </div>

                  {/* Description */}
                  <div className="sm:col-span-2 space-y-1">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                      Description
                    </span>
                    <p className="text-sm text-foreground leading-relaxed">
                      {org?.description || (
                        <span className="text-muted-foreground italic">No description provided.</span>
                      )}
                    </p>
                  </div>
                </div>

                {/* Read-only permission note for non-admins */}
                {!canEdit && !roleLoading && (
                  <div className="p-3.5 rounded-lg bg-surface-base border border-border/70 flex items-start gap-2.5 text-xs text-muted-foreground">
                    <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                    <span>
                      You have <span className="font-semibold text-foreground">member-level</span> permissions in this organization. Modifying organization details requires an <span className="font-semibold text-foreground">admin</span> or <span className="font-semibold text-foreground">owner</span> role.
                    </span>
                  </div>
                )}
              </CardContent>

              {/* System Identifiers & Timestamps */}
              <CardFooter className="flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-[11px] font-mono">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Fingerprint className="h-3.5 w-3.5 text-muted-foreground/70" />
                  <span>ID:</span>
                  <code className="text-foreground select-all">{org?.id}</code>
                </div>

                <div className="flex flex-wrap items-center gap-4 text-muted-foreground/80">
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    Created: {formatDateTime(org?.created_at)}
                  </span>
                  <span>Updated: {formatDateTime(org?.updated_at)}</span>
                </div>
              </CardFooter>
            </div>
          )}
        </Card>
      </div>
    </PageContainer>
  )
}
