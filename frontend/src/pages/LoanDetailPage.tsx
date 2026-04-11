import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { loansApi, accountsApi, categoriesApi } from '../api/umay'
import { BankIcon, ZapIcon, CloseIcon } from '../components/Icons'

const STATUS_CLASS: Record<string, string> = {
  ACTIVE: 'badge-confirmed', PAID_OFF: 'badge-draft',
  DEFAULTED: 'badge-expense', RESTRUCTURED: 'badge-warning',
  CANCELLED: 'badge-draft',
}

const INST_STATUS: Record<string, { label: string; cls: string }> = {
  PENDING:       { label: 'Bekliyor',   cls: 'badge-pending' },
  PAID:          { label: 'Ödendi',     cls: 'badge-confirmed' },
  OVERDUE:       { label: 'Gecikmiş',   cls: 'badge-expense' },
  PARTIALLY_PAID:{ label: 'Kısmi',      cls: 'badge-warning' },
}

export function LoanDetailPage() {
  const { loanId } = useParams<{ loanId: string }>()
  const navigate = useNavigate()

  const [loan, setLoan] = useState<any>(null)
  const [installments, setInstallments] = useState<any[]>([])
  const [accounts, setAccounts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  // Pay installment modal
  const [payModal, setPayModal] = useState<{ open: boolean; inst?: any }>({ open: false })
  const [payAccount, setPayAccount] = useState('')
  const [paying, setPaying] = useState(false)
  const [payError, setPayError] = useState('')
  const [categories, setCategories] = useState<any[]>([])

  // Faiz ayarları
  const [interestType, setInterestType] = useState<'none' | 'discount' | 'late'>('none')
  const [interestInputMode, setInterestInputMode] = useState<'rate' | 'amount'>('amount')
  const [interestValue, setInterestValue] = useState('')
  const [lateInterestCategoryId, setLateInterestCategoryId] = useState('')

  // Early close modal
  const [showEarlyClose, setShowEarlyClose] = useState(false)
  const [ecAmount, setEcAmount] = useState('')
  const [ecAccount, setEcAccount] = useState('')
  const [ecClosing, setEcClosing] = useState(false)
  const [ecError, setEcError] = useState('')

  const load = async () => {
    if (!loanId) return
    setLoading(true)
    try {
      const [lRes, iRes, aRes, cRes] = await Promise.all([
        loansApi.get(loanId),
        loansApi.installments(loanId),
        accountsApi.list({ skip: 0, limit: 100 }),
        categoriesApi.list({ skip: 0, limit: 100 }),
      ])
      setLoan(lRes.data)
      const iData = Array.isArray(iRes.data) ? iRes.data : (iRes.data?.items || [])
      setInstallments(iData)
      setAccounts(aRes.data)
      setCategories(cRes.data)
    } catch { navigate('/loans') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [loanId])

  const paymentAccounts = accounts.filter(a =>
    (a.account_type === 'BANK' || a.account_type === 'CASH') &&
    (!loan || a.currency === loan.currency)
  )

  const handlePayInstallment = async () => {
    if (!payAccount || !payModal.inst || !loan) return
    setPayError('')
    setPaying(true)
    try {
      const baseAmount = payModal.inst.total_amount
      const interestAmount = parseFloat(interestValue) || 0
      const calculatedInterest = interestInputMode === 'rate'
        ? (baseAmount * interestAmount) / 100
        : interestAmount

      const payload: any = { amount: baseAmount, source_account_id: payAccount }
      if (interestType === 'discount' && calculatedInterest > 0)
        payload.interest_discount = calculatedInterest
      if (interestType === 'late' && calculatedInterest > 0) {
        payload.late_interest = calculatedInterest
        if (lateInterestCategoryId) payload.late_interest_category_id = lateInterestCategoryId
      }

      await loansApi.payInstallment(loan.id, payModal.inst.id, payload)
      setPayModal({ open: false })
      setPayAccount('')
      setInterestType('none'); setInterestValue(''); setLateInterestCategoryId('')
      load()
    } catch (e: any) {
      setPayError(e?.response?.data?.detail?.message || e?.response?.data?.detail || 'Hata oluştu')
    } finally { setPaying(false) }
  }

  const handleEarlyClose = async () => {
    if (!ecAccount || !ecAmount || !loan) return
    setEcError('')
    setEcClosing(true)
    try {
      await loansApi.earlyClose(loan.id, {
        amount: parseFloat(ecAmount),
        source_account_id: ecAccount,
      })
      setShowEarlyClose(false)
      load()
    } catch (e: any) {
      setEcError(e?.response?.data?.error?.message || e?.response?.data?.detail || 'Hata oluştu')
    } finally { setEcClosing(false) }
  }

  if (loading) return <div className="loading-state"><div className="spinner" /></div>
  if (!loan) return null

  const installmentsTotal = (loan.term_months || 0) * (loan.installment_amount || 0)
  const totalLoanCost = installmentsTotal + Number(loan.fees || 0)
  const totalPaid = loan.total_paid || 0 // Örn: 2000 (Açılışta)
  const paidCount = installments.filter(i => i.status === 'PAID').length
  const pendingCount = installments.filter(i => i.status !== 'PAID').length
  const pct = Math.round((totalPaid / Math.max(totalLoanCost, 1)) * 100)
  const isActive = loan.status === 'ACTIVE'

  const fmt = (v: number) => Number(v).toLocaleString('tr-TR', { minimumFractionDigits: 2 })

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/loans')}>
            ← Krediler
          </button>
          <div>
            <h1 className="page-title">{loan.loan_purpose || loan.lender_name}</h1>
            <p className="page-subtitle" style={{ display: 'flex', alignItems: 'center', gap: 6 }}><BankIcon size={13} /> {loan.lender_name} · {loan.currency}</p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <span className={`badge ${STATUS_CLASS[loan.status] || 'badge-neutral'}`}>{loan.status}</span>
          {isActive && (
            <button className="btn btn-secondary btn-sm" style={{ color: 'var(--warning)' }}
              onClick={() => { setEcAmount(String(loan.remaining_balance || 0)); setShowEarlyClose(true) }}>
              <ZapIcon size={13} /> Erken Kapat
            </button>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 'var(--space-6)' }}>
        <div className="stat-card">
          <div className="stat-card-label">Kalan Borç</div>
          <div className="stat-card-value" style={{ color: 'var(--expense)', fontSize: 'var(--font-size-xl)' }}>
            {loan.currency} {fmt(loan.remaining_balance || 0)}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Aylık Taksit</div>
          <div className="stat-card-value" style={{ fontSize: 'var(--font-size-xl)' }}>
            {loan.currency} {fmt(loan.installment_amount || 0)}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Ödenen / Kalan Taksit</div>
          <div className="stat-card-value" style={{ fontSize: 'var(--font-size-xl)' }}>
            <span style={{ color: 'var(--income)' }}>{paidCount}</span>
            <span style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}> / </span>
            <span style={{ color: 'var(--warning)' }}>{pendingCount}</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">İlerleme</div>
          <div className="stat-card-value" style={{ fontSize: 'var(--font-size-xl)' }}>% {pct}</div>
          <div style={{ height: 4, background: 'var(--bg-elevated)', borderRadius: 2, marginTop: 8 }}>
            <div style={{ height: '100%', width: `${pct}%`, background: 'var(--income)', borderRadius: 2, transition: 'width 0.4s' }} />
          </div>
        </div>
      </div>

      {/* Loan Financial Breakdown */}
      <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
        <div className="card-header">
          <div className="card-title">Kredi Finansal Özeti</div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 'var(--space-4)', padding: 'var(--space-4) var(--space-6)' }}>
          
          {/* Bilgi Alanları */}
          <div style={{ padding: 'var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 4 }}>Başvurulan Kredi Tutarı</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{loan.currency} {fmt(loan.principal || 0)}</div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 2 }}>Sadece bilgi</div>
          </div>

          <div style={{ padding: 'var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 4 }}>Hesaba Geçen Net Tutar</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--income)' }}>{loan.currency} {fmt(loan.disbursed_amount || 0)}</div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 2 }}>Banka hesabına giren</div>
          </div>

          <div style={{ padding: 'var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 4 }}>Masraf</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--warning)' }}>{loan.currency} {fmt(loan.fees || 0)}</div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 2 }}>Açılışta ödenen</div>
          </div>

          {/* Hesaplama Alanları */}
          <div style={{ padding: 'var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 4 }}>Taksit Sayısı × Tutarı</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
              {loan.term_months} × {loan.currency} {fmt(loan.installment_amount || 0)}
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 2 }}>Her ayın {loan.payment_day}. günü</div>
          </div>

          <div style={{ padding: 'var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 4 }}>Taksit Toplamı</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{loan.currency} {fmt(installmentsTotal)}</div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 2 }}>{loan.term_months} taksit × {fmt(loan.installment_amount || 0)}</div>
          </div>

          <div style={{ padding: 'var(--space-3)', background: 'rgba(var(--expense-rgb,239,68,68),0.08)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(var(--expense-rgb,239,68,68),0.2)' }}>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 4 }}>Toplam Kredi Maliyeti</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 'var(--font-size-md)', color: 'var(--expense)' }}>{loan.currency} {fmt(totalLoanCost)}</div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 2 }}>Taksitler ({fmt(installmentsTotal)}) + Masraf ({fmt(loan.fees || 0)})</div>
          </div>

          <div style={{ padding: 'var(--space-3)', background: 'rgba(34,197,94,0.08)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(34,197,94,0.2)' }}>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 4 }}>Açılışta Yapılan Ödeme</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 'var(--font-size-md)', color: 'var(--income)' }}>+ {loan.currency} {fmt(loan.fees || 0)}</div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 2 }}>Masraf kredi hesabına ödeme olarak kaydedildi</div>
          </div>

          <div style={{ padding: 'var(--space-3)', background: 'rgba(var(--expense-rgb,239,68,68),0.05)', borderRadius: 'var(--radius-sm)', border: '2px solid var(--expense)' }}>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 4 }}>Güncel Kalan Borç</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 'var(--font-size-lg)', color: 'var(--expense)' }}>{loan.currency} {fmt(loan.remaining_balance || 0)}</div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 2 }}>= Taksit toplamı ({fmt(installmentsTotal)})</div>
          </div>

        </div>
        
        {/* Tarih bilgileri */}
        <div style={{ display: 'flex', gap: 'var(--space-6)', padding: 'var(--space-3) var(--space-6)', borderTop: '1px solid var(--border)', flexWrap: 'wrap' }}>
          {[
            { label: 'Başlangıç Tarihi', val: loan.start_date },
            { label: 'Bitiş Tarihi', val: loan.maturity_date || '—' },
          ].map(({ label, val }) => (
            <div key={label}>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 2 }}>{label}</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 'var(--font-size-sm)' }}>{val}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Installments Table */}
      <div className="card" style={{ padding: 0 }}>
        <div className="card-header" style={{ padding: 'var(--space-4) var(--space-6)' }}>
          <div className="card-title">Taksit Planı</div>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>
            {loan.term_months} taksit · Her ayın {loan.payment_day}. günü
          </span>
        </div>
        {installments.length === 0 ? (
          <div className="empty-state" style={{ padding: 'var(--space-8)' }}>Taksit bulunamadı</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>No</th>
                <th>Vade Tarihi</th>
                <th style={{ textAlign: 'right' }}>Taksit Tutarı</th>
                <th style={{ textAlign: 'right' }}>Ödenen</th>
                <th>Durum</th>
                <th style={{ width: 90 }}></th>
              </tr>
            </thead>
            <tbody>
              {installments.map((inst: any, idx: number) => {
                const statusInfo = INST_STATUS[inst.status] || { label: inst.status, cls: 'badge-neutral' }
                const isPaid = inst.status === 'PAID'
                return (
                  <tr key={inst.id || idx} style={{ opacity: isPaid ? 0.6 : 1 }}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                      {inst.installment_number}/{loan.term_months}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{inst.due_date}</td>
                    <td className="text-right" style={{ fontFamily: 'var(--font-mono)' }}>
                      {loan.currency} {Number(inst.total_amount).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="text-right" style={{ fontFamily: 'var(--font-mono)', color: isPaid ? 'var(--income)' : 'var(--text-tertiary)' }}>
                      {Number(inst.paid_amount || 0).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
                    </td>
                    <td><span className={`badge ${statusInfo.cls}`}>{statusInfo.label}</span></td>
                    <td>
                      {!isPaid && isActive && (
                        <button
                          className="btn btn-success btn-sm"
                          style={{ fontSize: 11 }}
                          onClick={() => { setPayAccount(''); setPayError(''); setPayModal({ open: true, inst }) }}
                        >✓ Öde</button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pay Modal */}
      {payModal.open && (() => {
        const baseAmount: number = payModal.inst?.total_amount || 0
        const dueDate: string = payModal.inst?.due_date || ''
        const today = new Date().toISOString().slice(0, 10)
        const isLate = dueDate < today
        const isEarly = dueDate > today
        const interestAmt = parseFloat(interestValue) || 0
        const calcInterest = interestInputMode === 'rate' ? (baseAmount * interestAmt) / 100 : interestAmt
        const finalAmount = interestType === 'discount'
          ? baseAmount - calcInterest
          : interestType === 'late'
            ? baseAmount + calcInterest
            : baseAmount
        return (
          <div className="modal-backdrop" onClick={() => setPayModal({ open: false })} style={{ zIndex: 110 }}>
            <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 520 }}>
              <div className="modal-header">
                <span className="modal-title">Taksit Öde</span>
                <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setPayModal({ open: false })}><CloseIcon size={14} /></button>
              </div>
              <div className="modal-body">
                {payError && <div className="alert alert-danger">{payError}</div>}

                {/* Taksit özeti */}
                <div style={{ padding: 'var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', marginBottom: 'var(--space-4)' }}>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 4 }}>
                    Taksit {payModal.inst?.installment_number}/{loan.term_months} · Vade: {dueDate}
                    {isLate  && <span style={{ color: 'var(--expense)', marginLeft: 8, fontWeight: 600 }}>⚠ GECİKMİŞ</span>}
                    {isEarly && <span style={{ color: 'var(--income)',  marginLeft: 8, fontWeight: 600 }}>✓ ERKEN ÖDEME</span>}
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 'var(--font-size-lg)' }}>
                    {loan.currency} {baseAmount.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
                  </div>
                </div>

                {/* Hesap seç */}
                <div className="form-group">
                  <label className="form-label">Ödemenin Çıkacağı Hesap <span className="required">*</span></label>
                  <select className="form-select" value={payAccount} onChange={e => setPayAccount(e.target.value)} autoFocus>
                    <option value="">— Hesap Seçin —</option>
                    {paymentAccounts.map((a: any) => (
                      <option key={a.id} value={a.id}>{a.name} ({loan.currency} {Number(a.current_balance).toLocaleString('tr-TR', { minimumFractionDigits: 2 })})</option>
                    ))}
                  </select>
                </div>

                {/* Faiz bölümü */}
                <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: 'var(--space-3)' }}>
                  <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, marginBottom: 'var(--space-3)', color: 'var(--text-secondary)' }}>Faiz Ayarı</div>
                  <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-3)', flexWrap: 'wrap' }}>
                    {[
                      { val: 'none',     label: 'Yok' },
                      { val: 'discount', label: '↓ Faiz İndirimi (Erken)' },
                      { val: 'late',     label: '↑ Gecikme Faizi (Geç)' },
                    ].map(opt => (
                      <button type="button" key={opt.val}
                        className={`btn btn-sm ${interestType === opt.val
                          ? opt.val === 'late' ? 'btn-danger' : opt.val === 'discount' ? 'btn-success' : 'btn-primary'
                          : 'btn-secondary'}`}
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
                          onClick={() => setInterestInputMode('amount')}>
                          Tutar ({loan.currency})
                        </button>
                        <button type="button"
                          className={`btn btn-sm ${interestInputMode === 'rate' ? 'btn-primary' : 'btn-secondary'}`}
                          onClick={() => setInterestInputMode('rate')}>
                          Oran (%)
                        </button>
                      </div>
                      <input className="form-input" type="number" step="0.01" min="0"
                        placeholder={interestInputMode === 'rate' ? 'Faiz oranı (%)' : `Tutar (${loan.currency})`}
                        value={interestValue} onChange={e => setInterestValue(e.target.value)}
                        style={{ marginBottom: 'var(--space-2)' }} />
                      {interestType === 'late' && (
                        <div className="form-group" style={{ marginBottom: 0 }}>
                          <label className="form-label" style={{ fontSize: 'var(--font-size-xs)' }}>Gecikme Faizi Kategorisi</label>
                          <select className="form-select" value={lateInterestCategoryId} onChange={e => setLateInterestCategoryId(e.target.value)}>
                            <option value="">— Kategori Seç (opsiyonel) —</option>
                            {categories.filter((c: any) => c.category_type === 'EXPENSE').map((c: any) => (
                              <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                          </select>
                        </div>
                      )}
                    </>
                  )}
                </div>

                {/* Özet */}
                {interestType !== 'none' && calcInterest > 0 && (
                  <div style={{ marginTop: 'var(--space-3)', padding: 'var(--space-3)', background: interestType === 'discount' ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)', borderRadius: 'var(--radius-sm)', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Asıl Taksit</span>
                      <span>{loan.currency} {baseAmount.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: interestType === 'discount' ? 'var(--income)' : 'var(--expense)' }}>
                      <span>{interestType === 'discount' ? '− Faiz İndirimi' : '+ Gecikme Faizi'}</span>
                      <span>{interestType === 'discount' ? '-' : '+'}{loan.currency} {calcInterest.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, borderTop: '1px solid var(--border)', marginTop: 4, paddingTop: 4 }}>
                      <span>Ödenecek Tutar</span>
                      <span>{loan.currency} {finalAmount.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</span>
                    </div>
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button className="btn btn-secondary" onClick={() => setPayModal({ open: false })}>Vazgeç</button>
                <button className="btn btn-primary" onClick={handlePayInstallment} disabled={paying || !payAccount}>
                  {paying ? <><span className="spinner spinner-sm" /> İşleniyor...</> : '✓ Ödemeyi Gerçekleştir'}
                </button>
              </div>
            </div>
          </div>
        )
      })()}

      {/* Early Close Modal */}
      {showEarlyClose && (
        <div className="modal-backdrop" onClick={() => setShowEarlyClose(false)} style={{ zIndex: 110 }}>
          <div className="modal modal-sm" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">Erken Kapama</span>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowEarlyClose(false)}><CloseIcon size={14} /></button>
            </div>
            <div className="modal-body">
              {ecError && <div className="alert alert-danger">{ecError}</div>}
              <div style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', padding: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>Kalan Borç</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 'var(--font-size-lg)', color: 'var(--expense)' }}>
                  {loan.currency} {Number(loan.remaining_balance).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Erken Kapama Tutarı <span className="required">*</span></label>
                <input className="form-input" type="number" step="0.01" min="0.01"
                  max={loan.remaining_balance}
                  value={ecAmount} onChange={e => setEcAmount(e.target.value)} />
              </div>
              {parseFloat(ecAmount) > 0 && parseFloat(ecAmount) < (loan.remaining_balance || 0) && (
                <div style={{ background: 'var(--success-soft)', borderRadius: 'var(--radius-sm)', padding: 'var(--space-2) var(--space-3)', color: 'var(--success)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-3)' }}>
                  Faiz Tasarrufu: {loan.currency} {((loan.remaining_balance || 0) - parseFloat(ecAmount)).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
                </div>
              )}
              <div className="form-group">
                <label className="form-label">Ödemenin Çıkacağı Hesap <span className="required">*</span></label>
                <select className="form-select" value={ecAccount} onChange={e => setEcAccount(e.target.value)}>
                  <option value="">— Hesap Seçin —</option>
                  {paymentAccounts.map((a: any) => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowEarlyClose(false)}>Vazgeç</button>
              <button className="btn btn-primary" onClick={handleEarlyClose} disabled={ecClosing || !ecAccount || !ecAmount}
                style={{ background: 'var(--warning)' }}>
                {ecClosing ? <><span className="spinner spinner-sm" /> Kapatılıyor...</> : 'Krediyi Kapat'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
