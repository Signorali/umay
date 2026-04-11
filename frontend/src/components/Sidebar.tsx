import React from 'react'
import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { usePermissions } from '../hooks/usePermissions'

// SVG icon components — 16×16, stroke-based
const Icon = ({ d, d2 }: { d: string; d2?: string }) => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
    <path d={d} />
    {d2 && <path d={d2} />}
  </svg>
)

const Icons: Record<string, React.ReactNode> = {
  dashboard: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>,
  calendar: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>,
  accounts: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>,
  transactions: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M7 16V4m0 0L3 8m4-4 4 4"/><path d="M17 8v12m0 0 4-4m-4 4-4-4"/></svg>,
  categories: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M3 7h7v7H3zM14 7h7v7h-7zM3 17h7v4H3zM14 17h7v4h-7z"/><path d="M3 3h7v3H3zM14 3h7v3h-7z"/></svg>,
  plannedPayments: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M17 1v4M7 1v4M3 8h18M3 5h18a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z"/><path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01M16 18h.01"/></svg>,
  loans: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/><path d="M6 15h2m4 0h6"/></svg>,
  creditCards: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/><circle cx="7" cy="15" r="1" fill="currentColor"/><path d="M11 15h6"/></svg>,
  assets: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M3 22V12l9-9 9 9v10"/><path d="M9 22V16h6v6"/></svg>,
  investments: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>,
  market: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/><line x1="2" y1="20" x2="22" y2="20"/></svg>,
  institutions: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5"/></svg>,
  reports: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>,
  documents: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>,
  import: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>,
  ledger: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>,
  periodLock: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>,
  backup: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a9 9 0 0 0-9 9c0 4.17 2.84 7.67 6.69 8.69L12 22l2.31-2.31C18.16 18.67 21 15.17 21 11a9 9 0 0 0-9-9z"/><path d="M12 7v4l3 3"/></svg>,
  settings: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/></svg>,
}

interface NavItem {
  to: string
  iconKey: string
  labelKey: string
  exact?: boolean
  permission?: [string, string]
  adminOnly?: boolean
}

interface NavGroup {
  labelKey: string
  items: NavItem[]
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
        { to: '/', iconKey: 'dashboard', labelKey: 'nav.dashboard', exact: true },
        { to: '/calendar', iconKey: 'calendar', labelKey: 'nav.calendar', permission: ['calendar', 'view'] },
      ],
    },
    {
      labelKey: 'Finance',
      items: [
        { to: '/accounts',        iconKey: 'accounts',        labelKey: 'nav.accounts',        permission: ['accounts', 'view'] },
        { to: '/transactions',    iconKey: 'transactions',    labelKey: 'nav.transactions',    permission: ['transactions', 'view'] },
        { to: '/categories',      iconKey: 'categories',      labelKey: 'nav.categories',      permission: ['categories', 'view'] },
        { to: '/planned-payments', iconKey: 'plannedPayments', labelKey: 'nav.plannedPayments', permission: ['planned_payments', 'view'] },
      ],
    },
    {
      labelKey: 'Credit & Loans',
      items: [
        { to: '/loans',        iconKey: 'loans',       labelKey: 'nav.loans',       permission: ['loans', 'view'] },
        { to: '/credit-cards', iconKey: 'creditCards', labelKey: 'nav.creditCards', permission: ['credit_cards', 'view'] },
      ],
    },
    {
      labelKey: 'Investments',
      items: [
        { to: '/assets',       iconKey: 'assets',       labelKey: 'nav.assets',       permission: ['assets', 'view'] },
        { to: '/investments',  iconKey: 'investments',  labelKey: 'nav.investments',  permission: ['investments', 'view'] },
        { to: '/market',       iconKey: 'market',       labelKey: 'nav.market',       permission: ['market', 'view'] },
        { to: '/institutions', iconKey: 'institutions', labelKey: 'nav.institutions', permission: ['institutions', 'view'] },
      ],
    },
    {
      labelKey: 'Reports',
      items: [
        { to: '/reports',   iconKey: 'reports',   labelKey: 'nav.reports',   permission: ['reports', 'view'] },
        { to: '/documents', iconKey: 'documents', labelKey: 'nav.documents', permission: ['documents', 'view'] },
        { to: '/import',    iconKey: 'import',    labelKey: 'nav.import',    permission: ['import', 'create'] },
      ],
    },
    {
      labelKey: 'Admin',
      adminOnly: true,
      items: [
        { to: '/admin/ledger',       iconKey: 'ledger',      labelKey: 'nav.ledger',      adminOnly: true },
        { to: '/admin/period-lock',  iconKey: 'periodLock',  labelKey: 'nav.periodLock',  adminOnly: true },
        { to: '/admin/backup',       iconKey: 'backup',      labelKey: 'nav.backup',      adminOnly: true },
      ],
    },
    {
      labelKey: 'System',
      items: [
        { to: '/settings', iconKey: 'settings', labelKey: 'nav.settings', adminOnly: true },
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
                <span style={{ display: 'flex', alignItems: 'center', opacity: 0.75 }}>
                  {Icons[item.iconKey]}
                </span>
                <span>{t(item.labelKey)}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
    </aside>
  )
}
