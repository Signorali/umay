import { useAuth } from '../context/AuthContext'

/**
 * Returns permission-check helpers for the current user.
 *
 * Usage:
 *   const { can, isAdmin } = usePermissions()
 *   can('transactions', 'delete')  // true/false
 *   isAdmin                         // tenant_admin or superuser
 */
export function usePermissions() {
  const { user } = useAuth()

  const permissions: string[] = user?.permissions ?? []
  const isAdmin = !!(user?.is_superuser || user?.is_tenant_admin)
  const isWildcard = permissions.includes('*')

  function can(module: string, action: string): boolean {
    if (!user) return false
    if (isAdmin || isWildcard) return true
    return permissions.includes(`${module}:${action}`)
  }

  function canAny(checks: [string, string][]): boolean {
    return checks.some(([m, a]) => can(m, a))
  }

  return { can, canAny, isAdmin, permissions }
}
