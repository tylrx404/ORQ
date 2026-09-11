import * as React from "react"
import type { Organization } from "../types/api"
import { OrganizationContext } from "./useOrganization"
import { api } from "../services/api"

const SELECTED_ORG_KEY = "orq_selected_org_id"

export function OrganizationProvider({ children }: { children: React.ReactNode }) {
  const [organizations, setOrganizations] = React.useState<Organization[]>([])
  const [currentOrg, setCurrentOrg] = React.useState<Organization | null>(null)
  const [isLoading, setIsLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  const loadOrgs = React.useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const orgs = await api.listOrganizations()
      setOrganizations(orgs)

      if (orgs.length > 0) {
        const savedId = localStorage.getItem(SELECTED_ORG_KEY)
        const matched = savedId ? orgs.find((o) => o.id === savedId) : null
        const active = matched || orgs[0]
        setCurrentOrg(active)
        localStorage.setItem(SELECTED_ORG_KEY, active.id)
      } else {
        setCurrentOrg(null)
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load organizations"
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }, [])

  React.useEffect(() => {
    loadOrgs()
  }, [loadOrgs])

  const selectOrganization = React.useCallback(
    (orgId: string) => {
      const org = organizations.find((o) => o.id === orgId)
      if (org) {
        setCurrentOrg(org)
        localStorage.setItem(SELECTED_ORG_KEY, org.id)
      }
    },
    [organizations]
  )

  const value = React.useMemo(
    () => ({
      currentOrg,
      organizations,
      isLoading,
      error,
      selectOrganization,
      reloadOrganizations: loadOrgs,
    }),
    [currentOrg, organizations, isLoading, error, selectOrganization, loadOrgs]
  )

  return (
    <OrganizationContext.Provider value={value}>
      {children}
    </OrganizationContext.Provider>
  )
}
