import React from 'react'
import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { usePermissions } from '../hooks/usePermissions'

interface NavItem {
  to: string
  icon: string
  labelKey: string
  exact?: boolean
  // If set, item is only shown when user has this permission
  permission?: [string, string]
  // If set, item is only shown to admins (tenant_admin or superuser)
  adminOnly?: boolean
}

interface NavGroup {
  labelKey: string
  items: NavItem[]
  // If set, the entire group requires at least one permission or admin
  requireAny?: [string, string][]
  adminOnly?: boolean
}

export function Sidebar() {
  const { t } = useTranslation()
  const { can, isAdmin } = usePermissions()

  const NAV_GROUPS: NavGroup[] = [
    {
      labelKey: 'Overview',
      items: [
        { to: '/', icon: '⊞', labelKey: 'nav.dashboard', exact: true },
        { to: '/calendar', icon: '📅', labelKey: 'nav.calendar', permission: ['calendar', 'view'] },
      ],
    },
    {
      labelKey: 'Finance',
      items: [
        { to: '/accounts', icon: '🏦', labelKey: 'nav.accounts', permission: ['accounts', 'view'] },
        { to: '/transactions', icon: '↕️', labelKey: 'nav.transactions', permission: ['transactions', 'view'] },
        { to: '/categories', icon: '🏷️', labelKey: 'nav.categories', permission: ['categories', 'view'] },
        { to: '/planned-payments', icon: '🔁', labelKey: 'nav.plannedPayments', permission: ['planned_payments', 'view'] },
      ],
    },
    {
      labelKey: 'Credit & Loans',
      items: [
        { to: '/loans', icon: '💳', labelKey: 'nav.loans', permission: ['loans', 'view'] },
        { to: '/credit-cards', icon: '💎', labelKey: 'nav.creditCards', permission: ['credit_cards', 'view'] },
      ],
    },
    {
      labelKey: 'Investments',
      items: [
        { to: '/assets', icon: '🏠', labelKey: 'nav.assets', permission: ['assets', 'view'] },
        { to: '/investments', icon: '📈', labelKey: 'nav.investments', permission: ['investments', 'view'] },
        { to: '/market', icon: '📊', labelKey: 'nav.market', permission: ['market', 'view'] },
        { to: '/institutions', icon: '🏛️', labelKey: 'nav.institutions', permission: ['institutions', 'view'] },
      ],
    },
    {
      labelKey: 'Reports',
      items: [
        { to: '/reports', icon: '📋', labelKey: 'nav.reports', permission: ['reports', 'view'] },
        { to: '/documents', icon: '📁', labelKey: 'nav.documents', permission: ['documents', 'view'] },
        { to: '/import', icon: '📥', labelKey: 'nav.import', permission: ['import', 'create'] },
      ],
    },
    {
      labelKey: 'Admin',
      adminOnly: true,
      items: [
        { to: '/admin/ledger', icon: '📒', labelKey: 'nav.ledger', adminOnly: true },
        { to: '/admin/period-lock', icon: '📅', labelKey: 'nav.periodLock', adminOnly: true },
        { to: '/admin/backup', icon: '💾', labelKey: 'nav.backup', adminOnly: true },
      ],
    },
    {
      labelKey: 'System',
      items: [
        { to: '/settings', icon: '⚙️', labelKey: 'nav.settings', adminOnly: true },
      ],
    },
  ]

  const isItemVisible = (item: NavItem): boolean => {
    if (item.adminOnly && !isAdmin) return false
    if (item.permission && !can(item.permission[0], item.permission[1])) return false
    return true
  }

  const isGroupVisible = (group: NavGroup): boolean => {
    if (group.adminOnly && !isAdmin) return false
    const visibleItems = group.items.filter(isItemVisible)
    return visibleItems.length > 0
  }

  return (
    <aside className="app-sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-mark">U</div>
        <div>
          <div className="sidebar-logo-text">Umay</div>
          <div className="sidebar-logo-version">Finance Platform</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="sidebar-nav">
        {NAV_GROUPS.filter(isGroupVisible).map(group => (
          <div key={group.labelKey} className="sidebar-group">
            <div className="sidebar-group-label">{group.labelKey}</div>
            {group.items.filter(isItemVisible).map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.exact}
                className={({ isActive }) =>
                  `nav-item${isActive ? ' active' : ''}`
                }
              >
                <span style={{ fontSize: 16, lineHeight: 1 }}>{item.icon}</span>
                <span>{t(item.labelKey)}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
    </aside>
  )
}
