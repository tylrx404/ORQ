import * as React from "react"
import { Building2, ChevronDown, Check } from "lucide-react"
import { useOrganization } from "../../providers/useOrganization"
import { motion, AnimatePresence } from "framer-motion"

export function OrgSelector() {
  const { currentOrg, organizations, selectOrganization, isLoading } = useOrganization()
  const [isOpen, setIsOpen] = React.useState(false)

  if (isLoading) {
    return (
      <div className="h-8 w-28 rounded bg-surface-2 animate-pulse" />
    )
  }

  if (!currentOrg && organizations.length === 0) {
    return null
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-surface-base border border-border hover:border-border-strong hover:bg-surface-2 transition-colors cursor-pointer text-xs font-mono select-none"
        aria-label="Select organization"
        aria-expanded={isOpen}
      >
        <Building2 className="h-3.5 w-3.5 text-primary shrink-0" />
        <span className="text-foreground font-medium truncate max-w-[130px]">
          {currentOrg?.name || "Select Org"}
        </span>
        <ChevronDown className="h-3 w-3 text-muted-foreground shrink-0 ml-0.5" />
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            <div
              className="fixed inset-0 z-40"
              onClick={() => setIsOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, y: 4, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 4, scale: 0.98 }}
              transition={{ duration: 0.1, ease: "easeOut" }}
              className="absolute left-0 top-full mt-1.5 w-56 rounded-md surface-elevated border border-border shadow-xl z-50 py-1"
            >
              <div className="px-3 py-1.5 border-b border-border/60 text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
                Organizations
              </div>
              <div className="max-h-56 overflow-y-auto custom-scrollbar py-1">
                {organizations.map((org) => {
                  const isSelected = org.id === currentOrg?.id
                  return (
                    <button
                      key={org.id}
                      onClick={() => {
                        selectOrganization(org.id)
                        setIsOpen(false)
                      }}
                      className="w-full flex items-center justify-between px-3 py-1.5 text-xs text-left hover:bg-surface-2 transition-colors cursor-pointer"
                    >
                      <div className="flex flex-col truncate pr-2">
                        <span className="text-foreground font-medium truncate">
                          {org.name}
                        </span>
                        <span className="text-[10px] font-mono text-muted-foreground truncate">
                          {org.slug}
                        </span>
                      </div>
                      {isSelected && (
                        <Check className="h-3.5 w-3.5 text-primary shrink-0" />
                      )}
                    </button>
                  )
                })}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
