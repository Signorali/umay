import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { BankIcon, InvestmentIcon, CloseIcon, EditIcon } from '../components/Icons'
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { dashboardApi, transactionsApi, categoriesApi, marketApi, plannedPaymentsApi, accountsApi, usersApi } from '../api/umay'
import { useAuth } from '../context/AuthContext'
import GridLayout from "react-grid-layout"
import "react-grid-layout/css/styles.css"
import "react-resizable/css/styles.css"

/* ── Widget registry ─────────────────────────────────────────── */
type WidgetId =
  | 'market_ticker'
  | 'kpi_cards'
  | 'planned_chart'
  | 'expense_pie'
  | 'recent_txs'
  | 'upcoming'
  | 'accounts_list'

interface WidgetConfig {
  id: WidgetId
  visible: boolean
  x: number
  y: number
  w: number
  h: number
}

interface WidgetMeta {
  id: WidgetId
  label: string
  desc: string
  defaultW: number
  defaultH: number
}

const WIDGET_META: WidgetMeta[] = [
  { id: 'market_ticker', label: 'Piyasa Takibi',           desc: 'Pinlenmiş semboller ve anlık fiyatlar',    defaultW: 12, defaultH: 3 },
  { id: 'kpi_cards',     label: 'Özet Kartlar',            desc: 'Net servet, gelir, gider ve hesap sayısı', defaultW: 12, defaultH: 3 },
  { id: 'accounts_list', label: 'Hesap Bakiyeleri',        desc: 'Tüm hesapların anlık bakiyeleri',          defaultW: 6, defaultH: 8 },
  { id: 'planned_chart', label: 'Planlı Ödemeler Grafiği', desc: 'Haftalık gelir / gider projeksiyonu',      defaultW: 6, defaultH: 8 },
  { id: 'expense_pie',   label: 'Gider Dağılımı',          desc: 'Kategorilere göre pasta grafik',           defaultW: 6, defaultH: 8 },
  { id: 'recent_txs',    label: 'Son İşlemler',            desc: 'En son 5 işlem',                           defaultW: 6, defaultH: 10 },
  { id: 'upcoming',      label: 'Yaklaşan Ödemeler',       desc: 'Önümüzdeki ödemeler ve aylık özet',        defaultW: 6, defaultH: 10 },
]

const DEFAULT_CONFIGS: WidgetConfig[] = [
  { id: 'market_ticker', visible: true,  x: 0, y: 0,  w: 12, h: 2 },
  { id: 'kpi_cards',     visible: false, x: 0, y: 2,  w: 12, h: 3 },
  { id: 'accounts_list', visible: true,  x: 0, y: 2,  w: 6,  h: 9 },
  { id: 'expense_pie',   visible: true,  x: 6, y: 2,  w: 6,  h: 9 },
  { id: 'planned_chart', visible: true,  x: 0, y: 11, w: 12, h: 8 },
  { id: 'recent_txs',    visible: true,  x: 0, y: 19, w: 6,  h: 10 },
  { id: 'upcoming',      visible: true,  x: 6, y: 19, w: 6,  h: 10 },
]

const LS_KEY = 'dashboard_widgets_v10'

function parseConfigs(raw: string | null | undefined): WidgetConfig[] | null {
  try {
    const saved = JSON.parse(raw ?? 'null')
    if (Array.isArray(saved) && saved.length && saved[0]?.id && typeof saved[0]?.w === 'number') {
      const savedIds = new Set(saved.map((s: WidgetConfig) => s.id))
      const extras = DEFAULT_CONFIGS.filter(d => !savedIds.has(d.id))
      return [...saved, ...extras]
    }
  } catch { /* */ }
  return null
}

function loadConfigs(): WidgetConfig[] {
  return parseConfigs(localStorage.getItem(LS_KEY)) ?? DEFAULT_CONFIGS
}

function saveLocalConfigs(configs: WidgetConfig[]) {
  localStorage.setItem(LS_KEY, JSON.stringify(configs))
}

/* ── Helpers ─────────────────────────────────────────────────── */
const FMT = (n: number, cur = '₺') =>
  `${cur} ${Math.abs(n).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}`

const CHART_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#38bdf8', '#a78bfa']

