import React, { lazy, useEffect, useRef, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import { AppShell } from './components/AppShell'
import { SetupWizard } from './pages/SetupWizard'
import { LoginPage } from './pages/LoginPage'
import { setupApi, marketApi } from './api/umay'

const MARKET_BG_REFRESH_MS = 60_000 // 1 dakikada bir fiyat güncelle

function useMarketBackgroundRefresh(enabled: boolean) {
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!enabled) return

    const run = async () => {
      if (document.hidden) return // sekme arka plandaysa atla
      try { await marketApi.refreshPrices() } catch { /* sessiz hata */ }
    }

    timerRef.current = setInterval(run, MARKET_BG_REFRESH_MS)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [enabled])
}

/** Set a readable (non-httpOnly) cookie so the login page can pass X-Tenant-Id */
function setTenantCookie(tenantId: string) {
  const maxAge = 365 * 24 * 60 * 60
  document.cookie = `umay_tenant_id=${encodeURIComponent(tenantId)}; max-age=${maxAge}; path=/; samesite=lax`
}

// Lazy-loaded pages
const DashboardPage     = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })))
const AccountsPage      = lazy(() => import('./pages/AccountsPage').then(m => ({ default: m.AccountsPage })))
const AccountDetailPage = lazy(() => import('./pages/AccountDetailPage').then(m => ({ default: m.AccountDetailPage })))
const TransactionsPage  = lazy(() => import('./pages/TransactionsPage').then(m => ({ default: m.TransactionsPage })))
const CategoriesPage    = lazy(() => import('./pages/CategoriesPage').then(m => ({ default: m.CategoriesPage })))
const PlannedPage       = lazy(() => import('./pages/PlannedPaymentsPage').then(m => ({ default: m.PlannedPaymentsPage })))
const LoansPage         = lazy(() => import('./pages/LoansPage').then(m => ({ default: m.LoansPage })))
const LoanDetailPage    = lazy(() => import('./pages/LoanDetailPage').then(m => ({ default: m.LoanDetailPage })))
const CreditCardsPage   = lazy(() => import('./pages/CreditCardsPage').then(m => ({ default: m.CreditCardsPage })))
const AssetsPage        = lazy(() => import('./pages/AssetsPage').then(m => ({ default: m.AssetsPage })))
const InvestmentsPage   = lazy(() => import('./pages/InvestmentsPage').then(m => ({ default: m.InvestmentsPage })))
const MarketPage        = lazy(() => import('./pages/MarketPage').then(m => ({ default: m.MarketPage })))
const InstitutionsPage  = lazy(() => import('./pages/InstitutionsPage').then(m => ({ default: m.InstitutionsPage })))
const ReportsPage       = lazy(() => import('./pages/ReportsPage').then(m => ({ default: m.ReportsPage })))
const CalendarPage      = lazy(() => import('./pages/CalendarPage').then(m => ({ default: m.CalendarPage })))
const DocumentsPage     = lazy(() => import('./pages/DocumentsPage').then(m => ({ default: m.DocumentsPage })))
const SettingsPage      = lazy(() => import('./pages/SettingsPage').then(m => ({ default: m.SettingsPage })))
const GroupsPage        = lazy(() => import('./pages/GroupsPage').then(m => ({ default: m.GroupsPage })))
const UsersPage         = lazy(() => import('./pages/UsersPage').then(m => ({ default: m.UsersPage })))
const RolesPage         = lazy(() => import('./pages/RolesPage').then(m => ({ default: m.RolesPage })))
const LedgerPage        = lazy(() => import('./pages/LedgerPage').then(m => ({ default: m.LedgerPage })))
const ImportPage        = lazy(() => import('./pages/ImportPage'))
const AuditPage         = lazy(() => import('./pages/AuditPage').then(m => ({ default: m.AuditPage })))
const PeriodLockPage    = lazy(() => import('./pages/PeriodLockPage').then(m => ({ default: m.PeriodLockPage })))
const BackupPage        = lazy(() => import('./pages/BackupPage').then(m => ({ default: m.BackupPage })))
const LicensePage       = lazy(() => import('./pages/LicensePage').then(m => ({ default: m.LicensePage })))
const MfaPage              = lazy(() => import('./pages/MfaPage').then(m => ({ default: m.MfaPage })))
const DeleteRequestsPage   = lazy(() => import('./pages/DeleteRequestsPage').then(m => ({ default: m.DeleteRequestsPage })))
const ChangePasswordPage   = lazy(() => import('./pages/ChangePasswordPage').then(m => ({ default: m.ChangePasswordPage })))

const PERMISSIONS_REFRESH_INTERVAL_MS = 5 * 60 * 1000 // 5 minutes

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, user, refreshUser } = useAuth()
  const location = useLocation()
  const lastRefreshRef = useRef<number>(0)

  useEffect(() => {
    if (!isAuthenticated) return
    const now = Date.now()
    if (now - lastRefreshRef.current > PERMISSIONS_REFRESH_INTERVAL_MS) {
      lastRefreshRef.current = now
      refreshUser()
    }
  }, [location.pathname])

  if (isLoading) return <div className="app-loading"><div className="spinner" /></div>
  if (!isAuthenticated) return <Navigate to="/login" replace />
  // Force password change if required
  if (user?.must_change_password && window.location.pathname !== '/change-password') {
    return <Navigate to="/change-password" replace />
  }
  return <AppShell>{children}</AppShell>
}

