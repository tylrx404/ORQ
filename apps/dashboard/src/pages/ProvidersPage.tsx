import { useState, useEffect, useCallback } from "react"
import {
  Plus,
  RefreshCw,
  Server,
  Key,
  ExternalLink,
  Edit2,
  Trash2,
  Power,
  AlertTriangle,
  Cpu,
  Search,
} from "lucide-react"
import { PageHeader, PageContainer } from "../components/ui/PageHeader"
import { Button } from "../components/ui/Button"
import { Badge } from "../components/ui/Badge"
import { Dialog } from "../components/ui/Dialog"
import { Input } from "../components/ui/Input"
import { EmptyState } from "../components/ui/EmptyState"
import { ErrorState } from "../components/ui/ErrorState"
import { Skeleton } from "../components/ui/Loading"
import { useOrganization } from "../providers/useOrganization"
import { api, ApiClientError } from "../services/api"
import { showToast } from "../components/ui/toast-fn"
import type {
  ProviderResponse,
  ProviderCreateRequest,
  ProviderUpdateRequest,
  ProviderType,
} from "../types/api"

const PROVIDER_TYPE_OPTIONS: { label: string; value: ProviderType; hint: string }[] = [
  { label: "OpenAI", value: "openai", hint: "api.openai.com/v1" },
  { label: "Anthropic", value: "anthropic", hint: "api.anthropic.com" },
  { label: "Google Gemini", value: "gemini", hint: "generativelanguage.googleapis.com" },
  { label: "Groq", value: "groq", hint: "api.groq.com/openai/v1" },
  { label: "OpenRouter", value: "openrouter", hint: "openrouter.ai/api/v1" },
  { label: "Azure OpenAI", value: "azure_openai", hint: "Custom resource endpoint" },
  { label: "Ollama", value: "ollama", hint: "Local or remote Ollama server" },
  { label: "LM Studio", value: "lmstudio", hint: "Local LM Studio server" },
]