/* ── Market Ticker ───────────────────────────────────────────── */
function MarketTicker() {
  const [items, setItems] = useState<any[]>([])
  const load = useCallback(async () => {
    try {
      const res = await marketApi.watchlist()
      const all: any[] = Array.isArray(res.data) ? res.data : (res.data?.items ?? [])
      setItems(all.filter((w: any) => w.is_pinned).sort((a: any, b: any) => (a.display_order ?? 0) - (b.display_order ?? 0)))
    } catch { setItems([]) }
  }, [])
  useEffect(() => { load(); const iv = setInterval(load, 30_000); return () => clearInterval(iv) }, [load])
  if (!items.length) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyItems: 'center', justifyContent: 'center', height: '100%', width: '100%', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', color: 'var(--text-tertiary)', fontSize: 13, border: '1px solid var(--border)' }}>
        Takip edilen piyasa sembolü (Pinlenmiş) bulunmuyor.
      </div>
    )
  }
  const fmtPrice = (p: number | null, cur: string) => {
    if (p == null) return '—'
    const s = cur === 'TRY' ? '₺' : cur === 'USD' ? '$' : cur === 'EUR' ? '€' : ''
    return `${s}${p.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`
  }
  return (
    <div style={{ display: 'flex', gap: 'var(--space-3)', height: '100%', overflowX: 'auto', paddingBottom: 4 }}>
      {items.map((w: any) => {
        const chg = w.change_percent ?? w.change_pct ?? null
        const trend = w.trend ?? (chg == null ? null : chg >= 0 ? 'up' : 'down')
        const up = trend === 'up'; const down = trend === 'down'
        const borderColor = trend == null ? 'var(--border)' : up ? 'rgba(34,197,94,0.35)' : 'rgba(239,68,68,0.35)'
        const chgColor = up ? 'var(--income)' : down ? 'var(--expense)' : 'var(--text-tertiary)'
        return (
          <div key={w.id} style={{ minWidth: 150, flex: 1, background: 'var(--bg-elevated)', border: `1px solid ${borderColor}`, borderRadius: 'var(--radius-sm)', padding: '7px 12px', position: 'relative', overflow: 'hidden' }}>
            {trend != null && <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: up ? 'var(--income)' : 'var(--expense)', opacity: 0.6 }} />}
            <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginBottom: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 600, letterSpacing: '0.03em', color: 'var(--text-secondary)' }}>{w.symbol}</span>
              <a href="/market" style={{ color: 'var(--accent)', textDecoration: 'none', fontSize: 9, opacity: 0.7 }}>Piyasa →</a>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 13, color: 'var(--text-primary)', marginBottom: 1 }}>{fmtPrice(w.price, w.currency)}</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              {chg != null
                ? <span style={{ fontSize: 11, fontWeight: 600, color: chgColor }}>{up ? '▲' : down ? '▼' : '→'}{Math.abs(chg).toFixed(2)}%</span>
                : <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>—</span>}
              <span style={{ fontSize: 10, color: 'var(--text-tertiary)', marginLeft: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {w.label !== w.symbol ? w.label : ''}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

/* ── KPI Card ────────────────────────────────────────────────── */
function KPICard({ label, value, sub, color, icon }: { label: string; value: string; sub?: string; color?: string; icon: React.ReactNode }) {
  return (
    <div style={{ flex: 1, background: 'var(--bg-elevated)', border: '1px solid ' + (color ? (color + '40') : 'var(--border-subtle)'), borderRadius: 'var(--radius-sm)', padding: '10px 12px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
        <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-secondary)', flex: 1 }}>{label}</div>
        <div style={{ width: 28, height: 28, borderRadius: 'var(--radius-sm)', background: color ? (color + '15') : 'var(--bg-surface)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>{icon}</div>
      </div>
      <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 13, color: color || 'var(--text-primary)', marginBottom: 2 }}>{value}</div>
      {sub && <div style={{ fontSize: 9, color: 'var(--text-tertiary)', lineHeight: 1.3 }}>{sub}</div>}
    </div>
  )
}

/* ── Transaction Row ─────────────────────────────────────────── */
function TxRow({ tx }: { tx: any }) {
  const isIncome = tx.transaction_type === 'INCOME'
  const isTransfer = tx.transaction_type === 'TRANSFER'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
      <div style={{ width: 36, height: 36, borderRadius: 'var(--radius-sm)', flexShrink: 0, background: isIncome ? 'var(--success-soft)' : isTransfer ? 'var(--info-soft)' : 'var(--danger-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, fontWeight: 700, color: isIncome ? 'var(--income)' : isTransfer ? 'var(--transfer)' : 'var(--expense)' }}>
        {isIncome ? '↑' : isTransfer ? '⇄' : '↓'}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 500, fontSize: 'var(--font-size-sm)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{tx.description || tx.transaction_type}</div>
        <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>{tx.transaction_date}</div>
      </div>
      <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 'var(--font-size-sm)', flexShrink: 0, color: isIncome ? 'var(--income)' : isTransfer ? 'var(--transfer)' : 'var(--expense)' }}>
        {isIncome ? '+' : isTransfer ? '' : '-'}{tx.currency || '₺'} {tx.amount?.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
      </div>
    </div>
  )
}

/* ── Chart Tooltip ───────────────────────────────────────────── */
function ChartTooltip({ active, payload, label }: any) {
  const { t } = useTranslation()
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', fontSize: 'var(--font-size-xs)', boxShadow: 'var(--shadow-md)' }}>
      <div style={{ color: 'var(--text-tertiary)', marginBottom: 4 }}>{label}</div>
      {payload.map((p: any, i: number) => (
        <div key={i} style={{ color: p.color, fontWeight: 600 }}>
          {p.name === 'income' ? t('transactions.income') : p.name === 'expense' ? t('transactions.expense') : p.name}: ₺ {Number(p.value).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
        </div>
      ))}
    </div>
  )
}

/* ── Customize Panel (Only toggles visibility now) ───────────── */
function CustomizePanel({
  configs,
  onToggle,
  onClose,
  onReset,
}: {
  configs: WidgetConfig[]
  onToggle: (id: WidgetId) => void
  onClose: () => void
  onReset: () => void
}) {
  return (
    <>
      <div style={{ position: 'fixed', top: 0, right: 0, bottom: 0, zIndex: 101, width: 320, background: 'var(--bg-surface)', borderLeft: '1px solid var(--border)', boxShadow: 'var(--shadow-lg)', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 'var(--space-5)', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 'var(--font-size-md)', color: 'var(--text-primary)' }}>Özelleştirme Paneli</div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 2 }}>Kartların görünürlüğünü ayarla</div>
          </div>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={onClose}><CloseIcon size={14} /></button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-4)' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {configs.map((cfg) => {
              const meta = WIDGET_META.find(m => m.id === cfg.id)!
              const on = cfg.visible
              return (
                <div key={cfg.id} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', padding: 'var(--space-3)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', background: on ? 'var(--bg-elevated)' : 'var(--bg-surface)' }}>
                  {/* toggle */}
                  <div onClick={() => onToggle(cfg.id)} style={{ width: 34, height: 19, borderRadius: 10, flexShrink: 0, background: on ? 'var(--accent)' : 'var(--border-strong)', position: 'relative', transition: 'background 0.2s', cursor: 'pointer' }}>
                    <div style={{ position: 'absolute', top: 2.5, left: on ? 17 : 2.5, width: 14, height: 14, borderRadius: '50%', background: '#fff', transition: 'left 0.2s', boxShadow: '0 1px 3px rgba(0,0,0,0.2)' }} />
                  </div>
                  <div style={{ flex: 1, fontWeight: 600, fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)' }}>{meta.label}</div>
                </div>
              )
            })}
          </div>
          <div style={{ marginTop: 'var(--space-5)', padding: 'var(--space-4)', background: 'var(--accent-subtle)', color: 'var(--text-primary)', borderRadius: 'var(--radius-md)', fontSize: 'var(--font-size-xs)' }}>
            💡 Düzenleme modu açıkken kartları <strong>fare ile üst kısmından tutup sürükleyebilir</strong> veya <strong>sağ alt köşesinden çekerek boyutlandırabilirsiniz</strong>.
          </div>
        </div>

        <div style={{ padding: 'var(--space-4) var(--space-5)', borderTop: '1px solid var(--border)', flexShrink: 0, display: 'flex', gap: 'var(--space-2)' }}>
          <button className="btn btn-secondary btn-sm" style={{ flex: 1 }} onClick={onReset}>Sıfırla</button>
          <button className="btn btn-primary btn-sm" style={{ flex: 1 }} onClick={onClose}>Bitti</button>
        </div>
      </div>
    </>
  )
}

