import React, { useEffect, useState, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { dashboardApi, transactionsApi, categoriesApi, marketApi, plannedPaymentsApi } from '../api/umay'

/* ── Helpers ─────────────────────────────────────────────── */
const FMT = (n: number, cur = '₺') =>
  `${cur} ${Math.abs(n).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}`

const CHART_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#38bdf8', '#a78bfa']

/* ── Market Ticker (pinned symbols from DB) ──────────────── */
function MarketTicker() {
  const [items, setItems] = useState<any[]>([])

  const load = useCallback(async () => {
    try {
      const res = await marketApi.watchlist()
      const all: any[] = Array.isArray(res.data) ? res.data : (res.data?.items ?? [])
      // Only show pinned items, sorted by display_order (all from DB)
      const pinned = all
        .filter((w: any) => w.is_pinned)
        .sort((a: any, b: any) => (a.display_order ?? 0) - (b.display_order ?? 0))
      setItems(pinned)
    } catch { setItems([]) }
  }, [])

  useEffect(() => {
    load()
    const iv = setInterval(load, 30_000)
    return () => clearInterval(iv)
  }, [load])

  if (!items.length) return null

  const fmtPrice = (p: number | null, cur: string) => {
    if (p == null) return '—'
    const s = cur === 'TRY' ? '₺' : cur === 'USD' ? '$' : cur === 'EUR' ? '€' : ''
    return `${s}${p.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`
  }

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
      gap: 'var(--space-3)',
      marginBottom: 'var(--space-5)',
    }}>
      {items.map((w: any) => {
        const chg = w.change_percent ?? w.change_pct ?? null
        const trend = w.trend ?? (chg == null ? null : chg >= 0 ? 'up' : 'down')
        const up = trend === 'up'
        const down = trend === 'down'
        const borderColor = trend == null
          ? 'var(--border)'
          : up ? 'rgba(34,197,94,0.35)' : 'rgba(239,68,68,0.35)'
        const chgColor = up ? 'var(--income)' : down ? 'var(--expense)' : 'var(--text-tertiary)'

        return (
          <div key={w.id} style={{
            background: 'var(--bg-elevated)',
            border: `1px solid ${borderColor}`,
            borderRadius: 'var(--radius-sm)',
            padding: '10px 14px',
            position: 'relative',
            overflow: 'hidden',
          }}>
            {/* subtle top bar */}
            {trend != null && (
              <div style={{
                position: 'absolute', top: 0, left: 0, right: 0, height: 2,
                background: up ? 'var(--income)' : 'var(--expense)', opacity: 0.6,
              }} />
            )}
            <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginBottom: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 600, letterSpacing: '0.03em', color: 'var(--text-secondary)' }}>{w.symbol}</span>
              <a href="/market" style={{ color: 'var(--accent)', textDecoration: 'none', fontSize: 9, opacity: 0.7 }}>Piyasa →</a>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 15, color: 'var(--text-primary)', marginBottom: 2 }}>
              {fmtPrice(w.price, w.currency)}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              {chg != null ? (
                <span style={{ fontSize: 11, fontWeight: 600, color: chgColor, display: 'flex', alignItems: 'center', gap: 2 }}>
                  {up ? '▲' : down ? '▼' : '→'}
                  {Math.abs(chg).toFixed(2)}%
                </span>
              ) : (
                <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>—</span>
              )}
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

/* ── Stat Card ───────────────────────────────────────────── */
function KPICard({
  label, value, sub, color, icon,
}: {
  label: string; value: string; sub?: string; color?: string; icon: string
}) {
  return (
    <div style={{
      background: 'var(--bg-elevated)',
      border: `1px solid ${color ? `${color}40` : 'var(--border-subtle)'}`,
      borderRadius: 'var(--radius-sm)',
      padding: '10px 12px',
      position: 'relative',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
        <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-secondary)', flex: 1 }}>
          {label}
        </div>
        <div style={{
          width: 28, height: 28, borderRadius: 'var(--radius-sm)',
          background: color ? `${color}15` : 'var(--bg-surface)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 14, flexShrink: 0,
        }}>{icon}</div>
      </div>
      <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 13, color: color || 'var(--text-primary)', marginBottom: 2 }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: 9, color: 'var(--text-tertiary)', lineHeight: 1.3 }}>
          {sub}
        </div>
      )}
    </div>
  )
}

