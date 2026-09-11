import { Link } from "react-router-dom"
import {
  Terminal,
  Cpu,
  Plug,
  KeyRound,
  ScrollText,
  BarChart2,
  ShieldCheck,
  ArrowRight,
} from "lucide-react"

interface QuickAction {
  to: string
  label: string
  description: string
  icon: React.ReactNode
  eyebrow: string
}

const ACTIONS: QuickAction[] = [
  {
    to: "/app/playground",
    label: "Playground",
    description: "Test model completions interactively.",
    icon: <Terminal className="h-4 w-4" />,
    eyebrow: "Core",
  },
  {
    to: "/app/models",
    label: "Models",
    description: "Manage model registry and routing.",
    icon: <Cpu className="h-4 w-4" />,
    eyebrow: "Infrastructure",
  },
  {
    to: "/app/providers",
    label: "Providers",
    description: "Configure upstream LLM providers.",
    icon: <Plug className="h-4 w-4" />,
    eyebrow: "Infrastructure",
  },
  {
    to: "/app/api-keys",
    label: "API Keys",
    description: "Issue and revoke access credentials.",
    icon: <KeyRound className="h-4 w-4" />,
    eyebrow: "Infrastructure",
  },
  {
    to: "/app/executions",
    label: "Executions",
    description: "Inspect full gateway execution logs.",
    icon: <ScrollText className="h-4 w-4" />,
    eyebrow: "Observability",
  },
  {
    to: "/app/usage",
    label: "Usage Analytics",
    description: "Aggregated usage metrics by model.",
    icon: <BarChart2 className="h-4 w-4" />,
    eyebrow: "Observability",
  },
  {
    to: "/app/quotas",
    label: "Quotas & Limits",
    description: "Request and token consumption budgets.",
    icon: <ShieldCheck className="h-4 w-4" />,
    eyebrow: "Observability",
  },
]

export function OverviewQuickActions() {
  return (
    <div>
      <p className="text-[10px] font-mono text-muted-foreground/60 uppercase tracking-widest mb-3">
        Quick Navigation
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {ACTIONS.map((action) => (
          <Link
            key={action.to}
            to={action.to}
            className="group surface-card border border-border rounded-lg p-3.5 flex flex-col gap-2
              hover:border-primary/40 hover:bg-surface-2 transition-all duration-200"
          >
            {/* Top row: icon + eyebrow */}
            <div className="flex items-center justify-between">
              <span className="text-primary/80 group-hover:text-primary transition-colors">
                {action.icon}
              </span>
              <span className="text-[9px] font-mono text-muted-foreground/40 uppercase tracking-widest">
                {action.eyebrow}
              </span>
            </div>

            {/* Label */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-mono font-medium text-foreground group-hover:text-primary transition-colors">
                {action.label}
              </span>
              <ArrowRight className="h-3 w-3 text-muted-foreground/30 group-hover:text-primary/60 group-hover:translate-x-0.5 transition-all duration-200" />
            </div>

            {/* Description */}
            <p className="text-[11px] font-mono text-muted-foreground leading-snug">
              {action.description}
            </p>
          </Link>
        ))}
      </div>
    </div>
  )
}
