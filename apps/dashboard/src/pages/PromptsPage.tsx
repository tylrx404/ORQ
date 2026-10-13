import * as React from "react"
import { useState, useEffect, useCallback } from "react"
import {
  Plus,
  RefreshCw,
  FileText,
  Search,
  AlertTriangle,
  Calendar,
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
import type { PromptResponse, PromptCreateRequest } from "../types/api"

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—"
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  })
}

export function PromptsPage() {
  const { currentOrg, isLoading: orgLoading } = useOrganization()

  const [prompts, setPrompts] = useState<PromptResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")

  // Create Modal state
  const [createOpen, setCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState({
    name: "",
    description: "",
    initial_content: "",
  })
  const [actionLoading, setActionLoading] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const fetchPrompts = useCallback(async () => {
    if (!currentOrg) return
    setLoading(true)
    setError(null)
    try {
      const data = await api.listPrompts(currentOrg.id)
      setPrompts(data)
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.detail : "Failed to load prompts."
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [currentOrg])

  useEffect(() => {
    fetchPrompts()
  }, [fetchPrompts])

  const openCreate = () => {
    setCreateForm({
      name: "",
      description: "",
      initial_content: "",
    })
    setFormError(null)
    setCreateOpen(true)
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentOrg) return

    if (!createForm.name.trim()) {
      setFormError("Prompt name is required.")
      return
    }

    if (!createForm.initial_content.trim()) {
      setFormError("Initial prompt content is required.")
      return
    }

    setActionLoading(true)
    setFormError(null)
    try {
      const payload: PromptCreateRequest = {
        name: createForm.name.trim(),
        description: createForm.description.trim() || null,
        initial_content: createForm.initial_content.trim(),
      }
      await api.createPrompt(currentOrg.id, payload)
      showToast(`Prompt "${payload.name}" created successfully.`, "success")
      setCreateOpen(false)
      setCreateForm({ name: "", description: "", initial_content: "" })
      fetchPrompts()
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.detail : "Failed to create prompt."
      setFormError(msg)
      showToast(msg, "error")
    } finally {
      setActionLoading(false)
    }
  }

  const filteredPrompts = prompts.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.description && p.description.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  if (!orgLoading && !currentOrg) {
    return (
      <PageContainer>
        <div className="py-16">
          <EmptyState
            title="No organization selected"
            description="Select or create an organization to view and manage prompt templates."
          />
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <PageHeader
        eyebrow="Registry"
        title="Prompts"
        description={
          currentOrg
            ? `Manage versioned prompt templates and instructions for ${currentOrg.name}.`
            : "Manage versioned prompt templates and active deployment instructions."
        }
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchPrompts}
              disabled={loading}
              title="Refresh prompt list"
            >
              <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button variant="primary" size="sm" onClick={openCreate}>
              <Plus className="h-4 w-4 mr-1.5" />
              Create Prompt
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
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search prompts by name or description..."
            className="h-8.5 w-full pl-9 pr-3 rounded-md surface-base border border-border text-xs font-sans text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:border-border-strong transition-colors"
          />
        </div>
        <div className="text-xs font-mono text-muted-foreground self-center sm:self-auto">
          {prompts.length} {prompts.length === 1 ? "prompt" : "prompts"} registered
        </div>
      </div>

      {/* --- Main Content / States --- */}
      {loading && prompts.length === 0 ? (
        <div className="space-y-3 mt-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="p-5 surface-card rounded-lg border border-border space-y-3">
              <div className="flex justify-between items-center">
                <Skeleton className="h-5 w-48" />
                <Skeleton className="h-5 w-20" />
              </div>
              <Skeleton className="h-4 w-72" />
              <Skeleton className="h-3 w-32" />
            </div>
          ))}
        </div>
      ) : error ? (
        <ErrorState
          title="Failed to load prompts"
          message={error}
          onRetry={fetchPrompts}
          className="mt-6"
        />
      ) : filteredPrompts.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            icon={<FileText className="h-6 w-6" />}
            title={searchQuery ? "No matching prompts" : "No prompts registered"}
            description={
              searchQuery
                ? `No prompts match "${searchQuery}". Clear your search query or create a new prompt.`
                : "Create versioned prompt templates with immutable versions and published active states."
            }
            action={
              searchQuery ? (
                <Button variant="outline" size="sm" onClick={() => setSearchQuery("")}>
                  Clear search
                </Button>
              ) : (
                <Button variant="primary" size="sm" onClick={openCreate}>
                  <Plus className="h-4 w-4 mr-1.5" />
                  Create First Prompt
                </Button>
              )
            }
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 mt-2">
          {filteredPrompts.map((p) => (
            <div
              key={p.id}
              className="surface-card rounded-lg border border-border hover:border-border-strong transition-all p-5 flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              {/* Left Column: Info */}
              <div className="space-y-2 min-w-0">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <div className="flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded bg-primary/10 border border-primary/20 text-primary shrink-0">
                      <FileText className="h-4 w-4" />
                    </div>
                    <span className="text-sm font-semibold text-foreground tracking-tight">
                      {p.name}
                    </span>
                  </div>
                  {p.published_version_id ? (
                    <Badge variant="success" size="sm" withDot>
                      Published
                    </Badge>
                  ) : (
                    <Badge variant="neutral" size="sm" withDot>
                      Unpublished
                    </Badge>
                  )}
                </div>

                {p.description ? (
                  <p className="text-xs text-muted-foreground line-clamp-2 max-w-2xl leading-relaxed">
                    {p.description}
                  </p>
                ) : (
                  <p className="text-xs text-muted-foreground/50 italic">
                    No description provided.
                  </p>
                )}

                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-mono text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3 w-3 shrink-0 text-muted-foreground/60" />
                    Created {fmtDate(p.created_at)}
                  </span>
                  <span className="text-muted-foreground/40 hidden sm:inline">
                    Updated {fmtDate(p.updated_at)}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── CREATE PROMPT MODAL ─────────────────────────────────────── */}
      <Dialog
        isOpen={createOpen}
        onClose={() => !actionLoading && setCreateOpen(false)}
        title="Create Prompt"
        description="Define a new prompt template. Creating a prompt will automatically publish its initial Version 1."
        maxWidth="lg"
      >
        <form onSubmit={handleCreate} className="space-y-4">
          {formError && (
            <div className="p-3 rounded-md bg-destructive/10 border border-destructive/30 text-xs font-mono text-destructive flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div>
            <Input
              label="Prompt Name"
              type="text"
              required
              placeholder="e.g. customer-support-agent"
              value={createForm.name}
              onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
              hint="Unique identifier for this prompt template within the organization."
            />
          </div>

          <div>
            <Input
              label="Description (Optional)"
              type="text"
              placeholder="e.g. Handles incoming customer queries and resolves support tickets."
              value={createForm.description}
              onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
              hint="Brief explanation of the prompt's purpose and usage context."
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider select-none block">
              Initial Content (Version 1) <span className="text-destructive">*</span>
            </label>
            <textarea
              required
              rows={6}
              value={createForm.initial_content}
              onChange={(e) => setCreateForm({ ...createForm, initial_content: e.target.value })}
              placeholder="Enter system instructions or template content for version 1..."
              className="w-full rounded-md bg-surface-1 border border-border p-3 text-xs font-mono text-foreground placeholder:text-muted-foreground/60 focus-visible:outline-none focus-visible:border-primary/60 focus-visible:ring-1 focus-visible:ring-primary/40 resize-y shadow-xs"
            />
            <p className="text-xs text-muted-foreground mt-0.5">
              Immutable content that will be stored and published as Version 1.
            </p>
          </div>

          <div className="flex items-center justify-end gap-2 pt-4 border-t border-border/60">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={actionLoading}
              onClick={() => setCreateOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={actionLoading}
            >
              Create Prompt
            </Button>
          </div>
        </form>
      </Dialog>
    </PageContainer>
  )
}
