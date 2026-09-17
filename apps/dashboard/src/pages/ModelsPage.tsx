import { useState, useEffect, useCallback } from "react"
import {
  Plus,
  RefreshCw,
  Cpu,
  Edit2,
  Trash2,
  Power,
  AlertTriangle,
  Search,
  Radio,
  Wrench,
  Eye,
  Brain,
  Hash,
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
  ProviderModelResponse,
  ProviderModelCreateRequest,
  ProviderModelUpdateRequest,
} from "../types/api"

interface FlattenedModelItem extends ProviderModelResponse {
  providerName: string
  providerType: string
}

export function ModelsPage() {
  const { currentOrg, isLoading: orgLoading } = useOrganization()

  const [providers, setProviders] = useState<ProviderResponse[]>([])
  const [models, setModels] = useState<FlattenedModelItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedProviderFilter, setSelectedProviderFilter] = useState<string>("all")
  const [failedProviders, setFailedProviders] = useState<string[]>([])

  // Modals state
  const [createOpen, setCreateOpen] = useState(false)
  const [editModel, setEditModel] = useState<FlattenedModelItem | null>(null)
  const [deleteModel, setDeleteModel] = useState<FlattenedModelItem | null>(null)

  // Form states
  const [targetProviderId, setTargetProviderId] = useState<string>("")
  const [createForm, setCreateForm] = useState<ProviderModelCreateRequest>({
    name: "",
    model_identifier: "",
    context_window: null,
    max_output_tokens: null,
    supports_streaming: true,
    supports_tools: false,
    supports_vision: false,
    supports_reasoning: false,
    is_active: true,
  })
  const [editForm, setEditForm] = useState<ProviderModelUpdateRequest>({
    name: "",
    model_identifier: "",
    context_window: null,
    max_output_tokens: null,
    supports_streaming: true,
    supports_tools: false,
    supports_vision: false,
    supports_reasoning: false,
    is_active: true,
  })
  const [actionLoading, setActionLoading] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Fetch all providers and their models
  const fetchAllData = useCallback(async () => {
    if (!currentOrg) return
    setLoading(true)
    setError(null)
    setFailedProviders([])
    try {
      const orgProviders = await api.listProviders(currentOrg.id)
      setProviders(orgProviders)

      let allModels: FlattenedModelItem[] = []
      const failedNames: string[] = []

      for (const p of orgProviders) {
        try {
          const pModels = await api.listProviderModels(currentOrg.id, p.id)
          const enriched = pModels.map(m => ({
            ...m,
            providerName: p.name,
            providerType: p.provider_type,
          }))
          allModels = [...allModels, ...enriched]
        } catch {
          failedNames.push(p.name)
        }
      }

      setModels(allModels)
      setFailedProviders(failedNames)
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.detail : "Failed to load models."
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [currentOrg])

  useEffect(() => {
    fetchAllData()
  }, [fetchAllData])

  // Open Create Modal
  const openCreate = () => {
    const defaultPid = providers.length > 0 ? providers[0].id : ""
    setTargetProviderId(defaultPid)
    setCreateForm({
      name: "",
      model_identifier: "",
      context_window: null,
      max_output_tokens: null,
      supports_streaming: true,
      supports_tools: false,
      supports_vision: false,
      supports_reasoning: false,
      is_active: true,
    })
    setFormError(null)
    setCreateOpen(true)
  }

  // Open Edit Modal
  const openEdit = (m: FlattenedModelItem) => {
    setEditModel(m)
    setEditForm({
      name: m.name,
      model_identifier: m.model_identifier,
      context_window: m.context_window ?? null,
      max_output_tokens: m.max_output_tokens ?? null,
      supports_streaming: m.supports_streaming,
      supports_tools: m.supports_tools,
      supports_vision: m.supports_vision,
      supports_reasoning: m.supports_reasoning,
      is_active: m.is_active,
    })
    setFormError(null)
  }

  // Handle Create
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentOrg) return
    if (!targetProviderId) {
      setFormError("Please select a provider.")
      return
    }
    if (!createForm.name.trim()) {
      setFormError("Model name is required.")
      return
    }
    if (!createForm.model_identifier.trim()) {
      setFormError("Model identifier is required.")
      return
    }

    setActionLoading(true)
    setFormError(null)
    try {
      const payload: ProviderModelCreateRequest = {
        name: createForm.name.trim(),
        model_identifier: createForm.model_identifier.trim(),
        context_window: createForm.context_window ? Number(createForm.context_window) : null,
        max_output_tokens: createForm.max_output_tokens ? Number(createForm.max_output_tokens) : null,
        supports_streaming: createForm.supports_streaming ?? false,
        supports_tools: createForm.supports_tools ?? false,
        supports_vision: createForm.supports_vision ?? false,
        supports_reasoning: createForm.supports_reasoning ?? false,
        is_active: createForm.is_active ?? true,
      }
      await api.createProviderModel(currentOrg.id, targetProviderId, payload)
      showToast(`Model "${payload.name}" created successfully.`, "success")
      setCreateOpen(false)
      fetchAllData()
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.detail : "Failed to create model."
      setFormError(msg)
      showToast(msg, "error")
    } finally {
      setActionLoading(false)
    }
  }

  // Handle Edit
  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editModel) return

    setActionLoading(true)
    setFormError(null)
    try {
      const payload: ProviderModelUpdateRequest = {
        name: editForm.name?.trim() || undefined,
        model_identifier: editForm.model_identifier?.trim() || undefined,
        context_window: editForm.context_window ? Number(editForm.context_window) : null,
        max_output_tokens: editForm.max_output_tokens ? Number(editForm.max_output_tokens) : null,
        supports_streaming: editForm.supports_streaming,
        supports_tools: editForm.supports_tools,
        supports_vision: editForm.supports_vision,
        supports_reasoning: editForm.supports_reasoning,
        is_active: editForm.is_active,
      }

      await api.updateProviderModel(editModel.provider_id, editModel.id, payload)
      showToast(`Model "${editForm.name || editModel.name}" updated.`, "success")
      setEditModel(null)
      fetchAllData()
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.detail : "Failed to update model."
      setFormError(msg)
      showToast(msg, "error")
    } finally {
      setActionLoading(false)
    }
  }

  // Handle Toggle Active
  const handleToggleActive = async (m: FlattenedModelItem) => {
    const nextState = !m.is_active
    try {
      await api.updateProviderModel(m.provider_id, m.id, { is_active: nextState })
      setModels(prev =>
        prev.map(item => (item.id === m.id ? { ...item, is_active: nextState } : item))
      )
      showToast(
        `Model "${m.name}" ${nextState ? "activated" : "deactivated"}.`,
        "success"
      )
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.detail : "Failed to toggle status."
      showToast(msg, "error")
    }
  }

  // Handle Delete
  const handleDelete = async () => {
    if (!deleteModel) return
    setActionLoading(true)
    try {
      await api.deleteProviderModel(deleteModel.provider_id, deleteModel.id)
      showToast(`Model "${deleteModel.name}" deleted.`, "success")
      setDeleteModel(null)
      setModels(prev => prev.filter(item => item.id !== deleteModel.id))
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.detail : "Failed to delete model."
      showToast(msg, "error")
    } finally {
      setActionLoading(false)
    }
  }

  const filteredModels = models.filter(m => {
    const matchesSearch =
      m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.model_identifier.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.providerName.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesProvider =
      selectedProviderFilter === "all" || m.provider_id === selectedProviderFilter
    return matchesSearch && matchesProvider
  })

  if (!orgLoading && !currentOrg) {
    return (
      <PageContainer>
        <div className="py-16">
          <EmptyState
            title="No organization found"
            description="Create or select an organization to view models."
          />
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <PageHeader
        eyebrow="Infrastructure"
        title="Models"
        description={
          currentOrg
            ? `Catalog and map models configured for ${currentOrg.name}.`
            : "Configure, catalog, and map upstream models for routing."
        }
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchAllData}
              disabled={loading}
              title="Refresh model catalog"
            >
              <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={openCreate}
              disabled={providers.length === 0}
              title={providers.length === 0 ? "Add a provider first" : "Add new model"}
            >
              <Plus className="h-4 w-4 mr-1.5" />
              Add Model
            </Button>
          </div>
        }
      />

      {/* --- Filter & Search Bar --- */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 mt-6 mb-4">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 flex-1 max-w-xl">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/60 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search models, identifiers, providers..."
              className="h-8.5 w-full pl-9 pr-3 rounded-md surface-base border border-border text-xs font-sans text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:border-border-strong transition-colors"
            />
          </div>

          {providers.length > 1 && (
            <select
              value={selectedProviderFilter}
              onChange={e => setSelectedProviderFilter(e.target.value)}
              className="h-8.5 px-3 rounded-md surface-base border border-border text-xs font-sans text-foreground focus:outline-none focus:border-border-strong cursor-pointer"
            >
              <option value="all">All Providers ({providers.length})</option>
              {providers.map(p => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          )}
        </div>

        <div className="text-xs font-mono text-muted-foreground self-center sm:self-auto">
          {models.length} {models.length === 1 ? "model" : "models"} cataloged
        </div>
      </div>

      {/* --- Non-blocking Provider Fetch Warning --- */}
      {failedProviders.length > 0 && (
        <div className="mb-4 px-3.5 py-2.5 rounded-md bg-status-warning/10 border border-status-warning/30 text-xs font-mono text-status-warning flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>
              Could not load models for {failedProviders.length === 1 ? "provider" : "providers"}:{" "}
              <strong>{failedProviders.join(", ")}</strong>. Other models remain available.
            </span>
          </div>
          <button
            onClick={fetchAllData}
            disabled={loading}
            className="text-[11px] font-sans underline hover:opacity-80 transition-opacity cursor-pointer shrink-0"
          >
            Retry
          </button>
        </div>
      )}

      {/* --- Main Content / States --- */}
      {loading && models.length === 0 ? (
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
          title="Failed to load models"
          message={error}
          onRetry={fetchAllData}
          className="mt-6"
        />
      ) : providers.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            icon={<Cpu className="h-6 w-6" />}
            title="No providers configured"
            description="Before adding models, you must configure at least one upstream provider in this organization."
            action={
              <a href="/app/providers">
                <Button variant="primary" size="sm">
                  Configure Providers
                </Button>
              </a>
            }
          />
        </div>
      ) : filteredModels.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            icon={<Cpu className="h-6 w-6" />}
            title={searchQuery ? "No matching models" : "No models cataloged"}
            description={
              searchQuery
                ? `No models match "${searchQuery}". Try clearing your search query.`
                : "Catalog models to designate routing identifiers, capabilities, and context limits for your gateway."
            }
            action={
              searchQuery ? (
                <Button variant="outline" size="sm" onClick={() => setSearchQuery("")}>
                  Clear search
                </Button>
              ) : (
                <Button variant="primary" size="sm" onClick={openCreate}>
                  <Plus className="h-4 w-4 mr-1.5" />
                  Add First Model
                </Button>
              )
            }
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 mt-2">
          {filteredModels.map(m => (
            <div
              key={m.id}
              className={`surface-card rounded-lg border transition-all p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                m.is_active ? "border-border hover:border-border-strong" : "border-border/60 opacity-70"
              }`}
            >
              {/* Left Column: Info */}
              <div className="space-y-2 min-w-0">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <span className="text-sm font-semibold text-foreground tracking-tight">
                    {m.name}
                  </span>
                  <Badge variant="default" size="sm" className="font-mono text-[10px]">
                    {m.model_identifier}
                  </Badge>
                  <Badge variant="neutral" size="sm" className="uppercase font-mono text-[10px]">
                    {m.providerName}
                  </Badge>
                  {m.is_active ? (
                    <Badge variant="success" size="sm" withDot>
                      Active
                    </Badge>
                  ) : (
                    <Badge variant="neutral" size="sm" withDot>
                      Inactive
                    </Badge>
                  )}
                </div>

                {/* Metadata & Capabilities */}
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs font-mono text-muted-foreground">
                  {m.context_window !== null && m.context_window !== undefined && (
                    <span className="flex items-center gap-1">
                      <Hash className="h-3 w-3 shrink-0 text-muted-foreground/60" />
                      Context: <strong className="text-foreground/80">{m.context_window.toLocaleString()}</strong>
                    </span>
                  )}
                  {m.max_output_tokens !== null && m.max_output_tokens !== undefined && (
                    <span className="flex items-center gap-1">
                      Max Out: <strong className="text-foreground/80">{m.max_output_tokens.toLocaleString()}</strong>
                    </span>
                  )}

                  {/* Feature Pills */}
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {m.supports_streaming && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-2 border border-border text-[10px] text-foreground/80" title="Supports streaming">
                        <Radio className="h-2.5 w-2.5 text-status-success" />
                        stream
                      </span>
                    )}
                    {m.supports_tools && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-2 border border-border text-[10px] text-foreground/80" title="Supports function calling / tools">
                        <Wrench className="h-2.5 w-2.5 text-primary" />
                        tools
                      </span>
                    )}
                    {m.supports_vision && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-2 border border-border text-[10px] text-foreground/80" title="Supports vision / multimodal">
                        <Eye className="h-2.5 w-2.5 text-status-warning" />
                        vision
                      </span>
                    )}
                    {m.supports_reasoning && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-2 border border-border text-[10px] text-foreground/80" title="Supports reasoning / chain-of-thought">
                        <Brain className="h-2.5 w-2.5 text-purple-400" />
                        reasoning
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Right Column: Actions */}
              <div className="flex items-center gap-2 shrink-0 pt-2 md:pt-0 border-t md:border-t-0 border-border/40 justify-end">
                <Button
                  variant="outline"
                  size="xs"
                  onClick={() => handleToggleActive(m)}
                  title={m.is_active ? "Deactivate model" : "Activate model"}
                  className="gap-1 text-xs h-7.5 px-2.5"
                >
                  <Power className={`h-3 w-3 ${m.is_active ? "text-status-warning" : "text-status-success"}`} />
                  {m.is_active ? "Deactivate" : "Activate"}
                </Button>
                <Button
                  variant="secondary"
                  size="xs"
                  onClick={() => openEdit(m)}
                  title="Edit model configuration"
                  className="gap-1 text-xs h-7.5 px-2.5"
                >
                  <Edit2 className="h-3 w-3" />
                  Edit
                </Button>
                <Button
                  variant="danger"
                  size="xs"
                  onClick={() => setDeleteModel(m)}
                  title="Delete model"
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

      {/* ── CREATE MODEL MODAL ────────────────────────────────────── */}
      <Dialog
        isOpen={createOpen}
        onClose={() => !actionLoading && setCreateOpen(false)}
        title="Add Model to Catalog"
        description="Map an upstream provider model identifier with token limits and capabilities."
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
              Provider
            </label>
            <select
              value={targetProviderId}
              onChange={e => setTargetProviderId(e.target.value)}
              className="h-9 w-full rounded-md surface-base border border-border px-3 text-sm font-sans text-foreground focus:outline-none focus:border-border-strong cursor-pointer"
              required
            >
              {providers.map(p => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.provider_type})
                </option>
              ))}
            </select>
          </div>

          <Input
            label="Display Name"
            placeholder="e.g. GPT-4o Production"
            value={createForm.name}
            onChange={e => setCreateForm({ ...createForm, name: e.target.value })}
            required
          />

          <Input
            label="Model Identifier"
            placeholder="e.g. gpt-4o, claude-3-5-sonnet-20241022"
            value={createForm.model_identifier}
            onChange={e => setCreateForm({ ...createForm, model_identifier: e.target.value })}
            hint="Exact identifier accepted by the upstream provider's chat-completion API."
            required
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="Context Window (Tokens)"
              type="number"
              placeholder="128000"
              value={createForm.context_window ?? ""}
              onChange={e =>
                setCreateForm({
                  ...createForm,
                  context_window: e.target.value ? parseInt(e.target.value, 10) : null,
                })
              }
            />

            <Input
              label="Max Output Tokens"
              type="number"
              placeholder="4096"
              value={createForm.max_output_tokens ?? ""}
              onChange={e =>
                setCreateForm({
                  ...createForm,
                  max_output_tokens: e.target.value ? parseInt(e.target.value, 10) : null,
                })
              }
            />
          </div>

          {/* Capabilities Checkboxes */}
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider select-none mb-2 block">
              Capabilities
            </label>
            <div className="grid grid-cols-2 gap-2 p-3 surface-base rounded-md border border-border text-xs">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={createForm.supports_streaming ?? false}
                  onChange={e => setCreateForm({ ...createForm, supports_streaming: e.target.checked })}
                  className="rounded border-border text-primary focus:ring-0"
                />
                <span>Streaming</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={createForm.supports_tools ?? false}
                  onChange={e => setCreateForm({ ...createForm, supports_tools: e.target.checked })}
                  className="rounded border-border text-primary focus:ring-0"
                />
                <span>Function Calling / Tools</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={createForm.supports_vision ?? false}
                  onChange={e => setCreateForm({ ...createForm, supports_vision: e.target.checked })}
                  className="rounded border-border text-primary focus:ring-0"
                />
                <span>Vision / Multimodal</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={createForm.supports_reasoning ?? false}
                  onChange={e => setCreateForm({ ...createForm, supports_reasoning: e.target.checked })}
                  className="rounded border-border text-primary focus:ring-0"
                />
                <span>Reasoning</span>
              </label>
            </div>
          </div>

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
              Add Model
            </Button>
          </div>
        </form>
      </Dialog>

      {/* ── EDIT MODEL MODAL ──────────────────────────────────────── */}
      <Dialog
        isOpen={!!editModel}
        onClose={() => !actionLoading && setEditModel(null)}
        title={`Edit Model: ${editModel?.name || ""}`}
        description="Update routing parameters, token limits, and capabilities."
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
            label="Display Name"
            placeholder="Model display name"
            value={editForm.name || ""}
            onChange={e => setEditForm({ ...editForm, name: e.target.value })}
          />

          <Input
            label="Model Identifier"
            placeholder="Exact model identifier"
            value={editForm.model_identifier || ""}
            onChange={e => setEditForm({ ...editForm, model_identifier: e.target.value })}
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="Context Window (Tokens)"
              type="number"
              placeholder="128000"
              value={editForm.context_window ?? ""}
              onChange={e =>
                setEditForm({
                  ...editForm,
                  context_window: e.target.value ? parseInt(e.target.value, 10) : null,
                })
              }
            />

            <Input
              label="Max Output Tokens"
              type="number"
              placeholder="4096"
              value={editForm.max_output_tokens ?? ""}
              onChange={e =>
                setEditForm({
                  ...editForm,
                  max_output_tokens: e.target.value ? parseInt(e.target.value, 10) : null,
                })
              }
            />
          </div>

          {/* Capabilities Checkboxes */}
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider select-none mb-2 block">
              Capabilities
            </label>
            <div className="grid grid-cols-2 gap-2 p-3 surface-base rounded-md border border-border text-xs">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={editForm.supports_streaming ?? false}
                  onChange={e => setEditForm({ ...editForm, supports_streaming: e.target.checked })}
                  className="rounded border-border text-primary focus:ring-0"
                />
                <span>Streaming</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={editForm.supports_tools ?? false}
                  onChange={e => setEditForm({ ...editForm, supports_tools: e.target.checked })}
                  className="rounded border-border text-primary focus:ring-0"
                />
                <span>Function Calling / Tools</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={editForm.supports_vision ?? false}
                  onChange={e => setEditForm({ ...editForm, supports_vision: e.target.checked })}
                  className="rounded border-border text-primary focus:ring-0"
                />
                <span>Vision / Multimodal</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={editForm.supports_reasoning ?? false}
                  onChange={e => setEditForm({ ...editForm, supports_reasoning: e.target.checked })}
                  className="rounded border-border text-primary focus:ring-0"
                />
                <span>Reasoning</span>
              </label>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-border/50">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setEditModel(null)}
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
        isOpen={!!deleteModel}
        onClose={() => !actionLoading && setDeleteModel(null)}
        title="Delete Model"
        maxWidth="sm"
      >
        <div className="space-y-4">
          <p className="text-xs text-muted-foreground leading-relaxed">
            Are you sure you want to delete{" "}
            <strong className="text-foreground font-semibold">"{deleteModel?.name}"</strong> (
            <code className="text-xs font-mono text-foreground/80">{deleteModel?.model_identifier}</code>)?
            This model will no longer be available for completions or routing.
          </p>

          <div className="flex items-center justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setDeleteModel(null)}
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
              Delete Model
            </Button>
          </div>
        </div>
      </Dialog>
    </PageContainer>
  )
}