export function ProvidersPage() {
  const { currentOrg, isLoading: orgLoading } = useOrganization()

  const [providers, setProviders] = useState<ProviderResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")

  // Modals state
  const [createOpen, setCreateOpen] = useState(false)
  const [editProvider, setEditProvider] = useState<ProviderResponse | null>(null)
  const [deleteProvider, setDeleteProvider] = useState<ProviderResponse | null>(null)

  // Form states
  const [createForm, setCreateForm] = useState<ProviderCreateRequest>({
    name: "",
    provider_type: "openai",
    api_key: "",
    base_url: "",
    default_model: "",
  })
  const [editForm, setEditForm] = useState<ProviderUpdateRequest>({
    name: "",
    provider_type: "openai",
    api_key: "",
    base_url: "",
    default_model: "",
  })
  const [actionLoading, setActionLoading] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const fetchProviders = useCallback(async () => {
    if (!currentOrg) return
    setLoading(true)
    setError(null)
    try {
      const data = await api.listProviders(currentOrg.id)
      setProviders(data)
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.detail : "Failed to load providers."
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [currentOrg])

  useEffect(() => {
    fetchProviders()
  }, [fetchProviders])

  // Open Edit Modal
  const openEdit = (p: ProviderResponse) => {
    setEditProvider(p)
    setEditForm({
      name: p.name,
      provider_type: p.provider_type as ProviderType,
      api_key: "", // Keep blank unless updating
      base_url: p.base_url || "",
      default_model: p.default_model || "",
    })
    setFormError(null)
  }

  // Open Create Modal
  const openCreate = () => {
    setCreateForm({
      name: "",
      provider_type: "openai",
      api_key: "",
      base_url: "",
      default_model: "",
    })
    setFormError(null)
    setCreateOpen(true)
  }

  // Handle Create
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentOrg) return
    if (!createForm.name.trim()) {
      setFormError("Provider name is required.")
      return
    }
    if (!createForm.api_key.trim()) {
      setFormError("API Key is required.")
      return
    }

    setActionLoading(true)
    setFormError(null)
    try {
      const payload: ProviderCreateRequest = {
        name: createForm.name.trim(),
        provider_type: createForm.provider_type,
        api_key: createForm.api_key.trim(),
        base_url: createForm.base_url?.trim() || null,
        default_model: createForm.default_model?.trim() || null,
      }
      await api.createProvider(currentOrg.id, payload)
      showToast(`Provider "${payload.name}" created successfully.`, "success")
      setCreateOpen(false)
      fetchProviders()
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.detail : "Failed to create provider."
      setFormError(msg)
      showToast(msg, "error")
    } finally {
      setActionLoading(false)
    }
  }

  // Handle Edit
  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editProvider) return

    setActionLoading(true)
    setFormError(null)
    try {
      const payload: ProviderUpdateRequest = {
        name: editForm.name?.trim() || undefined,
        provider_type: editForm.provider_type,
        base_url: editForm.base_url?.trim() || null,
        default_model: editForm.default_model?.trim() || null,
      }
      // Only send api_key if user typed a new one
      if (editForm.api_key && editForm.api_key.trim()) {
        payload.api_key = editForm.api_key.trim()
      }

      await api.updateProvider(editProvider.id, payload)
      showToast(`Provider "${editForm.name || editProvider.name}" updated.`, "success")
      setEditProvider(null)
      fetchProviders()
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.detail : "Failed to update provider."
      setFormError(msg)
      showToast(msg, "error")
    } finally {
      setActionLoading(false)
    }
  }

  // Handle Toggle Active/Inactive
  const handleToggleActive = async (p: ProviderResponse) => {
    const nextState = !p.is_active
    try {
      await api.updateProvider(p.id, { is_active: nextState })
      setProviders(prev =>
        prev.map(item => (item.id === p.id ? { ...item, is_active: nextState } : item))
      )
      showToast(
        `Provider "${p.name}" ${nextState ? "activated" : "deactivated"}.`,
        "success"
      )
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.detail : "Failed to toggle status."
      showToast(msg, "error")
    }
  }

  // Handle Delete
  const handleDelete = async () => {
    if (!deleteProvider) return
    setActionLoading(true)
    try {
      await api.deleteProvider(deleteProvider.id)
      showToast(`Provider "${deleteProvider.name}" deleted.`, "success")
      setDeleteProvider(null)
      setProviders(prev => prev.filter(item => item.id !== deleteProvider.id))
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.detail : "Failed to delete provider."
      showToast(msg, "error")
    } finally {
      setActionLoading(false)
    }
  }

  const filteredProviders = providers.filter(
    p =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.provider_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.default_model && p.default_model.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  if (!orgLoading && !currentOrg) {
    return (
      <PageContainer>
        <div className="py-16">
          <EmptyState
            title="No organization found"
            description="Create or select an organization to manage upstream LLM providers."
          />
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <PageHeader
        eyebrow="Infrastructure"
        title="Providers"
        description={
          currentOrg
            ? `Configure upstream LLM credentials and endpoints for ${currentOrg.name}.`
            : "Manage upstream LLM provider credentials, custom base URLs, and active routing status."
        }
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchProviders}
              disabled={loading}
              title="Refresh provider list"
            >
              <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button variant="primary" size="sm" onClick={openCreate}>
              <Plus className="h-4 w-4 mr-1.5" />
              Add Provider
            </Button>
          </div>
        }
      />

      {/* --- Filter & Search Bar --- */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 mt-6 mb-4">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/60 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search providers, types, models..."
            className="h-8.5 w-full pl-9 pr-3 rounded-md surface-base border border-border text-xs font-sans text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:border-border-strong transition-colors"
          />
        </div>
        <div className="text-xs font-mono text-muted-foreground self-center sm:self-auto">
          {providers.length} {providers.length === 1 ? "provider" : "providers"} configured
        </div>
      </div>

      {/* --- Main Content / States --- */}
      {loading && providers.length === 0 ? (
        <div className="space-y-3 mt-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="p-5 surface-card rounded-lg border border-border space-y-3">
              <div className="flex justify-between items-center">
                <Skeleton className="h-5 w-48" />
                <Skeleton className="h-5 w-20" />
              </div>
              <Skeleton className="h-4 w-64" />
              <Skeleton className="h-4 w-32" />
            </div>
          ))}
        </div>
      ) : error ? (
        <ErrorState
          title="Failed to load providers"
          message={error}
          onRetry={fetchProviders}
          className="mt-6"
        />
      ) : filteredProviders.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            icon={<Server className="h-6 w-6" />}
            title={searchQuery ? "No matching providers" : "No providers configured"}
            description={
              searchQuery
                ? `No providers match "${searchQuery}". Clear your search query or add a new provider.`
                : "Upstream providers connect your organization to models like OpenAI, Anthropic, Gemini, and Groq."
            }
            action={
              searchQuery ? (
                <Button variant="outline" size="sm" onClick={() => setSearchQuery("")}>
                  Clear search
                </Button>
              ) : (
                <Button variant="primary" size="sm" onClick={openCreate}>
                  <Plus className="h-4 w-4 mr-1.5" />
                  Connect First Provider
                </Button>
              )
            }
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 mt-2">
          {filteredProviders.map(p => (
            <div
              key={p.id}
              className={`surface-card rounded-lg border transition-all p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                p.is_active ? "border-border hover:border-border-strong" : "border-border/60 opacity-70"
              }`}
            >
              {/* Left Column: Info */}
              <div className="space-y-2 min-w-0">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <span className="text-sm font-semibold text-foreground tracking-tight">
                    {p.name}
                  </span>
                  <Badge variant="neutral" size="sm" className="uppercase font-mono text-[10px]">
                    {p.provider_type}
                  </Badge>
                  {p.is_active ? (
                    <Badge variant="success" size="sm" withDot>
                      Active
                    </Badge>
                  ) : (
                    <Badge variant="neutral" size="sm" withDot>
                      Inactive
                    </Badge>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-mono text-muted-foreground">
                  {p.base_url ? (
                    <span className="flex items-center gap-1 truncate max-w-sm" title={p.base_url}>
                      <ExternalLink className="h-3 w-3 shrink-0 text-muted-foreground/60" />
                      {p.base_url}
                    </span>
                  ) : (
                    <span className="text-muted-foreground/50">Default Endpoint</span>
                  )}
                  {p.default_model && (
                    <span className="flex items-center gap-1">
                      <Cpu className="h-3 w-3 shrink-0 text-muted-foreground/60" />
                      Default: <strong className="text-foreground/80 font-mono">{p.default_model}</strong>
                    </span>
                  )}
                  <span className="text-muted-foreground/40 hidden sm:inline">
                    Created {new Date(p.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>

              {/* Right Column: Actions */}
              <div className="flex items-center gap-2 shrink-0 pt-2 md:pt-0 border-t md:border-t-0 border-border/40 justify-end">
                <Button
                  variant="outline"
                  size="xs"
                  onClick={() => handleToggleActive(p)}
                  title={p.is_active ? "Deactivate provider" : "Activate provider"}
                  className="gap-1 text-xs h-7.5 px-2.5"
                >
                  <Power className={`h-3 w-3 ${p.is_active ? "text-status-warning" : "text-status-success"}`} />
                  {p.is_active ? "Deactivate" : "Activate"}
                </Button>
                <Button
                  variant="secondary"
                  size="xs"
                  onClick={() => openEdit(p)}
                  title="Edit provider configuration"
                  className="gap-1 text-xs h-7.5 px-2.5"
                >
                  <Edit2 className="h-3 w-3" />
                  Edit
                </Button>
                <Button
                  variant="danger"
                  size="xs"
                  onClick={() => setDeleteProvider(p)}
                  title="Delete provider"
                  className="gap-1 text-xs h-7.5 px-2.5"
                >
                  <Trash2 className="h-3 w-3" />
                  Delete
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── CREATE PROVIDER MODAL ─────────────────────────────────── */}
      <Dialog
        isOpen={createOpen}
        onClose={() => !actionLoading && setCreateOpen(false)}
        title="Add Upstream Provider"
        description="Register an upstream LLM API provider with secure credentials for this organization."
        maxWidth="md"
      >
        <form onSubmit={handleCreate} className="space-y-4">
          {formError && (
            <div className="p-3 rounded-md bg-destructive/10 border border-destructive/30 text-xs font-mono text-destructive flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider select-none mb-1.5 block">
              Provider Type
            </label>
            <select
              value={createForm.provider_type}
              onChange={e =>
                setCreateForm({
                  ...createForm,
                  provider_type: e.target.value as ProviderType,
                  // Auto-suggest name if empty
                  name: createForm.name ? createForm.name : e.target.value.toUpperCase(),
                })
              }
              className="h-9 w-full rounded-md surface-base border border-border px-3 text-sm font-sans text-foreground focus:outline-none focus:border-border-strong cursor-pointer"
            >
              {PROVIDER_TYPE_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>
                  {opt.label} ({opt.hint})
                </option>
              ))}
            </select>
          </div>

          <Input
            label="Provider Name"
            placeholder="e.g. Primary OpenAI, Production Anthropic"
            value={createForm.name}
            onChange={e => setCreateForm({ ...createForm, name: e.target.value })}
            required
          />

          <Input
            label="API Key"
            type="password"
            placeholder="sk-..."
            value={createForm.api_key}
            onChange={e => setCreateForm({ ...createForm, api_key: e.target.value })}
            prefixIcon={<Key className="h-3.5 w-3.5" />}
            required
          />

          <Input
            label="Custom Base URL (Optional)"
            placeholder="https://api.openai.com/v1"
            value={createForm.base_url || ""}
            onChange={e => setCreateForm({ ...createForm, base_url: e.target.value })}
            hint="Leave blank to use default public endpoints. Useful for proxies or self-hosted models."
          />

          <Input
            label="Default Model (Optional)"
            placeholder="e.g. gpt-4o, claude-3-5-sonnet-20241022"
            value={createForm.default_model || ""}
            onChange={e => setCreateForm({ ...createForm, default_model: e.target.value })}
          />

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-border/50">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setCreateOpen(false)}
              disabled={actionLoading}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm" isLoading={actionLoading}>
              Connect Provider
            </Button>
          </div>
        </form>
      </Dialog>

      {/* ── EDIT PROVIDER MODAL ───────────────────────────────────── */}
      <Dialog
        isOpen={!!editProvider}
        onClose={() => !actionLoading && setEditProvider(null)}
        title={`Edit Provider: ${editProvider?.name || ""}`}
        description="Update provider configuration, endpoint URL, or rotate the API key."
        maxWidth="md"
      >
        <form onSubmit={handleUpdate} className="space-y-4">
          {formError && (
            <div className="p-3 rounded-md bg-destructive/10 border border-destructive/30 text-xs font-mono text-destructive flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <Input
            label="Provider Name"
            placeholder="Provider name"
            value={editForm.name || ""}
            onChange={e => setEditForm({ ...editForm, name: e.target.value })}
          />

          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider select-none mb-1.5 block">
              Provider Type
            </label>
            <select
              value={editForm.provider_type}
              onChange={e =>
                setEditForm({ ...editForm, provider_type: e.target.value as ProviderType })
              }
              className="h-9 w-full rounded-md surface-base border border-border px-3 text-sm font-sans text-foreground focus:outline-none focus:border-border-strong cursor-pointer"
            >
              {PROVIDER_TYPE_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>
                  {opt.label} ({opt.hint})
                </option>
              ))}
            </select>
          </div>

          <Input
            label="Rotate API Key"
            type="password"
            placeholder="Enter new key to rotate, or leave empty to keep unchanged"
            value={editForm.api_key || ""}
            onChange={e => setEditForm({ ...editForm, api_key: e.target.value })}
            prefixIcon={<Key className="h-3.5 w-3.5" />}
            hint="For security, existing API keys are never displayed."
          />

          <Input
            label="Custom Base URL"
            placeholder="https://api.openai.com/v1"
            value={editForm.base_url || ""}
            onChange={e => setEditForm({ ...editForm, base_url: e.target.value })}
          />

          <Input
            label="Default Model"
            placeholder="e.g. gpt-4o"
            value={editForm.default_model || ""}
            onChange={e => setEditForm({ ...editForm, default_model: e.target.value })}
          />

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-border/50">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setEditProvider(null)}
              disabled={actionLoading}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm" isLoading={actionLoading}>
              Save Changes
            </Button>
          </div>
        </form>
      </Dialog>

      {/* ── DELETE CONFIRMATION MODAL ─────────────────────────────── */}
      <Dialog
        isOpen={!!deleteProvider}
        onClose={() => !actionLoading && setDeleteProvider(null)}
        title="Delete Provider"
        maxWidth="sm"
      >
        <div className="space-y-4">
          <p className="text-xs text-muted-foreground leading-relaxed">
            Are you sure you want to delete{" "}
            <strong className="text-foreground font-semibold">"{deleteProvider?.name}"</strong>?
            This will permanently remove the credentials and any routing associated with this
            provider.
          </p>

          <div className="flex items-center justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setDeleteProvider(null)}
              disabled={actionLoading}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="danger"
              size="sm"
              onClick={handleDelete}
              isLoading={actionLoading}
            >
              Delete Provider
            </Button>
          </div>
        </div>
      </Dialog>
    </PageContainer>
  )
}
