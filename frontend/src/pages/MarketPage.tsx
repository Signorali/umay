import React, { useEffect, useState, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import {
  marketApi, investmentsApi, loansApi, plannedPaymentsApi,
  accountsApi, categoriesApi, obligationsApi, usersApi,
} from '../api/umay'
import { usePermissions } from '../hooks/usePermissions'
import { MarketIcon, BankIcon, InvestmentIcon, CalendarIcon, CloseIcon, UsersIcon, BuildingIcon } from '../components/Icons'

const REFRESH_INTERVAL_MS = 15_000
const MAX_PINNED = 10

const FUND_TYPES = [
  { code: 'YAT', label: 'Yatırım Fonu' },
  { code: 'EMK', label: 'Emeklilik Fonu' },
  { code: 'BYF', label: 'Borsa YF (ETF)' },
]

function applyOrder(items: any[]): any[] {
  return [...items].sort((a, b) => {
    if (a.is_pinned !== b.is_pinned) return (b.is_pinned ? 1 : 0) - (a.is_pinned ? 1 : 0)
    return (a.display_order ?? 0) - (b.display_order ?? 0)
  })
}

function Modal({ open, onClose, children }: { open: boolean; onClose: () => void; children: React.ReactNode }) {
  if (!open) return null
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>{children}</div>
    </div>
  )
}

const today = () => new Date().toISOString().slice(0, 10)

