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
  Users,
  UserPlus,
  Trash2,
  Copy,
  Check,
  AlertTriangle,
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
import type { Organization, MembershipRole, MembershipResponse } from "../types/api"

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

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

export function SettingsPage() {
  const { currentOrg, isLoading: orgLoading, reloadOrganizations } = useOrganization()

  const [org, setOrg] = useState<Organization | null>(currentOrg)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Current logged in user info & RBAC
  const [currentUserId, setCurrentUserId] = useState<string | null>(null)
  const [userRole, setUserRole] = useState<MembershipRole | null>(null)
  const [roleLoading, setRoleLoading] = useState(false)

  // Edit form state for Organization Profile
  const [isEditing, setIsEditing] = useState(false)
  const [name, setName] = useState("")
  const [slug, setSlug] = useState("")
  const [description, setDescription] = useState("")
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  // Members section state
  const [members, setMembers] = useState<MembershipResponse[]>([])
  const [membersLoading, setMembersLoading] = useState(false)
  const [membersError, setMembersError] = useState<string | null>(null)

  // Add Member state
  const [isAddingMember, setIsAddingMember] = useState(false)
  const [newUserId, setNewUserId] = useState("")
  const [newMemberRole, setNewMemberRole] = useState<MembershipRole>("member")
  const [addingMember, setAddingMember] = useState(false)
  const [addMemberError, setAddMemberError] = useState<string | null>(null)

  // Role mutation state
  const [updatingRoleId, setUpdatingRoleId] = useState<string | null>(null)

  // Remove member state
  const [removingMember, setRemovingMember] = useState<MembershipResponse | null>(null)
  const [confirmRemoving, setConfirmRemoving] = useState(false)

  // Copied User ID feedback
  const [copiedId, setCopiedId] = useState<string | null>(null)

  // Unique accessible IDs for inputs
  const nameInputId = useId()
  const slugInputId = useId()
  const descInputId = useId()
  const newUserIdInputId = useId()
  const newRoleSelectId = useId()

  const fetchMembers = useCallback(async (orgId: string) => {
    setMembersLoading(true)
    setMembersError(null)
    try {
      const data = await api.listOrganizationMembers(orgId)
      setMembers(data)
      return data
    } catch (err: unknown) {
      const msg =
        err instanceof ApiClientError
          ? err.detail
          : err instanceof Error
          ? err.message
          : "Failed to load organization members."
      setMembersError(msg)
      return []
    } finally {
      setMembersLoading(false)
    }
  }, [])

  // Determine user's role in this organization
  const resolveRole = useCallback(
    async (orgId: string) => {
      setRoleLoading(true)
      try {
        const token = api.getAuthToken()
        if (!token) {
          setCurrentUserId(null)
          setUserRole(null)
          return
        }

        const payload = parseJwt(token)
        const myUserId = payload?.sub as string | undefined
        setCurrentUserId(myUserId || null)

        const memberList = await fetchMembers(orgId)
        if (myUserId) {
          const myMembership = memberList.find((m) => m.user_id === myUserId)
          if (myMembership) {
            setUserRole(myMembership.role)
            return
          }
        }

        if (memberList.length > 0) {
          setUserRole("member")
        } else {
          setUserRole(null)
        }
      } catch {
        setUserRole("member")
      } finally {
        setRoleLoading(false)
      }
    },
    [fetchMembers]
  )

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
      setIsAddingMember(false)
      setRemovingMember(null)
      resolveRole(currentOrg.id)
    }
  }, [currentOrg, resolveRole])

  const canEditOrg = userRole === "admin" || userRole === "owner"
  const canManageMembers = userRole === "admin" || userRole === "owner"
  const isOwner = userRole === "owner"

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

      await reloadOrganizations()
    } catch (err: unknown) {
      const msg =
        err instanceof ApiClientError
          ? err.detail
          : err instanceof Error
          ? err.message
          : "Failed to update organization."
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
      showToast("Settings refreshed", "info")
    } catch (err: unknown) {
      const msg =
        err instanceof ApiClientError
          ? err.detail
          : err instanceof Error
          ? err.message
          : "Failed to refresh organization."
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  // --- Member Handlers ---

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!org) return

    const trimmedUserId = newUserId.trim()
    if (!trimmedUserId) {
      setAddMemberError("User ID (UUID) is required.")
      return
    }

    if (!UUID_REGEX.test(trimmedUserId)) {
      setAddMemberError("User ID must be a valid UUID format (e.g. 12345678-1234-1234-1234-123456789abc).")
      return
    }

    setAddingMember(true)
    setAddMemberError(null)

    try {
      const newMember = await api.addOrganizationMember(org.id, {
        user_id: trimmedUserId,
        role: newMemberRole,
      })

      setMembers((prev) => [...prev, newMember])
      setNewUserId("")
      setNewMemberRole("member")
      setIsAddingMember(false)
      showToast("Member added successfully", "success")
    } catch (err: unknown) {
      const msg =
        err instanceof ApiClientError
          ? err.detail
          : err instanceof Error
          ? err.message
          : "Failed to add member."
      setAddMemberError(msg)
      showToast(msg, "error")
    } finally {
      setAddingMember(false)
    }
  }

  const handleRoleChange = async (member: MembershipResponse, newRole: MembershipRole) => {
    if (!org || !isOwner) return
    if (member.role === newRole) return

    setUpdatingRoleId(member.user_id)
    try {
      const updated = await api.updateOrganizationMemberRole(org.id, member.user_id, {
        role: newRole,
      })

      setMembers((prev) => prev.map((m) => (m.user_id === member.user_id ? updated : m)))
      if (member.user_id === currentUserId) {
        setUserRole(updated.role)
      }
      showToast("Member role updated", "success")
    } catch (err: unknown) {
      const msg =
        err instanceof ApiClientError
          ? err.detail
          : err instanceof Error
          ? err.message
          : "Failed to update member role."
      showToast(msg, "error")
    } finally {
      setUpdatingRoleId(null)
    }
  }

  const handleConfirmRemoveMember = async () => {
    if (!org || !removingMember) return

    if (removingMember.user_id === currentUserId) {
      showToast("You cannot remove yourself from the organization.", "error")
      setRemovingMember(null)
      return
    }

    setConfirmRemoving(true)
    try {
      await api.removeOrganizationMember(org.id, removingMember.user_id)
      setMembers((prev) => prev.filter((m) => m.user_id !== removingMember.user_id))
      showToast("Member removed from organization", "success")
      setRemovingMember(null)
    } catch (err: unknown) {
      const msg =
        err instanceof ApiClientError
          ? err.detail
          : err instanceof Error
          ? err.message
          : "Failed to remove member."
      showToast(msg, "error")
    } finally {
      setConfirmRemoving(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedId(text)
    showToast("User ID copied to clipboard", "info")
    setTimeout(() => {
      setCopiedId((current) => (current === text ? null : current))
    }, 2000)
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
        description="Manage organizational metadata, identifiers, and team membership access control."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRefresh}
              disabled={loading || saving || membersLoading}
              leftIcon={<RefreshCw className={`h-3.5 w-3.5 ${loading || membersLoading ? "animate-spin" : ""}`} />}
            >
              Refresh
            </Button>
            {!isEditing && canEditOrg && (
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
                {!canEditOrg && !roleLoading && (
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
                {!canEditOrg && !roleLoading && (
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

        {/* Organization Members Card */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Users className="h-4 w-4 text-primary" />
                <CardTitle>Organization Members</CardTitle>
                {!membersLoading && (
                  <Badge variant="neutral" size="sm">
                    {members.length} {members.length === 1 ? "member" : "members"}
                  </Badge>
                )}
              </div>
              <div className="flex items-center gap-2">
                {canManageMembers && !isAddingMember && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setIsAddingMember(true)
                      setAddMemberError(null)
                    }}
                    leftIcon={<UserPlus className="h-3.5 w-3.5" />}
                  >
                    Add Member
                  </Button>
                )}
              </div>
            </div>
            <CardDescription>
              Users with direct role assignments and security scopes within this organization.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            {/* Add Member Form (inline expandable) */}
            {isAddingMember && (
              <form
                onSubmit={handleAddMember}
                className="p-4 rounded-lg bg-surface-2 border border-border/80 space-y-4 mb-4"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-medium text-foreground flex items-center gap-1.5">
                    <UserPlus className="h-3.5 w-3.5 text-primary" />
                    Add Existing User by UUID
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsAddingMember(false)}
                    disabled={addingMember}
                    className="h-6 w-6 p-0"
                  >
                    <X className="h-3.5 w-3.5" />
                  </Button>
                </div>

                {addMemberError && (
                  <div className="p-3 rounded-md bg-status-error/10 border border-status-error/30 text-xs font-mono text-status-error">
                    {addMemberError}
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="sm:col-span-2">
                    <label htmlFor={newUserIdInputId} className="block text-[11px] font-mono text-muted-foreground mb-1">
                      User UUID <span className="text-status-error">*</span>
                    </label>
                    <input
                      id={newUserIdInputId}
                      type="text"
                      value={newUserId}
                      onChange={(e) => setNewUserId(e.target.value.trim())}
                      placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
                      required
                      className="w-full rounded-md border border-border bg-surface-base px-3 py-1.5 text-xs text-foreground placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 focus:border-primary/50 font-mono"
                    />
                  </div>

                  <div>
                    <label htmlFor={newRoleSelectId} className="block text-[11px] font-mono text-muted-foreground mb-1">
                      Role
                    </label>
                    <select
                      id={newRoleSelectId}
                      value={newMemberRole}
                      onChange={(e) => setNewMemberRole(e.target.value as MembershipRole)}
                      className="w-full rounded-md border border-border bg-surface-base px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 focus:border-primary/50 font-mono"
                    >
                      <option value="member">member</option>
                      <option value="admin">admin</option>
                      <option value="owner">owner</option>
                    </select>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2 pt-1">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsAddingMember(false)}
                    disabled={addingMember}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    isLoading={addingMember}
                    leftIcon={<UserPlus className="h-3.5 w-3.5" />}
                  >
                    Add Member
                  </Button>
                </div>
              </form>
            )}

            {/* Error loading members */}
            {membersError && (
              <div className="p-3 rounded-md bg-status-error/10 border border-status-error/30 text-xs font-mono text-status-error flex items-center justify-between">
                <span>{membersError}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => org && fetchMembers(org.id)}
                  className="h-7 text-xs"
                >
                  Retry
                </Button>
              </div>
            )}

            {/* Loading state */}
            {membersLoading ? (
              <div className="space-y-3 py-2">
                <Skeleton className="h-12 w-full rounded" />
                <Skeleton className="h-12 w-full rounded" />
                <Skeleton className="h-12 w-full rounded" />
              </div>
            ) : members.length === 0 ? (
              <EmptyState
                icon={<Users className="h-5 w-5" />}
                title="No members found"
                description="This organization does not currently have any associated member accounts."
              />
            ) : (
              /* Members Table */
              <div className="overflow-x-auto rounded-md border border-border/80">
                <table className="w-full min-w-[640px] text-left border-collapse">
                  <thead>
                    <tr className="border-b border-border/80 bg-surface-2/60 text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
                      <th className="py-2.5 px-3 font-medium">User Identifier (UUID)</th>
                      <th className="py-2.5 px-3 font-medium">Role</th>
                      <th className="py-2.5 px-3 font-medium">Joined</th>
                      <th className="py-2.5 px-3 font-medium text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60 text-xs font-mono">
                    {members.map((member) => {
                      const isMe = currentUserId ? member.user_id === currentUserId : false
                      const isRoleUpdating = updatingRoleId === member.user_id

                      return (
                        <tr
                          key={member.id}
                          className={`transition-colors hover:bg-surface-2/40 ${isMe ? "bg-primary/5" : ""}`}
                        >
                          {/* User ID column */}
                          <td className="py-3 px-3">
                            <div className="flex items-center gap-2">
                              <code className="text-xs text-foreground font-mono select-all">
                                {member.user_id}
                              </code>
                              <button
                                type="button"
                                onClick={() => copyToClipboard(member.user_id)}
                                title="Copy User UUID"
                                className="text-muted-foreground hover:text-foreground transition-colors p-0.5 rounded"
                              >
                                {copiedId === member.user_id ? (
                                  <Check className="h-3 w-3 text-status-success" />
                                ) : (
                                  <Copy className="h-3 w-3" />
                                )}
                              </button>
                              {isMe && (
                                <Badge variant="primary" size="sm">
                                  You
                                </Badge>
                              )}
                            </div>
                          </td>

                          {/* Role column */}
                          <td className="py-3 px-3">
                            {isOwner ? (
                              /* Owner can change role inline */
                              <div className="flex items-center gap-1.5">
                                <select
                                  value={member.role}
                                  onChange={(e) =>
                                    handleRoleChange(member, e.target.value as MembershipRole)
                                  }
                                  disabled={isRoleUpdating}
                                  className="rounded border border-border bg-surface-base px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 font-mono disabled:opacity-50"
                                >
                                  <option value="member">member</option>
                                  <option value="admin">admin</option>
                                  <option value="owner">owner</option>
                                </select>
                                {isRoleUpdating && (
                                  <RefreshCw className="h-3 w-3 animate-spin text-muted-foreground" />
                                )}
                              </div>
                            ) : (
                              /* Admin & members see static badge */
                              <Badge
                                variant={
                                  member.role === "owner"
                                    ? "primary"
                                    : member.role === "admin"
                                    ? "success"
                                    : "neutral"
                                }
                                size="sm"
                              >
                                {member.role}
                              </Badge>
                            )}
                          </td>

                          {/* Joined date */}
                          <td className="py-3 px-3 text-muted-foreground text-[11px]">
                            {formatDateTime(member.created_at)}
                          </td>

                          {/* Actions column */}
                          <td className="py-3 px-3 text-right">
                            {canManageMembers && (
                              <div className="inline-flex items-center justify-end">
                                {isMe ? (
                                  <span
                                    title="You cannot remove yourself from the organization."
                                    className="text-[11px] text-muted-foreground/60 italic cursor-not-allowed select-none"
                                  >
                                    Self (Protected)
                                  </span>
                                ) : (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setRemovingMember(member)}
                                    className="h-7 px-2 text-status-error hover:bg-status-error/10 hover:text-status-error"
                                    title="Remove member"
                                  >
                                    <Trash2 className="h-3.5 w-3.5" />
                                  </Button>
                                )}
                              </div>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>

          {/* Remove Member Confirmation Modal */}
          {removingMember && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
              <div className="w-full max-w-md rounded-lg border border-border bg-surface-1 p-5 shadow-2xl space-y-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-full bg-status-error/10 text-status-error">
                    <AlertTriangle className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">Remove Organization Member</h3>
                    <p className="text-xs text-muted-foreground">Confirm access revocation</p>
                  </div>
                </div>

                <div className="space-y-2 text-xs text-foreground bg-surface-2 p-3 rounded border border-border/70 font-mono">
                  <div>
                    <span className="text-muted-foreground">User ID:</span> {removingMember.user_id}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Role:</span> {removingMember.role}
                  </div>
                </div>

                <p className="text-xs text-muted-foreground leading-relaxed">
                  This user will immediately lose all permissions and access to projects, executions, and keys within this organization.
                </p>

                <div className="flex items-center justify-end gap-2.5 pt-2">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setRemovingMember(null)}
                    disabled={confirmRemoving}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="button"
                    variant="primary"
                    size="sm"
                    onClick={handleConfirmRemoveMember}
                    isLoading={confirmRemoving}
                    className="bg-status-error hover:bg-status-error/90 text-white"
                  >
                    Revoke Access
                  </Button>
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>
    </PageContainer>
  )
}