/* ── Recent Tx Row ───────────────────────────────────────── */
function TxRow({ tx }: { tx: any }) {
  const isIncome = tx.transaction_type === 'INCOME'
  const isTransfer = tx.transaction_type === 'TRANSFER'
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 'var(--space-3)',
      padding: '10px 0', borderBottom: '1px solid var(--border)',
    }}>
      <div style={{
        width: 36, height: 36, borderRadius: 'var(--radius-sm)', flexShrink: 0,
        background: isIncome ? 'var(--success-soft)' : isTransfer ? 'var(--info-soft)' : 'var(--danger-soft)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 16, fontWeight: 700,
        color: isIncome ? 'var(--income)' : isTransfer ? 'var(--transfer)' : 'var(--expense)',
      }}>
        {isIncome ? '↑' : isTransfer ? '⇄' : '↓'}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 500, fontSize: 'var(--font-size-sm)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {tx.description || tx.transaction_type}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>{tx.transaction_date}</div>
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 'var(--font-size-sm)', flexShrink: 0,
        color: isIncome ? 'var(--income)' : isTransfer ? 'var(--transfer)' : 'var(--expense)',
      }}>
        {isIncome ? '+' : isTransfer ? '' : '-'}{tx.currency || '₺'} {tx.amount?.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
      </div>
    </div>
  )
}

/* ── Tooltip ─────────────────────────────────────────────── */
function ChartTooltip({ active, payload, label }: any) {
  const { t } = useTranslation()
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--bg-elevated)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-sm)', padding: '8px 12px',
      fontSize: 'var(--font-size-xs)', boxShadow: 'var(--shadow-md)',
    }}>
      <div style={{ color: 'var(--text-tertiary)', marginBottom: 4 }}>{label}</div>
      {payload.map((p: any, i: number) => (
        <div key={i} style={{ color: p.color, fontWeight: 600 }}>
          {p.name === 'Income' || p.name === 'income' ? t('transactions.income') : p.name === 'Expense' || p.name === 'expense' ? t('transactions.expense') : p.name}: ₺ {Number(p.value).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
        </div>
      ))}
    </div>
  )
}

