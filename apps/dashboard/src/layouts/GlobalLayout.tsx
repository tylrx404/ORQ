import * as React from "react"
import { Sidebar } from "../components/layout/Sidebar"
import { TopNav } from "../components/layout/TopNav"
import { Toaster } from "../components/ui/toast"

export function GlobalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen w-full overflow-hidden aurora-bg text-foreground">
      <Sidebar />
      <div className="flex flex-col flex-1 h-full relative">
        <TopNav />
        <main className="flex-1 overflow-y-auto p-8 relative z-0 custom-scrollbar">
          {children}
        </main>
      </div>
      <Toaster />
    </div>
  )
}
