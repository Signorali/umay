import React, { ReactNode } from 'react'
import { usePermissions } from '../hooks/usePermissions'

interface CanDoProps {
  module: string
  action: string
  children: ReactNode
  fallback?: ReactNode
}

/**
 * Renders children only if the current user has the required permission.
 *
 * Usage:
 *   <CanDo module="transactions" action="delete">
 *     <button>Delete</button>
 *   </CanDo>
 */
export function CanDo({ module, action, children, fallback = null }: CanDoProps) {
  const { can } = usePermissions()
  return <>{can(module, action) ? children : fallback}</>
}
