import { useState, useEffect, useRef } from "react"
import { Send, Square, RotateCcw, Box, AlertCircle, Clock } from "lucide-react"
import { PageHeader, PageContainer } from "../components/ui/PageHeader"
import { Button } from "../components/ui/Button"
import { useOrganization } from "../providers/useOrganization"
import { api, ApiClientError } from "../services/api"
import { showToast } from "../components/ui/toast-fn"

type Role = "system" | "user" | "assistant"

interface Message {
  role: Role
  content: string
  partial?: boolean
}

interface FlattenedModel {
  id: string
  providerName: string
  modelIdentifier: string
}

export function PlaygroundPage() {
  const { currentOrg } = useOrganization()

  // Data states
  const [models, setModels] = useState<FlattenedModel[]>([])
  const [selectedModel, setSelectedModel] = useState<string>("")
  const [initLoading, setInitLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Chat states
  const [messages, setMessages] = useState<Message[]>([
    { role: "system", content: "You are a helpful AI assistant." }
  ])
  const [input, setInput] = useState("")
  const [isStreaming, setIsStreaming] = useState(false)
  
  // Metadata states
  const [latency, setLatency] = useState<number | null>(null)
  const [usage, setUsage] = useState<{ prompt: number; completion: number; total: number } | null>(null)

  const abortControllerRef = useRef<AbortController | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }
  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Initialization
  useEffect(() => {
    let mounted = true
    const initPlayground = async () => {
      if (!currentOrg) return
      setInitLoading(true)
      setError(null)
      try {
        // Fetch providers and models for current organization
        const providers = await api.listProviders(currentOrg.id)
        const activeProviders = providers.filter(p => p.is_active)
        
        let allModels: FlattenedModel[] = []
        for (const provider of activeProviders) {
          const pModels = await api.listProviderModels(currentOrg.id, provider.id)
          const activeModels = pModels
            .filter(m => m.is_active && m.supports_streaming)
            .map(m => ({
              id: m.id,
              providerName: provider.name,
              modelIdentifier: m.model_identifier
            }))
          allModels = [...allModels, ...activeModels]
        }
        
        if (mounted) {
          setModels(allModels)
          if (allModels.length > 0) {
            setSelectedModel(allModels[0].modelIdentifier)
          }
        }
      } catch (err) {
        if (mounted) {
          const msg = err instanceof ApiClientError ? err.detail : "Failed to initialize playground."
          setError(msg)
          showToast(msg, "error")
        }
      } finally {
        if (mounted) setInitLoading(false)
      }
    }

    initPlayground()
    return () => { mounted = false }
  }, [currentOrg])

  const handleSend = async () => {
    if (!input.trim() || !selectedModel || isStreaming || !currentOrg) return

    const token = api.getAuthToken()
    if (!token) {
      showToast("Authentication required. Please sign in again.", "error")
      return
    }

    const userMsg: Message = { role: "user", content: input.trim() }
    const newMessages = [...messages, userMsg]
    setMessages([...newMessages, { role: "assistant", content: "", partial: true }])
    setInput("")
    setLatency(null)
    setUsage(null)
    setIsStreaming(true)

    abortControllerRef.current = new AbortController()
    const startTime = performance.now()

    try {
      const baseUrl = import.meta.env.VITE_API_URL || "/api/v1"
      const res = await fetch(`${baseUrl}/chat/completions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
          "X-Organization-Id": currentOrg.id,
          "Accept": "text/event-stream"
        },
        body: JSON.stringify({
          model: selectedModel,
          messages: newMessages.map(m => ({ role: m.role, content: m.content })),
          stream: true
        }),
        signal: abortControllerRef.current.signal
      })

      if (!res.ok) {
        let errStr = `HTTP ${res.status}`
        try {
          const errData = await res.json()
          errStr = errData.detail || errData.message || errData?.error?.message || errStr
        } catch { /* ignore */ }
        throw new Error(errStr)
      }

      if (!res.body) throw new Error("No response body")

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let assistantContent = ""
      let doneReading = false

      while (!doneReading) {
        const { value, done } = await reader.read()
        if (done) break

        const chunkStr = decoder.decode(value, { stream: true })
        const lines = chunkStr.split("\n")
        
        for (const line of lines) {
          if (line.startsWith("data: ") && line.trim() !== "data: [DONE]") {
            try {
              const data = JSON.parse(line.slice(6))
              
              if (data.choices?.[0]?.delta?.content) {
                assistantContent += data.choices[0].delta.content
                setMessages(prev => {
                  const last = prev[prev.length - 1]
                  return [...prev.slice(0, -1), { ...last, content: assistantContent }]
                })
              }
              
              // Standard OpenAI stream usage pattern
              if (data.usage) {
                setUsage({
                  prompt: data.usage.prompt_tokens || 0,
                  completion: data.usage.completion_tokens || 0,
                  total: data.usage.total_tokens || 0
                })
              }
            } catch (e) {
              console.error("Error parsing SSE JSON:", e)
            }
          }
        }
      }

      const endTime = performance.now()
      setLatency(Math.round(endTime - startTime))

      // Mark as complete
      setMessages(prev => {
        const last = prev[prev.length - 1]
        return [...prev.slice(0, -1), { ...last, partial: false }]
      })
    } catch (err: any) {
      if (err.name === "AbortError") {
        showToast("Generation stopped.", "info")
      } else {
        showToast(err.message || "Streaming failed.", "error")
      }
      // Leave whatever was generated as final
      setMessages(prev => {
        const last = prev[prev.length - 1]
        return [...prev.slice(0, -1), { ...last, partial: false }]
      })
    } finally {
      setIsStreaming(false)
      abortControllerRef.current = null
    }
  }

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
  }

  const handleClear = () => {
    setMessages([{ role: "system", content: "You are a helpful AI assistant." }])
    setLatency(null)
    setUsage(null)
  }

  if (initLoading) {
    return (
      <PageContainer>
        <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
          <div className="flex items-center gap-2 text-muted-foreground font-mono text-sm animate-pulse">
            <Box className="h-4 w-4" />
            Initializing Playground Environment...
          </div>
        </div>
      </PageContainer>
    )
  }

  if (error) {
    return (
      <PageContainer>
        <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
          <div className="max-w-md w-full surface-card rounded-lg border border-border p-6 text-center space-y-4">
            <AlertCircle className="h-8 w-8 text-status-error mx-auto opacity-80" />
            <h3 className="text-sm font-semibold text-foreground">Initialization Failed</h3>
            <p className="text-xs font-mono text-muted-foreground">
              {error}
            </p>
          </div>
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <PageHeader
        eyebrow="Core"
        title="Playground"
        description="Interactive testing environment for routing models."
      />

      <div className="flex flex-col h-[calc(100vh-14rem)] mt-4">
        
        {/* --- Top Controls --- */}
        <div className="flex items-center justify-between mb-4 shrink-0">
          <div className="flex items-center gap-3">
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="h-8 pl-3 pr-8 rounded-md surface-base border border-border text-xs font-mono text-foreground focus:outline-none focus:border-border-strong appearance-none cursor-pointer min-w-[200px]"
            >
              {models.length === 0 && (
                <option value="">No streaming models found</option>
              )}
              {models.map(m => (
                <option key={m.id} value={m.modelIdentifier}>
                  {m.providerName} : {m.modelIdentifier}
                </option>
              ))}
            </select>
          </div>
          
          <div className="flex items-center gap-2">
            {latency !== null && (
              <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-2 border border-border text-[10px] font-mono text-muted-foreground">
                <Clock className="h-3 w-3" />
                {latency}ms
              </div>
            )}
            {usage !== null && (
              <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-2 border border-border text-[10px] font-mono text-muted-foreground">
                <Box className="h-3 w-3" />
                {usage.total} tok ({usage.prompt}in/{usage.completion}out)
              </div>
            )}
            <Button variant="outline" size="sm" onClick={handleClear} disabled={isStreaming} className="h-8 px-3 text-xs">
              <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
              Clear
            </Button>
          </div>
        </div>

        {/* --- Conversation Area --- */}
        <div className="flex-1 overflow-y-auto custom-scrollbar surface-card rounded-lg border border-border flex flex-col">
          <div className="flex-1 p-4 space-y-6">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] sm:max-w-[75%] rounded-lg px-4 py-3 text-sm font-sans whitespace-pre-wrap ${
                  msg.role === "user" 
                    ? "bg-surface-elevated border border-border-strong text-foreground" 
                    : msg.role === "system"
                    ? "bg-surface-2 border border-border text-muted-foreground font-mono text-xs w-full"
                    : "bg-surface-base border border-border text-foreground"
                } ${msg.partial ? "opacity-80" : ""}`}>
                  
                  {/* Role Label */}
                  <div className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/70 mb-1.5 flex items-center justify-between">
                    <span>{msg.role}</span>
                    {msg.partial && <span className="animate-pulse">●</span>}
                  </div>
                  
                  {/* Content */}
                  {msg.content}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* --- Composer --- */}
        <div className="mt-4 shrink-0 flex items-end gap-3 relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
            placeholder="Type your message... (Shift+Enter for newline)"
            className="w-full min-h-[56px] max-h-32 resize-y surface-card border border-border rounded-lg p-3 pr-12 text-sm font-sans focus:outline-none focus:border-border-strong custom-scrollbar"
            disabled={isStreaming}
          />
          <div className="absolute right-3 bottom-3 flex items-center">
            {isStreaming ? (
              <button
                onClick={handleStop}
                className="p-1.5 rounded-md bg-surface-2 text-foreground hover:bg-surface-elevated transition-colors"
                title="Stop Generation"
              >
                <Square className="h-4 w-4 fill-current" />
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={!input.trim() || !selectedModel}
                className="p-1.5 rounded-md bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-colors"
                title="Send Message"
              >
                <Send className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

      </div>
    </PageContainer>
  )
}
