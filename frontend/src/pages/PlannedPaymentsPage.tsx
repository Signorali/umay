import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { plannedPaymentsApi, accountsApi, categoriesApi, creditCardsApi } from '../api/umay'

const STATUS_CLASS: Record<string, string> = {
  PENDING: 'badge-pending', PAID: 'badge-confirmed',
  CANCELLED: 'badge-draft', OVERDUE: 'badge-expense',
  PARTIALLY_PAID: 'badge-pending',
}

const RECURRENCE_LABELS: Record<string, string> = {
  NONE: 'Tek Seferlik', DAILY: 'Günlük', WEEKLY: 'Haftalık',
  MONTHLY: 'Aylık', QUARTERLY: 'Üç Aylık', YEARLY: 'Yıllık',
}

const EMPTY_FORM = {
  title: '', amount: '', currency: 'TRY',
  payment_type: 'EXPENSE', recurrence_rule: 'NONE',
  planned_date: new Date().toISOString().slice(0, 10),
  recurrence_end_date: '',
  due_date: '', account_id: '', category_id: '', notes: '',
}

type SortField = 'title' | 'amount' | 'planned_date' | 'due_date' | 'status'
type SortOrder = 'asc' | 'desc'

export function PlannedPaymentsPage() {
  const { t } = useTranslation()
  const [items, setItems] = useState<any[]>([])
  const [accounts, setAccounts] = useState<any[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('PENDING')
  const [typeTab, setTypeTab] = useState<'PLANNED' | 'CC_INSTALLMENTS'>('PLANNED')
  const [cards, setCards] = useState<any[]>([])
  const [closedStatements, setClosedStatements] = useState<any[]>([])

  // Sorting
  const [sortBy, setSortBy] = useState<SortField>('planned_date')
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc')

  // Statement Pay modal
  const [stmtPayTarget, setStmtPayTarget] = useState<any>(null)
  const [showStmtPayModal, setShowStmtPayModal] = useState(false)
  const [stmtPayAccountId, setStmtPayAccountId] = useState('')
  const [stmtPayAmount, setStmtPayAmount] = useState('')
  const [stmtPaying, setStmtPaying] = useState(false)
  const [stmtPayError, setStmtPayError] = useState('')

  // Create / Edit modal
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [form, setForm] = useState({ ...EMPTY_FORM })
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')

  // Delete modal
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')

  // Pay modal
  const [payingItem, setPayingItem] = useState<any>(null)
  const [showPayModal, setShowPayModal] = useState(false)
  const [payAccountId, setPayAccountId] = useState('')
  const [payAmount, setPayAmount] = useState('')
  const [payDate, setPayDate] = useState(new Date().toISOString().slice(0, 10))
  const [paying, setPaying] = useState(false)
  const [payError, setPayError] = useState('')

  const load = () => {
    setLoading(true)
    Promise.allSettled([
      plannedPaymentsApi.list({ skip: 0, limit: 200 }),
      accountsApi.list({ skip: 0, limit: 100 }),
      categoriesApi.list({ skip: 0, limit: 100 }),
      creditCardsApi.list({ skip: 0, limit: 100 }),
    ]).then(async ([p, a, c, cc]) => {
      if (p.status === 'fulfilled') setItems(p.value.data)
      if (a.status === 'fulfilled') setAccounts(a.value.data)
      if (c.status === 'fulfilled') setCategories(c.value.data)
      if (cc.status === 'fulfilled') {
        const cardList = cc.value.data
        setCards(cardList)
        // Load closed statements for all cards
        const stmtResults = await Promise.allSettled(
          cardList.map((card: any) =>
            creditCardsApi.listStatements(card.id, { skip: 0, limit: 50 })
              .then((r: any) => r.data.filter((s: any) => s.status === 'CLOSED' || s.status === 'PARTIALLY_PAID')
                .map((s: any) => ({ ...s, _card: card })))
          )
        )
        const allClosed = stmtResults
          .filter(r => r.status === 'fulfilled')
          .flatMap((r: any) => r.value)
        setClosedStatements(allClosed)
      }
    }).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const ccItems = items.filter(i => i.credit_card_purchase_id)
  const plannedItems = items.filter(i => !i.credit_card_purchase_id)

  // Combine planned items + closed statements (marked as STATEMENT type)
  const combinedItems = [
    ...plannedItems,
    ...closedStatements.map((s: any) => ({
      id: `stmt-${s.id}`,
      _isStatement: true,
      _stmt: s,
      title: `📄 ${s._card.card_name} (${s.period_start} → ${s.period_end})`,
      amount: Number(s.total_spending) - Number(s.paid_amount),
      currency: s._card.currency,
      status: s.status === 'PAID' ? 'PAID' : 'PENDING',
      planned_date: s.due_date,
      due_date: s.due_date,
    }))
  ]

  const baseItems = typeTab === 'CC_INSTALLMENTS' ? ccItems : combinedItems

  // Apply filter
  const filtered = filter === 'ALL' ? baseItems : baseItems.filter(i => i.status === filter)

  // Apply sorting
  const sorted = [...filtered].sort((a, b) => {
    let aVal: any = a[sortBy]
    let bVal: any = b[sortBy]

    if (typeof aVal === 'string') {
      aVal = aVal.toLowerCase()
      bVal = (bVal as string).toLowerCase()
      return sortOrder === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal)
    }
    if (typeof aVal === 'number') {
      return sortOrder === 'asc' ? aVal - bVal : bVal - aVal
    }
    return 0
  })

  // Calculate totals by type
  const pendingItems = plannedItems.filter(i => i.status === 'PENDING')
  const totalIncome = pendingItems.filter(i => i.payment_type === 'INCOME').reduce((s, i) => s + Number(i.amount || 0), 0)
  const totalExpense = pendingItems.filter(i => i.payment_type === 'EXPENSE').reduce((s, i) => s + Number(i.amount || 0), 0)
  const netDifference = totalIncome - totalExpense

  const paymentAccounts = accounts.filter((a: any) => a.account_type === 'BANK' || a.account_type === 'CASH')

  const openNew = () => {
    setEditing(null)
    setForm({ ...EMPTY_FORM })
    setFormError('')
    setShowModal(true)
  }

  const openEdit = (item: any) => {
    setEditing(item)
    setForm({
      title: item.title || '',
      amount: String(item.amount || ''),
      currency: item.currency || 'TRY',
      payment_type: item.payment_type || 'EXPENSE',
      recurrence_rule: item.recurrence_rule || 'NONE',
      planned_date: item.planned_date || new Date().toISOString().slice(0, 10),
      recurrence_end_date: item.recurrence_end_date || '',
      due_date: item.due_date || '',
      account_id: item.account_id || '',
      category_id: item.category_id || '',
      notes: item.notes || '',
    })
    setFormError('')
    setShowModal(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.title.trim()) { setFormError('Başlık zorunlu'); return }
    if (!form.amount || parseFloat(form.amount) <= 0) { setFormError('Geçerli bir tutar girin'); return }
    if (!form.account_id) { setFormError('Hesap seçimi zorunludur'); return }
    if (!form.category_id) { setFormError('Kategori seçimi zorunludur'); return }
    setSaving(true)
    setFormError('')
    try {
      const payload: any = {
        title: form.title,
        payment_type: form.payment_type,
        amount: parseFloat(form.amount),
        currency: form.currency,
        planned_date: form.planned_date,
        recurrence_rule: form.recurrence_rule,
      }
      if (form.due_date) payload.due_date = form.due_date
      payload.account_id = form.account_id
      payload.category_id = form.category_id
      if (form.notes) payload.notes = form.notes
      if (form.recurrence_end_date) payload.recurrence_end_date = form.recurrence_end_date

      if (editing) {
        await plannedPaymentsApi.update(editing.id, {
          title: payload.title,
          amount: payload.amount,
          planned_date: payload.planned_date,
          due_date: payload.due_date,
          notes: payload.notes,
        })
      } else {
        await plannedPaymentsApi.create(payload)
      }
      setShowModal(false)
      load()
    } catch (err: any) {
      const msg = err?.response?.data?.error?.message
        || err?.response?.data?.detail?.[0]?.msg
        || err?.response?.data?.detail
        || t('common.error')
      setFormError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally { setSaving(false) }
  }

  const confirmDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setDeletingId(id)
    setDeleteError('')
    setShowDeleteModal(true)
  }

  const openPay = (item: any, e: React.MouseEvent) => {
    e.stopPropagation()
    setPayingItem(item)
    const defaultAccount = paymentAccounts.find((a: any) => a.id === item.account_id)
    setPayAccountId(defaultAccount ? item.account_id : (paymentAccounts[0]?.id || ''))
    setPayAmount(parseFloat(String(item.amount || 0)).toFixed(2))
    setPayDate(new Date().toISOString().slice(0, 10))
    setPayError('')
    setShowPayModal(true)
  }

  const handlePay = async () => {
    if (!payAccountId) { setPayError('Lütfen bir hesap seçin'); return }
    if (!payAmount || parseFloat(payAmount) <= 0) { setPayError('Geçerli bir tutar girin'); return }
    setPaying(true)
    setPayError('')
    try {
      // For statements, call statement payment API
      if (payingItem._isStatement) {
        await creditCardsApi.payStatement(payingItem._stmt._card.id, payingItem._stmt.id, {
          source_account_id: payAccountId,
          amount: parseFloat(payAmount),
        })
      } else {
        // If amount changed, update first then execute
        if (parseFloat(payAmount) !== parseFloat(payingItem.amount || 0)) {
          await plannedPaymentsApi.update(payingItem.id, { amount: parseFloat(payAmount) })
        }
        await plannedPaymentsApi.execute(payingItem.id, {
          account_id: payAccountId,
          transaction_date: payDate,
        })
      }
      setShowPayModal(false)
      load()
    } catch (err: any) {
      const msg = err?.response?.data?.error?.message
        || err?.response?.data?.detail?.message
        || err?.response?.data?.detail
        || 'Ödeme gerçekleştirilemedi'
      setPayError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally { setPaying(false) }
  }

  const handleDelete = async () => {
    if (!deletingId) return
    setDeleting(true)
    try {
      await plannedPaymentsApi.delete(deletingId)
      setShowDeleteModal(false)
      setDeletingId(null)
      load()
    } catch (err: any) {
      setDeleteError(err?.response?.data?.error?.message || 'Silinemedi')
    } finally { setDeleting(false) }
  }

  const fmt = (v: number) => Number(v).toLocaleString('tr-TR', { minimumFractionDigits: 2 })

  const SOURCE_LABEL = (item: any) => {
    if (item._isStatement) return <span className="badge badge-neutral" style={{ fontSize: 10 }}>📄 Ekstre</span>
    if (item.loan_id) return <span className="badge badge-neutral" style={{ fontSize: 10 }}>🏦 Kredi</span>
    if (item.credit_card_purchase_id) return <span className="badge badge-neutral" style={{ fontSize: 10 }}>💳 KK</span>
    return null
  }

  const canDelete = (item: any): boolean => {
    const dateStr = item.updated_at || item.created_at
    if (!dateStr) return true
    const diffDays = (Date.now() - new Date(dateStr).getTime()) / 86_400_000
    return diffDays <= 5
  }

  const handleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder('asc')
    }
  }

  const SortIndicator = ({ field }: { field: SortField }) => {
    if (sortBy !== field) return <span style={{ opacity: 0.3 }}>⇅</span>
    return <span>{sortOrder === 'asc' ? '↑' : '↓'}</span>
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="page-header" style={{ flexShrink: 0 }}>
        <div>
          <h1 className="page-title">{t('plannedPayments.title')}</h1>
          <p className="page-subtitle">{items.length} {t('plannedPayments.scheduled')} · {sorted.length} {t('common.view')}</p>
        </div>
        <button className="btn btn-primary" onClick={openNew}>{t('plannedPayments.newPayment')}</button>
      </div>

      {typeTab === 'PLANNED' && items.length > 0 && (
        <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 'var(--space-6)', flexShrink: 0 }}>
          <div className="stat-card">
            <div className="stat-card-label">Toplam Gelir</div>
            <div className="stat-card-value" style={{ color: 'var(--income)' }}>
              ₺ {totalIncome.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-card-label">Toplam Gider</div>
            <div className="stat-card-value" style={{ color: 'var(--expense)' }}>
              ₺ {totalExpense.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-card-label">Fark (Net)</div>
            <div className="stat-card-value" style={{ color: netDifference >= 0 ? 'var(--income)' : 'var(--expense)' }}>
              ₺ {netDifference.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
            </div>
          </div>
        </div>
      )}

      {/* Ana sekme: Planlı Ödemeler / KK Taksitleri */}
      <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-3)', flexShrink: 0 }}>
        <button className={`btn btn-sm ${typeTab === 'PLANNED' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => { setTypeTab('PLANNED'); setFilter('PENDING') }}>
          🔁 Planlı Ödemeler {plannedItems.length + closedStatements.length > 0 && <span style={{ opacity: 0.7, marginLeft: 4 }}>({plannedItems.length + closedStatements.length})</span>}
        </button>
        <button className={`btn btn-sm ${typeTab === 'CC_INSTALLMENTS' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => { setTypeTab('CC_INSTALLMENTS'); setFilter('ALL') }}>
          💳 KK Taksitleri {ccItems.length > 0 && <span style={{ opacity: 0.7, marginLeft: 4 }}>({ccItems.length})</span>}
        </button>
      </div>

      {/* Durum filtresi */}
      <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-4)', flexShrink: 0 }}>
        {['ALL', 'PENDING', 'PAID', 'OVERDUE', 'CANCELLED'].map(f => (
          <button key={f} className={`btn btn-sm ${filter === f ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilter(f)}>
            {f === 'ALL' ? t('common.all') : t('status.' + f, f.charAt(0) + f.slice(1).toLowerCase())}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="loading-state"><div className="spinner" /></div>
      ) : sorted.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🔁</div>
          <div className="empty-state-title">{t('plannedPayments.noPayments')}</div>
          <div className="empty-state-desc">{t('plannedPayments.noPaymentsDesc')}</div>
          {typeTab === 'PLANNED' && <button className="btn btn-primary" onClick={openNew}>{t('plannedPayments.newPayment')}</button>}
        </div>
      ) : (
        <div className="card" style={{ padding: 0, flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <div style={{ overflow: 'auto', flex: 1 }}>
            <table className="data-table">
              <thead style={{ position: 'sticky', top: 0, zIndex: 2, background: 'var(--bg-card)' }}>
                <tr>
                  <th style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('title')}>
                    Açıklama <SortIndicator field="title" />
                  </th>
                  <th>Kaynak</th>
                  <th>{t('common.type')}</th>
                  <th>{t('plannedPayments.form.frequency')}</th>
                  <th style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('planned_date')}>
                    {t('plannedPayments.form.startDate')} <SortIndicator field="planned_date" />
                  </th>
                  <th>Gerçekleşme</th>
                  <th style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('due_date')}>
                    {t('plannedPayments.form.dueDate')} <SortIndicator field="due_date" />
                  </th>
                  <th style={{ textAlign: 'right', cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('amount')}>
                    {t('common.amount')} <SortIndicator field="amount" />
                  </th>
                  <th style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('status')}>
                    {t('common.status')} <SortIndicator field="status" />
                  </th>
                  <th style={{ width: 120 }}></th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((item: any) => (
                  <tr key={item.id}>
                    <td style={{ fontWeight: 500 }}>{item.title}</td>
                    <td>{SOURCE_LABEL(item)}</td>
                    <td>
                      {item._isStatement ? (
                        <span className="badge badge-neutral">Ekstre</span>
                      ) : (
                        <span className={`badge ${item.payment_type === 'INCOME' ? 'badge-confirmed' : 'badge-expense'}`}>
                          {item.payment_type === 'INCOME' ? '↑ Gelir' : '↓ Gider'}
                        </span>
                      )}
                    </td>
                    <td>
                      {item._isStatement ? (
                        '—'
                      ) : (
                        <span className="badge badge-neutral">{RECURRENCE_LABELS[item.recurrence_rule] || item.recurrence_rule}</span>
                      )}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)' }}>{item.planned_date}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)' }}>
                      {item._isStatement ? (
                        '—'
                      ) : (
                        (item.status === 'PAID' || item.status === 'PARTIALLY_PAID') && item.updated_at
                          ? new Date(item.updated_at).toISOString().slice(0, 10)
                          : '—'
                      )}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)' }}>{item.due_date || '—'}</td>
                    <td className="text-right">
                      <span className={`amount ${item._isStatement || item.payment_type === 'EXPENSE' ? 'negative' : 'positive'}`}>
                        {item.currency} {fmt(Number(item.amount))}
                      </span>
                    </td>
                    <td><span className={`badge ${STATUS_CLASS[item.status] || 'badge-neutral'}`}>{t('status.' + item.status, item.status) as string}</span></td>
                    <td style={{ display: 'flex', gap: 4, flexWrap: 'nowrap' }}>
                      {(item.status === 'PENDING' || item.status === 'PARTIALLY_PAID') && (
                        <button
                          className="btn btn-sm btn-success"
                          style={{ fontSize: 11, padding: '2px 8px', whiteSpace: 'nowrap' }}
                          onClick={(e) => openPay(item, e)}
                          title="Öde"
                        >✓ Öde</button>
                      )}
                      {!item._isStatement && !item.credit_card_purchase_id && !item.loan_id && (
                        <button className="btn btn-ghost btn-icon btn-sm" onClick={() => openEdit(item)} title="Düzenle">✎</button>
                      )}
                      {!item._isStatement && !item.credit_card_purchase_id && !item.loan_id && (
                        <button
                          className="btn btn-ghost btn-icon btn-sm"
                          style={{ color: canDelete(item) ? 'var(--expense)' : 'var(--text-tertiary)', opacity: canDelete(item) ? 1 : 0.4, cursor: canDelete(item) ? 'pointer' : 'not-allowed' }}
                          onClick={(e) => canDelete(item) && confirmDelete(item.id, e)}
                          title={canDelete(item) ? 'Sil' : '5 günlük silme süresi doldu'}
                          disabled={!canDelete(item)}
                        >✕</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Create / Edit Modal */}
      {showModal && (
        <div className="modal-backdrop" onClick={e => e.target === e.currentTarget && setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">{editing ? 'Ödeme Düzenle' : t('plannedPayments.newPayment')}</span>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {formError && <div className="alert alert-danger" style={{ marginBottom: 'var(--space-4)' }}>{formError}</div>}
                <div className="form-grid">
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label className="form-label">{t('plannedPayments.form.title')} <span className="required">*</span></label>
                    <input className="form-input" required value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} autoFocus />
                  </div>
                  <div className="form-group">
                    <label className="form-label">{t('plannedPayments.form.paymentType')} <span className="required">*</span></label>
                    <select className="form-select" value={form.payment_type} onChange={e => setForm({ ...form, payment_type: e.target.value })} disabled={!!editing}>
                      <option value="EXPENSE">{t('transactions.expense')}</option>
                      <option value="INCOME">{t('transactions.income')}</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">{t('plannedPayments.form.frequency')} <span className="required">*</span></label>
                    <select className="form-select" value={form.recurrence_rule} onChange={e => setForm({ ...form, recurrence_rule: e.target.value })} disabled={!!editing}>
                      {Object.entries(RECURRENCE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">{t('common.amount')} <span className="required">*</span></label>
                    <input className="form-input" type="number" step="0.01" min="0.01" required value={form.amount}
                      onChange={e => setForm({ ...form, amount: e.target.value })} placeholder="0.00" />
                  </div>
                  <div className="form-group">
                    <label className="form-label">{t('common.currency')}</label>
                    <select className="form-select" value={form.currency} onChange={e => setForm({ ...form, currency: e.target.value })} disabled={!!editing}>
                      {['TRY', 'USD', 'EUR', 'GBP'].map(c => <option key={c}>{c}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">{t('plannedPayments.form.startDate')} <span className="required">*</span></label>
                    <input className="form-input" type="date" required value={form.planned_date}
                      onChange={e => setForm({ ...form, planned_date: e.target.value })} />
                  </div>
                  {form.recurrence_rule !== 'NONE' && !editing && (
                    <div className="form-group">
                      <label className="form-label">Tekrar Bitiş Tarihi <span className="required">*</span></label>
                      <input className="form-input" type="date" required={form.recurrence_rule !== 'NONE'}
                        min={form.planned_date}
                        value={form.recurrence_end_date}
                        onChange={e => setForm({ ...form, recurrence_end_date: e.target.value })} />
                    </div>
                  )}
                  <div className="form-group">
                    <label className="form-label">{t('plannedPayments.form.dueDate')}</label>
                    <input className="form-input" type="date" value={form.due_date}
                      onChange={e => setForm({ ...form, due_date: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">{t('plannedPayments.form.account')} <span className="required">*</span></label>
                    <select className="form-select" value={form.account_id} onChange={e => setForm({ ...form, account_id: e.target.value })}>
                      <option value="">Seçiniz...</option>
                      {accounts.filter((a: any) => a.currency === form.currency).map((a: any) => <option key={a.id} value={a.id}>{a.name}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">{t('plannedPayments.form.category')} <span className="required">*</span></label>
                    <select className="form-select" value={form.category_id} onChange={e => setForm({ ...form, category_id: e.target.value })}>
                      <option value="">Seçiniz...</option>
                      {categories.filter((c: any) => c.category_type === form.payment_type).map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </select>
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label className="form-label">{t('common.notes')}</label>
                    <textarea className="form-input" rows={2} value={form.notes}
                      onChange={e => setForm({ ...form, notes: e.target.value })} placeholder={t('common.optional') as string} />
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>{t('common.cancel')}</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? <><span className="spinner spinner-sm" /> {t('common.saving')}</> : (editing ? t('common.save') : t('plannedPayments.newPayment'))}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Pay Modal — Planlı ödemeler ve ekstreler için */}
      {showPayModal && payingItem && (
        <div className="modal-backdrop" onClick={() => setShowPayModal(false)} style={{ zIndex: 110 }}>
          <div className="modal modal-sm" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">✓ Ödeme Yap</span>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowPayModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              {payError && <div className="alert alert-danger" style={{ marginBottom: 'var(--space-3)' }}>{payError}</div>}
              <p style={{ marginBottom: 'var(--space-3)', fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
                <strong>{payingItem.title}</strong>
              </p>
              <div className="form-group">
                <label className="form-label">Ödeme Hesabı <span className="required">*</span></label>
                <select className="form-select" value={payAccountId} onChange={e => setPayAccountId(e.target.value)} autoFocus>
                  <option value="">— Hesap seçin —</option>
                  {paymentAccounts.map((a: any) => (
                    <option key={a.id} value={a.id}>{a.name} ({a.currency})</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Tutar <span className="required">*</span></label>
                <input className="form-input" type="number" step="0.01" min="0" value={payAmount} onChange={e => setPayAmount(e.target.value)} />
              </div>
              {!payingItem._isStatement && (
                <div className="form-group">
                  <label className="form-label">Ödeme Tarihi</label>
                  <input className="form-input" type="date" value={payDate} onChange={e => setPayDate(e.target.value)} />
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowPayModal(false)}>Vazgeç</button>
              <button className="btn btn-primary" onClick={handlePay} disabled={paying}>
                {paying ? <><span className="spinner spinner-sm" /> İşleniyor...</> : '✓ Ödemeyi Gerçekleştir'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="modal-backdrop" onClick={() => setShowDeleteModal(false)} style={{ zIndex: 110 }}>
          <div className="modal modal-sm" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">Sil</span>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowDeleteModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              {deleteError && <div className="alert alert-danger" style={{ marginBottom: 'var(--space-3)' }}>{deleteError}</div>}
              <p>Bu ödemeyi silmek istediğinize emin misiniz? Bu işlem geri alınamaz.</p>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowDeleteModal(false)}>İptal</button>
              <button className="btn btn-danger" onClick={handleDelete} disabled={deleting}>
                {deleting ? <><span className="spinner spinner-sm" /> Siliniyor...</> : 'Sil'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
