import { createContext, useContext } from "react"
import type { OrganizationContextType } from "./organization-types"

export const OrganizationContext = createContext<OrganizationContextType>({
  currentOrg: null,
  organizations: [],
  isLoading: true,
  error: null,
  selectOrganization: () => {},
  reloadOrganizations: async () => {},
})

export function useOrganization() {
  const context = useContext(OrganizationContext)
  if (!context) {
    throw new Error("useOrganization must be used within an OrganizationProvider")
  }
  return context
}
