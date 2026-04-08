import React, { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { investmentsApi } from '../api/umay'
import { getCurrencySymbol } from '../constants/currencies'

/* ── helpers ───────────────────────────────────────────────────────── */
const fmt = (n: number | null | undefined, decimals = 2) =>
  n == null ? '—' : n.toLocaleString('tr-TR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })

const isTrade = (type: string) => type === 'BUY' || type === 'SELL'

/* ── Modal wrapper ─────────────────────────────────────────────────── */
function Modal({ open, onClose, children }: { open: boolean; onClose: () => void; children: React.ReactNode }) {
  if (!open) return null
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>{children}</div>
    </div>
  )
}

/* ── Symbol combobox ───────────────────────────────────────────────── */
interface SymbolComboProps {
  value: string
  onChange: (symbol: string, price?: number) => void
  marketPrices: any[]
  onAddSymbol: (symbol: string) => Promise<any>
}
function SymbolCombo({ value, onChange, marketPrices, onAddSymbol }: SymbolComboProps) {
  const [search, setSearch] = useState(value)
  const [open, setOpen] = useState(false)
  const [adding, setAdding] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => { setSearch(value) }, [value])

  const filtered = search
    ? marketPrices.filter(mp =>
        mp.symbol.includes(search.toUpperCase()) ||
        (mp.name || '').toLowerCase().includes(search.toLowerCase())
      )
    : marketPrices

  const exactMatch = marketPrices.some(mp => mp.symbol === search.toUpperCase())

  const select = (mp: any) => {
    const price = parseFloat(mp.price)
    onChange(mp.symbol, price > 0 ? price : undefined)
    setSearch(mp.symbol)
    setOpen(false)
  }

  const handleAdd = async () => {
    if (!search) return
    setAdding(true)
    try {
      const res = await onAddSymbol(search.toUpperCase())
      const price = res?.data?.price ? parseFloat(res.data.price) : undefined
      onChange(search.toUpperCase(), price && price > 0 ? price : undefined)
      setOpen(false)
    } catch {
      // ignore
    } finally { setAdding(false) }
  }

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <input
        className="form-input"
        placeholder="ör: GARAN, THYAO, USDTRY"
        value={search}
        onChange={e => {
          const v = e.target.value.toUpperCase()
          setSearch(v)
          const mp = marketPrices.find((m: any) => m.symbol === v)
          onChange(v, mp && parseFloat(mp.price) > 0 ? parseFloat(mp.price) : undefined)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 200)}
        autoComplete="off"
      />
      {open && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 200,
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius-sm)', maxHeight: 220, overflowY: 'auto',
          boxShadow: 'var(--shadow-md)',
        }}>
          {filtered.length === 0 && !search && (
            <div style={{ padding: '10px 12px', color: 'var(--text-tertiary)', fontSize: 'var(--font-size-xs)' }}>
              Piyasa ekranından sembol ekleyin veya aşağıdan ekleyin
            </div>
          )}
          {filtered.map((mp: any) => {
            const price = parseFloat(mp.price)
            return (
              <div
                key={mp.symbol}
                onMouseDown={() => select(mp)}
                style={{
                  padding: '8px 12px', cursor: 'pointer', display: 'flex',
                  justifyContent: 'space-between', alignItems: 'center',
                  borderBottom: '1px solid var(--border-subtle)',
                }}
                className="hover-row"
              >
                <div>
                  <span style={{ fontWeight: 600, fontSize: 'var(--font-size-sm)' }}>{mp.symbol}</span>
                  {mp.name && (
                    <span style={{ marginLeft: 8, color: 'var(--text-tertiary)', fontSize: 'var(--font-size-xs)' }}>
                      {mp.name}
                    </span>
                  )}
                </div>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: price > 0 ? 'var(--income)' : 'var(--text-tertiary)' }}>
                  {price > 0 ? `${fmt(price, 4)} ${mp.currency}` : '—'}
                </span>
              </div>
            )
          })}
          {search && !exactMatch && (
            <div style={{ padding: '8px 12px', borderTop: '1px solid var(--border)' }}>
              <button
                type="button"
                className="btn btn-sm btn-secondary"
                style={{ width: '100%' }}
                onMouseDown={handleAdd}
                disabled={adding}
              >
                {adding ? 'Ekleniyor...' : `"${search}" piyasaya ekle ve seç`}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ── Main page ─────────────────────────────────────────────────────── */
const EMPTY_TX_FORM = {
  transaction_type: 'BUY', symbol: '', quantity: '',
  price: '', fee: '', transaction_date: new Date().toISOString().slice(0, 10), notes: '',
}

export function InvestmentsPage() {
  const { t } = useTranslation()

  // ── State ────────────────────────────────────────────────────────
  const [portfolios, setPortfolios] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedPortfolio, setSelectedPortfolio] = useState<any | null>(null)
  const [positions, setPositions] = useState<any[]>([])
  const [transactions, setTransactions] = useState<any[]>([])
  const [marketPrices, setMarketPrices] = useState<any[]>([])
  const [detailLoading, setDetailLoading] = useState(false)

  const [showPortModal, setShowPortModal] = useState(false)
  const [showTxModal, setShowTxModal] = useState(false)
  const [saving, setSaving] = useState(false)
  const [txError, setTxError] = useState('')
  const [editingTx, setEditingTx] = useState<any | null>(null)

  const [portForm, setPortForm] = useState({ name: '', currency: 'TRY', description: '' })
  const [txForm, setTxForm] = useState({ ...EMPTY_TX_FORM })

  // ── Data loaders ─────────────────────────────────────────────────
  const load = () => {
    setLoading(true)
    investmentsApi.listPortfolios({ skip: 0, limit: 100 })
      .then(r => setPortfolios(r.data)).catch(() => {}).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const openPortfolio = async (p: any) => {
    setSelectedPortfolio(p)
    setDetailLoading(true)
    const [posRes, txRes, mktRes] = await Promise.allSettled([
      investmentsApi.getPositions(p.id),
      investmentsApi.listTransactions(p.id, { skip: 0, limit: 200 }),
      investmentsApi.listMarketPrices(),
    ])
    if (posRes.status === 'fulfilled') {
      const d = posRes.value.data
      setPositions(Array.isArray(d) ? d : (d?.items || []))
    }
    if (txRes.status === 'fulfilled') setTransactions(txRes.value.data)
    if (mktRes.status === 'fulfilled') {
      const d = mktRes.value.data
      setMarketPrices(Array.isArray(d) ? d : [])
    }
    setDetailLoading(false)
  }

  const refreshDetail = () => {
    if (selectedPortfolio) openPortfolio(selectedPortfolio)
  }

  // ── Market price helpers ─────────────────────────────────────────
  const getMarketPrice = (symbol: string) =>
    marketPrices.find((mp: any) => mp.symbol === symbol?.toUpperCase())

  const handleAddSymbol = async (symbol: string) => {
    const res = await investmentsApi.addMarketSymbol({ symbol })
    // Refresh market prices
    const mktRes = await investmentsApi.listMarketPrices()
    if (mktRes.data) setMarketPrices(Array.isArray(mktRes.data) ? mktRes.data : [])
    return res
  }

  // ── Portfolio form ───────────────────────────────────────────────
  const handlePortSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await investmentsApi.createPortfolio(portForm)
      setShowPortModal(false)
      setPortForm({ name: '', currency: 'TRY', description: '' })
      load()
    } catch (err: any) {
      alert(err?.response?.data?.detail || t('common.error'))
    } finally { setSaving(false) }
  }

  // ── Transaction modal ────────────────────────────────────────────
  const openTxModal = (editTx?: any) => {
    setTxError('')
    if (editTx) {
      setEditingTx(editTx)
      setTxForm({
        transaction_type: editTx.transaction_type,
        symbol: editTx.symbol || '',
        quantity: String(editTx.quantity || ''),
        price: String(editTx.price || ''),
        fee: String(editTx.commission || ''),
        transaction_date: editTx.transaction_date,
        notes: editTx.notes || '',
      })
    } else {
      setEditingTx(null)
      setTxForm({ ...EMPTY_TX_FORM })
    }
    setShowTxModal(true)
  }

  const handleTxSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedPortfolio) return
    setSaving(true)
    setTxError('')
    try {
      const qty = parseFloat(txForm.quantity)
      const prc = parseFloat(txForm.price)
      const commission = txForm.fee ? parseFloat(txForm.fee) : 0
      const gross = qty * prc
      const net = txForm.transaction_type === 'BUY' ? (gross + commission) : (gross - commission)

      const payload = {
        transaction_type: txForm.transaction_type,
        symbol: txForm.symbol || undefined,
        quantity: qty || undefined,
        price: prc || undefined,
        gross_amount: gross || 0,
        commission: commission,
        net_amount: net || 0,
        currency: selectedPortfolio.currency || 'TRY',
        transaction_date: txForm.transaction_date,
        notes: txForm.notes || undefined,
        instrument_type: 'STOCK',
      }

      if (editingTx) {
        await investmentsApi.updateTransaction(selectedPortfolio.id, editingTx.id, payload)
      } else {
        await investmentsApi.recordTransaction(selectedPortfolio.id, payload)
      }

      setShowTxModal(false)
      setEditingTx(null)
      refreshDetail()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setTxError(typeof detail === 'string' ? detail : (err?.response?.data?.error?.message || 'Bir hata oluştu.'))
    } finally { setSaving(false) }
  }

  const handleDeleteTx = async (tx: any) => {
    const typeLabel = tx.transaction_type === 'BUY' ? 'Alış' : tx.transaction_type === 'SELL' ? 'Satış' : tx.transaction_type
    if (!confirm(
      `Bu işlemi silmek istediğinizden emin misiniz?\n\n` +
      `${typeLabel}: ${tx.symbol} × ${tx.quantity} adet @ ${tx.price}\n\n` +
      `Nakit akışı tersine dönecek, hesap bakiyesi güncellecektir.`
    )) return

    try {
      await investmentsApi.deleteTransaction(selectedPortfolio.id, tx.id)
      refreshDetail()
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Silme işlemi başarısız.')
    }
  }

  // ── Computed ─────────────────────────────────────────────────────
  const totalValue = portfolios.reduce((s, p) => s + parseFloat(p.total_value || '0'), 0)
  const totalPnl = portfolios.reduce((s, p) => s + parseFloat(p.unrealized_pnl || '0'), 0)
  const showTrade = isTrade(txForm.transaction_type)

  // Live position data enriched with market prices
  const enrichedPositions = positions.map((pos: any) => {
    const mp = getMarketPrice(pos.symbol)
    const livePrice = mp ? parseFloat(mp.price) : (pos.current_price ? parseFloat(pos.current_price) : null)
    const qty = parseFloat(pos.quantity || '0')
    const avgCost = parseFloat(pos.avg_cost || '0')
    const liveValue = livePrice != null ? qty * livePrice : (pos.current_value ? parseFloat(pos.current_value) : null)
    const livePnl = livePrice != null && avgCost ? (livePrice - avgCost) * qty : (pos.unrealized_pnl ? parseFloat(pos.unrealized_pnl) : null)
    const livePct = avgCost && livePrice ? ((livePrice - avgCost) / avgCost) * 100 : null
    return { ...pos, livePrice, liveValue, livePnl, livePct }
  })

  // ── Render ────────────────────────────────────────────────────────
  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">{t('investments.title')}</h1>
          <p className="page-subtitle">{t('investments.portfolios')} ({portfolios.length})</p>
        </div>
        {!selectedPortfolio && (
          <button className="btn btn-primary" onClick={() => setShowPortModal(true)}>
            {t('investments.newPortfolio')}
          </button>
        )}
      </div>

      {/* KPI cards */}
      {portfolios.length > 0 && !selectedPortfolio && (
        <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 'var(--space-6)' }}>
          <div className="stat-card">
            <div className="stat-card-label">{t('investments.totalValue')}</div>
            <div className="stat-card-value" style={{ color: 'var(--accent)' }}>
              ₺ {fmt(totalValue)}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-card-label">{t('investments.unrealizedPnL')}</div>
            <div className="stat-card-value" style={{ color: totalPnl >= 0 ? 'var(--income)' : 'var(--expense)' }}>
              {totalPnl >= 0 ? '+' : ''}₺ {fmt(Math.abs(totalPnl))}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-card-label">{t('investments.portfolios')}</div>
            <div className="stat-card-value">{portfolios.length}</div>
          </div>
        </div>
      )}

      {/* Back button */}
      {selectedPortfolio && (
        <div style={{ marginBottom: 'var(--space-4)' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => { setSelectedPortfolio(null); setPositions([]); setTransactions([]) }}
          >
            ← {t('investments.backToPortfolios')}
          </button>
        </div>
      )}

      {/* Portfolio list */}
      {!selectedPortfolio && (
        loading ? (
          <div className="loading-state"><div className="spinner" /></div>
        ) : portfolios.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📈</div>
            <div className="empty-state-title">{t('investments.noPortfolios')}</div>
            <div className="empty-state-desc">{t('investments.noPortfoliosDesc')}</div>
            <button className="btn btn-primary" onClick={() => setShowPortModal(true)}>
              {t('investments.newPortfolio')}
            </button>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 'var(--space-4)' }}>
            {portfolios.map((p: any) => {
              const pnl = parseFloat(p.unrealized_pnl || '0')
              const sym = getCurrencySymbol(p.currency)
              return (
                <div key={p.id} className="card" style={{ cursor: 'pointer' }} onClick={() => openPortfolio(p)}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-3)' }}>
                    <span className="badge badge-accent">{p.currency}</span>
                  </div>
                  <div style={{ fontWeight: 600, fontSize: 'var(--font-size-md)', marginBottom: 4 }}>{p.name}</div>
                  {p.group_names && p.group_names.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 'var(--space-2)' }}>
                      {p.group_names.map((g: string, i: number) => (
                        <span key={i} className="badge" style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)', fontSize: 11 }}>👥 {g}</span>
                      ))}
                    </div>
                  )}
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 'var(--space-4)' }}>
                    {p.description || '—'}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                    <div>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>{t('investments.totalValue')}</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 'var(--font-size-xl)', color: 'var(--accent)' }}>
                        {sym} {fmt(parseFloat(p.total_value || '0'))}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>Kar/Zarar</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: pnl >= 0 ? 'var(--income)' : 'var(--expense)' }}>
                        {pnl >= 0 ? '+' : ''}{sym} {fmt(Math.abs(pnl))}
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )
      )}

      {/* Portfolio detail */}
      {selectedPortfolio && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-5)' }}>
            <div>
              <h2 style={{ fontWeight: 700, fontSize: 'var(--font-size-xl)' }}>{selectedPortfolio.name}</h2>
              <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)' }}>{selectedPortfolio.currency}</div>
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <button
                className="btn btn-secondary"
                title="Fiyatları yenile"
                onClick={async () => {
                  await investmentsApi.refreshMarketPrices()
                  refreshDetail()
                }}
              >↻ Fiyatları Yenile</button>
              <button className="btn btn-primary" onClick={() => openTxModal()}>
                + {t('investments.recordTransaction')}
              </button>
            </div>
          </div>

          {detailLoading ? (
            <div className="loading-state"><div className="spinner" /></div>
          ) : (
            <>
              {/* Portfolio Summary Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--space-3)', marginBottom: 'var(--space-5)' }}>
                <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '12px 14px' }}>
                  <div style={{ fontSize: 10, color: 'var(--text-secondary)', fontWeight: 600, marginBottom: 6 }}>Portföy Değeri</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 16, color: 'var(--accent)' }}>
                    {getCurrencySymbol(selectedPortfolio.currency)} {fmt(parseFloat(selectedPortfolio.total_value || '0'))}
                  </div>
                </div>
                <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '12px 14px' }}>
                  <div style={{ fontSize: 10, color: 'var(--text-secondary)', fontWeight: 600, marginBottom: 6 }}>Gerçekleşmemiş K/Z</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 16, color: parseFloat(selectedPortfolio.unrealized_pnl || '0') >= 0 ? 'var(--income)' : 'var(--expense)' }}>
                    {parseFloat(selectedPortfolio.unrealized_pnl || '0') >= 0 ? '+' : ''}{getCurrencySymbol(selectedPortfolio.currency)} {fmt(Math.abs(parseFloat(selectedPortfolio.unrealized_pnl || '0')))}
                  </div>
                </div>
                <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '12px 14px' }}>
                  <div style={{ fontSize: 10, color: 'var(--text-secondary)', fontWeight: 600, marginBottom: 6 }}>Gerçekleşen K/Z</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 16, color: (positions.reduce((s, p) => s + parseFloat(p.realized_pnl || '0'), 0)) >= 0 ? 'var(--income)' : 'var(--expense)' }}>
                    {(positions.reduce((s, p) => s + parseFloat(p.realized_pnl || '0'), 0)) >= 0 ? '+' : ''}{getCurrencySymbol(selectedPortfolio.currency)} {fmt(Math.abs(positions.reduce((s, p) => s + parseFloat(p.realized_pnl || '0'), 0)))}
                  </div>
                </div>
                <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '12px 14px', boxShadow: '0 0 0 2px var(--income)' }}>
                  <div style={{ fontSize: 10, color: 'var(--text-secondary)', fontWeight: 600, marginBottom: 6 }}>🎯 NET KAR</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 18, color: (parseFloat(selectedPortfolio.unrealized_pnl || '0') + (positions.reduce((s, p) => s + parseFloat(p.realized_pnl || '0'), 0))) >= 0 ? 'var(--income)' : 'var(--expense)' }}>
                    {((parseFloat(selectedPortfolio.unrealized_pnl || '0') + (positions.reduce((s, p) => s + parseFloat(p.realized_pnl || '0'), 0)))) >= 0 ? '+' : ''}{getCurrencySymbol(selectedPortfolio.currency)} {fmt(Math.abs(parseFloat(selectedPortfolio.unrealized_pnl || '0') + (positions.reduce((s, p) => s + parseFloat(p.realized_pnl || '0'), 0))))}
                  </div>
                </div>
              </div>

              {/* Positions */}
              <div className="card" style={{ padding: 0, marginBottom: 'var(--space-5)' }}>
                <div className="card-header">
                  <div className="card-title">{t('investments.positions')}</div>
                </div>
                {enrichedPositions.length === 0 ? (
                  <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)' }}>
                    {t('investments.noPositions')}
                  </div>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>{t('investments.table.instrument')}</th>
                        <th style={{ textAlign: 'right' }}>{t('investments.table.quantity')}</th>
                        <th style={{ textAlign: 'right' }}>{t('investments.table.avgCost')}</th>
                        <th style={{ textAlign: 'right' }}>Güncel Fiyat</th>
                        <th style={{ textAlign: 'right' }}>Piyasa Değeri</th>
                        <th style={{ textAlign: 'right' }}>Kar/Zarar</th>
                        <th style={{ textAlign: 'right' }}>Gerçekleşen K/Z</th>
                      </tr>
                    </thead>
                    <tbody>
                      {enrichedPositions.map((pos: any) => {
                        const sym = getCurrencySymbol(selectedPortfolio.currency)
                        const pnlColor = (pos.livePnl || 0) >= 0 ? 'var(--income)' : 'var(--expense)'
                        const mp = getMarketPrice(pos.symbol)
                        return (
                          <tr key={pos.id || pos.symbol}>
                            <td>
                              <span className="badge badge-accent">{pos.symbol}</span>
                              {mp && <span style={{ marginLeft: 4, fontSize: 10, color: 'var(--text-tertiary)' }}>●</span>}
                            </td>
                            <td className="text-right" style={{ fontFamily: 'var(--font-mono)' }}>
                              {fmt(parseFloat(pos.quantity), 4)}
                            </td>
                            <td className="text-right" style={{ fontFamily: 'var(--font-mono)' }}>
                              {pos.avg_cost ? fmt(parseFloat(pos.avg_cost), 4) : '—'}
                            </td>
                            <td className="text-right" style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent)' }}>
                              {pos.livePrice != null ? fmt(pos.livePrice, 4) : '—'}
                            </td>
                            <td className="text-right" style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                              {pos.liveValue != null ? `${sym} ${fmt(pos.liveValue)}` : '—'}
                            </td>
                            <td className="text-right">
                              {pos.livePnl != null ? (
                                <span style={{ fontFamily: 'var(--font-mono)', color: pnlColor }}>
                                  {pos.livePnl >= 0 ? '+' : ''}{sym} {fmt(Math.abs(pos.livePnl))}
                                  {pos.livePct != null && (
                                    <span style={{ fontSize: 11, marginLeft: 4 }}>
                                      ({pos.livePct >= 0 ? '+' : ''}{fmt(pos.livePct, 1)}%)
                                    </span>
                                  )}
                                </span>
                              ) : '—'}
                            </td>
                            <td className="text-right" style={{ fontFamily: 'var(--font-mono)', color: parseFloat(pos.realized_pnl || '0') >= 0 ? 'var(--income)' : 'var(--expense)' }}>
                              {pos.realized_pnl ? `${sym} ${fmt(parseFloat(pos.realized_pnl))}` : '—'}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                )}
              </div>

              {/* Transactions */}
              <div className="card" style={{ padding: 0 }}>
                <div className="card-header">
                  <div className="card-title">{t('investments.recentTransactions')}</div>
                </div>
                {transactions.length === 0 ? (
                  <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)' }}>
                    {t('investments.noTransactions')}
                  </div>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>{t('common.date')}</th>
                        <th>{t('common.type')}</th>
                        <th>{t('investments.table.instrument')}</th>
                        <th style={{ textAlign: 'right' }}>Adet</th>
                        <th style={{ textAlign: 'right' }}>Fiyat</th>
                        <th style={{ textAlign: 'right' }}>Tutar</th>
                        <th style={{ textAlign: 'right' }}>Komisyon</th>
                        <th style={{ textAlign: 'right' }}>Güncel Fiyat</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {transactions.map((tx: any) => {
                        const mp = getMarketPrice(tx.symbol)
                        const livePrice = mp ? parseFloat(mp.price) : null
                        const txPrice = parseFloat(tx.price || '0')
                        const qty = parseFloat(tx.quantity || '0')
                        const gross = qty * txPrice
                        const isBuy = tx.transaction_type === 'BUY'
                        const pnlHint = livePrice && isTrade(tx.transaction_type)
                          ? (livePrice - txPrice) * qty
                          : null
                        return (
                          <tr key={tx.id}>
                            <td style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)' }}>
                              {tx.transaction_date}
                            </td>
                            <td>
                              <span className={`badge ${isBuy ? 'badge-confirmed' : tx.transaction_type === 'SELL' ? 'badge-expense' : 'badge-accent'}`}>
                                {isBuy ? 'Alış' : tx.transaction_type === 'SELL' ? 'Satış' : tx.transaction_type}
                              </span>
                            </td>
                            <td><span className="badge badge-neutral">{tx.symbol || '—'}</span></td>
                            <td className="text-right" style={{ fontFamily: 'var(--font-mono)' }}>{qty > 0 ? fmt(qty, 4) : '—'}</td>
                            <td className="text-right" style={{ fontFamily: 'var(--font-mono)' }}>{txPrice > 0 ? fmt(txPrice, 4) : '—'}</td>
                            <td className="text-right" style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                              {gross > 0 ? fmt(gross) : '—'}
                            </td>
                            <td className="text-right" style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>
                              {tx.commission > 0 ? fmt(parseFloat(tx.commission)) : '—'}
                            </td>
                            <td className="text-right" style={{ fontFamily: 'var(--font-mono)' }}>
                              {livePrice != null ? (
                                <span>
                                  <span style={{ color: 'var(--accent)' }}>{fmt(livePrice, 4)}</span>
                                  {pnlHint != null && (
                                    <span style={{ fontSize: 10, marginLeft: 4, color: pnlHint >= 0 ? 'var(--income)' : 'var(--expense)' }}>
                                      ({pnlHint >= 0 ? '+' : ''}{fmt(pnlHint)})
                                    </span>
                                  )}
                                </span>
                              ) : '—'}
                            </td>
                            <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                              <button
                                className="btn btn-ghost btn-sm"
                                style={{ padding: '2px 8px', marginRight: 4 }}
                                title="Düzenle"
                                onClick={() => openTxModal(tx)}
                              >✎</button>
                              <button
                                className="btn btn-ghost btn-sm"
                                style={{ padding: '2px 8px', color: 'var(--danger)' }}
                                title="Sil"
                                onClick={() => handleDeleteTx(tx)}
                              >✕</button>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* Portfolio Modal */}
      <Modal open={showPortModal} onClose={() => setShowPortModal(false)}>
        <div className="modal-header">
          <div className="modal-title">{t('investments.newPortfolio')}</div>
          <button className="modal-close" onClick={() => setShowPortModal(false)}>✕</button>
        </div>
        <form onSubmit={handlePortSubmit}>
          <div className="modal-body">
            <div className="form-grid">
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label className="form-label">{t('investments.form.portfolioName')} *</label>
                <input className="form-input" required placeholder="ör: Garanti Portföyü"
                  value={portForm.name} onChange={e => setPortForm({ ...portForm, name: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Para Birimi</label>
                <select className="form-input" value={portForm.currency} onChange={e => setPortForm({ ...portForm, currency: e.target.value })}>
                  {['TRY', 'USD', 'EUR', 'GBP'].map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label className="form-label">{t('common.description')}</label>
                <textarea className="form-input" rows={2}
                  value={portForm.description} onChange={e => setPortForm({ ...portForm, description: e.target.value })} />
              </div>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setShowPortModal(false)}>{t('common.cancel')}</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? t('common.saving') : t('common.create')}
            </button>
          </div>
        </form>
      </Modal>

      {/* Transaction Modal */}
      <Modal open={showTxModal} onClose={() => { setShowTxModal(false); setEditingTx(null) }}>
        <div className="modal-header">
          <div className="modal-title">
            {editingTx ? 'İşlemi Düzenle' : t('investments.recordTransaction')}
          </div>
          <button className="modal-close" onClick={() => { setShowTxModal(false); setEditingTx(null) }}>✕</button>
        </div>
        <form onSubmit={handleTxSubmit}>
          <div className="modal-body">
            {txError && (
              <div style={{
                padding: 'var(--space-3)', marginBottom: 'var(--space-4)',
                background: 'rgba(var(--danger-rgb,220,53,69),0.1)', border: '1px solid var(--danger)',
                borderRadius: 'var(--radius-sm)', color: 'var(--danger)', fontSize: 'var(--font-size-sm)',
              }}>
                ⚠ {txError}
              </div>
            )}
            <div className="form-grid">
              {/* Transaction type */}
              <div className="form-group">
                <label className="form-label">İşlem Tipi *</label>
                <select
                  className="form-input"
                  value={txForm.transaction_type}
                  onChange={e => setTxForm({ ...txForm, transaction_type: e.target.value })}
                >
                  <option value="BUY">Alış</option>
                  <option value="SELL">Satış</option>
                  <option value="DIVIDEND">Temettü</option>
                  <option value="INTEREST_INCOME">Faiz Geliri</option>
                  <option value="FEE">Ücret/Gider</option>
                </select>
              </div>

              {/* Symbol */}
              <div className="form-group">
                <label className="form-label">Sembol {showTrade && '*'}</label>
                <SymbolCombo
                  value={txForm.symbol}
                  marketPrices={marketPrices}
                  onAddSymbol={handleAddSymbol}
                  onChange={(symbol, price) => {
                    const mp = marketPrices.find((m: any) => m.symbol === symbol.toUpperCase())
                    const resolved = price != null && price > 0
                      ? price
                      : (mp && parseFloat(mp.price) > 0 ? parseFloat(mp.price) : null)
                    setTxForm(prev => ({
                      ...prev,
                      symbol,
                      price: resolved != null ? String(resolved) : prev.price,
                    }))
                  }}
                />
                {txForm.symbol && (() => {
                  const mp = getMarketPrice(txForm.symbol)
                  if (!mp || parseFloat(mp.price) <= 0) return null
                  return (
                    <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>
                      Piyasa fiyatı: <strong style={{ color: 'var(--accent)' }}>{fmt(parseFloat(mp.price), 4)} {mp.currency}</strong>
                      {' '}<button type="button" style={{ fontSize: 11, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                        onClick={() => setTxForm(prev => ({ ...prev, price: String(mp.price) }))}>
                        Uygula
                      </button>
                    </div>
                  )
                })()}
              </div>

              {/* Quantity */}
              <div className="form-group">
                <label className="form-label">Adet {showTrade && '*'}</label>
                <input
                  className="form-input" type="number" step="0.000001" min="0"
                  required={showTrade} placeholder="0"
                  value={txForm.quantity}
                  onChange={e => setTxForm({ ...txForm, quantity: e.target.value })}
                />
              </div>

              {/* Price */}
              <div className="form-group">
                <label className="form-label">
                  Fiyat {showTrade && '*'}
                  {txForm.symbol && (() => {
                    const mp = getMarketPrice(txForm.symbol)
                    const lp = mp ? parseFloat(mp.price) : 0
                    const tp = parseFloat(txForm.price || '0')
                    if (!mp || lp <= 0 || tp <= 0) return null
                    const diff = ((tp - lp) / lp) * 100
                    return (
                      <span style={{ marginLeft: 8, fontWeight: 400, fontSize: 11, color: Math.abs(diff) > 5 ? 'var(--warning, orange)' : 'var(--text-tertiary)' }}>
                        (piyasa: {fmt(lp, 4)}{Math.abs(diff) > 0.01 ? `, fark: ${diff >= 0 ? '+' : ''}${fmt(diff, 1)}%` : ''})
                      </span>
                    )
                  })()}
                </label>
                <input
                  className="form-input" type="number" step="0.000001" min="0"
                  required={showTrade} placeholder="0.00"
                  value={txForm.price}
                  onChange={e => setTxForm({ ...txForm, price: e.target.value })}
                />
              </div>

              {/* Fee */}
              <div className="form-group">
                <label className="form-label">Komisyon</label>
                <input
                  className="form-input" type="number" step="0.01" min="0" placeholder="0.00"
                  value={txForm.fee}
                  onChange={e => setTxForm({ ...txForm, fee: e.target.value })}
                />
              </div>

              {/* Date */}
              <div className="form-group">
                <label className="form-label">{t('common.date')} *</label>
                <input
                  className="form-input" type="date" required
                  value={txForm.transaction_date}
                  onChange={e => setTxForm({ ...txForm, transaction_date: e.target.value })}
                />
              </div>

              {/* Notes */}
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label className="form-label">{t('common.notes')}</label>
                <input className="form-input" placeholder="İsteğe bağlı not"
                  value={txForm.notes} onChange={e => setTxForm({ ...txForm, notes: e.target.value })} />
              </div>

              {/* Summary */}
              {txForm.quantity && txForm.price && parseFloat(txForm.quantity) > 0 && parseFloat(txForm.price) > 0 && (
                <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                  {(() => {
                    const qty = parseFloat(txForm.quantity)
                    const prc = parseFloat(txForm.price)
                    const comm = parseFloat(txForm.fee || '0')
                    const gross = qty * prc
                    const total = txForm.transaction_type === 'BUY' ? gross + comm : gross - comm
                    const isBuy = txForm.transaction_type === 'BUY'
                    return (
                      <div style={{ padding: 'var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', fontSize: 'var(--font-size-sm)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                          <span style={{ color: 'var(--text-tertiary)' }}>Brüt tutar ({qty} × {prc}):</span>
                          <span style={{ fontFamily: 'var(--font-mono)' }}>{fmt(gross)}</span>
                        </div>
                        {comm > 0 && (
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                            <span style={{ color: 'var(--text-tertiary)' }}>Komisyon:</span>
                            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--expense)' }}>−{fmt(comm)}</span>
                          </div>
                        )}
                        <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border)', paddingTop: 4 }}>
                          <span style={{ fontWeight: 600 }}>{isBuy ? 'Hesaptan çıkacak:' : 'Hesaba girecek:'}</span>
                          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: isBuy ? 'var(--expense)' : 'var(--income)' }}>
                            {fmt(total)}
                          </span>
                        </div>
                      </div>
                    )
                  })()}
                </div>
              )}
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => { setShowTxModal(false); setEditingTx(null) }}>
              {t('common.cancel')}
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? t('common.saving') : (editingTx ? 'Güncelle' : t('common.create'))}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
