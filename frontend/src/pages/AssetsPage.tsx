import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { assetsApi, accountsApi, loansApi, tenantApi, marketApi, groupsApi } from '../api/umay'
import { usePermissions } from '../hooks/usePermissions'

const TYPE_ICON: Record<string, string> = {
  REAL_ESTATE: '🏠', VEHICLE: '🚗', EQUIPMENT: '⚙️',
  FINANCIAL: '📈', LAND: '🏕️', OTHER: '📦',
  SECURITY: '📊', CRYPTO: '₿', COLLECTIBLE: '🎨',
}
const STATUS_CLASS: Record<string, string> = {
  OWNED: 'badge-confirmed', SOLD: 'badge-draft',
  LEASED: 'badge-accent', DISPOSED: 'badge-neutral',
}
const STATUS_LABELS: Record<string, string> = {
  OWNED: 'Sahip', SOLD: 'Satıldı', LEASED: 'Kirada', DISPOSED: 'Elden Çıkarıldı',
}
const TYPE_LABELS: Record<string, string> = {
  REAL_ESTATE: 'Gayrimenkul', VEHICLE: 'Araç', EQUIPMENT: 'Ekipman',
  FINANCIAL: 'Finansal', LAND: 'Arsa',
  SECURITY: 'Menkul Kıymet', CRYPTO: 'Kripto', COLLECTIBLE: 'Koleksiyon', OTHER: 'Diğer',
}

const EMPTY_FORM: Record<string, any> = {
  name: '', asset_type: 'REAL_ESTATE', status: 'OWNED',
  purchase_date: new Date().toISOString().slice(0, 10),
  purchase_value: '', current_value: '', currency: 'TRY', fx_rate: '1',
  description: '', notes: '',
  source_account_ids: [], loan_ids: [], group_id: '',
}

function fmt(val: any, currency?: string) {
  const n = Number(val) || 0
  const num = n.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return currency ? `${currency} ${num}` : num
}

