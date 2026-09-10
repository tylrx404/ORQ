import * as React from "react"
import { motion } from "framer-motion"
import { Copy, Check, Terminal } from "lucide-react"

const CURL_EXAMPLE = `curl -X POST https://api.orq.ai/v1/chat/completions \\
  -H "Authorization: Bearer orq_live_9d82f7c014e" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "gpt-4o",
    "messages": [
      {"role": "system", "content": "You are a precise technical assistant."},
      {"role": "user", "content": "Execute distributed consensus audit."}
    ],
    "stream": true
  }'`

const PYTHON_EXAMPLE = `from openai import OpenAI

# Simply redirect base_url to your ORQ control plane instance
client = OpenAI(
    api_key="orq_live_9d82f7c014e",
    base_url="https://api.orq.ai/v1"
)

response = client.chat.completions.create(
    model="claude-3-5-sonnet", # Handled via dynamic mapping
    messages=[{"role": "user", "content": "Ping cluster"}],
    stream=True
)

for chunk in response:
    print(chunk.choices[0].delta.content or "", end="")`

const NODE_EXAMPLE = `import OpenAI from "openai";

// Zero SDK migration: swap baseURL to your ORQ gateway
const openai = new OpenAI({
  apiKey: process.env.ORQ_API_KEY,
  baseURL: "https://api.orq.ai/v1",
});

const stream = await openai.chat.completions.create({
  model: "gpt-4o-mini",
  messages: [{ role: "user", content: "Check quota status" }],
  stream: true,
});

for await (const chunk of stream) {
  process.stdout.write(chunk.choices[0]?.delta?.content || "");
}`

export function DeveloperSection() {
  const [activeLang, setActiveLang] = React.useState<"curl" | "python" | "node">("curl")
  const [copied, setCopied] = React.useState(false)

  const codeMap = {
    curl: CURL_EXAMPLE,
    python: PYTHON_EXAMPLE,
    node: NODE_EXAMPLE,
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(codeMap[activeLang])
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <section id="developer" className="py-20 md:py-28 border-b border-border/60">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Column: Developer Narrative */}
          <div className="lg:col-span-5 space-y-6">
            <span className="text-xs font-mono uppercase tracking-widest text-primary font-medium">
              Developer Experience
            </span>
            <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-foreground font-sans">
              Zero SDK changes. Swap base URL and ship.
            </h2>
            <p className="text-sm sm:text-base text-muted-foreground leading-relaxed font-normal">
              ORQ exposes an OpenAI-compatible REST API. Seamlessly route chat completions,
              enforce rate limits, and track atomic quota usage using standard client libraries without
              proprietary SDK wrappers.
            </p>

            <div className="space-y-3 pt-2">
              <div className="flex items-start gap-3 text-xs font-mono">
                <div className="h-5 w-5 rounded bg-primary/10 border border-primary/30 flex items-center justify-center text-primary shrink-0 mt-0.5">
                  1
                </div>
                <div>
                  <div className="text-foreground font-semibold">One-line Base URL redirection</div>
                  <div className="text-muted-foreground mt-0.5">Direct traffic through `https://api.orq.ai/v1`.</div>
                </div>
              </div>

              <div className="flex items-start gap-3 text-xs font-mono">
                <div className="h-5 w-5 rounded bg-primary/10 border border-primary/30 flex items-center justify-center text-primary shrink-0 mt-0.5">
                  2
                </div>
                <div>
                  <div className="text-foreground font-semibold">Standard SSE streaming format</div>
                  <div className="text-muted-foreground mt-0.5">Seamless drop-in chunking across all major language runtimes.</div>
                </div>
              </div>

              <div className="flex items-start gap-3 text-xs font-mono">
                <div className="h-5 w-5 rounded bg-primary/10 border border-primary/30 flex items-center justify-center text-primary shrink-0 mt-0.5">
                  3
                </div>
                <div>
                  <div className="text-foreground font-semibold">Deterministic RFC-7807 error schema</div>
                  <div className="text-muted-foreground mt-0.5">Predictable HTTP status codes with structured JSON error diagnostics.</div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Code Snippet Card */}
          <div className="lg:col-span-7">
            <div className="rounded-xl border border-border-strong bg-surface-base shadow-2xl overflow-hidden">
              {/* Header with language selector and copy */}
              <div className="h-11 border-b border-border bg-surface-1 px-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Terminal className="h-4 w-4 text-primary" />
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setActiveLang("curl")}
                      className={`px-2.5 py-1 rounded text-xs font-mono transition-colors ${
                        activeLang === "curl"
                          ? "bg-surface-2 text-foreground font-medium"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      cURL
                    </button>
                    <button
                      onClick={() => setActiveLang("python")}
                      className={`px-2.5 py-1 rounded text-xs font-mono transition-colors ${
                        activeLang === "python"
                          ? "bg-surface-2 text-foreground font-medium"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      Python
                    </button>
                    <button
                      onClick={() => setActiveLang("node")}
                      className={`px-2.5 py-1 rounded text-xs font-mono transition-colors ${
                        activeLang === "node"
                          ? "bg-surface-2 text-foreground font-medium"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      Node.js / TS
                    </button>
                  </div>
                </div>

                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-2 text-muted-foreground hover:text-foreground transition-colors text-xs font-mono"
                  aria-label="Copy code to clipboard"
                >
                  {copied ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-status-success" />
                      <span className="text-status-success">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>

              {/* Code Pre Block */}
              <motion.div
                key={activeLang}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.15 }}
                className="p-5 overflow-x-auto custom-scrollbar bg-surface-base"
              >
                <pre className="text-xs font-mono text-muted-foreground leading-relaxed selection:bg-primary/20">
                  <code>{codeMap[activeLang]}</code>
                </pre>
              </motion.div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
