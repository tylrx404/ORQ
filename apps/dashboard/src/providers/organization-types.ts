import type { Organization } from "../types/api"

export interface OrganizationContextType {
  currentOrg: Organization | null
  organizations: Organization[]
  isLoading: boolean
  error: string | null
  selectOrganization: (orgId: string) => void
  reloadOrganizations: () => Promise<void>
}
