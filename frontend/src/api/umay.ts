import axios from 'axios'

const _base = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : '/api/v1'

// Helper: read a cookie value by name (for non-httpOnly cookies)
function getCookie(name: string): string {
  return document.cookie.split('; ').reduce((acc, part) => {
    const [k, v] = part.split('=')
    return k === name ? decodeURIComponent(v || '') : acc
  }, '')
}

const api = axios.create({ baseURL: _base, withCredentials: true })

// Attach tenant header on every request (tenant_id from cookie, token via httpOnly cookie)
api.interceptors.request.use(cfg => {
  const tenantId = getCookie('umay_tenant_id')
  if (tenantId) cfg.headers['x-tenant-id'] = tenantId
  return cfg
})

// 401 → logout (only redirect if not already on login/setup page)
api.interceptors.response.use(
  r => r,
  err => {
    if (err.response?.status === 401) {
      const path = window.location.pathname
      if (path !== '/login' && path !== '/setup') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

/** Normalize paginated list responses: { items, total } → items array */
const list = (url: string, params?: object) =>
  api.get(url, { params }).then(r => ({
    ...r,
    data: Array.isArray(r.data) ? r.data : (r.data?.items ?? r.data ?? []),
  }))

/* ── Auth ───────────────────────────────────────────────── */
export const setupApi = {
  status: () => api.get('/setup/status'),
  precheck: () => api.get('/setup/precheck'),
  init: (data: object) => api.post('/setup/init', data),
}

export const authApi = {
  login: (email: string, password: string, tenantId?: string) =>
    api.post('/auth/login', { email, password }, {
      headers: tenantId ? { 'X-Tenant-Id': tenantId } : {},
    }),
  logout: () => api.post('/auth/logout').catch(() => {}),
  updatePreferences: (data: { ui_theme?: string; locale?: string }) =>
    api.patch('/users/me/preferences', data),
  me: () => api.get('/auth/me'),
  refresh: () => api.post('/auth/refresh'),

  // MFA / TOTP — cloud.md §14
  mfa: {
    status:  () => api.get('/auth/mfa/status'),
    setup:   () => api.post('/auth/mfa/setup', {}),
    confirm: (totp_code: string) => api.post('/auth/mfa/confirm', { totp_code }),
    verify:  (totp_code: string) => api.post('/auth/mfa/verify', { totp_code }),
    disable: (totp_code: string) => api.post('/auth/mfa/disable', { totp_code }),
    regenBackupCodes: (totp_code: string) => api.post('/auth/mfa/backup-codes', { totp_code }),
  },

  // Internal helpers for MFA page (passes through the axios instance)
  _get: (path: string) => api.get(path),
  _post: (path: string, data: object) => api.post(path, data),
}

/* ── Finance ────────────────────────────────────────────── */
export const accountsApi = {
  list: (params?: object) => list('/accounts', params),
  create: (data: object) => api.post('/accounts', data),
  update: (id: string, data: object) => api.patch(`/accounts/${id}`, data),
  delete: (id: string) => api.delete(`/accounts/${id}`),
  get: (id: string) => api.get(`/accounts/${id}`),
  transactions: (id: string, params?: object) => api.get(`/accounts/${id}/transactions`, { params }),
  profit: (id: string) => api.get(`/accounts/${id}/profit`),
}

export const categoriesApi = {
  list: (params?: object) => list('/categories', params),
  create: (data: object) => api.post('/categories', data),
  update: (id: string, data: object) => api.patch(`/categories/${id}`, data),
  delete: (id: string) => api.delete(`/categories/${id}`),
}

export const transactionsApi = {
  list: (params?: object) => list('/transactions', params),
  create: (data: object) => api.post('/transactions', data),
  update: (id: string, data: object) => api.patch(`/transactions/${id}`, data),
  delete: (id: string) => api.delete(`/transactions/${id}`),
  confirm: (id: string) => api.post(`/transactions/${id}/confirm`),
}

export const transactionTemplatesApi = {
  list: () => api.get('/transaction-templates'),
  create: (data: object) => api.post('/transaction-templates', data),
  delete: (id: string) => api.delete(`/transaction-templates/${id}`),
}

export const ccPurchaseTemplatesApi = {
  list: () => api.get('/cc-purchase-templates'),
  create: (data: object) => api.post('/cc-purchase-templates', data),
  delete: (id: string) => api.delete(`/cc-purchase-templates/${id}`),
}

export const dashboardApi = {
  get: (params?: object) => api.get('/dashboard', { params }),
}

export const reportsApi = {
  incomeExpense: (params: object) => api.get('/reports/income-expense', { params }),
  categoryBreakdown: (params: object) => api.get('/reports/category-breakdown', { params }),
  cashFlow: (params?: object) => api.get('/reports/cash-flow', { params }),
  loans: (params?: object) => api.get('/reports/loans', { params }),
  creditCards: (params?: object) => api.get('/reports/credit-cards', { params }),
  assets: (params?: object) => api.get('/reports/assets', { params }),
  investmentPerformance: (params?: object) => api.get('/reports/investment-performance', { params }),
}

/* ── Assets & Investments ───────────────────────────────── */
export const assetsApi = {
  list: (params?: object) => list('/assets', params),
  create: (data: object) => api.post('/assets', data),
  get: (id: string) => api.get(`/assets/${id}`),
  update: (id: string, data: object) => api.patch(`/assets/${id}`, data),
  delete: (id: string) => api.delete(`/assets/${id}`),
  summary: () => api.get('/assets/summary'),
  addValuation: (id: string, data: object) => api.post(`/assets/${id}/valuations`, data),
  getValuations: (id: string) => api.get(`/assets/${id}/valuations`),
  dispose: (id: string, data: object) => api.post(`/assets/${id}/dispose`, data),
}

export const tenantApi = {
  me: () => api.get('/tenants/me'),
}

export const investmentsApi = {
  listPortfolios: (params?: object) => list('/investments/portfolios', params),
  createPortfolio: (data: object) => api.post('/investments/portfolios', data),
  getPortfolio: (id: string) => api.get(`/investments/portfolios/${id}`),
  getPositions: (id: string) => api.get(`/investments/portfolios/${id}/positions`),
  listAllPositions: () => list('/investments/positions'),
  listTransactions: (id: string, params?: object) =>
    list(`/investments/portfolios/${id}/transactions`, params),
  recordTransaction: (id: string, data: object) =>
    api.post(`/investments/portfolios/${id}/transactions`, data),
  updateTransaction: (portfolioId: string, txId: string, data: object) =>
    api.patch(`/investments/portfolios/${portfolioId}/transactions/${txId}`, data),
  deleteTransaction: (portfolioId: string, txId: string) =>
    api.delete(`/investments/portfolios/${portfolioId}/transactions/${txId}`),
  listMarketPrices: () => list('/investments/market'),
  addMarketSymbol: (data: object) => api.post('/investments/market', data),
  removeMarketSymbol: (symbol: string) => api.delete(`/investments/market/${symbol}`),
  refreshMarketPrices: () => api.post('/investments/market/refresh'),
}

export const marketApi = {
  watchlist: () => api.get('/market/watchlist'),
  addToWatchlist: (data: object) => api.post('/market/watchlist', data),
  removeFromWatchlist: (id: string) => api.delete(`/market/watchlist/${id}`),
  refreshPrices: () => api.post('/market/watchlist/refresh'),
  updatePins: (pinnedIds: string[], orderedIds: string[]) =>
    api.put('/market/watchlist/pins', { pinned_ids: pinnedIds, ordered_ids: orderedIds }),
  searchFunds: (q: string, fundType: string = 'YAT') =>
    api.get('/market/tefas/search', { params: { q, fund_type: fundType } }),
  getCurrentPrices: (symbols: string[]) =>
    api.get('/market/prices/current', { params: { symbols: symbols.join(',') } }),
}

/* ── Planned Payments ───────────────────────────────────────── */
export const plannedPaymentsApi = {
  list: (params?: object) => list('/planned-payments', params),
  create: (data: object) => api.post('/planned-payments', data),
  update: (id: string, data: object) => api.patch(`/planned-payments/${id}`, data),
  delete: (id: string) => api.delete(`/planned-payments/${id}`),
  execute: (id: string, data: { account_id: string; transaction_date?: string }) =>
    api.post(`/planned-payments/${id}/execute`, data),
}

/* ── Institutions ───────────────────────────────────────────── */
export const institutionsApi = {
  list: (params?: object) => list('/institutions', params),
  create: (data: object) => api.post('/institutions', data),
  update: (id: string, data: object) => api.patch(`/institutions/${id}`, data),
  delete: (id: string) => api.delete(`/institutions/${id}`),
}

/* ── Credit & Loans ─────────────────────────────────────── */
export const loansApi = {
  list: (params?: object) => list('/loans', params),
  create: (data: object) => api.post('/loans', data),
  get: (id: string) => api.get(`/loans/${id}`),
  installments: (id: string) => api.get(`/loans/${id}/installments`),
  payInstallment: (id: string, instId: string, data: object) => api.post(`/loans/${id}/installments/${instId}/pay`, data),
  earlyClose: (id: string, data: object) => api.post(`/loans/${id}/early-close`, data),
  delete: (id: string) => api.delete(`/loans/${id}`),
}

export const creditCardsApi = {
  list: (params?: object) => list('/credit-cards', params),
  create: (data: object) => api.post('/credit-cards', data),
  get: (id: string) => api.get(`/credit-cards/${id}`),
  update: (id: string, data: object) => api.patch(`/credit-cards/${id}`, data),
  limits: (id: string, atDate?: string) => api.get(`/credit-cards/${id}/limits`, { params: { at_date: atDate } }),
  // Purchases
  createPurchase: (id: string, data: object) => api.post(`/credit-cards/${id}/purchases`, data),
  listPurchases: (id: string, params?: object) => list(`/credit-cards/${id}/purchases`, params),
  cancelPurchase: (id: string, purchaseId: string, data: object) =>
    api.post(`/credit-cards/${id}/purchases/${purchaseId}/cancel`, data),
  // Statements
  listStatements: (id: string, params?: object) => list(`/credit-cards/${id}/statements`, params),
  getStatement: (id: string, stmtId: string) => api.get(`/credit-cards/${id}/statements/${stmtId}`),
  previewStatement: (id: string, data: object) => api.post(`/credit-cards/${id}/statements/preview`, data),
  generateStatement: (id: string, data: object) => api.post(`/credit-cards/${id}/statements/generate`, data),
  detailStatement: (id: string, stmtId: string, data: object) =>
    api.post(`/credit-cards/${id}/statements/${stmtId}/detail`, data),
  finalizeStatement: (id: string, stmtId: string) =>
    api.post(`/credit-cards/${id}/statements/${stmtId}/finalize`),
  payStatement: (id: string, stmtId: string, data: object) =>
    api.post(`/credit-cards/${id}/statements/${stmtId}/pay`, data),
  deleteStatement: (id: string, stmtId: string) =>
    api.delete(`/credit-cards/${id}/statements/${stmtId}`),
  // Sensitive data
  saveSensitive: (id: string, data: { password: string; card_number?: string; cvv?: string }) =>
    api.post(`/credit-cards/${id}/sensitive/save`, data),
  revealSensitive: (id: string, data: { password: string }) =>
    api.post(`/credit-cards/${id}/sensitive/reveal`, data),
}

/* ── Calendar & Documents ───────────────────────────────── */
export const calendarApi = {
  items: (params?: object) => list('/calendar', params),
  sync: (months?: number) => api.post('/calendar/sync', null, { params: { months_ahead: months || 3 } }),
  dismiss: (id: string) => api.post(`/calendar/items/${id}/dismiss`),
  complete: (id: string) => api.post(`/calendar/items/${id}/complete`),
  exportIcs: (months?: number) => api.get('/calendar/export/ics', { params: { months_ahead: months || 3 }, responseType: 'blob' }),
  integrations: () => api.get('/calendar/integrations'),
  getCredentials: () => api.get('/calendar/integrations/credentials'),
  saveCredentials: (data: object) => api.put('/calendar/integrations/credentials', data),
  connectGoogle: () => api.get('/calendar/integrations/google/connect').then(r => { window.location.href = r.data.auth_url }),
  connectMicrosoft: () => api.get('/calendar/integrations/microsoft/connect').then(r => { window.location.href = r.data.auth_url }),
  disconnect: (provider: string) => api.delete(`/calendar/integrations/${provider}`),
  syncExternal: () => api.post('/calendar/integrations/sync'),
}

export const documentsApi = {
  list: (params?: object) => list('/documents', params),
  upload: (formData: FormData) =>
    api.post('/documents', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  delete: (id: string) => api.delete(`/documents/${id}`),
}

/* ── Export / System ────────────────────────────────────── */
export const exportApi = {
  transactionsCsv: (params?: object) =>
    api.get('/export/transactions.csv', { params, responseType: 'blob' }),
  accountsCsv: () => api.get('/export/accounts.csv', { responseType: 'blob' }),
  fullJson: () => api.get('/export/data.json', { responseType: 'blob' }),
  diagnostics: () => api.get('/export/diagnostics.zip', { responseType: 'blob' }),
}

export const demoApi = {
  status: () => api.get('/demo/status'),
  activate: () => api.post('/demo/activate'),
  deactivate: () => api.delete('/demo/deactivate'),
}

export const licenseApi = {
  status: () => api.get('/license/status'),
  activate: (license_key: string) => api.post('/license/activate', { license_key }),
}

export const systemApi = {
  flags: () => api.get('/system/flags'),
  maintenance: () => api.get('/system/maintenance'),
  enableMaintenance: (reason?: string) => api.post('/system/maintenance/enable', { reason }),
  disableMaintenance: () => api.post('/system/maintenance/disable'),
  validateRestore: () => api.get('/system/restore/validate'),
  factoryReset: (confirm: boolean) => api.post('/system/factory-reset', { confirm }),
  getVersion: () => api.get('/system/version'),
  checkUpdate: (license_key: string) => api.post('/system/version/check', { license_key }),
}

export const updatesApi = {
  status: () => api.get('/updates/status'),
  trigger: () => api.post('/updates/trigger'),
  logs: () => api.get('/updates/logs'),
}

export const backupApi = {
  list: () => list('/backup'),
  create: () => api.post('/backup'),
  verify: (filename: string) => api.get(`/backup/${filename}/verify`),
  restore: (filename: string) => api.post(`/backup/${filename}/restore`, { confirm: true }),
  download: (filename: string) => api.get(`/backup/${filename}/download`, { responseType: 'blob' }),
  delete: (filename: string) => api.delete(`/backup/${filename}`),
  uploadRestore: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/backup/upload-restore', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  purgeTransactions: (dateFrom: string, dateTo: string) =>
    api.post('/backup/purge/transactions', null, { params: { date_from: dateFrom, date_to: dateTo, confirm: true } }),
}

/* ── Admin APIs ──────────────────────────────────────────── */
export const usersApi = {
  list: (params?: object) => api.get('/users', { params }),
  get: (id: string) => api.get(`/users/${id}`),
  create: (data: object) => api.post('/users', data),
  update: (id: string, data: object) => api.patch(`/users/${id}`, data),
  deactivate: (id: string) => api.post(`/users/${id}/deactivate`),
  me: () => api.get('/users/me'),
  changePassword: (data: object) => api.post('/users/me/change-password', data),
  updatePreferences: (data: { ui_theme?: string; locale?: string; dashboard_layout?: string }) =>
    api.patch('/users/me/preferences', data),
  adminResetPassword: (id: string, new_password: string) =>
    api.post(`/users/${id}/reset-password`, { new_password }),
}

export const rolesApi = {
  list: (params?: object) => api.get('/roles', { params }),
  create: (data: object) => api.post('/roles', data),
  update: (id: string, data: object) => api.patch(`/roles/${id}`, data),
  delete: (id: string) => api.delete(`/roles/${id}`),
  getPermissions: (id: string) => api.get(`/roles/${id}/permissions`),
  assignPermission: (id: string, permissionId: string) =>
    api.post(`/roles/${id}/permissions`, { permission_id: permissionId }),
  removePermission: (id: string, permissionId: string) =>
    api.delete(`/roles/${id}/permissions/${permissionId}`),
}

export const permissionsApi = {
  list: () => api.get('/permissions'),
  seed: () => api.post('/permissions/seed'),
}

export const groupsApi = {
  list: (params?: object) => list('/groups', params),
  create: (data: object) => api.post('/groups', data),
  get: (id: string) => api.get(`/groups/${id}`),
  update: (id: string, data: object) => api.patch(`/groups/${id}`, data),
  delete: (id: string) => api.delete(`/groups/${id}`),
  addMember: (groupId: string, userId: string) =>
    api.post(`/groups/${groupId}/members`, { user_id: userId }),
  removeMember: (groupId: string, userId: string) =>
    api.delete(`/groups/${groupId}/members/${userId}`),
}

export const ledgerApi = {
  getEntries: (accountId: string, params?: object) =>
    api.get(`/ledger/accounts/${accountId}/entries`, { params }),
  getBalance: (accountId: string) =>
    api.get(`/ledger/accounts/${accountId}/balance`),
  verifyIntegrity: (accountId: string) =>
    api.get(`/ledger/verify/${accountId}`),
}

export const importApi = {
  previewTransactions: (form: FormData) =>
    api.post('/import/transactions/preview', form, { headers: { 'Content-Type': 'multipart/form-data' } }),
  importTransactions: (form: FormData, asDraft = true) =>
    api.post(`/import/transactions?as_draft=${asDraft}`, form, { headers: { 'Content-Type': 'multipart/form-data' } }),
  previewAccounts: (form: FormData) =>
    api.post('/import/accounts/preview', form, { headers: { 'Content-Type': 'multipart/form-data' } }),
  importAccounts: (form: FormData) =>
    api.post('/import/accounts', form, { headers: { 'Content-Type': 'multipart/form-data' } }),
}

export const periodLockApi = {
  getLockedPeriods: () => api.get('/period-lock'),
  lockPeriod: (year: number, month: number) => api.post(`/period-lock/${year}/${month}`),
  unlockPeriod: (year: number, month: number) => api.delete(`/period-lock/${year}/${month}`),
}

export const notificationsApi = {
  list: (params?: { page?: number; page_size?: number; unread_only?: boolean }) =>
    api.get('/notifications', { params }),
  getCount: () => api.get('/notifications/count'),
  markRead: (id: string) => api.post(`/notifications/${id}/read`),
  markAllRead: () => api.post('/notifications/read-all'),
  delete: (id: string) => api.delete(`/notifications/${id}`),
}

export const auditApi = {
  list: (params?: {
    module?: string
    action?: string
    actor_id?: string
    record_id?: string
    date_from?: string
    date_to?: string
    page?: number
    page_size?: number
  }) => api.get('/audit', { params }),
  securityEvents: (params?: { limit?: number }) =>
    api.get('/audit/security', { params }),
  recordHistory: (module: string, recordId: string, params?: { limit?: number }) =>
    api.get(`/audit/record/${module}/${recordId}`, { params }),
}

export const deleteRequestsApi = {
  create: (data: { target_table: string; target_id: string; target_label?: string; reason?: string }) =>
    api.post('/delete-requests', data),
  listMine: (params?: { offset?: number; limit?: number }) =>
    api.get('/delete-requests/mine', { params }),
  list: (params?: { status?: string; offset?: number; limit?: number }) =>
    api.get('/delete-requests', { params }),
  approve: (id: string) => api.post(`/delete-requests/${id}/approve`),
  reject: (id: string, reject_reason?: string) =>
    api.post(`/delete-requests/${id}/reject`, { reject_reason }),
}

/* ── Symbol Obligations (Borç / Alacak) ─────────────────────── */
export const obligationsApi = {
  list: () => api.get('/obligations'),
  create: (data: object) => api.post('/obligations', data),
  updateStatus: (id: string, status: 'SETTLED' | 'CANCELLED') =>
    api.patch(`/obligations/${id}/status`, { status }),
  delete: (id: string) => api.delete(`/obligations/${id}`),
}

export default api
