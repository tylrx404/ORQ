import * as React from "react"
import { Link } from "react-router-dom"
import { Layers, Menu, X, ArrowUpRight } from "lucide-react"
import { Button } from "../ui/Button"

interface LandingNavProps {
  onOpenDocs?: () => void
}

export function LandingNav({ onOpenDocs }: LandingNavProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false)

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/80 bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-primary/10 border border-primary/30 text-primary group-hover:border-primary/60 transition-colors">
            <Layers className="h-4 w-4" />
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold tracking-tight text-base text-foreground">
              ORQ
            </span>
            <span className="hidden sm:inline-block text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-2 border border-border text-muted-foreground uppercase">
              Control Plane
            </span>
          </div>
        </Link>

        {/* Desktop Nav Links */}
        <nav className="hidden md:flex items-center gap-8 text-xs font-medium tracking-wide">
          <a
            href="#product"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            Product
          </a>
          <a
            href="#platform"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            Platform
          </a>
          <a
            href="#architecture"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            Architecture
          </a>
          <a
            href="#developer"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            Developers
          </a>
          <a
            href="#docs"
            onClick={(e) => {
              if (onOpenDocs) {
                e.preventDefault()
                onOpenDocs()
              }
            }}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            Docs
          </a>
        </nav>

        {/* Desktop Actions */}
        <div className="hidden md:flex items-center gap-3">
          <Link to="/app">
            <Button variant="ghost" size="sm" className="font-mono text-xs text-muted-foreground hover:text-foreground">
              Sign in
            </Button>
          </Link>
          <Link to="/app">
            <Button variant="primary" size="sm" rightIcon={<ArrowUpRight className="h-3.5 w-3.5" />}>
              Get started
            </Button>
          </Link>
        </div>

        {/* Mobile menu toggle */}
        <div className="flex md:hidden items-center gap-2">
          <Link to="/app">
            <Button variant="primary" size="xs">
              Console
            </Button>
          </Link>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-surface-2"
            aria-label="Toggle navigation"
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="border-b border-border bg-surface-1 px-4 py-6 md:hidden space-y-4">
          <nav className="flex flex-col space-y-3 text-sm font-medium">
            <a
              href="#product"
              onClick={() => setMobileMenuOpen(false)}
              className="text-muted-foreground hover:text-foreground transition-colors py-1"
            >
              Product
            </a>
            <a
              href="#platform"
              onClick={() => setMobileMenuOpen(false)}
              className="text-muted-foreground hover:text-foreground transition-colors py-1"
            >
              Platform
            </a>
            <a
              href="#architecture"
              onClick={() => setMobileMenuOpen(false)}
              className="text-muted-foreground hover:text-foreground transition-colors py-1"
            >
              Architecture
            </a>
            <a
              href="#developer"
              onClick={() => setMobileMenuOpen(false)}
              className="text-muted-foreground hover:text-foreground transition-colors py-1"
            >
              Developers
            </a>
            <a
              href="#docs"
              onClick={(e) => {
                setMobileMenuOpen(false)
                if (onOpenDocs) {
                  e.preventDefault()
                  onOpenDocs()
                }
              }}
              className="text-muted-foreground hover:text-foreground transition-colors py-1"
            >
              Docs
            </a>
          </nav>
          <div className="pt-4 border-t border-border flex flex-col gap-2">
            <Link to="/app" onClick={() => setMobileMenuOpen(false)}>
              <Button variant="secondary" size="md" className="w-full justify-center">
                Sign in
              </Button>
            </Link>
            <Link to="/app" onClick={() => setMobileMenuOpen(false)}>
              <Button variant="primary" size="md" className="w-full justify-center">
                Get started
              </Button>
            </Link>
          </div>
        </div>
      )}
    </header>
  )
}
