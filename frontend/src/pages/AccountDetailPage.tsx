import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { accountsApi, groupsApi, categoriesApi } from '../api/umay'
import { getCurrencySymbol } from '../constants/currencies'

const TYPE_BADGE: Record<string, string> = {
  INCOME: 'badge-income', EXPENSE: 'badge-expense', TRANSFER: 'badge-transfer',
}

export function AccountDetailPage() {
  const { t } = useTranslation()
  const { accountId } = useParams<{ accountId: string }>()
  const navigate = useNavigate()

  const [account, setAccount] = useState<any>(null)
  const [transactions, setTransactions] = useState<any[]>([])
  const [totalTx, setTotalTx] = useState(0)
  const [groups, setGroups] = useState<any[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [accounts, setAccounts] = useState<any[]>([])
  const [profit, setProfit] = useState<{ net_profit: number; net_capital: number } | null>(null)
  const [loading, setLoading] = useState(true)
  const [txLoading, setTxLoading] = useState(false)
  const [page, setPage] = useState(1)
  const pageSize = 25

  // Filters
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [filterType, setFilterType] = useState('')

  useEffect(() => {
    if (!accountId) return
    setLoading(true)
    Promise.allSettled([
      accountsApi.get(accountId),
      groupsApi.list({ skip: 0, limit: 100 }),
      categoriesApi.list({ skip: 0, limit: 100 }),
      accountsApi.list({ skip: 0, limit: 200 }),
    ]).then(([acctRes, grpRes, catRes, acctListRes]) => {
      if (acctRes.status === 'fulfilled') setAccount(acctRes.value.data)
      if (grpRes.status === 'fulfilled') setGroups(grpRes.value.data)
      if (catRes.status === 'fulfilled') setCategories(catRes.value.data)
      if (acctListRes.status === 'fulfilled') setAccounts(acctListRes.value.data)
      accountsApi.profit(accountId).then(r => setProfit(r.data)).catch(() => {})
    }).finally(() => setLoading(false))
  }, [accountId])

  const loadTransactions = () => {
    if (!accountId) return
    setTxLoading(true)
    const params: any = { page, page_size: pageSize }
    if (dateFrom) params.date_from = dateFrom
    if (dateTo) params.date_to = dateTo
    if (filterType) params.transaction_type = filterType
    accountsApi.transactions(accountId, params)
      .then(res => {
        const data = res.data
        setTransactions(data.items || [])
        setTotalTx(data.total || 0)
      })
      .catch(() => {})
      .finally(() => setTxLoading(false))
  }

  useEffect(() => { loadTransactions() }, [accountId, page, dateFrom, dateTo, filterType])

  const totalPages = Math.ceil(totalTx / pageSize) || 1

  const getAccountName = (id: string | null) => {
    if (!id) return '—'
    const a = accounts.find((acc: any) => acc.id === id)
    return a ? a.name : id.slice(0, 8) + '...'
  }

  const getCategoryName = (id: string | null) => {
    if (!id) return ''
    const c = categories.find((cat: any) => cat.id === id)
    return c ? c.name : ''
  }

  if (loading) {
    return <div className="loading-state"><div className="spinner" /></div>
  }

  if (!account) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">❌</div>
        <div className="empty-state-title">{t('common.notFound', 'Bulunamadı')}</div>
        <button className="btn btn-secondary" onClick={() => navigate('/accounts')}>{t('common.back', 'Geri')}</button>
      </div>
    )
  }

  const symbol = getCurrencySymbol(account.currency)
  const isNeg = Number(account.current_balance) < 0

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/accounts')} style={{ fontSize: '18px' }}>
            ←
          </button>
          <div style={{ flex: 1 }}>
            <h1 className="page-title">{account.name}</h1>
            <p className="page-subtitle">
              {t(`accounts.types.${account.account_type}`, account.account_type) as string}
              {account.institution_name ? ` · ${account.institution_name}` : ''}
            </p>
            {(account.iban || account.group_name) && (
              <div style={{ display: 'flex', gap: 'var(--space-4)', marginTop: 'var(--space-2)', fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
                {account.iban && (
                  <div style={{ fontFamily: 'monospace' }}>
                    {account.iban}
                  </div>
                )}
                {account.group_name && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span>👥</span> {account.group_name}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Balance KPI */}
      <div className="stats-grid" style={{ gridTemplateColumns: account.account_type === 'INVESTMENT' ? 'repeat(2, 1fr)' : '1fr', marginBottom: 'var(--space-6)' }}>
        <div className="stat-card">
          <div className="stat-card-label">{t('accounts.currentBalance', 'Güncel Bakiye')}</div>
          <div className="stat-card-value" style={{ color: isNeg ? 'var(--expense)' : 'var(--income)' }}>
            {isNeg ? '-' : ''}{symbol} {Math.abs(Number(account.current_balance)).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
          </div>
        </div>
        {account.account_type === 'INVESTMENT' && (
          <div className="stat-card">
            <div className="stat-card-label">{t('accounts.netProfit', 'Net Kar / Zarar')}</div>
            {profit !== null ? (() => {
              const isLoss = profit.net_profit < 0
              return (
                <div className="stat-card-value" style={{ color: isLoss ? 'var(--expense)' : 'var(--income)' }}>
                  {isLoss ? '-' : '+'}{symbol} {Math.abs(profit.net_profit).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
                </div>
              )
            })() : (
              <div className="stat-card-value" style={{ color: 'var(--text-muted)' }}>—</div>
            )}
            {profit !== null && (
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginTop: 'var(--space-1)' }}>
                {t('accounts.capitalInvested', 'Yatırılan Sermaye')}: {symbol} {profit.net_capital.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
        <div style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div className="form-group" style={{ flex: '1 1 140px', marginBottom: 0 }}>
            <label className="form-label" style={{ fontSize: 'var(--font-size-xs)' }}>{t('common.dateFrom', 'Başlangıç')}</label>
            <input className="form-input" type="date" value={dateFrom} onChange={e => { setDateFrom(e.target.value); setPage(1) }} />
          </div>
          <div className="form-group" style={{ flex: '1 1 140px', marginBottom: 0 }}>
            <label className="form-label" style={{ fontSize: 'var(--font-size-xs)' }}>{t('common.dateTo', 'Bitiş')}</label>
            <input className="form-input" type="date" value={dateTo} onChange={e => { setDateTo(e.target.value); setPage(1) }} />
          </div>
          <div className="form-group" style={{ flex: '1 1 140px', marginBottom: 0 }}>
            <label className="form-label" style={{ fontSize: 'var(--font-size-xs)' }}>{t('common.transactionType', 'İşlem Tipi')}</label>
            <select className="form-input" value={filterType} onChange={e => { setFilterType(e.target.value); setPage(1) }}>
              <option value="">{t('common.all', 'Tümü')}</option>
              <option value="INCOME">{t('transactions.income', 'Gelir')}</option>
              <option value="EXPENSE">{t('transactions.expense', 'Gider')}</option>
              <option value="TRANSFER">{t('transactions.transfer', 'Transfer')}</option>
            </select>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => { setDateFrom(''); setDateTo(''); setFilterType(''); setPage(1) }}>
            {t('common.clearFilters', 'Temizle')}
          </button>
        </div>
      </div>

      {/* Transaction List */}
      {txLoading ? (
        <div className="loading-state"><div className="spinner" /></div>
      ) : transactions.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <div className="empty-state-title">{t('transactions.noTransactions', 'Hareket bulunamadı')}</div>
        </div>
      ) : (
        <div className="card" style={{ padding: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('common.date', 'Tarih')}</th>
                <th>{t('common.type', 'Tip')}</th>
                <th>{t('common.description', 'Açıklama')}</th>
                <th>{t('common.category', 'Kategori')}</th>
                <th>{t('accounts.fromTo', 'Hesap')}</th>
                <th style={{ textAlign: 'right' }}>{t('common.amount', 'Tutar')}</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((tx: any) => {
                const isCredit = tx.target_account_id === accountId
                const isDebit = tx.source_account_id === accountId
                const counterAccount = tx.transaction_type === 'TRANSFER'
                  ? (isDebit ? getAccountName(tx.target_account_id) : getAccountName(tx.source_account_id))
                  : (isCredit ? getAccountName(tx.source_account_id) : getAccountName(tx.target_account_id))

                // Determine sign
                let sign = ''
                let color = ''
                if (tx.transaction_type === 'INCOME') {
                  sign = '+'
                  color = 'var(--income)'
                } else if (tx.transaction_type === 'EXPENSE') {
                  sign = '-'
                  color = 'var(--expense)'
                } else if (tx.transaction_type === 'TRANSFER') {
                  if (isCredit) { sign = '+'; color = 'var(--income)' }
                  else { sign = '-'; color = 'var(--expense)' }
                }

                return (
                  <tr key={tx.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', whiteSpace: 'nowrap' }}>
                      {tx.transaction_date}
                    </td>
                    <td>
                      <span className={`badge ${TYPE_BADGE[tx.transaction_type] || 'badge-neutral'}`}>
                        {t(`transactions.${tx.transaction_type.toLowerCase()}`, tx.transaction_type) as string}
                      </span>
                    </td>
                    <td style={{ maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {tx.description || '—'}
                    </td>
                    <td style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>
                      {getCategoryName(tx.category_id) || '—'}
                    </td>
                    <td style={{ fontSize: 'var(--font-size-xs)' }}>
                      {counterAccount}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 600, color }}>
                      {sign}{tx.currency} {Number(tx.amount).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 'var(--space-2)', marginTop: 'var(--space-4)' }}>
          <button className="btn btn-secondary btn-sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
            ← {t('common.previous', 'Önceki')}
          </button>
          <span style={{ padding: '6px 12px', fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
            {page} / {totalPages}
          </span>
          <button className="btn btn-secondary btn-sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
            {t('common.next', 'Sonraki')} →
          </button>
        </div>
      )}
    </div>
  )
}
