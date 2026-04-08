import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { transactionsApi, accountsApi, categoriesApi, transactionTemplatesApi } from '../api/umay'

import { CURRENCIES, getCurrencySymbol } from '../constants/currencies'

interface Tx {
  id: string; transaction_type: string; amount: number; currency: string
  description?: string; transaction_date: string; status: string
  category_id?: string; source_account_id?: string
}

const TYPE_BADGE: Record<string, string> = {
  INCOME: 'badge-income', EXPENSE: 'badge-expense', TRANSFER: 'badge-transfer',
}

const STATUS_BADGE: Record<string, string> = {
  CONFIRMED: 'badge-confirmed', PENDING: 'badge-pending', DRAFT: 'badge-draft',
}

/** Sort accounts: positive balance desc first, then zero/negative at bottom */
function sortedAccounts(accounts: any[]) {
  return [...accounts].sort((a, b) => {
    const ba = parseFloat(a.current_balance || '0')
    const bb = parseFloat(b.current_balance || '0')
    if (ba > 0 && bb <= 0) return -1
    if (bb > 0 && ba <= 0) return 1
    return bb - ba
  })
}

function fmtBalance(account: any) {
  if (account.is_own_group === false) return null
  const bal = parseFloat(account.current_balance || '0')
  const sym = getCurrencySymbol(account.currency)
  return `${sym} ${bal.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function AccountOptions({ accounts }: { accounts: any[] }) {
  return (
    <>
      {sortedAccounts(accounts).map((a: any) => {
        const bal = parseFloat(a.current_balance || '0')
        const hasBalance = bal > 0
        const balStr = fmtBalance(a)
        return (
          <option key={a.id} value={a.id}>
            {a.group_name ? `${a.group_name} - ` : ''}{a.name}{balStr ? ` — ${balStr}${!hasBalance ? ' (bakiye yok)' : ''}` : ''}
          </option>
        )
      })}
    </>
  )
}

function CreateTxModal({ accounts, categories, templates, onClose, onSaved, onTemplateDeleted }: any) {
  const { t } = useTranslation()
  const [form, setForm] = useState({
    transaction_type: 'EXPENSE', amount: '', currency: 'TRY',
    description: '', transaction_date: new Date().toISOString().slice(0, 10),
    source_account_id: '', target_account_id: '', category_id: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saveAsTemplate, setSaveAsTemplate] = useState(false)
  const [templateName, setTemplateName] = useState('')
  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }))

  const applyTemplate = (tmplId: string) => {
    const tmpl = templates.find((t: any) => t.id === tmplId)
    if (!tmpl) return
    setForm(f => ({
      ...f,
      transaction_type: tmpl.transaction_type,
      currency: tmpl.currency || 'TRY',
      source_account_id: tmpl.source_account_id || '',
      target_account_id: tmpl.target_account_id || '',
      category_id: tmpl.category_id || '',
      description: tmpl.description || '',
      amount: '',
    }))
    setSaveAsTemplate(false)
    setTemplateName('')
  }

  const submit = async () => {
    if (!form.amount) { setError('Tutar zorunludur'); return }
    if (form.transaction_type !== 'TRANSFER' && !form.category_id) {
      setError('Kategori seçimi zorunludur'); return
    }

    const payload: any = {
      transaction_type: form.transaction_type,
      amount: parseFloat(form.amount),
      currency: form.currency,
      description: form.description,
      transaction_date: form.transaction_date,
      status: 'CONFIRMED',
    }

    if (form.transaction_type === 'TRANSFER') {
      if (!form.source_account_id || !form.target_account_id) {
        setError('Kaynak ve hedef hesaplar transfer için zorunludur'); return
      }
      if (form.source_account_id === form.target_account_id) {
        setError('Kaynak ve hedef hesaplar aynı olamaz'); return
      }
      payload.source_account_id = form.source_account_id
      payload.target_account_id = form.target_account_id
    } else if (form.transaction_type === 'INCOME') {
      if (!form.target_account_id) { setError('Hedef hesap zorunludur'); return }
      payload.target_account_id = form.target_account_id
      payload.category_id = form.category_id
    } else {
      if (!form.source_account_id) { setError('Kaynak hesap zorunludur'); return }
      payload.source_account_id = form.source_account_id
      payload.category_id = form.category_id
    }

    setSaving(true)
    try {
      await transactionsApi.create(payload)
      if (saveAsTemplate && templateName.trim()) {
        await transactionTemplatesApi.create({
          name: templateName.trim(),
          transaction_type: form.transaction_type,
          currency: form.currency,
          source_account_id: form.source_account_id || null,
          target_account_id: form.target_account_id || null,
          category_id: form.category_id || null,
          description: form.description || null,
        })
      }
      onSaved()
    } catch (e: any) {
      setError(e.response?.data?.error?.message || e.response?.data?.detail?.[0]?.msg || 'İşlem kaydedilemedi')
    } finally { setSaving(false) }
  }

  const filteredCats = categories.filter((c: any) => c.category_type === form.transaction_type)
  const typeTemplates = templates.filter((t: any) => !form.transaction_type || t.transaction_type === form.transaction_type)

  return (
    <div className="modal-backdrop" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <span className="modal-title">{t('transactions.newTransaction')}</span>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          {error && <div className="alert alert-danger">{error}</div>}

          {/* Şablon seç */}
          {templates.length > 0 && (
            <div className="form-group" style={{ marginBottom: 'var(--space-4)', padding: 'var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
              <label className="form-label" style={{ fontSize: 'var(--font-size-xs)', marginBottom: 'var(--space-2)' }}>Kayıtlı şablondan seç</label>
              <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                <select className="form-select" defaultValue="" onChange={e => applyTemplate(e.target.value)} style={{ flex: 1 }}>
                  <option value="">— Şablon seç —</option>
                  {templates.map((tmpl: any) => (
                    <option key={tmpl.id} value={tmpl.id}>
                      {tmpl.name} ({tmpl.transaction_type === 'INCOME' ? 'Gelir' : tmpl.transaction_type === 'EXPENSE' ? 'Gider' : 'Transfer'})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* Type tabs */}
          <div className="tabs" style={{ marginBottom: 'var(--space-4)' }}>
            {['INCOME', 'EXPENSE', 'TRANSFER'].map(type => (
              <button key={type} className={`tab${form.transaction_type === type ? ' active' : ''}`}
                onClick={() => setForm(f => ({ ...f, transaction_type: type, source_account_id: '', target_account_id: '', category_id: '' }))}>
                {type === 'INCOME' ? '↑ ' + t('transactions.income') : type === 'EXPENSE' ? '↓ ' + t('transactions.expense') : '⇄ ' + t('transactions.transfer')}
              </button>
            ))}
          </div>

          <div className="form-row cols-2">
            <div className="form-group">
              <label className="form-label">Tutar <span className="required">*</span></label>
              <div className="amount-input-wrap">
                <span className="currency-prefix">{getCurrencySymbol(form.currency)}</span>
                <input type="number" className="form-input" value={form.amount}
                  onChange={e => set('amount', e.target.value)} placeholder="0.00" min="0" step="0.01" />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">{t('common.currency')}</label>
              <select className="form-select" value={form.currency} onChange={e => set('currency', e.target.value)}>
                {CURRENCIES.map(c => <option key={c.code} value={c.code}>{c.trName} ({c.code})</option>)}
              </select>
            </div>
          </div>

          {form.transaction_type === 'TRANSFER' ? (
            <div className="form-row cols-2">
              <div className="form-group">
                <label className="form-label">{t('transactions.sourceAccount')} <span className="required">*</span></label>
                <select className="form-select" value={form.source_account_id} onChange={e => {
                  const id = e.target.value
                  set('source_account_id', id)
                  const acc = accounts.find((a: any) => a.id === id)
                  if (acc) set('amount', Math.abs(parseFloat(acc.current_balance || '0')).toFixed(2))
                }}>
                  <option value="">Seçiniz...</option>
                  <AccountOptions accounts={accounts.filter((a: any) => a.currency === form.currency && a.account_type !== 'CREDIT')} />
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">{t('transactions.targetAccount')} <span className="required">*</span></label>
                <select className="form-select" value={form.target_account_id} onChange={e => set('target_account_id', e.target.value)}>
                  <option value="">Seçiniz...</option>
                  <AccountOptions accounts={accounts.filter((a: any) => a.currency === form.currency && a.account_type !== 'CREDIT')} />
                </select>
              </div>
            </div>
          ) : (
            <div className="form-group">
              <label className="form-label">{form.transaction_type === 'INCOME' ? t('transactions.targetAccount') : t('transactions.sourceAccount')} <span className="required">*</span></label>
              <select className="form-select" value={form.transaction_type === 'INCOME' ? form.target_account_id : form.source_account_id}
                onChange={e => {
                  const id = e.target.value
                  const field = form.transaction_type === 'INCOME' ? 'target_account_id' : 'source_account_id'
                  set(field, id)
                  if (form.transaction_type === 'EXPENSE' && id) {
                    const acc = accounts.find((a: any) => a.id === id)
                    if (acc) set('amount', Math.abs(parseFloat(acc.current_balance || '0')).toFixed(2))
                  }
                }}>
                <option value="">Seçiniz...</option>
                <AccountOptions accounts={accounts.filter((a: any) => a.currency === form.currency && a.account_type !== 'CREDIT')} />
              </select>
            </div>
          )}

          <div className="form-row cols-2">
            <div className="form-group">
              <label className="form-label">{t('transactions.category')} {form.transaction_type !== 'TRANSFER' && <span className="required">*</span>}</label>
              <select className="form-select" value={form.category_id} onChange={e => set('category_id', e.target.value)} disabled={form.transaction_type === 'TRANSFER'}>
                <option value="">{form.transaction_type === 'TRANSFER' ? t('common.none') : 'Seçiniz...'}</option>
                {filteredCats.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">{t('transactions.transactionDate')}</label>
              <input type="date" className="form-input" value={form.transaction_date}
                onChange={e => set('transaction_date', e.target.value)} />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Açıklama</label>
            <input className="form-input" value={form.description}
              onChange={e => set('description', e.target.value)} placeholder="Opsiyonel" />
          </div>

          {/* Şablon kaydet */}
          <div style={{ borderTop: '1px solid var(--border)', paddingTop: 'var(--space-3)', marginTop: 'var(--space-2)' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', cursor: 'pointer', fontSize: 'var(--font-size-sm)' }}>
              <input type="checkbox" checked={saveAsTemplate} onChange={e => setSaveAsTemplate(e.target.checked)} />
              Bu işlemi şablon olarak kaydet
            </label>
            {saveAsTemplate && (
              <input className="form-input" style={{ marginTop: 'var(--space-2)' }}
                placeholder="Şablon adı (örn: Faiz Ödemesi)" value={templateName}
                onChange={e => setTemplateName(e.target.value)} />
            )}
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>{t('common.cancel')}</button>
          <button className="btn btn-primary" onClick={submit} disabled={saving}>
            {saving ? <><span className="spinner spinner-sm" /> {t('common.saving')}</> : t('common.save')}
          </button>
        </div>
      </div>
    </div>
  )
}

export function TransactionsPage() {
  const { t } = useTranslation()
  const [txs, setTxs] = useState<Tx[]>([])
  const [accounts, setAccounts] = useState<any[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [templates, setTemplates] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [showTemplates, setShowTemplates] = useState(false)
  const [filter, setFilter] = useState({ type: '', search: '' })
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')

  const loadTemplates = () => transactionTemplatesApi.list().then(r => setTemplates(r.data))

  const load = () => {
    setLoading(true)
    Promise.allSettled([
      transactionsApi.list({ skip: 0, limit: 100 }),
      accountsApi.list({ skip: 0, limit: 100 }),
      categoriesApi.list({ skip: 0, limit: 100 }),
      transactionTemplatesApi.list(),
    ]).then(([txRes, accRes, catRes, tmplRes]) => {
      if (txRes.status === 'fulfilled') setTxs(txRes.value.data)
      if (accRes.status === 'fulfilled') setAccounts(accRes.value.data)
      if (catRes.status === 'fulfilled') setCategories(catRes.value.data)
      if (tmplRes.status === 'fulfilled') setTemplates(tmplRes.value.data)
    }).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const deleteTemplate = async (id: string) => {
    await transactionTemplatesApi.delete(id)
    loadTemplates()
  }

  const canDelete = (item: any): boolean => {
    const dateStr = item.created_at || item.updated_at
    if (!dateStr) return true
    const diffDays = (Date.now() - new Date(dateStr).getTime()) / 86_400_000
    return diffDays <= 5
  }

  const confirmDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setDeletingId(id)
    setDeleteError('')
    setShowDeleteModal(true)
  }

  const handleDelete = async () => {
    if (!deletingId) return
    setDeleting(true)
    setDeleteError('')
    try {
      await transactionsApi.delete(deletingId)
      setShowDeleteModal(false)
      setDeletingId(null)
      load()
    } catch (e: any) {
      setDeleteError(e.response?.data?.error?.message || 'Silinemedi')
    } finally { setDeleting(false) }
  }

  const filtered = txs.filter(tx => {
    if (filter.type && tx.transaction_type !== filter.type) return false
    if (filter.search && !tx.description?.toLowerCase().includes(filter.search.toLowerCase())) return false
    return true
  })

  const income  = txs.filter(tx => tx.transaction_type === 'INCOME' && tx.status === 'CONFIRMED').reduce((s, tx) => s + Number(tx.amount), 0)
  const expense = txs.filter(tx => tx.transaction_type === 'EXPENSE' && tx.status === 'CONFIRMED').reduce((s, tx) => s + Number(tx.amount), 0)

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">{t('transactions.title')}</h1>
          <p className="page-subtitle">{txs.length} {t('common.total', 'kayıt')}</p>
        </div>
        <div className="page-actions">
          <button className="btn btn-secondary" onClick={() => setShowTemplates(true)}>
            Kayıtlı İşlemler {templates.length > 0 && <span style={{ marginLeft: 4, background: 'var(--primary)', color: '#fff', borderRadius: 10, padding: '1px 7px', fontSize: 'var(--font-size-xs)' }}>{templates.length}</span>}
          </button>
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>{t('transactions.newTransaction')}</button>
        </div>
      </div>

      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 'var(--space-6)' }}>
        <div className="stat-card">
          <div className="stat-card-label">{t('common.total')} {t('transactions.income')}</div>
          <div className="stat-card-value income">+{income.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">{t('common.total')} {t('transactions.expense')}</div>
          <div className="stat-card-value expense">-{expense.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">{t('dashboard.net')}</div>
          <div className={`stat-card-value${income - expense >= 0 ? '' : ' expense'}`}>
            {(income - expense).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
          </div>
        </div>
      </div>

      <div className="filter-bar">
        <div className="search-input-wrap">
          <span className="search-icon">🔍</span>
          <input className="form-input" placeholder={t('transactions.searchPlaceholder') as string}
            value={filter.search} onChange={e => setFilter(f => ({ ...f, search: e.target.value }))} />
        </div>
        <div className="tabs">
          {['', 'INCOME', 'EXPENSE', 'TRANSFER'].map(type => (
            <button key={type} className={`tab${filter.type === type ? ' active' : ''}`}
              onClick={() => setFilter(f => ({ ...f, type }))}>
              {type === '' ? t('common.all') : t('transactions.' + type.toLowerCase(), type)}
            </button>
          ))}
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        {loading ? (
          <div className="loading-state"><div className="spinner" /></div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">↕️</div>
            <div className="empty-state-title">{t('transactions.noTransactions')}</div>
            <div className="empty-state-desc">{t('transactions.noTransactionsDesc')}</div>
          </div>
        ) : (
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t('common.date')}</th>
                  <th>{t('common.description')}</th>
                  <th>{t('common.type')}</th>
                  <th>{t('common.status')}</th>
                  <th style={{ textAlign: 'right' }}>{t('common.amount')}</th>
                  <th style={{ width: 40 }}></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(tx => (
                  <tr key={tx.id}>
                    <td style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-xs)', fontFamily: 'var(--font-mono)' }}>
                      {tx.transaction_date}
                    </td>
                    <td>{tx.description || <span style={{ color: 'var(--text-tertiary)' }}>—</span>}</td>
                    <td><span className={`badge ${TYPE_BADGE[tx.transaction_type] || 'badge-neutral'}`}>{t('transactions.' + tx.transaction_type.toLowerCase(), tx.transaction_type)}</span></td>
                    <td><span className={`badge ${STATUS_BADGE[tx.status] || 'badge-draft'}`}>{t('status.' + tx.status, tx.status)}</span></td>
                    <td className="text-right">
                      <span className={`amount${tx.transaction_type === 'INCOME' ? ' positive' : tx.transaction_type === 'EXPENSE' ? ' negative' : ''}`}>
                        {tx.transaction_type === 'INCOME' ? '+' : tx.transaction_type === 'EXPENSE' ? '-' : ''}
                        {getCurrencySymbol(tx.currency)}{Number(tx.amount).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
                      </span>
                    </td>
                    <td>
                      <button
                        className="btn btn-ghost btn-icon btn-sm"
                        onClick={(e) => confirmDelete(tx.id, e)}
                        style={{ color: canDelete(tx) ? 'var(--expense)' : 'var(--text-tertiary)', cursor: canDelete(tx) ? 'pointer' : 'not-allowed', opacity: canDelete(tx) ? 1 : 0.4 }}
                        title={canDelete(tx) ? 'Sil' : '5 günlük silme süresi doldu'}
                        disabled={!canDelete(tx)}
                      >✕</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showCreate && (
        <CreateTxModal
          accounts={accounts} categories={categories} templates={templates}
          onClose={() => setShowCreate(false)}
          onSaved={() => { setShowCreate(false); load() }}
        />
      )}

      {/* Kayıtlı İşlemler Modal */}
      {showTemplates && (
        <div className="modal-backdrop" onClick={() => setShowTemplates(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">Kayıtlı İşlemler</span>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowTemplates(false)}>✕</button>
            </div>
            <div className="modal-body">
              {templates.length === 0 ? (
                <div style={{ textAlign: 'center', color: 'var(--text-tertiary)', padding: 'var(--space-6)' }}>
                  Henüz kayıtlı işlem yok.<br />
                  <small>Yeni işlem kaydederken "Şablon olarak kaydet" seçeneğini işaretleyerek ekleyebilirsiniz.</small>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                  {templates.map((tmpl: any) => (
                    <div key={tmpl.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 'var(--space-3)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', background: 'var(--bg-elevated)' }}>
                      <div>
                        <div style={{ fontWeight: 600 }}>{tmpl.name}</div>
                        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 2 }}>
                          {tmpl.transaction_type === 'INCOME' ? '↑ Gelir' : tmpl.transaction_type === 'EXPENSE' ? '↓ Gider' : '⇄ Transfer'}
                          {tmpl.description && ` · ${tmpl.description}`}
                          {tmpl.currency && ` · ${tmpl.currency}`}
                        </div>
                      </div>
                      <button className="btn btn-ghost btn-icon btn-sm" style={{ color: 'var(--expense)' }}
                        onClick={() => deleteTemplate(tmpl.id)} title="Şablonu sil">✕</button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowTemplates(false)}>Kapat</button>
            </div>
          </div>
        </div>
      )}

      {showDeleteModal && (
        <div className="modal-backdrop" onClick={() => setShowDeleteModal(false)} style={{ zIndex: 110 }}>
          <div className="modal modal-sm" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">İşlemi Sil</span>
            </div>
            <div className="modal-body">
              {deleteError && <div className="alert alert-danger">{deleteError}</div>}
              <p style={{ textAlign: 'center' }}>Bu işlemi silmek istediğinize emin misiniz?<br/>
                <small style={{ color: 'var(--text-secondary)' }}>Onaylanmış işlemlerde hesap bakiyesi otomatik düzeltilir.</small>
              </p>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowDeleteModal(false)}>Vazgeç</button>
              <button className="btn btn-danger" onClick={handleDelete} disabled={deleting}>
                {deleting ? <span className="spinner spinner-sm" /> : 'Sil'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