/* ── Main ─────────────────────────────────────────────────── */
export function DashboardPage() {
  const { t } = useTranslation()
  const [now, setNow] = useState(new Date())
  const [summary, setSummary] = useState<any>({})
  const [recentTxs, setRecentTxs] = useState<any[]>([])
  const [upcoming, setUpcoming] = useState<any[]>([])
  const [plannedItems, setPlannedItems] = useState<any[]>([])
  const [weekOffset, setWeekOffset] = useState(0)
  const [catBreakdown, setCatBreakdown] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showKPIs, setShowKPIs] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('dashboard_show_kpis') ?? 'false')
    } catch {
      return false
    }
  })

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 60_000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    const today = new Date()
    const periodStart = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0]
    const periodEnd = today.toISOString().split('T')[0]

    Promise.allSettled([
      dashboardApi.get(),
      transactionsApi.list({ skip: 0, limit: 2000, transaction_type: 'EXPENSE' }),
      categoriesApi.list({ skip: 0, limit: 200 }),
      plannedPaymentsApi.list({ skip: 0, limit: 500 }),
    ]).then(([dashRes, txRes, catListRes, ppRes]) => {
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
        const yearStart = periodStart
        const map: Record<string, number> = {}
        txs
          .filter((tx: any) => tx.transaction_date >= yearStart)
          .forEach((tx: any) => {
            const name = catMap[tx.category_id] || 'Diğer'
            map[name] = (map[name] || 0) + Math.abs(Number(tx.amount || 0))
          })
        setCatBreakdown(
          Object.entries(map)
            .map(([name, total_amount]) => ({ name, total_amount }))
            .sort((a: any, b: any) => b.total_amount - a.total_amount)
        )
      }
      if (ppRes.status === 'fulfilled') {
        setPlannedItems(ppRes.value.data || [])
      }
    }).finally(() => setLoading(false))
  }, [])

  const weeklyData = useMemo(() => {
    // Start of current week (Monday), shifted by offset (each page = 8 weeks)
    const d = new Date()
    const day = d.getDay()
    const diff = d.getDate() - day + (day === 0 ? -6 : 1)
    const monday = new Date(d)
    monday.setDate(diff + weekOffset * 8 * 7)
    monday.setHours(0, 0, 0, 0)

    return Array.from({ length: 8 }, (_, i) => {
      const weekStart = new Date(monday)
      weekStart.setDate(monday.getDate() + i * 7)
      const weekEnd = new Date(weekStart)
      weekEnd.setDate(weekStart.getDate() + 6)
      weekEnd.setHours(23, 59, 59, 999)

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

  const pieData = catBreakdown.length > 0
    ? catBreakdown.slice(0, 6).map((c: any) => ({
        name: c.category_name || c.name || '—',
        value: Math.abs(c.total_amount || c.amount || 0),
      }))
    : []

  return (
    <div>
      <div className="page-header">
        <p className="page-subtitle">
          {now.toLocaleDateString('tr-TR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          {' · '}
          {now.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>

      {loading ? (
        <div className="loading-state"><div className="spinner" /></div>
      ) : (
        <>
          {/* Pinned Market Symbols */}
          <MarketTicker />

          {/* KPI Cards - Collapsible */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: showKPIs ? 'var(--space-3)' : 'var(--space-2)' }}>
            <button
              onClick={() => {
                setShowKPIs(!showKPIs)
                localStorage.setItem('dashboard_show_kpis', JSON.stringify(!showKPIs))
              }}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '4px 0',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                color: 'var(--text-secondary)',
                fontSize: 12,
                fontWeight: 500,
              }}
              title={showKPIs ? 'Kartları gizle' : 'Kartları göster'}
            >
              <span style={{ fontSize: 14 }}>{showKPIs ? '▼' : '▶'}</span>
              <span>Özet Kartlar</span>
            </button>
          </div>

          {showKPIs && (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
              gap: 'var(--space-3)',
              marginBottom: 'var(--space-5)',
            }}>
              <KPICard
                label={t('dashboard.netWorth')} icon="💎"
                value={FMT(summary.total_net_worth || 0)}
                sub={t('dashboard.allAccounts', 'Tüm hesaplar')}
                color="var(--accent)"
              />
              <KPICard
                label={t('dashboard.incomeMTD')} icon="↑"
                value={FMT(summary.total_income || 0)}
                color="var(--income)"
              />
              <KPICard
                label={t('dashboard.expensesMTD')} icon="↓"
                value={FMT(summary.total_expenses || 0)}
                color="var(--expense)"
              />
              <KPICard
                label={t('dashboard.accounts')} icon="🏦"
                value={String(summary.account_count || 0)}
                sub={`${summary.transaction_count || 0} ${t('dashboard.totalTransactions')}`}
              />
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 'var(--space-5)', margin: 'var(--space-5) 0' }}>
            <div className="card">
              <div className="card-header">
                <div>
                  <div className="card-title">Planlı Ödemeler</div>
                  <div className="card-subtitle">Haftalık gelir ve gider planı (8 hafta)</div>
                </div>
                <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
                  <button className="btn btn-ghost btn-sm" onClick={() => setWeekOffset(w => w - 1)}>‹ Önceki</button>
                  <button className="btn btn-ghost btn-sm" onClick={() => setWeekOffset(0)} disabled={weekOffset === 0} style={{ opacity: weekOffset === 0 ? 0.4 : 1 }}>Bugün</button>
                  <button className="btn btn-ghost btn-sm" onClick={() => setWeekOffset(w => w + 1)}>Sonraki ›</button>
                </div>
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={weeklyData} margin={{ top: 4, right: 4, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis
                    tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v: number) => v >= 1_000_000
                      ? `${(v / 1_000_000).toLocaleString('tr-TR', { maximumFractionDigits: 1 })}M`
                      : v >= 1_000
                        ? `${(v / 1_000).toLocaleString('tr-TR', { maximumFractionDigits: 0 })}B`
                        : String(v)
                    }
                    width={52}
                  />
                  <Tooltip content={<ChartTooltip />} cursor={false} />
                  <Legend
                    iconType="circle"
                    iconSize={8}
                    wrapperStyle={{ fontSize: 12 }}
                    formatter={(value) => value === 'income' ? t('transactions.income') : t('transactions.expense')}
                  />
                  <Bar dataKey="income" name="income" fill="#22c55e" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="expense" name="expense" fill="#ef4444" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="card">
              <div className="card-header">
                <div className="card-title">{t('dashboard.expenseBreakdown')}</div>
              </div>
              {pieData.length === 0 ? (
                <div className="empty-state" style={{ padding: 'var(--space-8) 0' }}>
                  <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)', textAlign: 'center' }}>
                    {t('dashboard.noCategoryData', 'Henüz kategori verisi yok')}
                  </div>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={85}
                      paddingAngle={3} dataKey="value">
                      {pieData.map((_: any, i: number) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v: any) => `₺ ${Number(v).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}`} />
                    <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 'var(--space-5)' }}>
            <div className="card">
              <div className="card-header">
                <div>
                  <div className="card-title">{t('dashboard.recentTransactions')}</div>
                  <div className="card-subtitle">{t('dashboard.latestActivity')}</div>
                </div>
                <a href="/transactions" style={{ fontSize: 'var(--font-size-xs)', color: 'var(--accent)' }}>{t('common.viewAll')} →</a>
              </div>
              {recentTxs.length === 0 ? (
                <div className="empty-state" style={{ padding: 'var(--space-8) 0' }}>
                  <div className="empty-state-icon">↕️</div>
                  <div className="empty-state-title">{t('dashboard.noTransactions')}</div>
                  <div className="empty-state-desc">{t('dashboard.noTransactionsDesc')}</div>
                  <a href="/transactions" className="btn btn-primary btn-sm">+ {t('common.add')}</a>
                </div>
              ) : (
                recentTxs.slice(0, 5).map((tx: any) => <TxRow key={tx.id} tx={tx} />)
              )}
            </div>

            <div className="card">
              <div className="card-header">
                <div className="card-title">{t('dashboard.upcoming')}</div>
                <a href="/calendar" style={{ fontSize: 'var(--font-size-xs)', color: 'var(--accent)' }}>{t('common.view')} →</a>
              </div>
              {upcoming.length === 0 ? (
                <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)', textAlign: 'center', padding: 'var(--space-8) 0' }}>
                  {t('dashboard.noUpcoming')}
                </div>
              ) : (
                <div>
                  {upcoming.slice(0, 7).map((p: any, i: number) => (
                    <div key={i} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: '9px 0', borderBottom: '1px solid var(--border)',
                    }}>
                      <div>
                        <div style={{ fontWeight: 500, fontSize: 'var(--font-size-sm)' }}>{p.title || p.label}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>{p.due_date}</div>
                      </div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', color: 'var(--warning)', fontWeight: 600 }}>
                        {p.currency || '₺'} {p.amount?.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div style={{ marginTop: 'var(--space-5)', paddingTop: 'var(--space-4)', borderTop: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 'var(--space-2)' }}>
                  <span>{t('dashboard.incomeMTD')}</span><span style={{ color: 'var(--income)', fontWeight: 600 }}>{FMT(summary.total_income || 0)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 'var(--space-2)' }}>
                  <span>{t('dashboard.expensesMTD')}</span><span style={{ color: 'var(--expense)', fontWeight: 600 }}>{FMT(summary.total_expenses || 0)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-sm)', fontWeight: 600, paddingTop: 'var(--space-2)', borderTop: '1px solid var(--border)' }}>
                  <span>{t('dashboard.net')}</span>
                  <span style={{ color: (summary.total_income || 0) >= (summary.total_expenses || 0) ? 'var(--income)' : 'var(--expense)' }}>
                    {FMT((summary.total_income || 0) - (summary.total_expenses || 0))}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
