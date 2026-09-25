import { useState, useEffect, useCallback } from "react"
import { useOrganization } from "../providers/useOrganization"
import { api } from "../services/api"
import type { ApiKeyResponse, ApiKeyCreateRequest } from "../types/api"
import { Button } from "../components/ui/Button"
import { Badge } from "../components/ui/Badge"
import { Dialog } from "../components/ui/Dialog"
import { Input } from "../components/ui/Input"
import { EmptyState } from "../components/ui/EmptyState"
import { ErrorState } from "../components/ui/ErrorState"
import { Skeleton } from "../components/ui/Loading"

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—"
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  })
}

function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// Toast
// ─────────────────────────────────────────────────────────────────────────────

type ToastKind = "success" | "error" | "info"
interface ToastState { message: string; kind: ToastKind }

function showToast(set: (t: ToastState | null) => void, message: string, kind: ToastKind) {
  set({ message, kind })
  setTimeout(() => set(null), 4000)
}

// ─────────────────────────────────────────────────────────────────────────────
// Toast component
// ─────────────────────────────────────────────────────────────────────────────

function Toast({ toast }: { toast: ToastState | null }) {
  if (!toast) return null
  const colors: Record<ToastKind, string> = {
    success: "bg-emerald-900/90 border-emerald-700 text-emerald-100",
    error: "bg-red-900/90 border-red-700 text-red-100",
    info: "bg-zinc-800/90 border-zinc-600 text-zinc-100",
  }
  return (
    <div
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 rounded-lg border px-4 py-3 text-sm shadow-xl backdrop-blur-sm transition-all ${colors[toast.kind]}`}
    >
      <span>{toast.message}</span>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// New-key banner (shown once after creation)
// ─────────────────────────────────────────────────────────────────────────────

function NewKeyBanner({ rawKey, onDismiss }: { rawKey: string; onDismiss: () => void }) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(rawKey)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // fallback: select text
    }
  }

  return (
    <div className="rounded-lg border border-amber-700/60 bg-amber-950/40 p-4 space-y-3">
      <div className="flex items-start gap-3">
        <svg className="h-5 w-5 shrink-0 text-amber-400 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
        </svg>
        <div>
          <p className="text-sm font-semibold text-amber-300">Save your API key — it will not be shown again</p>
          <p className="text-xs text-amber-400/80 mt-0.5">
            Copy and store this key securely. After you dismiss this banner, the secret cannot be retrieved.
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <code className="flex-1 rounded bg-zinc-900 border border-zinc-700 px-3 py-2 text-xs font-mono text-zinc-200 break-all select-all">
          {rawKey}
        </code>
        <Button variant="outline" size="sm" onClick={handleCopy}>
          {copied ? "Copied!" : "Copy"}
        </Button>
      </div>
      <div className="flex justify-end">
        <Button variant="ghost" size="sm" onClick={onDismiss}>
          I have saved my key, dismiss
        </Button>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Create dialog
// ─────────────────────────────────────────────────────────────────────────────

interface CreateDialogProps {
  organizationId: string
  onCreated: (rawKey: string, key: ApiKeyResponse) => void
  onClose: () => void
}

function CreateKeyDialog({ organizationId, onCreated, onClose }: CreateDialogProps) {
  const [name, setName] = useState("")
  const [expiresAt, setExpiresAt] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      setError("Name is required.")
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const req: ApiKeyCreateRequest = {
        name: name.trim(),
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
      }
      const created = await api.createApiKey(organizationId, req)
      onCreated(created.key, created)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create API key.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog isOpen onClose={onClose} title="Create API Key" maxWidth="sm">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Name"
          value={name}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName(e.target.value)}
          placeholder="e.g. Production gateway key"
          autoFocus
        />
        <div>
          <label className="block text-xs font-medium text-zinc-400 mb-1.5">
            Expiry date <span className="text-zinc-500">(optional)</span>
          </label>
          <input
            type="date"
            value={expiresAt}
            onChange={(e) => setExpiresAt(e.target.value)}
            min={new Date().toISOString().split("T")[0]}
            className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500"
          />
        </div>
        {error && (
          <p className="text-xs text-red-400">{error}</p>
        )}
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="ghost" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" isLoading={submitting}>
            Create key
          </Button>
        </div>
      </form>
    </Dialog>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Rename dialog
// ─────────────────────────────────────────────────────────────────────────────

interface RenameDialogProps {
  apiKey: ApiKeyResponse
  onRenamed: (updated: ApiKeyResponse) => void
  onClose: () => void
}

function RenameKeyDialog({ apiKey, onRenamed, onClose }: RenameDialogProps) {
  const [name, setName] = useState(apiKey.name)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      setError("Name is required.")
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const updated = await api.updateApiKey(apiKey.id, { name: name.trim() })
      onRenamed(updated)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to rename API key.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog isOpen onClose={onClose} title="Rename API Key" maxWidth="sm">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Name"
          value={name}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName(e.target.value)}
          autoFocus
        />
        {error && <p className="text-xs text-red-400">{error}</p>}
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="ghost" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" isLoading={submitting}>
            Save
          </Button>
        </div>
      </form>
    </Dialog>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Delete confirm dialog
// ─────────────────────────────────────────────────────────────────────────────

interface DeleteDialogProps {
  apiKey: ApiKeyResponse
  onDeleted: () => void
  onClose: () => void
}

function DeleteKeyDialog({ apiKey, onDeleted, onClose }: DeleteDialogProps) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleDelete() {
    setSubmitting(true)
    setError(null)
    try {
      await api.deleteApiKey(apiKey.id)
      onDeleted()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete API key.")
      setSubmitting(false)
    }
  }

  return (
    <Dialog
      isOpen
      onClose={onClose}
      title="Delete API Key"
      description={`Delete "${apiKey.name}" (${apiKey.key_prefix}...)? This action cannot be undone. Any integrations using this key will stop working immediately.`}
      maxWidth="sm"
    >
      {error && <p className="text-xs text-red-400 mb-3">{error}</p>}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose} disabled={submitting}>
          Cancel
        </Button>
        <Button variant="danger" onClick={handleDelete} isLoading={submitting}>
          Delete key
        </Button>
      </div>
    </Dialog>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Key row
// ─────────────────────────────────────────────────────────────────────────────

interface KeyRowProps {
  apiKey: ApiKeyResponse
  onRename: (key: ApiKeyResponse) => void
  onToggle: (key: ApiKeyResponse) => void
  onDelete: (key: ApiKeyResponse) => void
  togglingId: string | null
}

function KeyRow({ apiKey, onRename, onToggle, onDelete, togglingId }: KeyRowProps) {
  const isToggling = togglingId === apiKey.id
  const isExpired = apiKey.expires_at ? new Date(apiKey.expires_at) < new Date() : false

  let badgeVariant: "success" | "error" | "warning" | "neutral" = "success"
  let badgeLabel = "Active"
  if (!apiKey.is_active) {
    badgeVariant = "neutral"
    badgeLabel = "Inactive"
  } else if (isExpired) {
    badgeVariant = "warning"
    badgeLabel = "Expired"
  }

  return (
    <tr className="border-t border-zinc-800 group">
      <td className="px-4 py-3.5">
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-medium text-zinc-100">{apiKey.name}</span>
          <span className="font-mono text-xs text-zinc-500">{apiKey.key_prefix}••••••••</span>
        </div>
      </td>
      <td className="px-4 py-3.5">
        <Badge variant={badgeVariant} withDot>
          {badgeLabel}
        </Badge>
      </td>
      <td className="px-4 py-3.5 text-sm text-zinc-400">{fmtDate(apiKey.expires_at)}</td>
      <td className="px-4 py-3.5 text-sm text-zinc-400">{fmtDateTime(apiKey.created_at)}</td>
      <td className="px-4 py-3.5">
        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button variant="ghost" size="xs" onClick={() => onRename(apiKey)}>
            Rename
          </Button>
          <Button
            variant="ghost"
            size="xs"
            onClick={() => onToggle(apiKey)}
            isLoading={isToggling}
            disabled={isToggling}
          >
            {apiKey.is_active ? "Deactivate" : "Activate"}
          </Button>
          <Button variant="ghost" size="xs" onClick={() => onDelete(apiKey)}>
            <span className="text-red-400 hover:text-red-300">Delete</span>
          </Button>
        </div>
      </td>
    </tr>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Loading skeleton
// ─────────────────────────────────────────────────────────────────────────────

function KeysSkeleton() {
  return (
    <div className="space-y-2">
      {[1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-14 w-full rounded-lg" />
      ))}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────────────

export function ApiKeysPage() {
  const { currentOrg } = useOrganization()
  const [keys, setKeys] = useState<ApiKeyResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Dialogs
  const [showCreate, setShowCreate] = useState(false)
  const [renameTarget, setRenameTarget] = useState<ApiKeyResponse | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<ApiKeyResponse | null>(null)

  // Post-creation banner
  const [newRawKey, setNewRawKey] = useState<string | null>(null)

  // Toggle loading tracker
  const [togglingId, setTogglingId] = useState<string | null>(null)

  // Toast
  const [toast, setToast] = useState<ToastState | null>(null)

  const loadKeys = useCallback(async () => {
    if (!currentOrg) return
    setLoading(true)
    setError(null)
    try {
      const data = await api.listApiKeys(currentOrg.id)
      setKeys(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load API keys.")
    } finally {
      setLoading(false)
    }
  }, [currentOrg])

  useEffect(() => {
    loadKeys()
  }, [loadKeys])

  // ── handlers ────────────────────────────────────────────────────────────

  function handleCreated(rawKey: string, created: ApiKeyResponse) {
    setShowCreate(false)
    setKeys((prev) => [created, ...prev])
    setNewRawKey(rawKey)
    showToast(setToast, "API key created.", "success")
  }

  function handleRenamed(updated: ApiKeyResponse) {
    setRenameTarget(null)
    setKeys((prev) => prev.map((k) => (k.id === updated.id ? updated : k)))
    showToast(setToast, "API key renamed.", "success")
  }

  async function handleToggle(apiKey: ApiKeyResponse) {
    setTogglingId(apiKey.id)
    try {
      const updated = await api.updateApiKey(apiKey.id, { is_active: !apiKey.is_active })
      setKeys((prev) => prev.map((k) => (k.id === updated.id ? updated : k)))
      showToast(setToast, `Key ${updated.is_active ? "activated" : "deactivated"}.`, "success")
    } catch (err: unknown) {
      showToast(setToast, err instanceof Error ? err.message : "Failed to update key.", "error")
    } finally {
      setTogglingId(null)
    }
  }

  function handleDeleted() {
    const id = deleteTarget!.id
    setDeleteTarget(null)
    setKeys((prev) => prev.filter((k) => k.id !== id))
    showToast(setToast, "API key deleted.", "success")
  }

  // ── render ────────────────────────────────────────────────────────────

  if (!currentOrg) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-zinc-500">
        Select an organization to manage API keys.
      </div>
    )
  }

  return (
    <div className="px-6 py-8 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-1">
            Infrastructure
          </p>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">API Keys</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Issue and manage machine-to-machine API keys for gateway access.
          </p>
        </div>
        <Button variant="primary" onClick={() => setShowCreate(true)}>
          <svg className="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New API Key
        </Button>
      </div>

      {/* Post-creation secret banner */}
      {newRawKey && (
        <NewKeyBanner rawKey={newRawKey} onDismiss={() => setNewRawKey(null)} />
      )}

      {/* Content */}
      {loading ? (
        <KeysSkeleton />
      ) : error ? (
        <ErrorState
          title="Could not load API keys"
          message={error}
          onRetry={loadKeys}
        />
      ) : keys.length === 0 ? (
        <EmptyState
          icon={
            <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
            </svg>
          }
          title="No API keys yet"
          description="Create your first API key to authenticate gateway requests."
          action={
            <Button variant="primary" onClick={() => setShowCreate(true)}>
              Create API Key
            </Button>
          }
        />
      ) : (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-zinc-800">
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Key
                </th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Status
                </th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Expires
                </th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Created
                </th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500 text-right">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {keys.map((k) => (
                <KeyRow
                  key={k.id}
                  apiKey={k}
                  onRename={setRenameTarget}
                  onToggle={handleToggle}
                  onDelete={setDeleteTarget}
                  togglingId={togglingId}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Dialogs */}
      {showCreate && (
        <CreateKeyDialog
          organizationId={currentOrg.id}
          onCreated={handleCreated}
          onClose={() => setShowCreate(false)}
        />
      )}
      {renameTarget && (
        <RenameKeyDialog
          apiKey={renameTarget}
          onRenamed={handleRenamed}
          onClose={() => setRenameTarget(null)}
        />
      )}
      {deleteTarget && (
        <DeleteKeyDialog
          apiKey={deleteTarget}
          onDeleted={handleDeleted}
          onClose={() => setDeleteTarget(null)}
        />
      )}

      <Toast toast={toast} />
    </div>
  )
}