export function AssetsPage() {
  const { t } = useTranslation()
  const { can } = usePermissions()
  const canCreate = can('assets', 'create') || can('assets', 'manage')
  const canUpdate = can('assets', 'update') || can('assets', 'manage')
  const canDelete = can('assets', 'delete') || can('assets', 'manage')
  const [assets, setAssets] = useState<any[]>([])
  const [accounts, setAccounts] = useState<any[]>([])
  const [loans, setLoans] = useState<any[]>([])
  const [groups, setGroups] = useState<any[]>([])
  const [baseCurrency, setBaseCurrency] = useState('TRY')
  // fxRates: { 'USD': 38.5, 'EUR': 41.2, ... } — base currency karşılığı
  const [fxRates, setFxRates] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const [filterType, setFilterType] = useState('ALL')

  // Create modal
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState<Record<string, any>>({ ...EMPTY_FORM })
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')

  // Valuation modal
  const [showValModal, setShowValModal] = useState(false)
  const [selectedAsset, setSelectedAsset] = useState<any>(null)
  const [valForm, setValForm] = useState({ value: '', valuation_date: new Date().toISOString().slice(0, 10), notes: '' })

  // History modal
  const [showHistoryModal, setShowHistoryModal] = useState(false)
  const [historyAsset, setHistoryAsset] = useState<any>(null)
  const [valuations, setValuations] = useState<any[]>([])
  const [histLoading, setHistLoading] = useState(false)

  // Sell modal
  const [showSellModal, setShowSellModal] = useState(false)
  const [sellAsset, setSellAsset] = useState<any>(null)
  const [sellForm, setSellForm] = useState({
    sale_date: new Date().toISOString().slice(0, 10),
    sale_value: '', sale_currency: '', sale_notes: '', target_account_id: '', is_sold: true,
  })
  const [selling, setSelling] = useState(false)
  const [sellError, setSellError] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const r = await assetsApi.list({ skip: 0, limit: 200 })
      const list: any[] = r.data || []
      setAssets(list)
      // Benzersiz yabancı para birimleri için piyasa kurlarını çek
      const base = baseCurrency || 'TRY'
      const foreignCurrencies = [...new Set(list.map((a: any) => a.currency).filter((c: string) => c !== base))]
      if (foreignCurrencies.length > 0) {
        const symbols = foreignCurrencies.map(c => `${c}${base}`)
        try {
          const pr = await marketApi.getCurrentPrices(symbols)
          const rates: Record<string, number> = {}
          for (const cur of foreignCurrencies) {
            const sym = `${cur}${base}`
            if (pr.data[sym]) rates[cur] = pr.data[sym].price
          }
          setFxRates(rates)
        } catch { /* piyasa verisi yoksa asset'in kayıtlı fx_rate'ini kullan */ }
      }
    } catch { }
    finally { setLoading(false) }
  }

  useEffect(() => {
    accountsApi.list().then(r => setAccounts(r.data?.items || r.data || [])).catch(() => {})
    loansApi.list({ skip: 0, limit: 100 }).then(r => setLoans(r.data?.items || r.data || [])).catch(() => {})
    groupsApi.list({ skip: 0, limit: 100 }).then(r => setGroups(r.data?.items || r.data || [])).catch(() => {})
    tenantApi.me().then(r => {
      setBaseCurrency(r.data?.base_currency || 'TRY')
    }).catch(() => {})
  }, [])

  // baseCurrency yüklendikten sonra asset listesini çek
  useEffect(() => { load() }, [baseCurrency])

  const filtered = filterType === 'ALL' ? assets : assets.filter(a => a.asset_type === filterType)

  // Bir varlık için efektif kur: piyasadan gelen > kayıtlı fx_rate > 1
  const effectiveFx = (a: any) =>
    a.currency === baseCurrency ? 1 : (fxRates[a.currency] ?? Number(a.fx_rate) ?? 1)

  // KPI: tüm varlıkların baz para birimindeki değeri
  const ownedAssets = assets.filter(a => a.status === 'OWNED')
  const totalBase = ownedAssets.reduce((s, a) => s + Number(a.current_value) * effectiveFx(a), 0)
  const purchaseBase = ownedAssets.reduce((s, a) => s + Number(a.purchase_value) * effectiveFx(a), 0)
  const gainBase = totalBase - purchaseBase

  const openHistory = async (a: any) => {
    setHistoryAsset(a)
    setShowHistoryModal(true)
    setHistLoading(true)
    try {
      const r = await assetsApi.getValuations(a.id)
      setValuations(r.data || [])
    } catch { setValuations([]) }
    finally { setHistLoading(false) }
  }

  const openSell = (a: any) => {
    setSellAsset(a)
    setSellForm({
      sale_date: new Date().toISOString().slice(0, 10),
      sale_value: String(Number(a.current_value) || ''),
      sale_currency: a.currency,
      sale_notes: '', target_account_id: '', is_sold: true,
    })
    setSellError('')
    setShowSellModal(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setFormError('')
    try {
      await assetsApi.create({
        ...form,
        purchase_value: parseFloat(form.purchase_value),
        current_value: parseFloat(form.current_value),
        fx_rate: parseFloat(form.fx_rate) || 1,
        source_account_ids: form.source_account_ids || [],
        loan_ids: form.loan_ids || [],
        group_id: form.group_id || undefined,
      })
      setShowModal(false)
      setForm({ ...EMPTY_FORM })
      load()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setFormError(Array.isArray(detail) ? detail.map((d: any) => d.msg).join(', ') : (detail || 'Hata'))
    } finally { setSaving(false) }
  }

  const handleValuation = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedAsset) return
    setSaving(true)
    try {
      await assetsApi.addValuation(selectedAsset.id, {
        value: parseFloat(valForm.value),
        valuation_date: valForm.valuation_date,
        notes: valForm.notes,
        currency: selectedAsset.currency,
      })
      setShowValModal(false)
      setValForm({ value: '', valuation_date: new Date().toISOString().slice(0, 10), notes: '' })
      load()
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Hata')
    } finally { setSaving(false) }
  }

  const handleSell = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!sellAsset) return
    setSelling(true)
    setSellError('')
    try {
      await assetsApi.dispose(sellAsset.id, {
        sale_date: sellForm.sale_date,
        sale_value: sellForm.sale_value ? parseFloat(sellForm.sale_value) : undefined,
        sale_notes: sellForm.sale_notes || undefined,
        is_sold: sellForm.is_sold,
        target_account_id: sellForm.target_account_id || undefined,
      })
      setShowSellModal(false)
      load()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setSellError(Array.isArray(detail) ? detail.map((d: any) => d.msg).join(', ') : (detail || 'Hata'))
    } finally { setSelling(false) }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Silmek istediğinizden emin misiniz?')) return
    await assetsApi.delete(id).catch(() => {})
    load()
  }

  const TYPES = ['ALL', 'REAL_ESTATE', 'VEHICLE', 'EQUIPMENT', 'FINANCIAL', 'LAND', 'SECURITY', 'CRYPTO', 'COLLECTIBLE', 'OTHER']

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Varlıklar</h1>
          <p className="page-subtitle">{assets.length} varlık</p>
        </div>
        {canCreate && (
          <button className="btn btn-primary" onClick={() => { setForm({ ...EMPTY_FORM }); setFormError(''); setShowModal(true) }}>
            + Yeni Varlık
          </button>
        )}
      </div>

      {/* KPI */}
      {assets.length > 0 && (
        <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 'var(--space-6)' }}>
          <div className="stat-card">
            <div className="stat-card-label">Toplam Değer ({baseCurrency})</div>
            <div className="stat-card-value" style={{ color: 'var(--accent)' }}>
              {baseCurrency} {fmt(totalBase)}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-card-label">Kar / Zarar ({baseCurrency})</div>
            <div className="stat-card-value" style={{ color: gainBase >= 0 ? 'var(--income)' : 'var(--expense)' }}>
              {gainBase >= 0 ? '+' : ''}{baseCurrency} {fmt(Math.abs(gainBase))}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-card-label">Aktif Varlık</div>
            <div className="stat-card-value">{ownedAssets.length}</div>
          </div>
        </div>
      )}

      {/* Type Filter */}
      <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', marginBottom: 'var(--space-4)' }}>
        {TYPES.map(typ => (
          <button
            key={typ}
            className={`btn btn-sm ${filterType === typ ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilterType(typ)}
          >
            {typ === 'ALL' ? 'Tümü' : `${TYPE_ICON[typ] || ''} ${TYPE_LABELS[typ] || typ}`}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="loading-state"><div className="spinner" /></div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🏠</div>
          <div className="empty-state-title">Varlık bulunamadı</div>
          <div className="empty-state-desc">Henüz varlık eklenmemiş</div>
          {canCreate && <button className="btn btn-primary" onClick={() => setShowModal(true)}>+ Ekle</button>}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 'var(--space-4)' }}>
          {filtered.map((a: any) => {
            const gainAmt = Number(a.current_value) - Number(a.purchase_value)
            const gainPct = Number(a.purchase_value) ? ((gainAmt / Number(a.purchase_value)) * 100).toFixed(1) : '0'
            const fx = effectiveFx(a)
            const baseVal = Number(a.current_value) * fx
            const showFx = a.currency !== baseCurrency
            return (
              <div key={a.id} className="card" style={{ position: 'relative', cursor: 'pointer' }}
                onClick={() => openHistory(a)}>
                {/* Action buttons */}
                <div style={{ position: 'absolute', top: 'var(--space-3)', right: 'var(--space-3)', display: 'flex', gap: 4 }}
                  onClick={e => e.stopPropagation()}>
                  {canUpdate && (
                    <button
                      className="btn btn-ghost btn-sm"
                      style={{ padding: '2px 6px', fontSize: 12 }}
                      onClick={() => { setSelectedAsset(a); setValForm({ value: String(Number(a.current_value)), valuation_date: new Date().toISOString().slice(0, 10), notes: '' }); setShowValModal(true) }}
                      title="Değer güncelle"
                    >📊</button>
                  )}
                  {canUpdate && a.status === 'OWNED' && (
                    <button
                      className="btn btn-sm btn-success"
                      style={{ padding: '2px 8px', fontSize: 11 }}
                      onClick={() => openSell(a)}
                      title="Sat"
                    >Sat</button>
                  )}
                  {canDelete && (
                    <button
                      className="btn btn-ghost btn-sm"
                      style={{ color: 'var(--danger)', padding: '2px 6px' }}
                      onClick={() => handleDelete(a.id)}
                      title="Sil"
                    >✕</button>
                  )}
                </div>

                {/* Header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
                  <span style={{ fontSize: 28 }}>{TYPE_ICON[a.asset_type] || '📦'}</span>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    <span className="badge badge-accent">{TYPE_LABELS[a.asset_type] || a.asset_type}</span>
                    <span className={`badge ${STATUS_CLASS[a.status] || 'badge-neutral'}`}>{STATUS_LABELS[a.status] || a.status}</span>
                    {a.currency !== 'TRY' && <span className="badge badge-neutral">{a.currency}</span>}
                  </div>
                </div>

                <div style={{ fontWeight: 600, fontSize: 'var(--font-size-md)', marginBottom: 4 }}>{a.name}</div>
                {a.description && (
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 'var(--space-3)' }}>
                    {a.description}
                  </div>
                )}

                {/* Values */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: 'var(--space-3)' }}>
                  <div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>Güncel Değer</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 'var(--font-size-lg)', color: 'var(--accent)' }}>
                      {fmt(a.current_value, a.currency)}
                    </div>
                    {showFx && (
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
                        ≈ {fmt(baseVal, baseCurrency)}
                      </div>
                    )}
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>Kar / Zarar</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 'var(--font-size-sm)', color: gainAmt >= 0 ? 'var(--income)' : 'var(--expense)' }}>
                      {gainAmt >= 0 ? '+' : ''}{fmt(Math.abs(gainAmt), a.currency)}
                      <span style={{ fontSize: 'var(--font-size-xs)', opacity: 0.7, marginLeft: 4 }}>({gainPct}%)</span>
                    </div>
                  </div>
                </div>

                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 'var(--space-2)', borderTop: '1px solid var(--border)', paddingTop: 'var(--space-2)' }}>
                  Alış: {a.purchase_date} · {fmt(a.purchase_value, a.currency)}
                  {showFx && (
                    <span style={{ marginLeft: 4 }}>
                      · 1 {a.currency} = {fx.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 4 })} {baseCurrency}
                      {fxRates[a.currency] ? <span style={{ color: 'var(--income)', marginLeft: 4 }}>(piyasa)</span> : <span style={{ opacity: 0.6, marginLeft: 4 }}>(kayıtlı)</span>}
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* ── Yeni Varlık Modalı ───────────────────────────── */}
      {showModal && (
        <div className="modal-backdrop" onClick={e => e.target === e.currentTarget && setShowModal(false)}>
          <div className="modal" style={{ maxWidth: 560 }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">Yeni Varlık</span>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {formError && <div className="alert alert-danger" style={{ marginBottom: 'var(--space-4)' }}>{formError}</div>}
                <div className="form-grid">
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label className="form-label">İsim *</label>
                    <input className="form-input" required autoFocus
                      value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Tür *</label>
                    <select className="form-input" value={form.asset_type} onChange={e => setForm({ ...form, asset_type: e.target.value })}>
                      {Object.entries(TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{TYPE_ICON[v]} {l}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Durum</label>
                    <select className="form-input" value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>
                      {Object.entries(STATUS_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Alış Tarihi *</label>
                    <input className="form-input" type="date" required
                      value={form.purchase_date} onChange={e => setForm({ ...form, purchase_date: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Para Birimi</label>
                    <select className="form-input" value={form.currency} onChange={e => setForm({ ...form, currency: e.target.value, fx_rate: e.target.value === baseCurrency ? '1' : form.fx_rate })}>
                      {['TRY', 'USD', 'EUR', 'GBP', 'CHF', 'JPY', 'XAU'].map(c => <option key={c}>{c}</option>)}
                    </select>
                  </div>
                  {form.currency !== baseCurrency && (
                    <div className="form-group">
                      <label className="form-label" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>Döviz Kuru (1 {form.currency} = ? {baseCurrency})</span>
                        <button type="button" className="btn btn-ghost btn-sm" style={{ fontSize: 11, padding: '1px 6px' }}
                          onClick={async () => {
                            try {
                              const r = await marketApi.getCurrentPrices([`${form.currency}${baseCurrency}`])
                              const sym = `${form.currency}${baseCurrency}`
                              if (r.data[sym]) setForm(f => ({ ...f, fx_rate: String(r.data[sym].price) }))
                            } catch { alert('Piyasa verisi bulunamadı') }
                          }}>
                          📡 Piyasadan al
                        </button>
                      </label>
                      <input className="form-input" type="number" step="0.0001" min="0.0001"
                        placeholder="Örn: 38.50"
                        value={form.fx_rate} onChange={e => setForm({ ...form, fx_rate: e.target.value })} />
                    </div>
                  )}
                  <div className="form-group">
                    <label className="form-label">Alış Fiyatı ({form.currency}) *</label>
                    <input className="form-input" type="number" step="0.01" min="0" required placeholder="0.00"
                      value={form.purchase_value} onChange={e => setForm({ ...form, purchase_value: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Güncel Değer ({form.currency}) *</label>
                    <input className="form-input" type="number" step="0.01" min="0" required placeholder="0.00"
                      value={form.current_value} onChange={e => setForm({ ...form, current_value: e.target.value })} />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label className="form-label">Kaynak Hesaplar <span style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>(alım parası hangi hesaplardan çıktı?)</span></label>
                    <select className="form-input"
                      onChange={e => {
                        const id = e.target.value
                        if (!id || form.source_account_ids.includes(id)) return
                        setForm({ ...form, source_account_ids: [...form.source_account_ids, id] })
                        e.target.value = ''
                      }}>
                      <option value="">+ Hesap ekle</option>
                      {accounts.filter((ac: any) => !form.source_account_ids.includes(ac.id)).map((ac: any) => (
                        <option key={ac.id} value={ac.id}>{ac.name} ({ac.currency})</option>
                      ))}
                    </select>
                    {form.source_account_ids.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
                        {form.source_account_ids.map((id: string) => {
                          const ac = accounts.find((a: any) => a.id === id)
                          return (
                            <span key={id} className="badge badge-accent" style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                              {ac ? `${ac.name} (${ac.currency})` : id}
                              <span onClick={() => setForm({ ...form, source_account_ids: form.source_account_ids.filter((x: string) => x !== id) })} style={{ fontWeight: 700, marginLeft: 2 }}>×</span>
                            </span>
                          )
                        })}
                      </div>
                    )}
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label className="form-label">Kredi Bağlantıları <span style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>(opsiyonel)</span></label>
                    <select className="form-input"
                      onChange={e => {
                        const id = e.target.value
                        if (!id || form.loan_ids.includes(id)) return
                        setForm({ ...form, loan_ids: [...form.loan_ids, id] })
                        e.target.value = ''
                      }}>
                      <option value="">+ Kredi ekle</option>
                      {loans.filter((l: any) => !form.loan_ids.includes(l.id)).map((l: any) => (
                        <option key={l.id} value={l.id}>{l.lender_name} · {fmt(l.principal, l.currency)}</option>
                      ))}
                    </select>
                    {form.loan_ids.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
                        {form.loan_ids.map((id: string) => {
                          const l = loans.find((x: any) => x.id === id)
                          return (
                            <span key={id} className="badge badge-neutral" style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                              {l ? `${l.lender_name} · ${fmt(l.principal, l.currency)}` : id}
                              <span onClick={() => setForm({ ...form, loan_ids: form.loan_ids.filter((x: string) => x !== id) })} style={{ fontWeight: 700, marginLeft: 2 }}>×</span>
                            </span>
                          )
                        })}
                      </div>
                    )}
                  </div>
                  {groups.length > 0 && (
                    <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                      <label className="form-label">Grup</label>
                      <select className="form-input" value={form.group_id || ''} onChange={e => setForm({ ...form, group_id: e.target.value })}>
                        <option value="">— Gruba bağlama</option>
                        {groups.map((g: any) => (
                          <option key={g.id} value={g.id}>{g.name}</option>
                        ))}
                      </select>
                    </div>
                  )}
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label className="form-label">Açıklama</label>
                    <input className="form-input" placeholder="Opsiyonel"
                      value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>İptal</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Kaydediliyor…' : 'Ekle'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Değer Güncelle Modalı ────────────────────────── */}
      {showValModal && (
        <div className="modal-backdrop" onClick={e => e.target === e.currentTarget && setShowValModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">Değer Güncelle — {selectedAsset?.name}</span>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowValModal(false)}>✕</button>
            </div>
            <form onSubmit={handleValuation}>
              <div className="modal-body">
                <div className="form-grid">
                  <div className="form-group">
                    <label className="form-label">Yeni Değer ({selectedAsset?.currency}) *</label>
                    <input className="form-input" type="number" step="0.01" min="0" required autoFocus
                      value={valForm.value} onChange={e => setValForm({ ...valForm, value: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Değerleme Tarihi *</label>
                    <input className="form-input" type="date" required
                      value={valForm.valuation_date} onChange={e => setValForm({ ...valForm, valuation_date: e.target.value })} />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label className="form-label">Not</label>
                    <textarea className="form-input" rows={2} placeholder="Kaynak veya açıklama"
                      value={valForm.notes} onChange={e => setValForm({ ...valForm, notes: e.target.value })} />
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowValModal(false)}>İptal</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Kaydediliyor…' : 'Güncelle'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Fiyat Geçmişi Modalı ────────────────────────── */}
      {showHistoryModal && historyAsset && (
        <div className="modal-backdrop" onClick={e => e.target === e.currentTarget && setShowHistoryModal(false)}>
          <div className="modal" style={{ maxWidth: 520 }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">{TYPE_ICON[historyAsset.asset_type] || '📦'} {historyAsset.name} — Fiyat Geçmişi</span>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowHistoryModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              {histLoading ? (
                <div className="loading-state"><div className="spinner" /></div>
              ) : valuations.length === 0 ? (
                <div style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: 'var(--space-6)' }}>Değerleme kaydı yok</div>
              ) : (
                <table className="table" style={{ width: '100%' }}>
                  <thead>
                    <tr>
                      <th>Tarih</th>
                      <th className="text-right">Değer</th>
                      {historyAsset.currency !== baseCurrency && <th className="text-right">{baseCurrency} Karşılığı</th>}
                      <th>Kaynak</th>
                    </tr>
                  </thead>
                  <tbody>
                    {valuations.map((v: any, i: number) => {
                      const prev = valuations[i + 1]
                      const change = prev ? Number(v.value) - Number(prev.value) : null
                      const baseEquiv = Number(v.value) * Number(historyAsset.fx_rate || 1)
                      return (
                        <tr key={v.id}>
                          <td style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)' }}>{v.valuation_date}</td>
                          <td className="text-right" style={{ fontFamily: 'var(--font-mono)' }}>
                            <span>{fmt(v.value, v.currency)}</span>
                            {change !== null && (
                              <span style={{ fontSize: 10, marginLeft: 6, color: change >= 0 ? 'var(--income)' : 'var(--expense)' }}>
                                {change >= 0 ? '▲' : '▼'} {fmt(Math.abs(change))}
                              </span>
                            )}
                          </td>
                          {historyAsset.currency !== baseCurrency && (
                            <td className="text-right" style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
                              ≈ {fmt(baseEquiv, baseCurrency)}
                            </td>
                          )}
                          <td style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>
                            {v.source || '—'}{v.notes ? ` · ${v.notes}` : ''}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => { setSelectedAsset(historyAsset); setValForm({ value: String(Number(historyAsset.current_value)), valuation_date: new Date().toISOString().slice(0, 10), notes: '' }); setShowValModal(true); setShowHistoryModal(false) }}>
                + Yeni Değerleme
              </button>
              <button className="btn btn-ghost" onClick={() => setShowHistoryModal(false)}>Kapat</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Satış Modalı ────────────────────────────────── */}
      {showSellModal && sellAsset && (
        <div className="modal-backdrop" onClick={e => e.target === e.currentTarget && setShowSellModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">Varlık Sat — {sellAsset.name}</span>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowSellModal(false)}>✕</button>
            </div>
            <form onSubmit={handleSell}>
              <div className="modal-body">
                {sellError && <div className="alert alert-danger" style={{ marginBottom: 'var(--space-4)' }}>{sellError}</div>}
                <div className="form-grid">
                  <div className="form-group">
                    <label className="form-label">Satış Tarihi *</label>
                    <input className="form-input" type="date" required
                      value={sellForm.sale_date} onChange={e => setSellForm({ ...sellForm, sale_date: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Satış Para Birimi</label>
                    <select className="form-input" value={sellForm.sale_currency}
                      onChange={e => setSellForm({ ...sellForm, sale_currency: e.target.value, target_account_id: '' })}>
                      {['TRY', 'USD', 'EUR', 'GBP', 'CHF'].map(c => <option key={c}>{c}</option>)}
                    </select>
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label className="form-label">Satış Tutarı ({sellForm.sale_currency || sellAsset.currency})</label>
                    <input className="form-input" type="number" step="0.01" min="0" placeholder="0.00"
                      value={sellForm.sale_value} onChange={e => setSellForm({ ...sellForm, sale_value: e.target.value })} />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label className="form-label">Paranın Gittiği Hesap
                      {sellForm.sale_currency && <span style={{ fontWeight: 400, color: 'var(--text-tertiary)', marginLeft: 6 }}>({sellForm.sale_currency} hesaplar gösteriliyor)</span>}
                    </label>
                    <select className="form-input" value={sellForm.target_account_id} onChange={e => setSellForm({ ...sellForm, target_account_id: e.target.value })}>
                      <option value="">— Seçilmedi (sadece kayıt)</option>
                      {accounts
                        .filter((ac: any) => !sellForm.sale_currency || ac.currency === sellForm.sale_currency)
                        .map((ac: any) => (
                          <option key={ac.id} value={ac.id}>{ac.name} ({ac.currency})</option>
                        ))}
                    </select>
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <input type="checkbox" checked={sellForm.is_sold} onChange={e => setSellForm({ ...sellForm, is_sold: e.target.checked })} />
                      Satış (işaretlenmezse "Elden Çıkarıldı" olarak kaydedilir)
                    </label>
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label className="form-label">Not</label>
                    <textarea className="form-input" rows={2}
                      value={sellForm.sale_notes} onChange={e => setSellForm({ ...sellForm, sale_notes: e.target.value })} />
                  </div>
                </div>
                {sellForm.sale_value && Number(sellForm.sale_value) > 0 && (
                  <div style={{ background: 'var(--surface-2)', borderRadius: 'var(--radius)', padding: 'var(--space-3)', marginTop: 'var(--space-3)', fontSize: 'var(--font-size-sm)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Alış Değeri</span><span style={{ fontFamily: 'var(--font-mono)' }}>{fmt(sellAsset.purchase_value, sellAsset.currency)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Satış Değeri</span><span style={{ fontFamily: 'var(--font-mono)' }}>{fmt(sellForm.sale_value, sellAsset.currency)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600, borderTop: '1px solid var(--border)', marginTop: 4, paddingTop: 4 }}>
                      <span>Kar / Zarar</span>
                      <span style={{ fontFamily: 'var(--font-mono)', color: (Number(sellForm.sale_value) - Number(sellAsset.purchase_value)) >= 0 ? 'var(--income)' : 'var(--expense)' }}>
                        {(Number(sellForm.sale_value) - Number(sellAsset.purchase_value)) >= 0 ? '+' : ''}
                        {fmt(Number(sellForm.sale_value) - Number(sellAsset.purchase_value), sellAsset.currency)}
                      </span>
                    </div>
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowSellModal(false)}>İptal</button>
                <button type="submit" className="btn btn-primary" disabled={selling}>{selling ? 'Kaydediliyor…' : 'Satışı Kaydet'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