function AppRoutes() {
  const { isAuthenticated, isLoading, user } = useAuth()
  const [setupChecked, setSetupChecked] = useState(false)
  const [isInitialized, setIsInitialized] = useState<boolean | null>(null)

  useMarketBackgroundRefresh(isAuthenticated)

  useEffect(() => {
    setupApi.status()
      .then(res => {
        setIsInitialized(res.data.initialized)
        // Store tenant_id as a readable cookie (not sensitive, needed for X-Tenant-Id header)
        if (res.data.tenant_id) {
          setTenantCookie(res.data.tenant_id)
        }
        setSetupChecked(true)
      })
      .catch(() => { setIsInitialized(false); setSetupChecked(true) })
  }, [])

  if (!setupChecked || isLoading) {
    return (
      <div className="app-loading">
        <div className="sidebar-logo-mark" style={{ width: 48, height: 48, fontSize: 22, borderRadius: 12 }}>U</div>
        <div className="spinner" style={{ marginTop: 16 }} />
        <span style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)', marginTop: 8 }}>
          Checking system status...
        </span>
      </div>
    )
  }

  if (!isInitialized) {
    return <SetupWizard onComplete={() => setIsInitialized(true)} />
  }

  return (
    <Routes>
      <Route path="/login"             element={isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />} />

      <Route path="/"                   element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/accounts"           element={<ProtectedRoute><AccountsPage /></ProtectedRoute>} />
      <Route path="/accounts/:accountId" element={<ProtectedRoute><AccountDetailPage /></ProtectedRoute>} />
      <Route path="/transactions"       element={<ProtectedRoute><TransactionsPage /></ProtectedRoute>} />
      <Route path="/categories"         element={<ProtectedRoute><CategoriesPage /></ProtectedRoute>} />
      <Route path="/planned-payments"   element={<ProtectedRoute><PlannedPage /></ProtectedRoute>} />
      <Route path="/loans"              element={<ProtectedRoute><LoansPage /></ProtectedRoute>} />
      <Route path="/loans/:loanId"      element={<ProtectedRoute><LoanDetailPage /></ProtectedRoute>} />
      <Route path="/credit-cards"       element={<ProtectedRoute><CreditCardsPage /></ProtectedRoute>} />
      <Route path="/assets"             element={<ProtectedRoute><AssetsPage /></ProtectedRoute>} />
      <Route path="/investments"        element={<ProtectedRoute><InvestmentsPage /></ProtectedRoute>} />
      <Route path="/market"             element={<ProtectedRoute><MarketPage /></ProtectedRoute>} />
      <Route path="/institutions"       element={<ProtectedRoute><InstitutionsPage /></ProtectedRoute>} />
      <Route path="/reports"            element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
      <Route path="/calendar"           element={<ProtectedRoute><CalendarPage /></ProtectedRoute>} />
      <Route path="/documents"          element={<ProtectedRoute><DocumentsPage /></ProtectedRoute>} />
      <Route path="/settings"           element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />

      {/* Admin pages */}
      <Route path="/admin/users"        element={<ProtectedRoute><UsersPage /></ProtectedRoute>} />
      <Route path="/admin/groups"       element={<ProtectedRoute><GroupsPage /></ProtectedRoute>} />
      <Route path="/admin/roles"        element={<ProtectedRoute><RolesPage /></ProtectedRoute>} />
      <Route path="/admin/ledger"       element={<ProtectedRoute><LedgerPage /></ProtectedRoute>} />
      <Route path="/admin/audit"        element={<ProtectedRoute><AuditPage /></ProtectedRoute>} />
      <Route path="/admin/period-lock"  element={<ProtectedRoute><PeriodLockPage /></ProtectedRoute>} />
      <Route path="/admin/backup"       element={<ProtectedRoute><BackupPage /></ProtectedRoute>} />
      <Route path="/admin/license"          element={<Navigate to="/settings?tab=license" replace />} />
      <Route path="/admin/delete-requests" element={<ProtectedRoute><DeleteRequestsPage /></ProtectedRoute>} />
      <Route path="/import"                element={<ProtectedRoute><ImportPage /></ProtectedRoute>} />
      <Route path="/security/mfa"          element={<ProtectedRoute><MfaPage /></ProtectedRoute>} />
      <Route path="/change-password"       element={isAuthenticated ? <ChangePasswordPage /> : <Navigate to="/login" replace />} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ThemeWrapper />
      </AuthProvider>
    </BrowserRouter>
  )
}

/**
 * Reads ui_theme from the authenticated user (DB) and passes it to ThemeProvider.
 * Falls back to 'dark' until user loads. Once user is loaded the theme is set
 * from DB — no localStorage needed.
 */
function ThemeWrapper() {
  const { user, isLoading } = useAuth()
  // While loading, use 'dark' as default to avoid flash
  const initialTheme = (!isLoading && user?.ui_theme) ? user.ui_theme : 'dark'
  return (
    <ThemeProvider initialTheme={initialTheme}>
      <AppRoutes />
    </ThemeProvider>
  )
}
