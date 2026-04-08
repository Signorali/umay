import React, { useEffect, useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { calendarApi } from '../api/umay'

/* ── helpers ── */
const DAYS_TR = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz']
const MONTHS_TR = ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık']

function isoDate(d: Date) { return d.toISOString().slice(0, 10) }

function getDaysInMonth(year: number, month: number) {
  return new Date(year, month + 1, 0).getDate()
}

// Returns 0=Mon … 6=Sun (ISO, week starts Mon)
function getFirstDayOfMonth(year: number, month: number) {
  const d = new Date(year, month, 1).getDay()
  return d === 0 ? 6 : d - 1
}

function fmtAmount(amount: number | null, currency: string) {
  if (amount == null) return ''
  const sym = currency === 'TRY' ? '₺' : currency === 'USD' ? '$' : currency === 'EUR' ? '€' : (currency || '')
  return `${sym}${amount.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}`
}

const TYPE_LABEL: Record<string, string> = {
  PLANNED_PAYMENT: 'Planlı Ödeme',
  LOAN_INSTALLMENT: 'Kredi Taksiti',
  CARD_DUE: 'Kart Ekstresi',
  CREDIT_CARD_DUE: 'Kart Ekstresi',
  CUSTOM: 'Hatırlatıcı',
}

function getSourceUrl(item: any): string | null {
  if (item.linked_planned_payment_id) return '/planned-payments'
  if (item.linked_loan_installment_id) return '/loans'
  if (item.linked_credit_card_id) return '/credit-cards'
  return null
}

function isIncome(item: any): boolean {
  return (item.description || '').toUpperCase() === 'INCOME'
}

/* ── DayCell ── */
function DayCell({ day, dateStr, items, today, selected, onSelect }: {
  day: number; dateStr: string; items: any[]; today: string
  selected: string | null; onSelect: (d: string) => void
}) {
  const isToday = dateStr === today
  const isSelected = dateStr === selected
  const incomeItems = items.filter(isIncome)
  const expenseItems = items.filter(i => !isIncome(i))

  return (
    <div
      onClick={() => items.length > 0 && onSelect(dateStr)}
      style={{
        minHeight: 76, padding: '4px 5px',
        border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--border-subtle)'}`,
        borderRadius: 'var(--radius-sm)',
        background: isSelected ? 'rgba(99,102,241,0.08)' : isToday ? 'rgba(99,102,241,0.04)' : 'var(--bg-surface)',
        cursor: items.length > 0 ? 'pointer' : 'default',
        transition: 'background 0.15s, border-color 0.15s',
        position: 'relative',
      }}
    >
      {/* Day number */}
      <div style={{ fontSize: 11, marginBottom: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={isToday ? {
          background: 'var(--accent)', color: '#fff',
          width: 19, height: 19, borderRadius: '50%',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 700,
        } : { color: 'var(--text-secondary)', fontWeight: isToday ? 700 : 400 }}>{day}</span>
        {items.length > 0 && <span style={{ fontSize: 9, color: 'var(--text-tertiary)' }}>{items.length}</span>}
      </div>

      {/* Pins */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {expenseItems.slice(0, 2).map((item: any) => (
          <div key={item.id} style={{
            fontSize: 9, lineHeight: '14px', padding: '0 4px',
            background: 'rgba(239,68,68,0.12)', color: '#ef4444',
            border: '1px solid rgba(239,68,68,0.25)', borderRadius: 3,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>🔴 {item.title}</div>
        ))}
        {incomeItems.slice(0, 2).map((item: any) => (
          <div key={item.id} style={{
            fontSize: 9, lineHeight: '14px', padding: '0 4px',
            background: 'rgba(34,197,94,0.12)', color: '#22c55e',
            border: '1px solid rgba(34,197,94,0.25)', borderRadius: 3,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>🟢 {item.title}</div>
        ))}
        {items.length > 4 && (
          <div style={{ fontSize: 9, color: 'var(--text-tertiary)', paddingLeft: 2 }}>+{items.length - 4} daha</div>
        )}
      </div>
    </div>
  )
}

/* ── Integration Panel ── */
function IntegrationPanel() {
  const [data, setData] = useState<any>(null)
  const [syncing, setSyncing] = useState(false)
  const [disconnecting, setDisconnecting] = useState<string | null>(null)

  const load = async () => {
    try { const r = await calendarApi.integrations(); setData(r.data) } catch { }
  }

  useEffect(() => { load() }, [])

  const handleSync = async () => {
    setSyncing(true)
    try { await calendarApi.syncExternal(); await load() } catch { }
    setSyncing(false)
  }

  const handleDisconnect = async (provider: string) => {
    if (!window.confirm(`${provider === 'google' ? 'Google' : 'Outlook'} bağlantısını kesmek istediğinize emin misiniz?`)) return
    setDisconnecting(provider)
    try { await calendarApi.disconnect(provider); await load() } catch { }
    setDisconnecting(null)
  }

  if (!data) return null

  const providers = [
    { key: 'google', label: 'Google Takvim', icon: '🗓️', color: '#4285F4' },
    { key: 'microsoft', label: 'Outlook Takvim', icon: '📅', color: '#0078D4' },
  ]

  const connected = (data.integrations || [])
  const providerInfo = data.providers || {}

  return (
    <div className="card" style={{ padding: 'var(--space-4)', marginBottom: 'var(--space-4)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
        <h3 style={{ margin: 0, fontSize: 'var(--font-size-base)', fontWeight: 600 }}>
          🔗 Takvim Entegrasyonları
        </h3>
        {connected.length > 0 && (
          <button className="btn btn-secondary btn-sm" onClick={handleSync} disabled={syncing}>
            {syncing ? '⏳' : '⟳'} Şimdi Senkronize Et
          </button>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
        {providers.map(p => {
          const integ = connected.find((i: any) => i.provider === p.key)
          const configured = providerInfo[p.key]?.configured
          const isConnected = !!integ
          return (
            <div key={p.key} style={{
              padding: 'var(--space-3)', borderRadius: 'var(--radius-sm)',
              border: `1px solid ${isConnected ? `${p.color}40` : 'var(--border)'}`,
              background: isConnected ? `${p.color}08` : 'var(--bg-elevated)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                <span style={{ fontSize: 24 }}>{p.icon}</span>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 'var(--font-size-sm)' }}>{p.label}</div>
                  {isConnected ? (
                    <div style={{ fontSize: 11, color: 'var(--income)' }}>✓ {integ.email}</div>
                  ) : (
                    <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                      {configured ? 'Bağlı değil' : '⚙️ Yapılandırma gerekli'}
                    </div>
                  )}
                </div>
              </div>

              {isConnected && integ.last_synced_at && (
                <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginBottom: 8 }}>
                  Son sync: {new Date(integ.last_synced_at).toLocaleString('tr-TR')}
                </div>
              )}
              {isConnected && integ.sync_error && (
                <div style={{ fontSize: 10, color: 'var(--danger)', marginBottom: 8 }}>
                  ⚠️ {integ.sync_error.slice(0, 80)}
                </div>
              )}

              {isConnected ? (
                <button
                  className="btn btn-ghost btn-sm"
                  style={{ color: 'var(--danger)', fontSize: 11, padding: '3px 8px' }}
                  disabled={disconnecting === p.key}
                  onClick={() => handleDisconnect(p.key)}
                >
                  {disconnecting === p.key ? '⏳' : '✕'} Bağlantıyı Kes
                </button>
              ) : configured ? (
                <button
                  className="btn btn-primary btn-sm"
                  style={{ fontSize: 11, padding: '4px 12px', background: p.color, border: 'none' }}
                  onClick={() => p.key === 'google' ? calendarApi.connectGoogle() : calendarApi.connectMicrosoft()}
                >
                  + Bağla
                </button>
              ) : (
                <div style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>
                  .env dosyasına {p.key === 'google' ? 'GOOGLE_CLIENT_ID' : 'MICROSOFT_CLIENT_ID'} ekleyin
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ── Main ── */
export function CalendarPage() {
  const { t } = useTranslation()
  const [items, setItems] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const today = isoDate(new Date())
  const [viewYear, setViewYear] = useState(new Date().getFullYear())
  const [viewMonth, setViewMonth] = useState(new Date().getMonth())

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    try {
      const r = await calendarApi.items({ skip: 0, limit: 500, include_completed: false, include_dismissed: false })
      setItems(Array.isArray(r.data) ? r.data : (r.data?.items ?? []))
    } catch { }
    finally { if (!silent) setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const handleSync = async () => {
    setSyncing(true)
    try { await calendarApi.sync(6); await load() } catch { }
    setSyncing(false)
  }

  const handleExportIcs = async () => {
    setExporting(true)
    try {
      const res = await calendarApi.exportIcs(6)
      const url = URL.createObjectURL(new Blob([res.data], { type: 'text/calendar' }))
      const a = document.createElement('a')
      a.href = url; a.download = 'umay-calendar.ics'; a.click()
      URL.revokeObjectURL(url)
    } catch { }
    setExporting(false)
  }

  const handleAction = async (id: string, action: 'dismiss' | 'complete') => {
    setActionLoading(id + action)
    try {
      if (action === 'dismiss') await calendarApi.dismiss(id)
      else await calendarApi.complete(id)
      setItems(prev => prev.filter(i => i.id !== id))
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Hata')
    }
    setActionLoading(null)
  }

  /* Build grid */
  const daysInMonth = getDaysInMonth(viewYear, viewMonth)
  const firstDay = getFirstDayOfMonth(viewYear, viewMonth)

  const byDate: Record<string, any[]> = {}
  items.forEach(item => {
    const d = item.due_date?.slice(0, 10)
    if (!d) return
    if (!byDate[d]) byDate[d] = []
    byDate[d].push(item)
  })

  const selectedItems = selectedDate ? (byDate[selectedDate] || []) : []

  const totalExpense = items.filter(i => !isIncome(i)).reduce((s, i) => s + (i.amount || 0), 0)
  const totalIncome = items.filter(isIncome).reduce((s, i) => s + (i.amount || 0), 0)
  const overdue = items.filter(i => (i.due_date?.slice(0, 10) || '') < today)

  const prevMonth = () => {
    if (viewMonth === 0) { setViewMonth(11); setViewYear(y => y - 1) }
    else setViewMonth(m => m - 1)
    setSelectedDate(null)
  }
  const nextMonth = () => {
    if (viewMonth === 11) { setViewMonth(0); setViewYear(y => y + 1) }
    else setViewMonth(m => m + 1)
    setSelectedDate(null)
  }

  const cells: React.ReactNode[] = []
  for (let i = 0; i < firstDay; i++) cells.push(<div key={`p${i}`} style={{ minHeight: 76 }} />)
  for (let d = 1; d <= daysInMonth; d++) {
    const ds = `${viewYear}-${String(viewMonth + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    cells.push(<DayCell key={ds} day={d} dateStr={ds} items={byDate[ds] || []} today={today} selected={selectedDate} onSelect={setSelectedDate} />)
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Takvim</h1>
          <p className="page-subtitle">Yaklaşan finansal yükümlülükler</p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <button className="btn btn-secondary" onClick={handleExportIcs} disabled={exporting} title="Outlook / Google Calendar için .ics indir">
            {exporting ? '⏳' : '📅'} Outlook'a Aktar
          </button>
          <button className="btn btn-secondary" onClick={handleSync} disabled={syncing}>
            {syncing ? '⏳ Senkronize Ediliyor…' : '⟳ Senkronize Et'}
          </button>
        </div>
      </div>

      {/* KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--space-3)', marginBottom: 'var(--space-5)' }}>
        <div className="stat-card">
          <div className="stat-card-label">Toplam Etkinlik</div>
          <div className="stat-card-value">{items.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Gecikmiş</div>
          <div className="stat-card-value" style={{ color: overdue.length > 0 ? 'var(--danger)' : 'var(--income)' }}>{overdue.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Toplam Gider</div>
          <div className="stat-card-value" style={{ color: 'var(--expense)', fontSize: 18 }}>₺ {totalExpense.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Toplam Gelir</div>
          <div className="stat-card-value" style={{ color: 'var(--income)', fontSize: 18 }}>₺ {totalIncome.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</div>
        </div>
      </div>

      <IntegrationPanel />

      <div style={{ display: 'grid', gridTemplateColumns: selectedDate ? '1fr 300px' : '1fr', gap: 'var(--space-4)', alignItems: 'start' }}>

        {/* Calendar Grid */}
        <div className="card" style={{ padding: 'var(--space-4)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
            <button className="btn btn-ghost btn-sm" onClick={prevMonth}>‹ Önceki</button>
            <h2 style={{ margin: 0, fontSize: 'var(--font-size-lg)', fontWeight: 600 }}>
              {MONTHS_TR[viewMonth]} {viewYear}
            </h2>
            <button className="btn btn-ghost btn-sm" onClick={nextMonth}>Sonraki ›</button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4, marginBottom: 4 }}>
            {DAYS_TR.map(d => (
              <div key={d} style={{ textAlign: 'center', fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', padding: '4px 0' }}>{d}</div>
            ))}
          </div>

          {loading ? (
            <div className="loading-state"><div className="spinner" /></div>
          ) : items.length === 0 ? (
            <div className="empty-state" style={{ minHeight: 300 }}>
              <div className="empty-state-icon">📅</div>
              <div className="empty-state-title">Yaklaşan etkinlik yok</div>
              <div className="empty-state-desc">Planlı ödemeler, kredi taksitleri ve kart son ödeme tarihlerini görüntülemek için takvimi senkronize edin.</div>
              <button className="btn btn-primary" onClick={handleSync} disabled={syncing}>
                {syncing ? '⏳ Senkronize Ediliyor…' : '⟳ Senkronize Et'}
              </button>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4 }}>{cells}</div>
          )}

          <div style={{ display: 'flex', gap: 'var(--space-4)', marginTop: 'var(--space-3)', fontSize: 11, color: 'var(--text-tertiary)', borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-3)' }}>
            <span>🔴 Gider / Ödeme</span>
            <span>🟢 Gelir</span>
            <span>Tarihe tıklayın → detay</span>
          </div>
        </div>

        {/* Day Detail Panel */}
        {selectedDate && (
          <div className="card" style={{ padding: 'var(--space-4)', position: 'sticky', top: 80 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
              <h3 style={{ margin: 0, fontSize: 'var(--font-size-base)', fontWeight: 600 }}>
                {new Date(selectedDate + 'T12:00:00').toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' })}
              </h3>
              <button onClick={() => setSelectedDate(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: 'var(--text-tertiary)' }}>✕</button>
            </div>

            {selectedItems.length === 0 ? (
              <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)', textAlign: 'center', padding: 'var(--space-4)' }}>Bu tarihte etkinlik yok</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                {selectedItems.map((item: any) => {
                  const income = isIncome(item)
                  const od = (item.due_date?.slice(0, 10) || '') < today
                  const url = getSourceUrl(item)
                  return (
                    <div key={item.id} style={{
                      padding: 'var(--space-3)', borderRadius: 'var(--radius-sm)',
                      border: `1px solid ${income ? 'rgba(34,197,94,0.3)' : od ? 'rgba(239,68,68,0.4)' : 'rgba(239,68,68,0.2)'}`,
                      background: income ? 'rgba(34,197,94,0.05)' : 'rgba(239,68,68,0.04)',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 'var(--font-size-sm)' }}>
                          {income ? '🟢' : '🔴'} {item.title}
                        </span>
                        {url && (
                          <a href={url} style={{ fontSize: 10, color: 'var(--accent)', textDecoration: 'none', whiteSpace: 'nowrap' }}>Git →</a>
                        )}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 6 }}>
                        {TYPE_LABEL[item.item_type] || item.item_type}
                        {od && <span style={{ color: 'var(--danger)', marginLeft: 6 }}>⚠️ Gecikmiş</span>}
                      </div>
                      {item.amount != null && (
                        <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 15, color: income ? 'var(--income)' : 'var(--expense)', marginBottom: 8 }}>
                          {income ? '+' : '-'}{fmtAmount(item.amount, item.currency || 'TRY')}
                        </div>
                      )}
                      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                        <button
                          className="btn btn-sm" style={{ flex: 1, background: 'var(--success-soft)', color: 'var(--income)', border: 'none', padding: '4px 0', fontSize: 11 }}
                          disabled={actionLoading === item.id + 'complete'}
                          onClick={() => handleAction(item.id, 'complete')}
                        >✓ Tamamlandı</button>
                        <button
                          className="btn btn-ghost btn-sm" style={{ color: 'var(--text-tertiary)', padding: '4px 10px', fontSize: 11 }}
                          disabled={actionLoading === item.id + 'dismiss'}
                          onClick={() => handleAction(item.id, 'dismiss')}
                        >Yoksay</button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
