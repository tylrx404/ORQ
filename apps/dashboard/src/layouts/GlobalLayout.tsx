import * as React from "react"
import { Sidebar } from "../components/layout/Sidebar"
import { TopNav } from "../components/layout/TopNav"
import { Toaster } from "../components/ui/toast"
import { ErrorBoundary } from "../components/ui/ErrorBoundary"

export function GlobalLayout({ children }: { children: React.ReactNode }) {
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false)

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-foreground font-sans">
      {/* Sidebar: Desktop fixed/docked + Mobile drawer */}
      <Sidebar
        isOpen={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
      />

      {/* Main Viewport Container */}
      <div className="flex flex-col flex-1 h-full min-w-0 relative overflow-hidden">
        <TopNav onOpenMobileMenu={() => setMobileMenuOpen(true)} />

        <main className="flex-1 overflow-y-auto custom-scrollbar relative z-0">
          <ErrorBoundary>{children}</ErrorBoundary>
        </main>
      </div>

      {/* Global Toast System */}
      <Toaster />
    </div>
  )
}
