import { Link } from "react-router-dom"
import { Layers } from "lucide-react"

export function FooterSection() {
  return (
    <footer className="border-t border-border bg-background py-12 md:py-16">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-12">
          {/* Brand Col */}
          <div className="col-span-2 space-y-3">
            <Link to="/" className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded bg-primary/10 border border-primary/30 text-primary">
                <Layers className="h-4 w-4" />
              </div>
              <span className="font-mono font-bold tracking-tight text-sm text-foreground">
                ORQ
              </span>
            </Link>
            <p className="text-xs text-muted-foreground max-w-sm leading-relaxed">
              Precision multi-tenant control plane for LLM routing, token telemetry, and atomic quota enforcement.
            </p>
            <div className="flex items-center gap-2 text-[11px] font-mono text-muted-foreground pt-1">
              <span className="inline-block h-2 w-2 rounded-full bg-status-success" />
              <span>Core Gateway Online</span>
            </div>
          </div>

          {/* Product Links */}
          <div className="space-y-2.5">
            <div className="text-xs font-mono font-medium text-foreground uppercase tracking-wider">
              Product
            </div>
            <ul className="space-y-2 text-xs text-muted-foreground">
              <li>
                <Link to="/app/models" className="hover:text-foreground transition-colors">
                  Models
                </Link>
              </li>
              <li>
                <Link to="/app/providers" className="hover:text-foreground transition-colors">
                  Providers
                </Link>
              </li>
              <li>
                <Link to="/app/playground" className="hover:text-foreground transition-colors">
                  Playground
                </Link>
              </li>
              <li>
                <Link to="/app/executions" className="hover:text-foreground transition-colors">
                  Executions
                </Link>
              </li>
            </ul>
          </div>

          {/* Platform Links */}
          <div className="space-y-2.5">
            <div className="text-xs font-mono font-medium text-foreground uppercase tracking-wider">
              Platform
            </div>
            <ul className="space-y-2 text-xs text-muted-foreground">
              <li>
                <Link to="/app/quotas" className="hover:text-foreground transition-colors">
                  Quotas & Limits
                </Link>
              </li>
              <li>
                <Link to="/app/usage" className="hover:text-foreground transition-colors">
                  Usage Analytics
                </Link>
              </li>
              <li>
                <Link to="/app/api-keys" className="hover:text-foreground transition-colors">
                  API Keys
                </Link>
              </li>
              <li>
                <Link to="/app/settings" className="hover:text-foreground transition-colors">
                  Settings
                </Link>
              </li>
            </ul>
          </div>

          {/* Resources */}
          <div className="space-y-2.5">
            <div className="text-xs font-mono font-medium text-foreground uppercase tracking-wider">
              Resources
            </div>
            <ul className="space-y-2 text-xs text-muted-foreground">
              <li>
                <a
                  href="https://github.com"
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-foreground transition-colors"
                >
                  GitHub Repository
                </a>
              </li>
              <li>
                <a
                  href="#architecture"
                  className="hover:text-foreground transition-colors"
                >
                  Architecture Docs
                </a>
              </li>
              <li>
                <a
                  href="#developer"
                  className="hover:text-foreground transition-colors"
                >
                  REST API Reference
                </a>
              </li>
              <li>
                <Link to="/app" className="hover:text-foreground transition-colors">
                  Web Console
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="pt-8 border-t border-border/50 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono text-muted-foreground">
          <div>© {new Date().getFullYear()} ORQ Control Plane. All rights reserved.</div>
          <div className="flex items-center gap-6">
            <span className="text-[11px]">MIT Licensed Core</span>
            <span className="text-[11px]">PostgreSQL 16 + Redis 7</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
