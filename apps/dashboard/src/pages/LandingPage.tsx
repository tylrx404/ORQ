import * as React from "react"
import { LandingNav } from "../components/landing/LandingNav"
import { HeroSection } from "../components/landing/HeroSection"
import { ConceptSection } from "../components/landing/ConceptSection"
import { CapabilitiesSection } from "../components/landing/CapabilitiesSection"
import { DashboardPreviewSection } from "../components/landing/DashboardPreviewSection"
import { DeveloperSection } from "../components/landing/DeveloperSection"
import { CtaSection } from "../components/landing/CtaSection"
import { FooterSection } from "../components/landing/FooterSection"
import { Dialog } from "../components/ui/Dialog"
import { Badge } from "../components/ui/Badge"
import { Button } from "../components/ui/Button"
import { Terminal, FileCode2, ExternalLink } from "lucide-react"

export function LandingPage() {
  const [docsModalOpen, setDocsModalOpen] = React.useState(false)

  return (
    <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary/20 selection:text-primary">
      {/* 1. Header Navigation */}
      <LandingNav onOpenDocs={() => setDocsModalOpen(true)} />

      {/* Main Sections */}
      <main>
        {/* 2. Hero Section with 3D Abstract Control Plane */}
        <HeroSection />

        {/* 3. Architectural Concept */}
        <ConceptSection />

        {/* 4. Core Capabilities Grid */}
        <CapabilitiesSection />

        {/* 5. Product/Dashboard Console Preview */}
        <DashboardPreviewSection />

        {/* 6. Developer/API Experience */}
        <DeveloperSection />

        {/* 7. Conversion CTA */}
        <CtaSection />
      </main>

      {/* 8. Minimal Editorial Footer */}
      <FooterSection />

      {/* Honest Documentation Dialog (clearly indicates upcoming docs phase) */}
      <Dialog
        isOpen={docsModalOpen}
        onClose={() => setDocsModalOpen(false)}
        title="ORQ Documentation & Specs"
        description="Comprehensive technical documentation is being assembled alongside the control plane implementation."
        maxWidth="md"
      >
        <div className="space-y-4 pt-1">
          <div className="p-3.5 rounded-lg bg-surface-1 border border-border/80 space-y-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-foreground font-medium flex items-center gap-1.5">
                <Terminal className="h-3.5 w-3.5 text-primary" />
                REST API OpenAPI Spec
              </span>
              <Badge variant="primary" size="sm">
                FastAPI v1
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              When the local backend service is running, explore the live interactive Swagger UI and OpenAPI documentation schema:
            </p>
            <div className="p-2.5 rounded bg-surface-base border border-border/60 text-xs font-mono text-foreground flex items-center justify-between">
              <span>http://localhost:8000/docs</span>
              <Badge variant="neutral" size="sm">Local Docs</Badge>
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-surface-1 border border-border/80 space-y-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-foreground font-medium flex items-center gap-1.5">
                <FileCode2 className="h-3.5 w-3.5 text-primary" />
                Integration Guide
              </span>
              <Badge variant="neutral" size="sm">
                In Progress
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Detailed multi-provider failover strategies, Redis token-bucket tuning parameters, and SDK migration patterns will be published in the next release cycle.
            </p>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDocsModalOpen(false)}
            >
              Close
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                window.open("https://github.com", "_blank")
                setDocsModalOpen(false)
              }}
              rightIcon={<ExternalLink className="h-3.5 w-3.5" />}
            >
              GitHub Repository
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  )
}
