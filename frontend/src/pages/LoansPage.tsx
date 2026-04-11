import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { loansApi, accountsApi, categoriesApi } from '../api/umay'
import { CreditCardIcon, BankIcon, DeleteIcon, CloseIcon } from '../components/Icons'

function Modal({ open, onClose, children }: { open: boolean; onClose: () => void; children: React.ReactNode }) {
  if (!open) return null
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>{children}</div>
    </div>
  )
}

const STATUS_CLASS: Record<string, string> = {
  ACTIVE: 'badge-confirmed', PAID_OFF: 'badge-draft',
  DEFAULTED: 'badge-expense', RESTRUCTURED: 'badge-warning',
  CANCELLED: 'badge-draft',
}

export function LoansPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [loans, setLoans] = useState<any[]>([])
  const [accounts, setAccounts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [saving, setSaving] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [installments, setInstallments] = useState<Record<string, any[]>>({})
  
  // Payment Modal State
  const [payModal, setPayModal] = useState<{ open: boolean; loan?: any, inst?: any }>({ open: false })
  const [payAccount, setPayAccount] = useState('')
  const [paying, setPaying] = useState(false)
  const [categories, setCategories] = useState<any[]>([])

  // Faiz ayarları
  const [interestType, setInterestType] = useState<'none' | 'discount' | 'late'>('none')
  const [interestInputMode, setInterestInputMode] = useState<'rate' | 'amount'>('amount')
  const [interestValue, setInterestValue] = useState('')
  const [lateInterestCategoryId, setLateInterestCategoryId] = useState('')

  // Early Close Modal State
  const [earlyCloseModal, setEarlyCloseModal] = useState<{ open: boolean; loan?: any }>({ open: false })
  const [earlyCloseAmount, setEarlyCloseAmount] = useState('')
  const [earlyCloseAccount, setEarlyCloseAccount] = useState('')
  const [earlyClosing, setEarlyClosing] = useState(false)

  const defaultForm = {
    name: '', loader_name: '', principal: '', disbursed_amount: '', fees: '0',
    term_months: '', payment_day: '1', installment_amount: '',
    start_date: new Date().toISOString().slice(0, 10),
    currency: 'TRY', target_account_id: '', category_id: '', notes: '',
  }
  const [form, setForm] = useState(defaultForm)

  const load = () => {
    setLoading(true)
    Promise.allSettled([
      loansApi.list({ skip: 0, limit: 100 }),
      accountsApi.list({ skip: 0, limit: 100 }),
      categoriesApi.list({ skip: 0, limit: 100 }),
    ]).then(([l, a, c]) => {
      if (l.status === 'fulfilled') setLoans(l.value.data)
      if (a.status === 'fulfilled') setAccounts(a.value.data)
      if (c.status === 'fulfilled') setCategories(c.value.data)
    }).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  // KPI Calculations - correct formulas
  const activeLoans = loans.filter(l => l.status === 'ACTIVE')
  const totalPrincipal = activeLoans.reduce((s, l) => s + Number(l.principal || 0), 0)
  const totalRemaining = activeLoans.reduce((s, l) => s + Number(l.remaining_balance || 0), 0)
  const totalPlannedPayment = activeLoans.reduce((s, l) => s + ((Number(l.term_months || 0) * Number(l.installment_amount || 0)) + Number(l.fees || 0)), 0)

  const toggleInstallments = async (loanId: string) => {
    if (expandedId === loanId) { setExpandedId(null); return }
    setExpandedId(loanId)
    if (!installments[loanId]) {
      const res = await loansApi.installments(loanId).catch(() => null)
      if (res) {
        const data = Array.isArray(res.data) ? res.data : (res.data?.items || [])
        setInstallments(prev => ({ ...prev, [loanId]: data }))
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (!form.category_id) { alert('Lütfen bir kategori seçin'); setSaving(false); return }
      await loansApi.create({
        lender_name: form.loader_name || form.name,
        loan_purpose: form.name,
        principal: parseFloat(form.principal),
        disbursed_amount: parseFloat(form.disbursed_amount),
        fees: parseFloat(form.fees) || 0,
        term_months: parseInt(form.term_months),
        payment_day: parseInt(form.payment_day),
        installment_amount: parseFloat(form.installment_amount),
        target_account_id: form.target_account_id,
        category_id: form.category_id,
        start_date: form.start_date,
        currency: form.currency,
        notes: form.notes || undefined,
      })
      setShowModal(false)
      setForm(defaultForm)
      load()
    } catch (err: any) {
      console.error(err)
      const msg = err?.response?.data?.detail 
        ? (Array.isArray(err.response.data.detail) ? err.response.data.detail[0]?.msg : err.response.data.detail)
        : (err?.response?.data?.error?.message || t('common.error'))
      alert(msg)
    } finally { setSaving(false) }
  }

  const handleDelete = async (loanId: string) => {
    if (!window.confirm(t('loans.deleteConfirm', 'Bu krediyi ve buna bağlı tüm kayıtları (borç hesabı, taksit planları, açılış hareketleri) tamamen silmek istediğinize emin misiniz?'))) return
    try {
      await loansApi.delete(loanId)
      load()
    } catch (err: any) {
      console.error(err)
      const msg = err?.response?.data?.detail || t('common.error')
      alert(msg)
    }
  }

  const handlePayInstallment = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!payAccount || !payModal.loan || !payModal.inst) return
    setPaying(true)
    try {
      const baseAmount = payModal.inst.total_amount
      const interestAmount = interestValue ? parseFloat(interestValue) : 0
      const calculatedInterest = interestInputMode === 'rate'
        ? (baseAmount * interestAmount) / 100
        : interestAmount

      const payload: any = {
        amount: baseAmount,
        source_account_id: payAccount,
      }
      if (interestType === 'discount' && calculatedInterest > 0) {
        payload.interest_discount = calculatedInterest
      }
      if (interestType === 'late' && calculatedInterest > 0) {
        payload.late_interest = calculatedInterest
        if (lateInterestCategoryId) payload.late_interest_category_id = lateInterestCategoryId
      }

      await loansApi.payInstallment(payModal.loan.id, payModal.inst.id, payload)
      setPayModal({ open: false })
      setPayAccount('')
      setInterestType('none'); setInterestValue(''); setLateInterestCategoryId('')

      const res = await loansApi.installments(payModal.loan.id).catch(() => null)
      if (res) {
        const data = Array.isArray(res.data) ? res.data : (res.data?.items || [])
        setInstallments(prev => ({ ...prev, [payModal.loan.id]: data }))
      }
      load()
    } catch (err: any) {
      console.error(err)
      const msg = err?.response?.data?.detail?.message || err?.response?.data?.detail || t('common.error')
      alert(msg)
    } finally { setPaying(false) }
  }

  const handleEarlyClose = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!earlyCloseAccount || !earlyCloseAmount || !earlyCloseModal.loan) return
    setEarlyClosing(true)
    try {
      await loansApi.earlyClose(earlyCloseModal.loan.id, {
        amount: parseFloat(earlyCloseAmount),
        source_account_id: earlyCloseAccount,
      })
      setEarlyCloseModal({ open: false })
      setEarlyCloseAmount('')
      setEarlyCloseAccount('')
      load()
    } catch (err: any) {
      console.error(err)
      const msg = err?.response?.data?.detail || t('common.error')
      alert(msg)
    } finally { setEarlyClosing(false) }
  }

  // Filter accounts for payments (Bank + Cash)
  const paymentAccounts = accounts.filter(a => a.account_type === 'BANK' || a.account_type === 'CASH')

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">{t('loans.title')}</h1>
          <p className="page-subtitle">{activeLoans.length} {t('loans.activeLoans', 'aktif kredi').toLowerCase()}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>{t('loans.newLoan')}</button>
      </div>

      {/* KPI */}
      {loans.length > 0 && (
        <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 'var(--space-6)' }}>
          <div className="stat-card">
            <div className="stat-card-label">{t('loans.totalPrincipal', 'Toplam Anapara (Başvurulan)')}</div>
            <div className="stat-card-value">₺ {totalPrincipal.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-label">{t('loans.totalPlannedPayment', 'Toplam Planlanan Ödeme')}</div>
            <div className="stat-card-value">₺ {totalPlannedPayment.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-label">{t('loans.remainingDebt', 'Toplam Kalan Borç')}</div>
            <div className="stat-card-value" style={{ color: 'var(--expense)' }}>
              ₺ {totalRemaining.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-card-label">{t('loans.activeLoans')}</div>
            <div className="stat-card-value">{activeLoans.length}</div>
          </div>
        </div>
      )}

      {/* List */}
      {loading ? (
        <div className="loading-state"><div className="spinner" /></div>
      ) : loans.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><CreditCardIcon size={48} /></div>
          <div className="empty-state-title">{t('loans.noLoans')}</div>
          <div className="empty-state-desc">{t('loans.noLoansDesc')}</div>
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>+ {t('common.add')}</button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {loans.map((loan: any) => {
            const totalRepayment = (Number(loan.term_months || 0) * Number(loan.installment_amount || 0)) + Number(loan.fees || 0)
            const remainingToPay = loan.remaining_balance || 0
            const paidAmount = loan.total_paid || 0
            const pct = Math.round((paidAmount / Math.max(totalRepayment, 1)) * 100)
            const hasInstallmentPayments = (loan.total_paid || 0) > (loan.fees || 0)
            const isActive = loan.status === 'ACTIVE'

            return (
              <div key={loan.id} className="card" style={{ cursor: 'pointer' }}
                onClick={() => navigate(`/loans/${loan.id}`)}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
                      <span style={{ fontWeight: 600, fontSize: 'var(--font-size-md)' }}>{loan.loan_purpose || loan.lender_name}</span>
                      <span className={`badge ${STATUS_CLASS[loan.status] || 'badge-neutral'}`}>{t('status.' + loan.status, loan.status) as string}</span>
                    </div>
                    {loan.lender_name && (
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 'var(--space-3)' }}>
                        <BankIcon size={13} /> {loan.lender_name}
                      </div>
                    )}
                    
                    <div style={{ marginBottom: 'var(--space-3)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 4 }}>
                        <span>% {pct} {t('loans.paid', 'Ödendi')}</span>
                        <span>{t('loans.remainingDebt', 'Kalan Borç')}</span>
                      </div>
                      <div style={{ height: 6, background: 'var(--bg-elevated)', borderRadius: 3, overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${pct}%`, background: 'var(--income)', borderRadius: 3, transition: 'width 0.4s' }} />
                      </div>
                    </div>
                    
                    <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap', marginTop: 'var(--space-4)' }}>
                      <div style={{ flex: '1 1 120px' }}>
                        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>{t('loans.appliedAmount', 'Başvurulan Kredi')}</div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 'var(--font-size-sm)' }}>
                          {loan.currency} {Number(loan.principal || 0).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
                        </div>
                      </div>
                      <div style={{ flex: '1 1 120px' }}>
                        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>{t('loans.totalRepayment', 'Geri Ödeme Tutarı')}</div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 'var(--font-size-sm)' }}>
                          {loan.currency} {totalRepayment.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
                        </div>
                      </div>
                      <div style={{ flex: '1 1 120px' }}>
                        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>{t('loans.remainingBalance', 'Kalan Borç')}</div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 'var(--font-size-sm)', color: 'var(--expense)' }}>
                          {loan.currency} {Number(loan.remaining_balance || 0).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
                        </div>
                      </div>
                      {loan.fees > 0 && (
                        <div style={{ flex: '1 1 120px' }}>
                          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>{t('loans.fees', 'Masraf')}</div>
                          <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 'var(--font-size-sm)', color: 'var(--warning)' }}>
                            {loan.currency} {Number(loan.fees || 0).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div style={{ display: 'flex', gap: 'var(--space-2)', flexShrink: 0, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                    {isActive && (
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ color: 'var(--warning)' }}
                        onClick={(e) => {
                          e.stopPropagation()
                          setEarlyCloseModal({ open: true, loan })
                          setEarlyCloseAmount(String(loan.remaining_balance || 0))
                        }}
                      >
                        {t('loans.earlyClose', 'Erken Kapat')}
                      </button>
                    )}
                    {!hasInstallmentPayments && (
                      <button className="btn btn-secondary btn-sm" style={{ color: 'var(--expense)' }}
                        onClick={(e) => { e.stopPropagation(); handleDelete(loan.id) }}>
                        <DeleteIcon size={13} /> {t('common.delete')}
                      </button>
                    )}
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={(e) => { e.stopPropagation(); navigate(`/loans/${loan.id}`) }}
                    >
                      → {t('loans.showInstallments', 'Taksitler')}
                    </button>
                  </div>
                </div>

                {expandedId === loan.id && (
                  <div style={{ marginTop: 'var(--space-4)', borderTop: '1px solid var(--border)', paddingTop: 'var(--space-4)' }}>
                    {!installments[loan.id] ? (
                      <div style={{ textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)' }}>{t('common.loading')}</div>
                    ) : installments[loan.id].length === 0 ? (
                      <div style={{ textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)' }}>{t('common.noData')}</div>
                    ) : (
                      <table className="data-table" style={{ fontSize: 'var(--font-size-xs)' }}>
                        <thead>
                          <tr>
                            <th>{t('loans.installmentNo', 'No')}</th>
                            <th>{t('loans.dueDate', 'Vade Tarihi')}</th>
                            <th style={{ textAlign: 'right' }}>{t('common.amount', 'Tutar')}</th>
                            <th>{t('common.status', 'Durum')}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {installments[loan.id].map((inst: any, idx: number) => (
                            <tr key={inst.id || idx}>
                              <td>{inst.installment_number || idx + 1}</td>
                              <td style={{ fontFamily: 'var(--font-mono)' }}>{inst.due_date}</td>
                              <td className="text-right" style={{ fontFamily: 'var(--font-mono)' }}>
                                {loan.currency} {inst.total_amount?.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
                              </td>
                              <td>
                                <span className={`badge ${inst.status === 'PAID' ? 'badge-confirmed' : 'badge-pending'}`} style={{ marginRight: 8 }}>
                                  {inst.status === 'PAID' ? t('status.PAID', 'Ödendi') : t('loans.due', 'Bekliyor')}
                                </span>
                                {inst.status !== 'PAID' && isActive && (
                                  <button 
                                    className="btn btn-primary btn-sm" 
                                    style={{ padding: '2px 8px', fontSize: '10px' }}
                                    onClick={() => { setPayModal({ open: true, loan, inst }); setPayAccount(''); setInterestType('none'); setInterestValue(''); setInterestInputMode('amount'); setLateInterestCategoryId('') }}
                                  >
                                    {t('loans.pay', 'Öde')}
                                  </button>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Pay Modal */}
      <Modal open={payModal.open} onClose={() => setPayModal({ open: false })}>
        <div className="modal-header">
          <div className="modal-title">Taksit Öde</div>
          <button className="modal-close" onClick={() => setPayModal({ open: false })}><CloseIcon size={14} /></button>
        </div>
        <form onSubmit={handlePayInstallment}>
          <div className="modal-body">
            {/* Taksit özeti */}
            {payModal.inst && (() => {
              const baseAmount: number = payModal.inst.total_amount
              const dueDate = payModal.inst.due_date
              const today = new Date().toISOString().slice(0, 10)
              const isLate = dueDate < today
              const isEarly = dueDate > today

              const interestAmount = parseFloat(interestValue) || 0
              const calculatedInterest = interestInputMode === 'rate'
                ? (baseAmount * interestAmount) / 100
                : interestAmount
              const finalAmount = interestType === 'discount'
                ? baseAmount - calculatedInterest
                : interestType === 'late'
                  ? baseAmount + calculatedInterest
                  : baseAmount

              return (
                <>
                  <div style={{ padding: 'var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', marginBottom: 'var(--space-4)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>
                          Taksit {payModal.inst.installment_number}/{payModal.loan?.term_months} · Vade: {dueDate}
                          {isLate && <span style={{ color: 'var(--expense)', marginLeft: 6, fontWeight: 600 }}>GECİKMİŞ</span>}
                          {isEarly && <span style={{ color: 'var(--income)', marginLeft: 6, fontWeight: 600 }}>ERKEN ÖDEME</span>}
                        </div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 'var(--font-size-lg)' }}>
                          {payModal.loan?.currency} {baseAmount.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Ödemenin Çıkacağı Hesap *</label>
                    <select className="form-input" required value={payAccount} onChange={e => setPayAccount(e.target.value)}>
                      <option value="">— Hesap Seçin —</option>
                      {paymentAccounts.map((a: any) => <option key={a.id} value={a.id}>{a.name} (Bakiye: {a.current_balance})</option>)}
                    </select>
                  </div>

                  {/* Faiz bölümü */}
                  <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: 'var(--space-3)', marginTop: 'var(--space-2)' }}>
                    <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, marginBottom: 'var(--space-3)', color: 'var(--text-secondary)' }}>
                      Faiz Ayarı
                    </div>
                    <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-3)' }}>
                      {[
                        { val: 'none', label: 'Yok' },
                        { val: 'discount', label: '↓ Faiz İndirimi (Erken)' },
                        { val: 'late', label: '↑ Gecikme Faizi (Geç)' },
                      ].map(opt => (
                        <button type="button" key={opt.val}
                          className={`btn btn-sm ${interestType === opt.val ? (opt.val === 'late' ? 'btn-danger' : opt.val === 'discount' ? 'btn-success' : 'btn-primary') : 'btn-secondary'}`}
                          style={{ fontSize: 12 }}
                          onClick={() => { setInterestType(opt.val as any); setInterestValue('') }}>
                          {opt.label}
                        </button>
                      ))}
                    </div>

                    {interestType !== 'none' && (
                      <>
                        <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
                          <button type="button"
                            className={`btn btn-sm ${interestInputMode === 'amount' ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={() => setInterestInputMode('amount')}>Tutar ({payModal.loan?.currency})</button>
                          <button type="button"
                            className={`btn btn-sm ${interestInputMode === 'rate' ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={() => setInterestInputMode('rate')}>Oran (%)</button>
                        </div>
                        <div className="form-group" style={{ marginBottom: 'var(--space-2)' }}>
                          <input className="form-input" type="number" step="0.01" min="0"
                            placeholder={interestInputMode === 'rate' ? 'Faiz oranı (%)' : `Tutar (${payModal.loan?.currency})`}
                            value={interestValue} onChange={e => setInterestValue(e.target.value)} />
                        </div>
                        {interestType === 'late' && (
                          <div className="form-group" style={{ marginBottom: 0 }}>
                            <label className="form-label" style={{ fontSize: 'var(--font-size-xs)' }}>Gecikme Faizi Kategorisi</label>
                            <select className="form-select" value={lateInterestCategoryId} onChange={e => setLateInterestCategoryId(e.target.value)}>
                              <option value="">— Kategori Seç (opsiyonel) —</option>
                              {categories.filter((c: any) => c.category_type === 'EXPENSE' || c.category_type === 'TRANSFER').map((c: any) => (
                                <option key={c.id} value={c.id}>{c.name}</option>
                              ))}
                            </select>
                          </div>
                        )}
                      </>
                    )}
                  </div>

                  {/* Ödeme özeti */}
                  {interestType !== 'none' && calculatedInterest > 0 && (
                    <div style={{ marginTop: 'var(--space-3)', padding: 'var(--space-3)', background: interestType === 'discount' ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)', borderRadius: 'var(--radius-sm)', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>Asıl Taksit</span>
                        <span>{payModal.loan?.currency} {baseAmount.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: interestType === 'discount' ? 'var(--income)' : 'var(--expense)' }}>
                        <span>{interestType === 'discount' ? '− Faiz İndirimi' : '+ Gecikme Faizi'}</span>
                        <span>{interestType === 'discount' ? '-' : '+'}{payModal.loan?.currency} {calculatedInterest.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, borderTop: '1px solid var(--border)', marginTop: 4, paddingTop: 4 }}>
                        <span>Ödenecek Tutar</span>
                        <span>{payModal.loan?.currency} {finalAmount.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</span>
                      </div>
                    </div>
                  )}
                </>
              )
            })()}
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setPayModal({ open: false })}>Vazgeç</button>
            <button type="submit" className="btn btn-primary" disabled={paying}>
              {paying ? <><span className="spinner spinner-sm" /> Ödeniyor...</> : 'Ödemeyi Gerçekleştir'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Early Close Modal */}
      <Modal open={earlyCloseModal.open} onClose={() => setEarlyCloseModal({ open: false })}>
        <div className="modal-header">
          <div className="modal-title">{t('loans.earlyClose', 'Erken Kapama')}</div>
          <button className="modal-close" onClick={() => setEarlyCloseModal({ open: false })}><CloseIcon size={14} /></button>
        </div>
        <form onSubmit={handleEarlyClose}>
          <div className="modal-body">
            <div style={{ 
              padding: 'var(--space-3)', 
              background: 'var(--bg-elevated)', 
              borderRadius: 'var(--radius-md)', 
              marginBottom: 'var(--space-4)' 
            }}>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 4 }}>{t('loans.currentDebt', 'Mevcut Kalan Borç')}</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 'var(--font-size-lg)', color: 'var(--expense)' }}>
                {earlyCloseModal.loan?.currency} {earlyCloseModal.loan?.remaining_balance?.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
              </div>
            </div>
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-4)' }}>
              {t('loans.earlyCloseDesc', 'Kalan borçtan düşük tutar girerseniz, fark faiz tasarrufu (gelir) olarak kaydedilir ve kredi kapatılır.')}
            </p>
            <div className="form-group">
              <label className="form-label">{t('loans.earlyCloseAmount', 'Erken Kapama Tutarı')} *</label>
              <input className="form-input" type="number" step="0.01" min="0.01" required
                max={earlyCloseModal.loan?.remaining_balance || 999999999}
                value={earlyCloseAmount} onChange={e => setEarlyCloseAmount(e.target.value)} />
            </div>
            {earlyCloseModal.loan && parseFloat(earlyCloseAmount) > 0 && parseFloat(earlyCloseAmount) < (earlyCloseModal.loan.remaining_balance || 0) && (
              <div style={{ 
                padding: 'var(--space-2) var(--space-3)', 
                background: 'rgba(34,197,94,0.1)', 
                borderRadius: 'var(--radius-sm)',
                fontSize: 'var(--font-size-sm)',
                color: 'var(--income)',
                marginBottom: 'var(--space-3)'
              }}>
                {t('loans.interestSavings', 'Faiz Tasarrufu')}: {earlyCloseModal.loan.currency} {((earlyCloseModal.loan.remaining_balance || 0) - parseFloat(earlyCloseAmount)).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
              </div>
            )}
            <div className="form-group">
              <label className="form-label">{t('loans.paymentAccount', 'Ödemenin Çıkacağı Hesap')} *</label>
              <select className="form-input" required value={earlyCloseAccount} onChange={e => setEarlyCloseAccount(e.target.value)}>
                <option value="">— {t('common.selectAccount', 'Hesap Seçin')} —</option>
                {paymentAccounts.map((a: any) => <option key={a.id} value={a.id}>{a.name} ({t('common.balance', 'Bakiye')}: {a.current_balance})</option>)}
              </select>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setEarlyCloseModal({ open: false })}>{t('common.cancel')}</button>
            <button type="submit" className="btn btn-primary" disabled={earlyClosing} style={{ background: 'var(--warning)' }}>
              {earlyClosing ? <><span className="spinner spinner-sm" /> {t('loans.closing', 'Kapatılıyor')}</> : t('loans.closeNow', 'Krediyi Kapat')}
            </button>
          </div>
        </form>
      </Modal>

      {/* Create Modal */}
      <Modal open={showModal} onClose={() => setShowModal(false)}>
        <div className="modal-header">
          <div className="modal-title">{t('loans.newLoan', 'Yeni Kredi Oluştur')}</div>
          <button className="modal-close" onClick={() => setShowModal(false)}><CloseIcon size={14} /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="form-grid">
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label className="form-label">{t('loans.form.purpose', 'Kredi Açıklaması / Adı')} *</label>
                <input className="form-input" required placeholder={t('loans.form.purposePlaceholder', 'İhtiyaç Kredisi vb.') as string}
                  value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">{t('loans.form.lender', 'Banka / Kurum')} *</label>
                <input className="form-input" required placeholder={t('loans.form.lenderPlaceholder', 'Banka Adı') as string}
                  value={form.loader_name} onChange={e => setForm({ ...form, loader_name: e.target.value })} />
              </div>
              
              <div className="form-group">
                <label className="form-label">{t('loans.form.principal', 'Başvurulan Kredi Tutarı')} *</label>
                <input className="form-input" type="number" step="0.01" min="0.01" required
                  value={form.principal} onChange={e => {
                    const principal = e.target.value
                    const disbursed = parseFloat(form.disbursed_amount) || 0
                    const fees = Math.max(0, (parseFloat(principal) || 0) - disbursed)
                    setForm({ ...form, principal, fees: fees > 0 ? fees.toFixed(2) : '0' })
                  }} />
              </div>
              <div className="form-group">
                <label className="form-label">{t('loans.form.disbursed', 'Hesaba Geçen Net Tutar')} *</label>
                <input className="form-input" type="number" step="0.01" min="0.01" required
                  value={form.disbursed_amount} onChange={e => {
                    const disbursed = e.target.value
                    const principal = parseFloat(form.principal) || 0
                    const fees = Math.max(0, principal - (parseFloat(disbursed) || 0))
                    setForm({ ...form, disbursed_amount: disbursed, fees: fees > 0 ? fees.toFixed(2) : '0' })
                  }} />
              </div>
              <div className="form-group">
                <label className="form-label">{t('loans.form.targetAccount', 'Paranın Yatacağı Hedef Hesap')} *</label>
                <select className="form-input" required value={form.target_account_id} onChange={e => setForm({ ...form, target_account_id: e.target.value })}>
                  <option value="">— {t('common.select', 'Seçiniz')} —</option>
                  {accounts.filter(a => a.account_type !== 'CREDIT').map((a: any) => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">{t('loans.form.fees', 'Masraf Tutarı (Gider)')}</label>
                <input className="form-input" type="number" step="0.01" min="0" required
                  value={form.fees} onChange={e => setForm({ ...form, fees: e.target.value })} />
              </div>

              <div className="form-group">
                <label className="form-label">Kategori <span className="required">*</span></label>
                <select className="form-input" required value={form.category_id} onChange={e => setForm({ ...form, category_id: e.target.value })}>
                  <option value="">— Kategori Seçin —</option>
                  {categories.filter((c: any) => c.category_type === 'EXPENSE' || c.category_type === 'TRANSFER').map((c: any) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
              
              <div className="form-group">
                <label className="form-label">{t('loans.form.termMonths', 'Taksit Sayısı (Ay)')} *</label>
                <input className="form-input" type="number" min="1" required placeholder="36"
                  value={form.term_months} onChange={e => setForm({ ...form, term_months: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">{t('loans.form.installmentAmount', 'Aylık Taksit Tutarı')} *</label>
                <input className="form-input" type="number" step="0.01" min="0.01" required
                  value={form.installment_amount} onChange={e => setForm({ ...form, installment_amount: e.target.value })} />
              </div>
              
              <div className="form-group">
                <label className="form-label">{t('loans.form.startDate', 'Başvuru Tarihi')} *</label>
                <input className="form-input" type="date" required
                  value={form.start_date} onChange={e => setForm({ ...form, start_date: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">{t('loans.form.paymentDay', 'Aylık Ödeme Günü (1-31)')} *</label>
                <input className="form-input" type="number" min="1" max="31" required
                  value={form.payment_day} onChange={e => setForm({ ...form, payment_day: e.target.value })} />
              </div>
              
              <div className="form-group">
                <label className="form-label">{t('common.currency')}</label>
                <select className="form-input" value={form.currency} onChange={e => setForm({ ...form, currency: e.target.value })}>
                  {['TRY', 'USD', 'EUR', 'GBP'].map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>{t('common.cancel')}</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? <><span className="spinner spinner-sm" /> {t('loans.creating', 'Oluşturuluyor')}</> : t('loans.createLoan', 'Krediyi Oluştur')}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