/* ── Main Page ───────────────────────────────────────────────── */
export function DashboardPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [now, setNow] = useState(new Date())
  const [summary, setSummary] = useState<any>({})
  const [recentTxs, setRecentTxs] = useState<any[]>([])
  const [upcoming, setUpcoming] = useState<any[]>([])
  const [plannedItems, setPlannedItems] = useState<any[]>([])
  const [weekOffset, setWeekOffset] = useState(0)
  const [catBreakdown, setCatBreakdown] = useState<any[]>([])
  const [accountsList, setAccountsList] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const [configs, setConfigs] = useState<WidgetConfig[]>(loadConfigs)
  const [showCustomize, setShowCustomize] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const [gridWidth, setGridWidth] = useState(0)
  const dbSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // On mount: if user has DB layout, prefer it over localStorage
  useEffect(() => {
    if (user?.dashboard_layout) {
      const dbConfigs = parseConfigs(user.dashboard_layout)
      if (dbConfigs) {
        setConfigs(dbConfigs)
        saveLocalConfigs(dbConfigs)
      }
    }
  }, [user?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!containerRef.current) return
    setGridWidth(containerRef.current.offsetWidth)
    const ro = new ResizeObserver(entries => {
      for (const entry of entries) {
        const w = entry.contentRect.width
        if (w > 0) setGridWidth(w)
      }
    })
    ro.observe(containerRef.current)
    return () => ro.disconnect()
  }, [])

  const updateConfigs = (next: WidgetConfig[]) => {
    setConfigs(next)
    saveLocalConfigs(next)
    // Debounce DB save — 1.5s after last change
    if (dbSaveTimer.current) clearTimeout(dbSaveTimer.current)
    dbSaveTimer.current = setTimeout(() => {
      usersApi.updatePreferences({ dashboard_layout: JSON.stringify(next) }).catch(() => {})
    }, 1500)
  }

  const toggleWidget  = (id: WidgetId) => updateConfigs(configs.map(c => c.id === id ? { ...c, visible: !c.visible } : c))
  const resetWidgets  = () => updateConfigs(DEFAULT_CONFIGS)

  const handleLayoutChange = (layout: any) => {
    if (!showCustomize) return
    const next = configs.map(c => {
      const l = layout.find((x: any) => x.i === c.id)
      if (l) return { ...c, x: l.x, y: l.y, w: l.w, h: l.h }
      return c
    })
    updateConfigs(next)
  }

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 60_000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    const today = new Date()
    const periodStart = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0]
    Promise.allSettled([
      dashboardApi.get(),
      transactionsApi.list({ skip: 0, limit: 2000, transaction_type: 'EXPENSE' }),
      categoriesApi.list({ skip: 0, limit: 200 }),
      plannedPaymentsApi.list({ skip: 0, limit: 500 }),
      accountsApi.list({ limit: 100 }),
    ]).then(([dashRes, txRes, catListRes, ppRes, accRes]) => {
      if (dashRes.status === 'fulfilled') {
        const d = dashRes.value.data
        setSummary(d.summary || {})
        setRecentTxs(d.recent_transactions || [])
        setUpcoming(d.upcoming_payments || [])
      }
      if (txRes.status === 'fulfilled' && catListRes.status === 'fulfilled') {
        const txs: any[] = txRes.value.data || []
        const cats: any[] = catListRes.value.data || []
        const catMap: Record<string, string> = {}
        cats.forEach((c: any) => { catMap[c.id] = c.name })
        const map: Record<string, number> = {}
        txs.filter((tx: any) => tx.transaction_date >= periodStart).forEach((tx: any) => {
          const name = catMap[tx.category_id] || 'Diğer'
          map[name] = (map[name] || 0) + Math.abs(Number(tx.amount || 0))
        })
        setCatBreakdown(Object.entries(map).map(([name, total_amount]) => ({ name, total_amount })).sort((a: any, b: any) => b.total_amount - a.total_amount))
      }
      if (ppRes.status === 'fulfilled') setPlannedItems(ppRes.value.data || [])
      if (accRes.status === 'fulfilled') {
        const d = accRes.value.data
        setAccountsList(Array.isArray(d) ? d : (d?.items ?? []))
      }
    }).finally(() => setLoading(false))
  }, [])

  const weeklyData = useMemo(() => {
    const d = new Date()
    const day = d.getDay()
    const diff = d.getDate() - day + (day === 0 ? -6 : 1)
    const monday = new Date(d)
    monday.setDate(diff + weekOffset * 8 * 7)
    monday.setHours(0, 0, 0, 0)
    return Array.from({ length: 8 }, (_, i) => {
      const weekStart = new Date(monday); weekStart.setDate(monday.getDate() + i * 7)
      const weekEnd = new Date(weekStart); weekEnd.setDate(weekStart.getDate() + 6); weekEnd.setHours(23, 59, 59, 999)
      const weekItems = plannedItems.filter((p: any) => {
        if (p.credit_card_purchase_id) return false
        const date = new Date(p.planned_date)
        return date >= weekStart && date <= weekEnd
      })
      return {
        label: weekStart.toLocaleDateString('tr-TR', { day: 'numeric', month: 'short' }),
        income: weekItems.filter((p: any) => p.payment_type === 'INCOME').reduce((s: number, p: any) => s + Number(p.amount), 0),
        expense: weekItems.filter((p: any) => p.payment_type === 'EXPENSE').reduce((s: number, p: any) => s + Number(p.amount), 0),
      }
    })
  }, [plannedItems, weekOffset])

  const pieData = catBreakdown.slice(0, 6).map((c: any) => ({ name: c.category_name || c.name || '—', value: Math.abs(c.total_amount || c.amount || 0) }))
  const visibleCount = configs.filter(c => c.visible).length

  /* ── Widget render map ─────────────────────────────────────── */
  const renderWidget = (id: WidgetId) => {
    switch (id) {
      case 'market_ticker':
        return <MarketTicker />

      case 'kpi_cards':
        return (
          <div style={{ display: 'flex', gap: 'var(--space-3)', height: '100%', overflowX: 'auto', paddingBottom: 4 }}>
            <KPICard label={t('dashboard.netWorth')} icon={<InvestmentIcon size={16} />} value={FMT(summary.total_net_worth || 0)} sub={t('dashboard.allAccounts', 'Tüm hesaplar')} color="var(--accent)" />
            <KPICard label={t('dashboard.incomeMTD')} icon="↑" value={FMT(summary.total_income || 0)} color="var(--income)" />
            <KPICard label={t('dashboard.expensesMTD')} icon="↓" value={FMT(summary.total_expenses || 0)} color="var(--expense)" />
            <KPICard label={t('dashboard.accounts')} icon={<BankIcon size={16} />} value={String(summary.account_count || 0)} sub={`${summary.transaction_count || 0} ${t('dashboard.totalTransactions')}`} />
          </div>
        )

      case 'accounts_list':
        return (
          <div className="card" style={{ height: '100%' }}>
            <div className="card-header" style={{ marginBottom: 'var(--space-3)' }}>
              <div><div className="card-title">Hesap Bakiyeleri</div></div>
              <a href="/accounts" style={{ fontSize: 'var(--font-size-xs)', color: 'var(--accent)' }}>Tümü →</a>
            </div>
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {accountsList.length === 0
                ? <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)', textAlign: 'center', padding: 'var(--space-5) 0' }}>Hesap bulunamadı</div>
                : accountsList.slice(0, 8).map((acc: any, i: number) => {
                  const bal = Number(acc.balance ?? acc.current_balance ?? 0)
                  return (
                    <div key={acc.id ?? i} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', padding: '7px 0', borderBottom: i < Math.min(accountsList.length, 8) - 1 ? '1px solid var(--border)' : 'none' }}>
                      <div style={{ width: 28, height: 28, borderRadius: 'var(--radius-sm)', background: 'var(--accent-subtle)', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><BankIcon size={12} /></div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 500, fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{acc.name || acc.account_name}</div>
                      </div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 12, flexShrink: 0, color: bal >= 0 ? 'var(--text-primary)' : 'var(--expense)' }}>
                        {acc.currency || '₺'} {bal.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
                      </div>
                    </div>
                  )
                })
              }
            </div>
          </div>
        )

      case 'planned_chart':
        return (
          <div className="card" style={{ height: '100%' }}>
            <div className="card-header" style={{ marginBottom: 'var(--space-2)' }}>
              <div><div className="card-title">Planlı Ödemeler</div></div>
              <div style={{ display: 'flex', gap: 'var(--space-1)', alignItems: 'center' }}>
                <button className="btn btn-ghost btn-sm" onClick={() => setWeekOffset(w => w - 1)}>‹</button>
                <button className="btn btn-ghost btn-sm" onClick={() => setWeekOffset(0)} disabled={weekOffset === 0}>Bgn</button>
                <button className="btn btn-ghost btn-sm" onClick={() => setWeekOffset(w => w + 1)}>›</button>
              </div>
            </div>
            <div style={{ flex: 1, position: 'relative', width: '100%', minHeight: 0 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={weeklyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: 'var(--text-tertiary)', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: 'var(--text-tertiary)', fontSize: 10 }} axisLine={false} tickLine={false}
                    tickFormatter={(v: number) => v >= 1_000_000 ? ((v/1_000_000).toLocaleString('tr-TR',{maximumFractionDigits:1}) + 'M') : v >= 1_000 ? ((v/1_000).toLocaleString('tr-TR',{maximumFractionDigits:0}) + 'B') : String(v)}
                    width={40} />
                  <Tooltip content={<ChartTooltip />} cursor={false} />
                  <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 10 }} formatter={(value) => value === 'income' ? t('transactions.income') : t('transactions.expense')} />
                  <Bar dataKey="income" name="income" fill="#22c55e" radius={[2,2,0,0]} />
                  <Bar dataKey="expense" name="expense" fill="#ef4444" radius={[2,2,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )

      case 'expense_pie':
        return (
          <div className="card" style={{ height: '100%' }}>
            <div className="card-header" style={{ marginBottom: 'var(--space-2)' }}><div className="card-title">{t('dashboard.expenseBreakdown')}</div></div>
            {pieData.length === 0
              ? <div className="empty-state" style={{ padding: 'var(--space-5) 0' }}><div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)', textAlign: 'center' }}>{t('dashboard.noCategoryData', 'Kategori yok')}</div></div>
              : <div style={{ flex: 1, position: 'relative', width: '100%', minHeight: 0 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={pieData} cx="50%" cy="50%" innerRadius="45%" outerRadius="75%" paddingAngle={2} dataKey="value">
                        {pieData.map((_: any, i: number) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                      </Pie>
                      <Tooltip formatter={(v: any) => ('₺ ' + Number(v).toLocaleString('tr-TR', { minimumFractionDigits: 2 }))} />
                      <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 10 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
            }
          </div>
        )

      case 'recent_txs':
        return (
          <div className="card" style={{ height: '100%' }}>
            <div className="card-header">
              <div><div className="card-title">{t('dashboard.recentTransactions')}</div></div>
              <a href="/transactions" style={{ fontSize: 'var(--font-size-xs)', color: 'var(--accent)' }}>Tümü →</a>
            </div>
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {recentTxs.length === 0
                ? <div className="empty-state" style={{ padding: 'var(--space-5) 0' }}>
                    <div className="empty-state-title">İşlem Yok</div>
                  </div>
                : recentTxs.slice(0, 3).map((tx: any) => <TxRow key={tx.id} tx={tx} />)
              }
            </div>
          </div>
        )

      case 'upcoming':
        return (
          <div className="card" style={{ height: '100%' }}>
            <div className="card-header" style={{ marginBottom: 'var(--space-3)' }}>
              <div className="card-title">{t('dashboard.upcoming')}</div>
              <a href="/calendar" style={{ fontSize: 'var(--font-size-xs)', color: 'var(--accent)' }}>Takvim →</a>
            </div>
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {upcoming.length === 0
                ? <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)', textAlign: 'center', padding: 'var(--space-5) 0' }}>{t('dashboard.noUpcoming')}</div>
                : <div>
                    {upcoming.slice(0, 5).map((p: any, i: number) => (
                      <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderBottom: '1px solid var(--border)' }}>
                        <div>
                          <div style={{ fontWeight: 500, fontSize: 12 }}>{p.title || p.label}</div>
                          <div style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>{p.due_date}</div>
                        </div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--warning)', fontWeight: 600 }}>
                          {p.currency || '₺'} {p.amount?.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
                        </div>
                      </div>
                    ))}
                  </div>
              }
            </div>
          </div>
        )

      default:
        return null
    }
  }

  // React Grid Layout requires integer x, y, w, h
  const layout = configs.filter(c => c.visible).map(c => {
    // Force Market Ticker to be full width
    if (c.id === 'market_ticker') {
      return {
        i: c.id, x: 0, y: c.y, w: 12, h: c.h, minW: 12, maxW: 12, minH: 3, static: true
      }
    }
    return {
      i: c.id,
      x: c.x,
      y: c.y,
      w: c.w,
      h: c.h,
      minW: 3,
      minH: 2
    }
  })

  return (
    <div>
      <div className="page-header">
        <p className="page-subtitle">
          {now.toLocaleDateString('tr-TR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          {' · '}{now.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}
        </p>
        <button className="btn btn-ghost btn-sm" onClick={() => setShowCustomize(true)} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: showCustomize ? 'var(--accent)' : 'var(--text-secondary)' }}>
          <EditIcon size={13} />
          {showCustomize ? 'Düzenleme Modu Açık' : 'Paneli Düzenle'}
          {visibleCount < WIDGET_META.length && (
            <span style={{ background: 'var(--accent)', color: '#fff', borderRadius: 10, padding: '1px 6px', fontSize: 10, fontWeight: 700 }}>
              {WIDGET_META.length - visibleCount} gizli
            </span>
          )}
        </button>
      </div>

      {/* containerRef always mounted so ResizeObserver fires correctly */}
      <div ref={containerRef} style={{ width: '100%' }}>
        {loading ? (
          <div className="loading-state"><div className="spinner" /></div>
        ) : visibleCount === 0 ? (
          <div className="empty-state" style={{ marginTop: 'var(--space-8)' }}>
            <div className="empty-state-title">Tüm widget'lar gizlendi</div>
            <div className="empty-state-desc">Paneli düzenleyerek görüntülemek istediklerini geri ekleyebilirsin.</div>
            <button className="btn btn-primary" onClick={() => setShowCustomize(true)}>Paneli Düzenle</button>
          </div>
        ) : (
          <div style={{
            background: showCustomize ? 'var(--bg-elevated)' : 'transparent',
            borderRadius: 'var(--radius-lg)',
            transition: 'background 0.3s'
          }}>
            {showCustomize && <div style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 10 }}>Kartları sürükle bırak ile taşı · tüm köşe ve kenarlardan yeniden boyutlandır</div>}
            {(() => {
              const RGL = GridLayout as any
              const w = (gridWidth || 800) - (showCustomize ? 356 : 0)
              return (
                <RGL
                  className="layout"
                  layout={layout}
                  width={w}
                  cols={12}
                  rowHeight={30}
                  containerPadding={[0, 0]}
                  onLayoutChange={handleLayoutChange}
                  isDraggable={showCustomize}
                  isResizable={showCustomize}
                  resizeHandles={['s', 'e', 'n', 'w', 'se', 'ne', 'sw', 'nw']}
                  margin={[16, 16]}
                  draggableHandle=".rgl-drag-handle"
                >
                  {configs.filter(c => c.visible).map(c => (
                    <div key={c.id} className={showCustomize ? 'dashboard-edit-item' : ''} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                      {showCustomize && (
                        <div className="rgl-drag-handle" style={{ padding: '4px 10px', cursor: 'grab', fontSize: 11, color: 'var(--text-tertiary)', background: 'var(--bg-hover)', borderRadius: 'var(--radius-sm) var(--radius-sm) 0 0', textAlign: 'center', userSelect: 'none', flexShrink: 0 }}>
                          ⠿ {WIDGET_META.find(m => m.id === c.id)?.label}
                        </div>
                      )}
                      <div style={{ flex: 1, minHeight: 0 }}>
                        {renderWidget(c.id)}
                      </div>
                    </div>
                  ))}
                </RGL>
              )
            })()}
          </div>
        )}
      </div>

      {showCustomize && (
        <CustomizePanel
          configs={configs}
          onToggle={toggleWidget}
          onClose={() => setShowCustomize(false)}
          onReset={resetWidgets}
        />
      )}
    </div>
  )
}
