import React, { useEffect, useState } from 'react'
import { LedgerIcon, ReportsIcon } from '../components/Icons'

const getCookie = (name: string) => document.cookie.split('; ').reduce((acc, p) => { const [k, v] = p.split('='); return k === name ? decodeURIComponent(v || '') : acc }, '')
const api = (url: string, opts?: RequestInit) => {
  const tenantId = getCookie('umay_tenant_id')
  return fetch(`/api/v1${url}`, {
    ...opts,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(tenantId ? { 'X-Tenant-Id': tenantId } : {}),
      ...(opts?.headers || {}),
    },
  }).then(r => r.ok ? r.json() : r.json().then((e: any) => Promise.reject(e)))
}

interface LedgerEntry {
  id: string
  transaction_id: string
  account_id: string
  entry_type: 'DEBIT' | 'CREDIT'
  amount: number
  currency: string
  posted_at: string
  description: string | null
}

interface Account {
  id: string
  name: string
  currency: string
  current_balance: number
  account_type: string
}

interface BalanceInfo {
  account_id: string
  ledger_balance: number
  is_balanced: boolean
}

const FMT = (n: number, cur = '₺') =>
  `${cur} ${Math.abs(n).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}`

export function LedgerPage() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null)
  const [entries, setEntries] = useState<LedgerEntry[]>([])
  const [balance, setBalance] = useState<BalanceInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [entriesLoading, setEntriesLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const PAGE_SIZE = 50

  useEffect(() => {
    api('/accounts?page_size=100').then(r => {
      setAccounts(r.items || [])
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const selectAccount = async (account: Account, p = 1) => {
    setSelectedAccount(account)
    setPage(p)
    setEntriesLoading(true)
    try {
      const [eRes, bRes] = await Promise.all([
        api(`/ledger/accounts/${account.id}/entries?page=${p}&page_size=${PAGE_SIZE}`),
        api(`/ledger/accounts/${account.id}/balance`),
      ])
      setEntries(eRes.items || [])
      setTotal(eRes.total || 0)
      setBalance(bRes)
    } catch { setEntries([]); setBalance(null) }
    finally { setEntriesLoading(false) }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Ledger</h1>
          <p className="page-subtitle">Double-entry accounting records — read-only audit view</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 'var(--space-5)', alignItems: 'start' }}>
        {/* Account list */}
        <div className="card" style={{ padding: 0 }}>
          <div className="card-header"><div className="card-title">Accounts</div></div>
          {loading ? (
            <div className="loading-state" style={{ minHeight: 100 }}><div className="spinner" /></div>
          ) : accounts.length === 0 ? (
            <div style={{ padding: 'var(--space-6)', color: 'var(--text-tertiary)', textAlign: 'center', fontSize: 'var(--font-size-sm)' }}>No accounts</div>
          ) : (
            <div>
              {accounts.map(acc => (
                <button
                  key={acc.id}
                  onClick={() => selectAccount(acc)}
                  style={{
                    display: 'flex', flexDirection: 'column', width: '100%',
                    padding: '12px 16px', border: 'none', textAlign: 'left',
                    background: selectedAccount?.id === acc.id ? 'var(--accent-soft)' : 'transparent',
                    borderBottom: '1px solid var(--border)', cursor: 'pointer', transition: 'background 0.15s',
                  }}
                >
                  <div style={{ fontWeight: 500, fontSize: 'var(--font-size-sm)' }}>{acc.name}</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                    <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{acc.account_type}</span>
                    <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: acc.current_balance >= 0 ? 'var(--income)' : 'var(--expense)' }}>
                      {FMT(acc.current_balance, acc.currency)}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Ledger entries */}
        <div>
          {balance && (
            <div className={`alert ${balance.is_balanced ? 'alert-success' : 'alert-danger'}`} style={{ marginBottom: 'var(--space-4)' }}>
              <strong>{balance.is_balanced ? '✓ Ledger Balanced' : '⚠ Integrity Issue'}</strong>
              {'  '}Ledger balance: <span style={{ fontFamily: 'var(--font-mono)' }}>{FMT(balance.ledger_balance)}</span>
              {!balance.is_balanced && ' — Account balance does not match ledger totals!'}
            </div>
          )}

          <div className="card" style={{ padding: 0 }}>
            <div className="card-header">
              <div>
                <div className="card-title">{selectedAccount ? `${selectedAccount.name} — Ledger Entries` : 'Select an account'}</div>
                {total > 0 && <div className="card-subtitle">{total} entries total</div>}
              </div>
              {totalPages > 1 && selectedAccount && (
                <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
                  <button className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => selectAccount(selectedAccount!, page - 1)}>‹</button>
                  <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>{page} / {totalPages}</span>
                  <button className="btn btn-ghost btn-sm" disabled={page >= totalPages} onClick={() => selectAccount(selectedAccount!, page + 1)}>›</button>
                </div>
              )}
            </div>

            {!selectedAccount ? (
              <div className="empty-state" style={{ padding: 'var(--space-10) 0' }}>
                <div className="empty-state-icon"><LedgerIcon size={48} /></div>
                <div className="empty-state-title">Select an account</div>
                <div className="empty-state-desc">Choose an account to view its double-entry ledger records.</div>
              </div>
            ) : entriesLoading ? (
              <div className="loading-state"><div className="spinner" /></div>
            ) : entries.length === 0 ? (
              <div className="empty-state" style={{ padding: 'var(--space-8) 0' }}>
                <div className="empty-state-icon"><ReportsIcon size={48} /></div>
                <div className="empty-state-title">No ledger entries</div>
                <div className="empty-state-desc">Entries are created automatically when transactions are confirmed.</div>
              </div>
            ) : (
              <div className="data-table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Posted At</th>
                      <th>Type</th>
                      <th>Description</th>
                      <th>Transaction ID</th>
                      <th style={{ textAlign: 'right' }}>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {entries.map(e => (
                      <tr key={e.id}>
                        <td style={{ fontSize: 'var(--font-size-xs)', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                          {new Date(e.posted_at).toLocaleString('tr-TR', { dateStyle: 'short', timeStyle: 'short' })}
                        </td>
                        <td>
                          <span className={`badge ${e.entry_type === 'DEBIT' ? 'badge-income' : 'badge-expense'}`}>
                            {e.entry_type}
                          </span>
                        </td>
                        <td style={{ fontSize: 'var(--font-size-sm)' }}>{e.description || <span style={{ color: 'var(--text-tertiary)' }}>—</span>}</td>
                        <td style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)', maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {e.transaction_id}
                        </td>
                        <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 600, color: e.entry_type === 'DEBIT' ? 'var(--income)' : 'var(--expense)' }}>
                          {e.entry_type === 'DEBIT' ? '+' : '-'}{e.currency} {Number(e.amount).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