export function MarketPage() {
  const { t } = useTranslation()
  const { can } = usePermissions()
  const canView = can('market', 'view')
  const canCreate = can('market', 'create') || can('market', 'manage')
  const canDelete = can('market', 'delete') || can('market', 'manage')
  const [watchlist, setWatchlist] = useState<any[]>([])
  const [loading, setLoading]     = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [saving, setSaving]       = useState(false)
  const [form, setForm] = useState({ symbol: '', label: '', source: 'google_finance' })
  const [error, setError]         = useState('')
  const [pinned, setPinnedState]  = useState<string[]>([])
  const [mode, setMode] = useState<'normal' | 'formula' | 'fund'>('normal')

  // Formula builder
  type Term = { type: 'symbol' | 'number'; value: string }
  const emptyTerm = (): Term => ({ type: 'symbol', value: '' })
  const [terms, setTerms] = useState<Term[]>([emptyTerm(), emptyTerm()])
  const [ops, setOps] = useState<string[]>(['*'])
  const [formulaLabel, setFormulaLabel] = useState('')
  const [formulaSymbol, setFormulaSymbol] = useState('')

  // TEFAS fund search
  const [fundQuery, setFundQuery] = useState('')
  const [fundType, setFundType] = useState('YAT')
  const [fundResults, setFundResults] = useState<any[]>([])
  const [fundSearching, setFundSearching] = useState(false)
  const fundSearchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Action modal (Al / Sat / Borç / Alacak / Plan)
  const [actionItem, setActionItem] = useState<any | null>(null)
  const [actionType, setActionType] = useState<'buy' | 'sell' | 'borrow' | 'lend' | 'plan' | null>(null)
  const [actionSaving, setActionSaving] = useState(false)
  const [actionError, setActionError] = useState('')
  const [actionSuccess, setActionSuccess] = useState('')

  // Buy/Sell form
  const [portfolios, setPortfolios] = useState<any[]>([])
  const [txForm, setTxForm] = useState({
    portfolio_id: '', quantity: '', price: '', commission: '0', date: today(), notes: '',
  })

  // Obligation (Borç / Alacak) form
  const [systemUsers, setSystemUsers] = useState<any[]>([])
  const [obligForm, setObligForm] = useState({
    quantity: '', price_per_unit: '', currency: 'TRY',
    counterparty_type: 'EXTERNAL' as 'EXTERNAL' | 'USER',
    counterparty_user_id: '',
    counterparty_name: '',
    due_date: '',
    notes: '',
  })

  // Borrow form (finans borç — kredi)
  const [accounts, setAccounts] = useState<any[]>([])
  const [loanForm, setLoanForm] = useState({
    lender_name: '', principal: '', interest_rate: '0', term_months: '12',
    payment_day: '1', target_account_id: '', currency: 'TRY', notes: '',
  })

  // Plan form
  const [categories, setCategories] = useState<any[]>([])
  const [planForm, setPlanForm] = useState({
    title: '', amount: '', currency: 'TRY', planned_date: today(),
    account_id: '', category_id: '', notes: '',
  })

  const dragId   = useRef<string | null>(null)
  const dragOver = useRef<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadWatchlist = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    try {
      const res = await marketApi.watchlist()
      const raw: any[] = Array.isArray(res.data) ? res.data : (res.data?.items ?? [])
      setWatchlist(applyOrder(raw))
      setLastUpdated(new Date())
      setPinnedState(raw.filter((w: any) => w.is_pinned).map((w: any) => w.id))
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [])

  const refreshPrices = useCallback(async () => {
    setRefreshing(true)
    try { await marketApi.refreshPrices() } catch {}
    finally { await loadWatchlist(true); setRefreshing(false) }
  }, [loadWatchlist])

  useEffect(() => { loadWatchlist() }, [loadWatchlist])
  useEffect(() => {
    intervalRef.current = setInterval(() => loadWatchlist(true), REFRESH_INTERVAL_MS)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [loadWatchlist])

  // ── Drag & Drop ──────────────────────────────────────────────────
  const onDragStart = (id: string) => { dragId.current = id }
  const onDragEnter = (id: string) => { dragOver.current = id }
  const savePinsToDb = useCallback((items: any[], pinnedIds: string[]) => {
    marketApi.updatePins(pinnedIds, items.map(w => w.id)).catch(() => {})
  }, [])
  const onDragEnd = () => {
    if (!dragId.current || !dragOver.current || dragId.current === dragOver.current) {
      dragId.current = dragOver.current = null; return
    }
    setWatchlist(prev => {
      const list = [...prev]
      const from = list.findIndex(w => w.id === dragId.current)
      const to   = list.findIndex(w => w.id === dragOver.current)
      if (from < 0 || to < 0) return prev
      const [moved] = list.splice(from, 1)
      list.splice(to, 0, moved)
      savePinsToDb(list, pinned)
      return list
    })
    dragId.current = dragOver.current = null
  }

  const togglePin = (id: string) => {
    let next: string[]
    if (pinned.includes(id)) {
      next = pinned.filter(x => x !== id)
    } else if (pinned.length >= MAX_PINNED) {
      setError(`En fazla ${MAX_PINNED} sembol sabitlenebilir.`); return
    } else {
      next = [...pinned, id]
    }
    setPinnedState(next)
    savePinsToDb(watchlist, next)
    setError('')
  }

  // ── Add Symbol Modal ─────────────────────────────────────────────
  const closeModal = () => {
    setShowModal(false)
    setMode('normal')
    setForm({ symbol: '', label: '', source: 'google_finance' })
    setTerms([emptyTerm(), emptyTerm()])
    setOps(['*'])
    setFormulaLabel(''); setFormulaSymbol('')
    setFundQuery(''); setFundResults([])
    setError('')
  }

  const buildFormula = (): string =>
    terms.map((t, i) => {
      const val = t.type === 'symbol' ? t.value.trim().toUpperCase() : t.value.trim()
      return i < terms.length - 1 ? `${val} ${ops[i]}` : val
    }).join(' ')

  const addTerm = () => {
    if (terms.length >= 3) return
    setTerms(prev => [...prev, emptyTerm()])
    setOps(prev => [...prev, '*'])
  }
  const removeTerm = (idx: number) => {
    if (terms.length <= 2) return
    setTerms(prev => prev.filter((_, i) => i !== idx))
    setOps(prev => prev.filter((_, i) => i !== idx))
  }

  // Fund search with debounce
  const handleFundQueryChange = (q: string) => {
    setFundQuery(q)
    if (fundSearchTimer.current) clearTimeout(fundSearchTimer.current)
    if (q.trim().length < 2) { setFundResults([]); return }
    fundSearchTimer.current = setTimeout(async () => {
      setFundSearching(true)
      try {
        const res = await marketApi.searchFunds(q.trim(), fundType)
        setFundResults(Array.isArray(res.data) ? res.data : [])
      } catch { setFundResults([]) }
      setFundSearching(false)
    }, 400)
  }

  const handleFundTypeChange = (ft: string) => {
    setFundType(ft)
    setFundResults([])
    if (fundQuery.trim().length >= 2) {
      // Re-search with new type
      setFundSearching(true)
      marketApi.searchFunds(fundQuery.trim(), ft)
        .then(res => setFundResults(Array.isArray(res.data) ? res.data : []))
        .catch(() => setFundResults([]))
        .finally(() => setFundSearching(false))
    }
  }

  const handleAddFund = async (fund: { code: string; name: string; fund_type: string }) => {
    setSaving(true); setError('')
    try {
      await marketApi.addToWatchlist({
        symbol: fund.code,
        label: fund.name,
        source: `tefas_${fund.fund_type}`,
      })
      closeModal()
      await loadWatchlist(true)
    } catch (err: any) {
      setError(err?.response?.data?.detail || t('common.error'))
    } finally { setSaving(false) }
  }

  const handleAddSymbol = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(''); setSaving(true)
    try {
      if (mode === 'formula') {
        if (!formulaSymbol.trim()) { setError('Sembol adı girin'); setSaving(false); return }
        const formula = buildFormula()
        if (terms.some(t => !t.value.trim())) { setError('Tüm terimleri doldurun'); setSaving(false); return }
        await marketApi.addToWatchlist({
          symbol: formulaSymbol.trim().toUpperCase(),
          label: formulaLabel.trim() || formulaSymbol.trim().toUpperCase(),
          source: 'formula', formula,
        })
      } else {
        if (!form.symbol.trim()) { setSaving(false); return }
        await marketApi.addToWatchlist({
          symbol: form.symbol.trim(),
          label: form.label.trim() || form.symbol.trim(),
          source: form.source,
        })
      }
      closeModal()
      await loadWatchlist(true)
    } catch (err: any) {
      setError(err?.response?.data?.detail || t('common.error'))
    } finally { setSaving(false) }
  }

  const handleRemove = async (id: string) => {
    try {
      await marketApi.removeFromWatchlist(id)
      setWatchlist(prev => {
        const next = prev.filter(w => w.id !== id)
        const np = pinned.filter(x => x !== id)
        setPinnedState(np)
        savePinsToDb(next, np)
        return next
      })
    } catch (e) { console.error(e) }
  }

  // ── Action Modals (Al / Sat / Borç / Alacak / Plan) ──────────────
  const openAction = async (type: 'buy' | 'sell' | 'borrow' | 'lend' | 'plan', item: any) => {
    setActionItem(item)
    setActionType(type)
    setActionError('')
    setActionSuccess('')

    if (type === 'buy' || type === 'sell') {
      try {
        const res = await investmentsApi.listPortfolios()
        setPortfolios(Array.isArray(res.data) ? res.data : [])
      } catch { setPortfolios([]) }
      setTxForm({
        portfolio_id: '', quantity: '', price: item.price ? String(item.price) : '',
        commission: '0', date: today(), notes: '',
      })
    }
    if (type === 'borrow' || type === 'lend') {
      try {
        const res = await usersApi.list()
        const all: any[] = Array.isArray(res.data) ? res.data : (res.data?.items ?? [])
        setSystemUsers(all)
      } catch { setSystemUsers([]) }
      setObligForm({
        quantity: '', price_per_unit: item.price ? String(item.price) : '',
        currency: item.currency || 'TRY',
        counterparty_type: 'EXTERNAL',
        counterparty_user_id: '',
        counterparty_name: '',
        due_date: '',
        notes: '',
      })
    }
    if (type === 'plan') {
      try {
        const [accRes, catRes] = await Promise.all([accountsApi.list(), categoriesApi.list()])
        setAccounts(Array.isArray(accRes.data) ? accRes.data : (accRes.data?.items ?? []))
        setCategories(Array.isArray(catRes.data) ? catRes.data : (catRes.data?.items ?? []))
      } catch { setAccounts([]); setCategories([]) }
      setPlanForm({
        title: `${item.label || item.symbol} Alımı`, amount: '',
        currency: item.currency || 'TRY', planned_date: today(),
        account_id: '', category_id: '', notes: '',
      })
    }
  }

  const closeAction = () => {
    setActionItem(null); setActionType(null)
    setActionError(''); setActionSuccess('')
  }

  const handleBuySell = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!txForm.portfolio_id) { setActionError('Portföy seçin'); return }
    setActionSaving(true); setActionError('')
    const qty = parseFloat(txForm.quantity)
    const price = parseFloat(txForm.price)
    const commission = parseFloat(txForm.commission || '0')
    const gross = qty * price
    const net = actionType === 'buy' ? gross + commission : gross - commission
    try {
      await investmentsApi.recordTransaction(txForm.portfolio_id, {
        transaction_type: actionType === 'buy' ? 'BUY' : 'SELL',
        instrument_type: isTefas(actionItem) ? 'FUND' : 'STOCK',
        symbol: actionItem.symbol,
        description: actionItem.label,
        quantity: qty,
        price,
        gross_amount: gross,
        commission,
        tax: 0,
        net_amount: net,
        currency: 'TRY',
        transaction_date: txForm.date,
        notes: txForm.notes || null,
      })
      setActionSuccess(`${actionType === 'buy' ? 'Alım' : 'Satım'} işlemi kaydedildi.`)
      setTimeout(closeAction, 1500)
    } catch (err: any) {
      setActionError(err?.response?.data?.detail?.message || err?.response?.data?.detail || t('common.error'))
    } finally { setActionSaving(false) }
  }

  const handleBorrow = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!loanForm.target_account_id) { setActionError('Hesap seçin'); return }
    setActionSaving(true); setActionError('')
    const principal = parseFloat(loanForm.principal)
    const rate = parseFloat(loanForm.interest_rate || '0')
    const months = parseInt(loanForm.term_months || '12')
    const payDay = parseInt(loanForm.payment_day || '1')
    // Basit faiz hesabı ile aylık taksit
    const totalInterest = principal * (rate / 100) * (months / 12)
    const installment = parseFloat(((principal + totalInterest) / months).toFixed(2))
    const startDate = today()
    try {
      await loansApi.create({
        lender_name: loanForm.lender_name || actionItem.label,
        loan_purpose: `${actionItem.label} — fon yatırımı`,
        principal,
        disbursed_amount: principal,
        interest_rate: rate,
        total_interest: totalInterest,
        fees: 0,
        currency: loanForm.currency,
        term_months: months,
        start_date: startDate,
        payment_day: payDay,
        installment_amount: installment,
        target_account_id: loanForm.target_account_id,
        notes: loanForm.notes || null,
      })
      setActionSuccess('Borç kaydı oluşturuldu.')
      setTimeout(closeAction, 1500)
    } catch (err: any) {
      setActionError(err?.response?.data?.detail?.message || err?.response?.data?.detail || t('common.error'))
    } finally { setActionSaving(false) }
  }

  const handleObligation = async (e: React.FormEvent) => {
    e.preventDefault()
    if (obligForm.counterparty_type === 'EXTERNAL' && !obligForm.counterparty_name.trim()) {
      setActionError('Karşı taraf adını girin'); return
    }
    if (obligForm.counterparty_type === 'USER' && !obligForm.counterparty_user_id) {
      setActionError('Kullanıcı seçin'); return
    }
    if (!obligForm.quantity || parseFloat(obligForm.quantity) <= 0) {
      setActionError('Miktar girin'); return
    }
    setActionSaving(true); setActionError('')
    try {
      await obligationsApi.create({
        symbol: actionItem.symbol,
        label: actionItem.label || actionItem.symbol,
        quantity: parseFloat(obligForm.quantity),
        price_per_unit: obligForm.price_per_unit ? parseFloat(obligForm.price_per_unit) : null,
        currency: obligForm.currency,
        direction: actionType === 'borrow' ? 'BORROW' : 'LEND',
        counterparty_type: obligForm.counterparty_type,
        counterparty_user_id: obligForm.counterparty_type === 'USER' ? obligForm.counterparty_user_id : null,
        counterparty_name: obligForm.counterparty_type === 'EXTERNAL' ? obligForm.counterparty_name : null,
        due_date: obligForm.due_date || null,
        notes: obligForm.notes || null,
      })
      setActionSuccess(actionType === 'borrow' ? 'Borç kaydı oluşturuldu.' : 'Alacak kaydı oluşturuldu.')
      setTimeout(closeAction, 1500)
    } catch (err: any) {
      setActionError(err?.response?.data?.detail?.message || err?.response?.data?.detail || t('common.error'))
    } finally { setActionSaving(false) }
  }

  const handlePlan = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!planForm.account_id) { setActionError('Hesap seçin'); return }
    if (!planForm.category_id) { setActionError('Kategori seçin'); return }
    setActionSaving(true); setActionError('')
    try {
      await plannedPaymentsApi.create({
        payment_type: 'EXPENSE',
        title: planForm.title,
        amount: parseFloat(planForm.amount),
        currency: planForm.currency,
        planned_date: planForm.planned_date,
        account_id: planForm.account_id,
        category_id: planForm.category_id,
        notes: planForm.notes || null,
      })
      setActionSuccess('Planlı ödeme oluşturuldu.')
      setTimeout(closeAction, 1500)
    } catch (err: any) {
      setActionError(err?.response?.data?.detail?.message || err?.response?.data?.detail || t('common.error'))
    } finally { setActionSaving(false) }
  }

  // ── Formatters ───────────────────────────────────────────────────
  const fmt = (price: number | null, currency: string) => {
    if (price == null) return '—'
    const s = currency === 'TRY' ? '₺' : currency === 'USD' ? '$' : currency === 'EUR' ? '€' : ''
    return `${s}${price.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`
  }
  const fmtChange = (changePercent: number | null, trend: string | null) => {
    if (changePercent == null) return '—'
    const arrow = trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'
    const color = trend === 'up' ? 'var(--success)' : trend === 'down' ? 'var(--danger)' : 'var(--text-secondary)'
    const sign = changePercent >= 0 ? '+' : ''
    return <span style={{ color, fontWeight: 500 }}>{arrow} {sign}{changePercent.toFixed(2)}%</span>
  }

  const isTefas = (w: any) => w.source?.startsWith('tefas')

  // ── Render ───────────────────────────────────────────────────────
  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Piyasa</h1>
          <p className="page-subtitle" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            Canlı piyasa verileri
            {lastUpdated && (
              <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>
                · {lastUpdated.toLocaleTimeString('tr-TR')}
              </span>
            )}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <button className="btn btn-secondary" onClick={refreshPrices} disabled={refreshing}>
            <span style={{ display: 'inline-block', animation: refreshing ? 'spin 1s linear infinite' : 'none' }}>⟳</span>
            {refreshing ? ' Güncelleniyor…' : ' Yenile'}
          </button>
          {canCreate && (
            <button className="btn btn-primary" onClick={() => { setError(''); setShowModal(true) }}>
              + Sembol Ekle
            </button>
          )}
        </div>
      </div>

      {pinned.length > 0 && (
        <div style={{
          marginBottom: 'var(--space-4)', padding: 'var(--space-2) var(--space-3)',
          background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)',
          border: '1px solid var(--border)', fontSize: 'var(--font-size-xs)',
          color: 'var(--text-secondary)',
        }}>
          {pinned.length}/{MAX_PINNED} sembol panelde görünüyor
        </div>
      )}

      {error && !showModal && (
        <div className="alert alert-danger" style={{ marginBottom: 'var(--space-3)' }}>{error}</div>
      )}

      {loading ? (
        <div className="loading-state"><div className="spinner" /></div>
      ) : watchlist.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><MarketIcon size={48} /></div>
          <div className="empty-state-title">Henüz sembol eklenmemiş</div>
          <div className="empty-state-desc">Hisse, döviz, emtia ve yatırım fonu fiyatlarını takip edin</div>
          {canCreate && (
            <button className="btn btn-primary" onClick={() => setShowModal(true)}>+ İlk Sembolü Ekle</button>
          )}
        </div>
      ) : (
        <div className="card" style={{ padding: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 32 }}></th>
                <th style={{ width: 40 }}></th>
                <th>Sembol</th>
                <th>Ad</th>
                <th style={{ textAlign: 'right' }}>Fiyat</th>
                <th style={{ textAlign: 'right' }}>Değişim</th>
                <th style={{ textAlign: 'right' }}>Güncelleme</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {watchlist.map((w: any) => {
                const isPinned = pinned.includes(w.id)
                const isFund = isTefas(w)
                return (
                  <tr
                    key={w.id}
                    draggable={canView}
                    onDragStart={canView ? () => onDragStart(w.id) : undefined}
                    onDragEnter={canView ? () => onDragEnter(w.id) : undefined}
                    onDragEnd={canView ? onDragEnd : undefined}
                    onDragOver={canView ? e => e.preventDefault() : undefined}
                    style={{
                      background: isPinned ? 'rgba(99,102,241,0.04)' : undefined,
                      cursor: canView ? 'grab' : 'default', transition: 'background 0.15s',
                    }}
                  >
                    <td style={{ textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 18, userSelect: 'none' }}>
                      {canView ? '⠿' : ''}
                    </td>
                    <td>
                      {canView ? (
                        <button
                          title={isPinned ? 'Panelden kaldır' : `Panele sabitle (${pinned.length}/${MAX_PINNED})`}
                          onClick={() => togglePin(w.id)}
                          style={{
                            background: 'none', border: 'none', cursor: 'pointer',
                            display: 'flex', opacity: isPinned ? 1 : 0.25,
                            transition: 'opacity 0.2s',
                            color: isPinned ? 'var(--accent)' : 'var(--text-tertiary)',
                          }}
                        ><MarketIcon size={14} /></button>
                      ) : (
                        <span style={{ display: 'flex', opacity: isPinned ? 1 : 0.15, color: isPinned ? 'var(--accent)' : 'var(--text-tertiary)' }}><MarketIcon size={14} /></span>
                      )}
                    </td>
                    <td>
                      <span className={isFund ? 'badge badge-success' : 'badge badge-accent'}>{w.symbol}</span>
                      {w.is_formula && (
                        <span title={`Formül: ${w.formula}`} style={{
                          marginLeft: 4, fontSize: 10, padding: '1px 5px',
                          background: 'rgba(168,85,247,0.15)', color: 'var(--accent)',
                          borderRadius: 4, border: '1px solid rgba(168,85,247,0.3)',
                        }}>ƒ</span>
                      )}
                      {isFund && (
                        <span style={{
                          marginLeft: 4, fontSize: 10, padding: '1px 5px',
                          background: 'rgba(34,197,94,0.12)', color: 'var(--success)',
                          borderRadius: 4, border: '1px solid rgba(34,197,94,0.25)',
                        }}>FON</span>
                      )}
                    </td>
                    <td style={{ color: 'var(--text-secondary)', maxWidth: 220 }}>
                      <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {w.label}
                      </span>
                      {w.is_formula && (
                        <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginTop: 2, fontFamily: 'var(--font-mono)' }}>
                          {w.formula}
                        </div>
                      )}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                      {w.price != null ? fmt(w.price, w.currency)
                        : <span style={{ color: 'var(--text-tertiary)' }}>{refreshing ? '…' : '—'}</span>}
                    </td>
                    <td style={{ textAlign: 'right', fontSize: 'var(--font-size-sm)' }}>
                      {w.change_percent != null ? fmtChange(w.change_percent, w.trend)
                        : <span style={{ color: 'var(--text-tertiary)' }}>—</span>}
                    </td>
                    <td style={{ textAlign: 'right', fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>
                      {w.snapshot_at ? new Date(w.snapshot_at).toLocaleTimeString('tr-TR') : '—'}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                        {!w.is_formula && (
                          <>
                            <button className="btn btn-ghost btn-sm" style={{ color: 'var(--success)', fontSize: 11 }}
                              onClick={() => openAction('buy', w)}>Al</button>
                            <button className="btn btn-ghost btn-sm" style={{ color: 'var(--danger)', fontSize: 11 }}
                              onClick={() => openAction('sell', w)}>Sat</button>
                          </>
                        )}
                        <button className="btn btn-ghost btn-sm" style={{ color: 'var(--warning)', fontSize: 11 }}
                          onClick={() => openAction('borrow', w)}>Borç</button>
                        <button className="btn btn-ghost btn-sm" style={{ color: 'var(--success)', fontSize: 11 }}
                          onClick={() => openAction('lend', w)}>Alacak</button>
                        <button className="btn btn-ghost btn-sm" style={{ color: 'var(--accent)', fontSize: 11 }}
                          onClick={() => openAction('plan', w)}>Plan</button>
                        {canDelete && (
                          <button className="btn btn-ghost btn-sm" style={{ color: 'var(--danger)' }}
                            onClick={() => handleRemove(w.id)}><CloseIcon size={13} /></button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          <div style={{
            padding: 'var(--space-3) var(--space-4)',
            fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex', gap: 'var(--space-4)',
          }}>
            <span>⠿ Satırları sürükleyerek sıralayın</span>
            <span>Max {MAX_PINNED} sembolü panele sabitleyin</span>
            <span>Tüm satırlarda Borç/Alacak/Plan; FON satırlarında ayrıca Al/Sat yapabilirsiniz</span>
          </div>
        </div>
      )}

      {/* ── Add Symbol Modal ── */}
      <Modal open={showModal} onClose={closeModal}>
        <div className="modal-header">
          <div className="modal-title">Sembol Ekle</div>
          <button className="modal-close" onClick={closeModal}><CloseIcon size={14} /></button>
        </div>
        <form onSubmit={handleAddSymbol}>
          <div className="modal-body">
            {error && <div className="alert alert-danger" style={{ marginBottom: 'var(--space-3)' }}>{error}</div>}

            {/* Mode toggle */}
            <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
              {([
                { key: 'normal', label: 'Piyasa Sembolü' },
                { key: 'fund',   label: 'Yatırım Fonu' },
                { key: 'formula',label: 'ƒ Formül' },
              ] as const).map(({ key, label }) => (
                <button
                  key={key} type="button"
                  onClick={() => { setMode(key); setError('') }}
                  style={{
                    flex: 1, padding: '6px 0', borderRadius: 'var(--radius-sm)',
                    border: `2px solid ${mode === key ? 'var(--accent)' : 'var(--border)'}`,
                    background: mode === key ? 'rgba(99,102,241,0.1)' : 'var(--bg-elevated)',
                    color: mode === key ? 'var(--accent)' : 'var(--text-secondary)',
                    fontWeight: mode === key ? 600 : 400, cursor: 'pointer', fontSize: 12,
                  }}
                >{label}</button>
              ))}
            </div>

            {/* Normal mode */}
            {mode === 'normal' && (
              <>
                <div className="form-group" style={{ marginBottom: 'var(--space-3)' }}>
                  <label className="form-label">Sembol *</label>
                  <input className="form-input"
                    placeholder="ör: IST:GARAN, USDTRY, NYMEX:BZW00"
                    value={form.symbol}
                    onChange={e => { setForm(f => ({ ...f, symbol: e.target.value })); setError('') }}
                    autoFocus />
                </div>
                <div className="form-group">
                  <label className="form-label">Görünen Ad (opsiyonel)</label>
                  <input className="form-input"
                    placeholder={form.symbol || 'ör: Gram Altın'}
                    value={form.label}
                    onChange={e => setForm(f => ({ ...f, label: e.target.value }))} />
                </div>
              </>
            )}

            {/* Fund mode */}
            {mode === 'fund' && (
              <>
                {/* Fund type filter */}
                <div style={{ display: 'flex', gap: 6, marginBottom: 'var(--space-3)' }}>
                  {FUND_TYPES.map(ft => (
                    <button
                      key={ft.code} type="button"
                      onClick={() => handleFundTypeChange(ft.code)}
                      style={{
                        flex: 1, padding: '5px 0', borderRadius: 'var(--radius-sm)',
                        border: `1px solid ${fundType === ft.code ? 'var(--accent)' : 'var(--border)'}`,
                        background: fundType === ft.code ? 'rgba(99,102,241,0.1)' : 'var(--bg-elevated)',
                        color: fundType === ft.code ? 'var(--accent)' : 'var(--text-secondary)',
                        cursor: 'pointer', fontSize: 11, fontWeight: fundType === ft.code ? 600 : 400,
                      }}
                    >{ft.label}</button>
                  ))}
                </div>

                {/* Search input */}
                <div className="form-group" style={{ marginBottom: 'var(--space-3)' }}>
                  <label className="form-label">Fon Adı veya Kodu</label>
                  <div style={{ position: 'relative' }}>
                    <input
                      className="form-input"
                      placeholder="ör: AAK, AKASYA, Para Piyasası..."
                      value={fundQuery}
                      onChange={e => handleFundQueryChange(e.target.value)}
                      autoFocus
                    />
                    {fundSearching && (
                      <div style={{
                        position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                        width: 16, height: 16, border: '2px solid var(--border-subtle)',
                        borderTop: '2px solid var(--accent)', borderRadius: '50%',
                        animation: 'spin 0.8s linear infinite',
                      }} />
                    )}
                  </div>
                </div>

                {/* Results */}
                {fundResults.length > 0 && (
                  <div style={{
                    maxHeight: 240, overflowY: 'auto',
                    border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)',
                    background: 'var(--bg-elevated)',
                  }}>
                    {fundResults.map((fund, i) => (
                      <div
                        key={fund.code + i}
                        onClick={() => handleAddFund(fund)}
                        style={{
                          padding: '10px 14px', cursor: 'pointer',
                          borderBottom: i < fundResults.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                          transition: 'background 0.1s',
                          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
                        }}
                        onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
                        onMouseLeave={e => (e.currentTarget.style.background = '')}
                      >
                        <div>
                          <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>{fund.code}</span>
                          <span style={{ marginLeft: 10, fontSize: 12, color: 'var(--text-secondary)' }}>{fund.name}</span>
                        </div>
                        <span style={{
                          fontSize: 10, padding: '2px 6px', borderRadius: 4,
                          background: 'rgba(34,197,94,0.12)', color: 'var(--success)',
                          border: '1px solid rgba(34,197,94,0.25)', whiteSpace: 'nowrap',
                        }}>+ Ekle</span>
                      </div>
                    ))}
                  </div>
                )}
                {!fundSearching && fundQuery.length >= 2 && fundResults.length === 0 && (
                  <div style={{ textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13, padding: 'var(--space-3)' }}>
                    Fon bulunamadı
                  </div>
                )}
                {fundQuery.length < 2 && !fundSearching && (
                  <div style={{ fontSize: 12, color: 'var(--text-tertiary)', textAlign: 'center', paddingTop: 'var(--space-2)' }}>
                    En az 2 karakter girin
                  </div>
                )}
              </>
            )}

            {/* Formula mode */}
            {mode === 'formula' && (
              <>
                <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
                  <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
                    <label className="form-label">Sembol Adı *</label>
                    <input className="form-input"
                      placeholder="ör: ALTIN_TRY, PORTFOY"
                      value={formulaSymbol}
                      onChange={e => setFormulaSymbol(e.target.value.toUpperCase().replace(/\s/g, '_'))}
                      autoFocus />
                  </div>
                  <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
                    <label className="form-label">Görünen Ad</label>
                    <input className="form-input"
                      placeholder="ör: Altın (TL)"
                      value={formulaLabel}
                      onChange={e => setFormulaLabel(e.target.value)} />
                  </div>
                </div>
                <div style={{ marginBottom: 'var(--space-3)' }}>
                  <label className="form-label">Formül</label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                    {terms.map((term, idx) => (
                      <div key={idx} style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
                        {idx > 0 && (
                          <select className="form-input" style={{ width: 56, padding: '6px 4px', textAlign: 'center' }}
                            value={ops[idx - 1]}
                            onChange={e => setOps(prev => prev.map((o, i) => i === idx - 1 ? e.target.value : o))}>
                            {['+', '-', '*', '/'].map(op => <option key={op}>{op}</option>)}
                          </select>
                        )}
                        <button type="button"
                          title={term.type === 'symbol' ? 'Sembol → sayı' : 'Sayı → sembol'}
                          onClick={() => setTerms(prev => prev.map((t, i) => i === idx ? { ...t, type: t.type === 'symbol' ? 'number' : 'symbol', value: '' } : t))}
                          style={{ padding: '6px 8px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', background: 'var(--bg-elevated)', cursor: 'pointer', fontSize: 12, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                          {term.type === 'symbol' ? '≋' : '1.0'}
                        </button>
                        {term.type === 'symbol' ? (
                          <select className="form-input" style={{ flex: 1 }} value={term.value}
                            onChange={e => setTerms(prev => prev.map((t, i) => i === idx ? { ...t, value: e.target.value } : t))}>
                            <option value="">— sembol seç —</option>
                            {watchlist.filter(w => !w.is_formula || w.symbol !== formulaSymbol).map((w: any) => (
                              <option key={w.id} value={w.symbol}>{w.symbol} — {w.label}</option>
                            ))}
                          </select>
                        ) : (
                          <input className="form-input" style={{ flex: 1 }} type="number" step="any"
                            placeholder="ör: 31.1" value={term.value}
                            onChange={e => setTerms(prev => prev.map((t, i) => i === idx ? { ...t, value: e.target.value } : t))} />
                        )}
                        {terms.length > 2 && (
                          <button type="button" onClick={() => removeTerm(idx)}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--danger)', display: 'flex' }}><CloseIcon size={14} /></button>
                        )}
                      </div>
                    ))}
                  </div>
                  {terms.length < 3 && (
                    <button type="button" onClick={addTerm}
                      style={{ marginTop: 'var(--space-2)', fontSize: 'var(--font-size-xs)', color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
                      + Terim Ekle
                    </button>
                  )}
                </div>
                {terms.some(t => t.value.trim()) && (
                  <div style={{ padding: 'var(--space-2) var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)' }}>
                    <span style={{ color: 'var(--text-tertiary)', marginRight: 6 }}>ƒ</span>
                    <strong>{formulaSymbol || '?'}</strong>
                    <span style={{ color: 'var(--text-tertiary)', margin: '0 6px' }}>=</span>
                    {terms.map((t, i) => (
                      <span key={i}>
                        {i > 0 && <span style={{ color: 'var(--accent)', margin: '0 4px' }}>{ops[i - 1]}</span>}
                        <span style={{ color: t.type === 'symbol' ? 'var(--success)' : 'var(--warning)' }}>{t.value || '?'}</span>
                      </span>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
          {mode !== 'fund' && (
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={closeModal}>İptal</button>
              <button type="submit" className="btn btn-primary"
                disabled={saving || (mode === 'normal' ? !form.symbol.trim() : !formulaSymbol.trim())}>
                {saving ? 'Kaydediliyor…' : 'Kaydet'}
              </button>
            </div>
          )}
        </form>
      </Modal>

      {/* ── Buy / Sell Modal ── */}
      <Modal open={actionItem != null && (actionType === 'buy' || actionType === 'sell')} onClose={closeAction}>
        <div className="modal-header">
          <div className="modal-title">
            {actionType === 'buy' ? 'Fon Alımı' : 'Fon Satımı'} — {actionItem?.symbol}
          </div>
          <button className="modal-close" onClick={closeAction}><CloseIcon size={14} /></button>
        </div>
        <form onSubmit={handleBuySell}>
          <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            {actionError && <div className="alert alert-danger">{actionError}</div>}
            {actionSuccess && <div className="alert alert-success">{actionSuccess}</div>}
            <div className="form-group">
              <label className="form-label">Portföy *</label>
              <select className="form-input" value={txForm.portfolio_id}
                onChange={e => setTxForm(f => ({ ...f, portfolio_id: e.target.value }))} required>
                <option value="">— Portföy seçin —</option>
                {portfolios.map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              {portfolios.length === 0 && (
                <p style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 4 }}>
                  Portföy bulunamadı. Önce Yatırımlar sayfasından portföy oluşturun.
                </p>
              )}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
              <div className="form-group">
                <label className="form-label">Adet *</label>
                <input className="form-input" type="number" step="0.000001" min="0.000001"
                  placeholder="0.00" value={txForm.quantity}
                  onChange={e => setTxForm(f => ({ ...f, quantity: e.target.value }))} required />
              </div>
              <div className="form-group">
                <label className="form-label">Fiyat (NAV) *</label>
                <input className="form-input" type="number" step="0.000001" min="0"
                  placeholder="0.00" value={txForm.price}
                  onChange={e => setTxForm(f => ({ ...f, price: e.target.value }))} required />
              </div>
            </div>
            {txForm.quantity && txForm.price && (
              <div style={{
                padding: '10px 14px', background: 'var(--bg-elevated)', borderRadius: 8,
                fontSize: 13, border: '1px solid var(--border)',
              }}>
                <span style={{ color: 'var(--text-secondary)' }}>Brüt Tutar: </span>
                <strong>₺{(parseFloat(txForm.quantity) * parseFloat(txForm.price)).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
              </div>
            )}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
              <div className="form-group">
                <label className="form-label">Komisyon</label>
                <input className="form-input" type="number" step="0.01" min="0"
                  value={txForm.commission}
                  onChange={e => setTxForm(f => ({ ...f, commission: e.target.value }))} />
              </div>
              <div className="form-group">
                <label className="form-label">Tarih *</label>
                <input className="form-input" type="date" value={txForm.date}
                  onChange={e => setTxForm(f => ({ ...f, date: e.target.value }))} required />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Notlar</label>
              <input className="form-input" type="text" value={txForm.notes}
                onChange={e => setTxForm(f => ({ ...f, notes: e.target.value }))} />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={closeAction}>İptal</button>
            <button type="submit" className="btn btn-primary" disabled={actionSaving}>
              {actionSaving ? 'Kaydediliyor…' : actionType === 'buy' ? 'Alımı Kaydet' : 'Satımı Kaydet'}
            </button>
          </div>
        </form>
      </Modal>

      {/* ── Borç / Alacak Modal ── */}
      <Modal open={actionItem != null && (actionType === 'borrow' || actionType === 'lend')} onClose={closeAction}>
        <div className="modal-header">
          <div className="modal-title">
            {actionType === 'borrow' ? 'Borç Kaydı' : 'Alacak Kaydı'} — {actionItem?.symbol}
          </div>
          <button className="modal-close" onClick={closeAction}><CloseIcon size={14} /></button>
        </div>
        <form onSubmit={handleObligation}>
          <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            {actionError && <div className="alert alert-danger">{actionError}</div>}
            {actionSuccess && <div className="alert alert-success">{actionSuccess}</div>}

            {/* Karşı taraf tipi */}
            <div className="form-group">
              <label className="form-label">Karşı Taraf</label>
              <div style={{ display: 'flex', gap: 8 }}>
                {(['EXTERNAL', 'USER'] as const).map(t => (
                  <button key={t} type="button"
                    onClick={() => setObligForm(f => ({ ...f, counterparty_type: t, counterparty_user_id: '', counterparty_name: '' }))}
                    style={{
                      flex: 1, padding: '6px 0', borderRadius: 'var(--radius-sm)',
                      border: `2px solid ${obligForm.counterparty_type === t ? 'var(--accent)' : 'var(--border)'}`,
                      background: obligForm.counterparty_type === t ? 'rgba(99,102,241,0.1)' : 'var(--bg-elevated)',
                      color: obligForm.counterparty_type === t ? 'var(--accent)' : 'var(--text-secondary)',
                      fontWeight: obligForm.counterparty_type === t ? 600 : 400, cursor: 'pointer', fontSize: 12,
                    }}>
                    {t === 'EXTERNAL' ? <><BuildingIcon size={13} /> Dış Kişi / Kurum</> : <><UsersIcon size={13} /> Sistem Kullanıcısı</>}
                  </button>
                ))}
              </div>
            </div>

            {obligForm.counterparty_type === 'EXTERNAL' ? (
              <div className="form-group">
                <label className="form-label">{actionType === 'borrow' ? 'Borç Alınan Kişi / Kurum *' : 'Alacaklı Olunan Kişi / Kurum *'}</label>
                <input className="form-input" type="text"
                  placeholder="Ad / Kurum"
                  value={obligForm.counterparty_name}
                  onChange={e => setObligForm(f => ({ ...f, counterparty_name: e.target.value }))}
                  autoFocus />
              </div>
            ) : (
              <div className="form-group">
                <label className="form-label">Kullanıcı *</label>
                <select className="form-input" value={obligForm.counterparty_user_id}
                  onChange={e => setObligForm(f => ({ ...f, counterparty_user_id: e.target.value }))} required>
                  <option value="">— Kullanıcı seçin —</option>
                  {systemUsers.map((u: any) => (
                    <option key={u.id} value={u.id}>{u.full_name || u.email}</option>
                  ))}
                </select>
                {obligForm.counterparty_user_id && (
                  <p style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>
                    Bu kullanıcının takvimine otomatik ters kayıt düşecek.
                  </p>
                )}
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
              <div className="form-group">
                <label className="form-label">Miktar *</label>
                <input className="form-input" type="number" step="0.000001" min="0.000001"
                  placeholder="0.00" value={obligForm.quantity}
                  onChange={e => setObligForm(f => ({ ...f, quantity: e.target.value }))} required />
              </div>
              <div className="form-group">
                <label className="form-label">Birim Fiyat (opsiyonel)</label>
                <input className="form-input" type="number" step="0.000001" min="0"
                  placeholder={actionItem?.price ? String(actionItem.price) : '0.00'}
                  value={obligForm.price_per_unit}
                  onChange={e => setObligForm(f => ({ ...f, price_per_unit: e.target.value }))} />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
              <div className="form-group">
                <label className="form-label">Para Birimi</label>
                <select className="form-input" value={obligForm.currency}
                  onChange={e => setObligForm(f => ({ ...f, currency: e.target.value }))}>
                  {['TRY', 'USD', 'EUR'].map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Vade Tarihi</label>
                <input className="form-input" type="date" value={obligForm.due_date}
                  onChange={e => setObligForm(f => ({ ...f, due_date: e.target.value }))} />
              </div>
            </div>

            {obligForm.quantity && obligForm.price_per_unit && (
              <div style={{ padding: '10px 14px', background: 'var(--bg-elevated)', borderRadius: 8, fontSize: 13, border: '1px solid var(--border)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Toplam Değer: </span>
                <strong>{obligForm.currency === 'TRY' ? '₺' : obligForm.currency === 'USD' ? '$' : '€'}
                  {(parseFloat(obligForm.quantity) * parseFloat(obligForm.price_per_unit)).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </strong>
              </div>
            )}

            <div className="form-group">
              <label className="form-label">Notlar</label>
              <input className="form-input" type="text" value={obligForm.notes}
                onChange={e => setObligForm(f => ({ ...f, notes: e.target.value }))} />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={closeAction}>İptal</button>
            <button type="submit" className="btn btn-primary" disabled={actionSaving}>
              {actionSaving ? 'Kaydediliyor…' : actionType === 'borrow' ? 'Borç Kaydını Oluştur' : 'Alacak Kaydını Oluştur'}
            </button>
          </div>
        </form>
      </Modal>

      {/* ── Plan Modal ── */}
      <Modal open={actionItem != null && actionType === 'plan'} onClose={closeAction}>
        <div className="modal-header">
          <div className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}><CalendarIcon size={15} /> Planlı Ödeme — {actionItem?.symbol}</div>
          <button className="modal-close" onClick={closeAction}><CloseIcon size={14} /></button>
        </div>
        <form onSubmit={handlePlan}>
          <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            {actionError && <div className="alert alert-danger">{actionError}</div>}
            {actionSuccess && <div className="alert alert-success">{actionSuccess}</div>}
            <div className="form-group">
              <label className="form-label">Başlık *</label>
              <input className="form-input" type="text"
                value={planForm.title}
                onChange={e => setPlanForm(f => ({ ...f, title: e.target.value }))} required />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
              <div className="form-group">
                <label className="form-label">Tutar *</label>
                <input className="form-input" type="number" step="0.01" min="0.01"
                  placeholder="0.00" value={planForm.amount}
                  onChange={e => setPlanForm(f => ({ ...f, amount: e.target.value }))} required />
              </div>
              <div className="form-group">
                <label className="form-label">Para Birimi</label>
                <select className="form-input" value={planForm.currency}
                  onChange={e => setPlanForm(f => ({ ...f, currency: e.target.value }))}>
                  {['TRY', 'USD', 'EUR'].map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Planlanan Tarih *</label>
              <input className="form-input" type="date" value={planForm.planned_date}
                onChange={e => setPlanForm(f => ({ ...f, planned_date: e.target.value }))} required />
            </div>
            <div className="form-group">
              <label className="form-label">Hesap *</label>
              <select className="form-input" value={planForm.account_id}
                onChange={e => setPlanForm(f => ({ ...f, account_id: e.target.value }))} required>
                <option value="">— Hesap seçin —</option>
                {accounts.map((a: any) => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Kategori *</label>
              <select className="form-input" value={planForm.category_id}
                onChange={e => setPlanForm(f => ({ ...f, category_id: e.target.value }))} required>
                <option value="">— Kategori seçin —</option>
                {categories.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Notlar</label>
              <input className="form-input" type="text" value={planForm.notes}
                onChange={e => setPlanForm(f => ({ ...f, notes: e.target.value }))} />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={closeAction}>İptal</button>
            <button type="submit" className="btn btn-primary" disabled={actionSaving}>
              {actionSaving ? 'Kaydediliyor…' : 'Planlı Ödemeyi Oluştur'}
            </button>
          </div>
        </form>
      </Modal>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        tr[draggable]:active { opacity: 0.7; }
      `}</style>
    </div>
  )
}
