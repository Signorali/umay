import React, { useState, useEffect } from 'react'
import {
  BarChart, Bar, AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line,
} from 'recharts'
import { reportsApi, groupsApi, loansApi } from '../api/umay'

// ─────────────────────────────────────────────────────────────────────────────
// Constants & helpers
// ─────────────────────────────────────────────────────────────────────────────

const CHART_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#38bdf8', '#a78bfa', '#fb7185']

const ASSET_TYPE_LABELS: Record<string, string> = {
  REAL_ESTATE: 'Gayrimenkul',
  VEHICLE: 'Araç',
  FINANCIAL: 'Finansal',
  SECURITY: 'Menkul Kıymet',
  CRYPTO: 'Kripto',
  COLLECTIBLE: 'Koleksiyon',
  OTHER: 'Diğer',
}

const MONTHS_TR = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
]

const fmt = (v: number, currency?: string) =>
  (currency ? `${currency} ` : '') +
  Number(v).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

function isoDate(d: Date) {
  return d.toISOString().split('T')[0]
}

function getPeriodDates(month: number, year: number, isFullYear: boolean) {
  if (isFullYear) {
    return {
      period_start: `${year}-01-01`,
      period_end: `${year}-12-31`,
    }
  }
  const start = new Date(year, month, 1)
  const end = new Date(year, month + 1, 0)
  return {
    period_start: isoDate(start),
    period_end: isoDate(end),
  }
}

function getLast6MonthRanges(): { label: string; period_start: string; period_end: string }[] {
  const today = new Date()
  const result = []
  for (let i = 5; i >= 0; i--) {
    const d = new Date(today.getFullYear(), today.getMonth() - i, 1)
    const year = d.getFullYear()
    const month = d.getMonth()
    const start = new Date(year, month, 1)
    const end = new Date(year, month + 1, 0)
    result.push({
      label: `${MONTHS_TR[month].slice(0, 3)} ${year}`,
      period_start: isoDate(start),
      period_end: isoDate(end),
    })
  }
  return result
}

// ─────────────────────────────────────────────────────────────────────────────
// Shared UI components
// ─────────────────────────────────────────────────────────────────────────────

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--bg-elevated)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-sm)',
      padding: '8px 12px',
      fontSize: 'var(--font-size-xs)',
      boxShadow: 'var(--shadow-md)',
    }}>
      <div style={{ color: 'var(--text-tertiary)', marginBottom: 4 }}>{label}</div>
      {payload.map((p: any, i: number) => (
        <div key={i} style={{ color: p.color, fontWeight: 600 }}>
          {p.name}: {fmt(p.value)}
        </div>
      ))}
    </div>
  )
}

function StatCard({ label, value, color, sub }: { label: string; value: string; color?: string; sub?: string }) {
  return (
    <div className="stat-card" style={{ flex: 1 }}>
      <div className="stat-card-label">{label}</div>
      <div className="stat-card-value" style={{ color: color || 'var(--text-primary)', fontSize: 18 }}>{value}</div>
      {sub && (
        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 2 }}>{sub}</div>
      )}
    </div>
  )
}

function EmptyState({ text }: { text: string }) {
  return (
    <div style={{
      color: 'var(--text-tertiary)',
      textAlign: 'center',
      padding: 'var(--space-8) 0',
      fontSize: 'var(--font-size-sm)',
    }}>
      {text}
    </div>
  )
}

function Spinner() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: 'var(--space-10) 0' }}>
      <div className="spinner" />
    </div>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontSize: 'var(--font-size-xs)',
      color: 'var(--text-tertiary)',
      fontWeight: 600,
      textTransform: 'uppercase',
      letterSpacing: '0.07em',
      marginBottom: 'var(--space-2)',
    }}>
      {children}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Report definitions
// ─────────────────────────────────────────────────────────────────────────────

type ReportId =
  | 'income-expense'
  | 'category-breakdown'
  | 'cash-flow'
  | 'loans'
  | 'credit-cards'
  | 'assets'
  | 'investment-performance'

// SVG icons for report items
const ReportIcons: Record<ReportId, React.ReactNode> = {
  'income-expense': <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/><line x1="2" y1="20" x2="22" y2="20"/></svg>,
  'category-breakdown': <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/></svg>,
  'cash-flow': <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>,
  'loans': <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/><path d="M6 15h2m4 0h6"/></svg>,
  'credit-cards': <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>,
  'assets': <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M3 22V12l9-9 9 9v10"/><path d="M9 22V16h6v6"/></svg>,
  'investment-performance': <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a10 10 0 1 0 10 10"/><path d="M12 12 22 2"/><path d="M17 2h5v5"/></svg>,
}

const NAV_GROUPS = [
  {
    label: 'Finansal',
    items: [
      { id: 'income-expense' as ReportId,     title: 'Gelir / Gider',        desc: 'Gelir ve gider karşılaştırması' },
      { id: 'category-breakdown' as ReportId, title: 'Kategori Dağılımı',    desc: 'Kategorilere göre dağılım' },
      { id: 'cash-flow' as ReportId,          title: 'Nakit Akışı',          desc: 'Nakit akış projeksiyonu' },
    ],
  },
  {
    label: 'Borçlar',
    items: [
      { id: 'loans' as ReportId,        title: 'Kredi Özeti',   desc: 'Aktif krediler ve taksitler' },
      { id: 'credit-cards' as ReportId, title: 'Kredi Kartı',   desc: 'Kart limitleri ve borçlar' },
    ],
  },
  {
    label: 'Portföy',
    items: [
      { id: 'assets' as ReportId,                title: 'Varlık Raporu',       desc: 'Portföy ve kazanç/kayıp' },
      { id: 'investment-performance' as ReportId, title: 'Yatırım Performansı', desc: 'Gerçekleşen K/Z ve gelirler' },
    ],
  },
]

const ALL_REPORTS = NAV_GROUPS.flatMap(g => g.items)

const REPORT_COLORS: Record<ReportId, string> = {
  'income-expense':         '#6366f1',
  'category-breakdown':     '#f59e0b',
  'cash-flow':              '#38bdf8',
  'loans':                  '#22c55e',
  'credit-cards':           '#ef4444',
  'assets':                 '#a78bfa',
  'investment-performance': '#fb7185',
}

const REPORT_DESCRIPTIONS: Record<ReportId, string> = {
  'income-expense':         'Seçili dönemdeki gelir ve gider karşılaştırması, aylık trend ve kategori özeti',
  'category-breakdown':     'Harcamalar ve gelirlerin kategorilere göre dağılımı',
  'cash-flow':              'Bekleyen planlı ödemelere göre nakit akış tahmini',
  'loans':                  'Aktif krediler, toplam borç ve gecikmiş taksitler',
  'credit-cards':           'Kart limitleri, borçlar ve kullanım oranları',
  'assets':                 'Varlık portföyü, kazanç/kayıp analizi ve tür dağılımı',
  'investment-performance': 'Portföy bazlı gerçekleşen kazanç, temettü ve faiz geliri',
}

// ─────────────────────────────────────────────────────────────────────────────
// Report content renderers
// ─────────────────────────────────────────────────────────────────────────────

// ── Gelir / Gider ─────────────────────────────────────────────────────────────

function IncomeExpenseReport({
  d,
  trendData,
  trendLoading,
  catIncome,
  catExpense,
  catLoading,
}: {
  d: any
  trendData: any[] | null
  trendLoading: boolean
  catIncome: any[] | null
  catExpense: any[] | null
  catLoading: boolean
}) {
  const income = d?.income?.total ?? 0
  const expense = d?.expense?.total ?? 0
  const net = d?.net ?? (income - expense)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* Stat cards */}
      <div style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
        <StatCard
          label="Toplam Gelir"
          value={fmt(income)}
          color="var(--income)"
          sub={`${d?.income?.count ?? 0} işlem`}
        />
        <StatCard
          label="Toplam Gider"
          value={fmt(expense)}
          color="var(--expense)"
          sub={`${d?.expense?.count ?? 0} işlem`}
        />
        <StatCard
          label="Net Durum"
          value={fmt(net)}
          color={net >= 0 ? 'var(--income)' : 'var(--expense)'}
          sub={net >= 0 ? 'Fazla' : 'Açık'}
        />
      </div>

      {/* Monthly trend */}
      <div>
        <SectionLabel>Son 6 Ay Trendi</SectionLabel>
        <div className="card" style={{ padding: 'var(--space-4)' }}>
          {trendLoading ? (
            <Spinner />
          ) : trendData && trendData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={trendData} margin={{ top: 4, right: 4, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorIncome" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorExpense" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<ChartTooltip />} />
                <Legend
                  wrapperStyle={{ fontSize: 12, paddingTop: 8, color: 'var(--text-secondary)' }}
                />
                <Area
                  type="monotone"
                  dataKey="income"
                  name="Gelir"
                  stroke="#22c55e"
                  strokeWidth={2}
                  fill="url(#colorIncome)"
                  dot={false}
                />
                <Area
                  type="monotone"
                  dataKey="expense"
                  name="Gider"
                  stroke="#ef4444"
                  strokeWidth={2}
                  fill="url(#colorExpense)"
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState text="Trend verisi bulunamadı." />
          )}
        </div>
      </div>

      {/* Top categories */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
        {/* Top income categories */}
        <div>
          <SectionLabel>En Yüksek Gelir Kategorileri</SectionLabel>
          <div className="card" style={{ padding: 'var(--space-4)' }}>
            {catLoading ? (
              <Spinner />
            ) : catIncome && catIncome.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {catIncome.slice(0, 5).map((c: any, i: number) => {
                  const total = catIncome.reduce((s: number, x: any) => s + Math.abs(x.total || 0), 0)
                  const pct = total > 0 ? (Math.abs(c.total || 0) / total) * 100 : 0
                  return (
                    <div key={i}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                        <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500 }}>
                          <span style={{
                            display: 'inline-block',
                            width: 18,
                            color: 'var(--text-tertiary)',
                            fontSize: 'var(--font-size-xs)',
                          }}>
                            {i + 1}.
                          </span>
                          {c.category_name || '—'}
                        </span>
                        <span style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: 'var(--font-size-xs)',
                          color: 'var(--income)',
                          fontWeight: 600,
                        }}>
                          {fmt(Math.abs(c.total || 0))}
                        </span>
                      </div>
                      <div style={{
                        height: 4,
                        background: 'var(--bg-overlay)',
                        borderRadius: 2,
                        overflow: 'hidden',
                      }}>
                        <div style={{
                          height: '100%',
                          width: `${pct}%`,
                          background: CHART_COLORS[i % CHART_COLORS.length],
                          borderRadius: 2,
                        }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <EmptyState text="Veri yok" />
            )}
          </div>
        </div>

        {/* Top expense categories */}
        <div>
          <SectionLabel>En Yüksek Gider Kategorileri</SectionLabel>
          <div className="card" style={{ padding: 'var(--space-4)' }}>
            {catLoading ? (
              <Spinner />
            ) : catExpense && catExpense.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {catExpense.slice(0, 5).map((c: any, i: number) => {
                  const total = catExpense.reduce((s: number, x: any) => s + Math.abs(x.total || 0), 0)
                  const pct = total > 0 ? (Math.abs(c.total || 0) / total) * 100 : 0
                  return (
                    <div key={i}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                        <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500 }}>
                          <span style={{
                            display: 'inline-block',
                            width: 18,
                            color: 'var(--text-tertiary)',
                            fontSize: 'var(--font-size-xs)',
                          }}>
                            {i + 1}.
                          </span>
                          {c.category_name || '—'}
                        </span>
                        <span style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: 'var(--font-size-xs)',
                          color: 'var(--expense)',
                          fontWeight: 600,
                        }}>
                          {fmt(Math.abs(c.total || 0))}
                        </span>
                      </div>
                      <div style={{
                        height: 4,
                        background: 'var(--bg-overlay)',
                        borderRadius: 2,
                        overflow: 'hidden',
                      }}>
                        <div style={{
                          height: '100%',
                          width: `${pct}%`,
                          background: '#ef4444',
                          borderRadius: 2,
                        }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <EmptyState text="Veri yok" />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Kategori Dağılımı ─────────────────────────────────────────────────────────

function CategoryBreakdownReport({
  d,
  groupId,
  periodDates,
}: {
  d: any
  groupId: string
  periodDates: { period_start: string; period_end: string }
}) {
  const [mode, setMode] = useState<'EXPENSE' | 'INCOME' | 'BOTH'>('EXPENSE')
  const [incomeData, setIncomeData] = useState<any[] | null>(null)
  const [incomeLoading, setIncomeLoading] = useState(false)

  useEffect(() => {
    if (mode === 'INCOME' || mode === 'BOTH') {
      if (!incomeData) {
        setIncomeLoading(true)
        const gp = groupId ? { group_id: groupId } : {}
        reportsApi
          .categoryBreakdown({ ...periodDates, ...gp, transaction_type: 'INCOME' })
          .then(r => setIncomeData(r?.data ?? []))
          .catch(() => setIncomeData([]))
          .finally(() => setIncomeLoading(false))
      }
    }
  }, [mode])

  const expenseRows: any[] = Array.isArray(d) ? d : []
  const incomeRows: any[] = incomeData || []

  const buildPieData = (rows: any[]) =>
    rows.map((c: any) => ({
      name: c.category_name || '—',
      value: Math.abs(c.total || 0),
    }))

  const renderDonutWithList = (rows: any[], accentColor: string, label: string) => {
    if (rows.length === 0) return <EmptyState text={`${label} verisi bulunamadı.`} />
    const pieData = buildPieData(rows)
    const total = pieData.reduce((s, x) => s + x.value, 0)
    return (
      <div>
        <SectionLabel>{label}</SectionLabel>
        <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: 'var(--space-5)', alignItems: 'center' }}>
          <ResponsiveContainer width={200} height={200}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={2}
                dataKey="value"
              >
                {pieData.map((_: any, i: number) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v: any) => fmt(Number(v))} />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {rows.map((c: any, i: number) => {
              const val = Math.abs(c.total || 0)
              const pct = total > 0 ? (val / total) * 100 : 0
              return (
                <div key={i}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                      <div style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: CHART_COLORS[i % CHART_COLORS.length],
                        flexShrink: 0,
                      }} />
                      <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500 }}>
                        {c.category_name || '—'}
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                      <span style={{
                        fontSize: 'var(--font-size-xs)',
                        color: 'var(--text-tertiary)',
                        minWidth: 36,
                        textAlign: 'right',
                      }}>
                        {pct.toFixed(1)}%
                      </span>
                      <span style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 'var(--font-size-xs)',
                        color: accentColor,
                        fontWeight: 600,
                        minWidth: 80,
                        textAlign: 'right',
                      }}>
                        {fmt(val)}
                      </span>
                    </div>
                  </div>
                  <div style={{ height: 3, background: 'var(--bg-overlay)', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${pct}%`,
                      background: CHART_COLORS[i % CHART_COLORS.length],
                      borderRadius: 2,
                    }} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* Mode toggle */}
      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
        {(['EXPENSE', 'INCOME', 'BOTH'] as const).map(m => (
          <button
            key={m}
            className={`btn btn-sm ${mode === m ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setMode(m)}
          >
            {m === 'EXPENSE' ? 'Giderler' : m === 'INCOME' ? 'Gelirler' : 'Her İkisi'}
          </button>
        ))}
      </div>

      {mode === 'BOTH' ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-6)' }}>
          <div className="card" style={{ padding: 'var(--space-4)' }}>
            {renderDonutWithList(expenseRows, 'var(--expense)', 'Giderler')}
          </div>
          <div className="card" style={{ padding: 'var(--space-4)' }}>
            {incomeLoading ? <Spinner /> : renderDonutWithList(incomeRows, 'var(--income)', 'Gelirler')}
          </div>
        </div>
      ) : mode === 'EXPENSE' ? (
        <div className="card" style={{ padding: 'var(--space-4)' }}>
          {renderDonutWithList(expenseRows, 'var(--expense)', 'Gider Kategorileri')}
        </div>
      ) : (
        <div className="card" style={{ padding: 'var(--space-4)' }}>
          {incomeLoading ? <Spinner /> : renderDonutWithList(incomeRows, 'var(--income)', 'Gelir Kategorileri')}
        </div>
      )}
    </div>
  )
}

// ── Nakit Akışı ───────────────────────────────────────────────────────────────

function CashFlowReport({ d, groupId, onRefetch, currentMonths }: { d: any; groupId: string; onRefetch: (months: number) => void; currentMonths: number }) {
  const [months, setMonths] = useState(currentMonths)

  // Sync local state when parent resets (e.g. group change)
  useEffect(() => {
    setMonths(currentMonths)
  }, [currentMonths])

  const handleMonths = (m: number) => {
    setMonths(m)
    onRefetch(m)
  }

  const rows: any[] = Array.isArray(d) ? d : (d?.payments ?? [])
  const totalIn = rows
    .filter((r: any) => r.type === 'INCOME')
    .reduce((s: number, r: any) => s + (r.amount || 0), 0)
  const totalOut = rows
    .filter((r: any) => r.type !== 'INCOME')
    .reduce((s: number, r: any) => s + (r.amount || 0), 0)
  const netProj = totalIn - totalOut

  // Build monthly bar chart data
  const monthlyMap: Record<string, { label: string; income: number; expense: number }> = {}
  rows.forEach((r: any) => {
    if (!r.date) return
    const key = r.date.slice(0, 7)
    if (!monthlyMap[key]) {
      const [y, m] = key.split('-').map(Number)
      monthlyMap[key] = { label: `${MONTHS_TR[m - 1].slice(0, 3)} ${y}`, income: 0, expense: 0 }
    }
    if (r.type === 'INCOME') {
      monthlyMap[key].income += r.amount || 0
    } else {
      monthlyMap[key].expense += r.amount || 0
    }
  })
  const chartData = Object.entries(monthlyMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, v]) => v)

  // Sort rows by date
  const sortedRows = [...rows].sort((a, b) => (a.date || '').localeCompare(b.date || ''))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* months_ahead selector */}
      <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
        <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginRight: 'var(--space-2)' }}>
          Gösterim:
        </span>
        {([0, 1, 2, 3, 6, 12] as const).map(m => (
          <button
            key={m}
            className={`btn btn-sm ${months === m ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => handleMonths(m)}
          >
            {m === 0 ? 'Tümü' : `${m} ay`}
          </button>
        ))}
      </div>

      {/* Stat cards */}
      <div style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
        <StatCard label="Beklenen Giriş"      value={fmt(totalIn)}   color="var(--income)" />
        <StatCard label="Beklenen Çıkış"      value={fmt(totalOut)}  color="var(--expense)" />
        <StatCard
          label="Net Projeksiyon"
          value={fmt(netProj)}
          color={netProj >= 0 ? 'var(--income)' : 'var(--expense)'}
        />
      </div>

      {/* Bar chart */}
      {chartData.length > 0 && (
        <div>
          <SectionLabel>Aylık Dağılım</SectionLabel>
          <div className="card" style={{ padding: 'var(--space-4)' }}>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chartData} margin={{ top: 4, right: 4, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={52}
                  tickFormatter={(v: number) =>
                    v >= 1_000_000
                      ? `${(v / 1_000_000).toLocaleString('tr-TR', { maximumFractionDigits: 1 })}M`
                      : v >= 1_000
                        ? `${(v / 1_000).toLocaleString('tr-TR', { maximumFractionDigits: 0 })}B`
                        : String(v)
                  }
                />
                <Tooltip cursor={false} content={<ChartTooltip />} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }} />
                <Bar dataKey="income" name="Giriş" fill="#22c55e" radius={[3, 3, 0, 0]} />
                <Bar dataKey="expense" name="Çıkış" fill="#ef4444" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Payment list */}
      <div>
        <SectionLabel>Yaklaşan Ödemeler</SectionLabel>
        {sortedRows.length === 0 ? (
          <EmptyState text="Planlı ödeme bulunamadı." />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {sortedRows.map((r: any, i: number) => (
              <div key={i} style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '10px 14px',
                background: 'var(--bg-surface)',
                borderRadius: 'var(--radius-sm)',
                borderLeft: `3px solid ${r.type === 'INCOME' ? 'var(--income)' : 'var(--expense)'}`,
                border: '1px solid var(--border)',
                borderLeftWidth: 3,
              }}>
                <div>
                  <div style={{ fontWeight: 500, fontSize: 'var(--font-size-sm)' }}>{r.title}</div>
                  {r.date && (
                    <div style={{
                      display: 'inline-block',
                      marginTop: 3,
                      padding: '1px 8px',
                      borderRadius: 'var(--radius-sm)',
                      background: 'var(--bg-overlay)',
                      fontSize: 'var(--font-size-xs)',
                      color: 'var(--text-tertiary)',
                    }}>
                      {r.date}
                    </div>
                  )}
                </div>
                <div style={{
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 600,
                  fontSize: 'var(--font-size-sm)',
                  color: r.type === 'INCOME' ? 'var(--income)' : 'var(--expense)',
                }}>
                  {r.type === 'INCOME' ? '+' : '-'}{fmt(r.amount || 0, r.currency)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Kredi Özeti ───────────────────────────────────────────────────────────────

function LoansReport({ d, loans, loansLoading }: { d: any; loans: any[]; loansLoading: boolean }) {
  const principalEntries = Object.entries(d.total_principal || {})
  const remainingEntries = Object.entries(d.total_remaining || {})

  // Calculate next due date from payment_day
  const getNextDueDate = (paymentDay: number): string => {
    const today = new Date()
    const thisMonth = new Date(today.getFullYear(), today.getMonth(), paymentDay)
    const next = thisMonth < today
      ? new Date(today.getFullYear(), today.getMonth() + 1, paymentDay)
      : thisMonth
    return next.toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* Stat cards */}
      <div style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
        <StatCard label="Aktif Kredi" value={`${d.active_loan_count ?? 0} adet`} />
        <StatCard
          label="Gecikmiş Taksit"
          value={`${d.overdue_installments ?? 0} adet`}
          color={d.overdue_installments ? 'var(--expense)' : undefined}
        />
        {principalEntries.map(([cur, val]) => (
          <StatCard key={`p-${cur}`} label={`Ana Para (${cur})`} value={fmt(val as number, cur)} />
        ))}
        {remainingEntries.map(([cur, val]) => (
          <StatCard key={`r-${cur}`} label={`Kalan Borç (${cur})`} value={fmt(val as number, cur)} color="var(--expense)" />
        ))}
      </div>

      {/* Individual loan cards */}
      <div>
        <SectionLabel>Aktif Krediler</SectionLabel>
        {loansLoading ? (
          <div className="loading-state" style={{ padding: 'var(--space-8)' }}><div className="spinner" /></div>
        ) : loans.length === 0 ? (
          <EmptyState text="Aktif kredi bulunamadı." />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            {loans.map((loan: any) => {
              const totalDebt = parseFloat(loan.principal) + parseFloat(loan.total_interest || 0)
              const remaining = parseFloat(loan.remaining_balance || 0)
              const paid = totalDebt - remaining
              const pct = totalDebt > 0 ? Math.min((paid / totalDebt) * 100, 100) : 0
              const paidMonths = loan.installment_amount > 0
                ? Math.round(parseFloat(loan.total_paid || 0) / parseFloat(loan.installment_amount))
                : 0
              const totalMonths = loan.term_months || 1
              const nextDue = getNextDueDate(loan.payment_day || 1)
              const maturity = loan.maturity_date
                ? new Date(loan.maturity_date).toLocaleDateString('tr-TR', { month: 'long', year: 'numeric' })
                : null
              const interestRate = parseFloat(loan.interest_rate || 0)

              return (
                <div key={loan.id} className="card" style={{ padding: 'var(--space-5)', borderLeft: '3px solid var(--accent)' }}>
                  {/* Header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-4)' }}>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 'var(--font-size-md)', marginBottom: 4 }}>
                        {loan.lender_name}
                      </div>
                      {loan.loan_purpose && (
                        <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
                          {loan.loan_purpose}
                        </div>
                      )}
                      <div style={{ display: 'flex', gap: 'var(--space-2)', marginTop: 6, flexWrap: 'wrap' }}>
                        <span style={{
                          fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 20,
                          background: 'var(--accent-subtle)', color: 'var(--accent)',
                        }}>
                          {loan.currency}
                        </span>
                        {interestRate > 0 && (
                          <span style={{
                            fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 20,
                            background: 'var(--bg-overlay)', color: 'var(--text-secondary)',
                          }}>
                            %{interestRate.toFixed(2)} faiz
                          </span>
                        )}
                        {maturity && (
                          <span style={{
                            fontSize: 11, padding: '2px 8px', borderRadius: 20,
                            background: 'var(--bg-overlay)', color: 'var(--text-tertiary)',
                          }}>
                            Bitiş: {maturity}
                          </span>
                        )}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 2 }}>Kalan Borç</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 'var(--font-size-lg)', color: 'var(--expense)' }}>
                        {fmt(remaining, loan.currency)}
                      </div>
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div style={{ marginBottom: 'var(--space-4)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>
                        {paidMonths} / {totalMonths} taksit ödendi
                      </span>
                      <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: pct > 70 ? 'var(--income)' : 'var(--accent)' }}>
                        %{pct.toFixed(1)} tamamlandı
                      </span>
                    </div>
                    <div style={{ height: 8, background: 'var(--bg-overlay)', borderRadius: 4, overflow: 'hidden' }}>
                      <div style={{
                        height: '100%', width: `${pct}%`,
                        background: `linear-gradient(90deg, var(--accent), ${pct > 70 ? 'var(--income)' : 'var(--accent)'})`,
                        borderRadius: 4, transition: 'width 0.5s ease',
                      }} />
                    </div>
                  </div>

                  {/* Bottom row: key figures */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--space-3)' }}>
                    <div style={{ padding: '10px 12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 3 }}>Kredi Tutarı</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 13 }}>{fmt(parseFloat(loan.principal), loan.currency)}</div>
                    </div>
                    <div style={{ padding: '10px 12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 3 }}>Ödenen</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 13, color: 'var(--income)' }}>{fmt(paid, loan.currency)}</div>
                    </div>
                    <div style={{ padding: '10px 12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 3 }}>Aylık Taksit</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 13 }}>{fmt(parseFloat(loan.installment_amount || 0), loan.currency)}</div>
                    </div>
                    <div style={{ padding: '10px 12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 3 }}>Sonraki Taksit</div>
                      <div style={{ fontWeight: 600, fontSize: 12, color: 'var(--warning)' }}>{nextDue}</div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Kredi Kartı Özeti ─────────────────────────────────────────────────────────

function CreditCardsReport({ d }: { d: any }) {
  const limitEntries = Object.entries(d.total_limit || {})
  const debtEntries = Object.entries(d.total_debt || {})
  const utilEntries = Object.entries(d.utilization || {})
  const cards: any[] = d.cards || []

  // Overall utilization (first currency or aggregate)
  const overallUtil = utilEntries.length > 0 ? (utilEntries[0][1] as number) : null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* Stat cards */}
      <div style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
        <StatCard label="Kart Sayısı" value={`${d.card_count ?? 0} adet`} />
        <StatCard
          label="Gecikmiş Ekstre"
          value={`${d.overdue_statements ?? 0} adet`}
          color={d.overdue_statements ? 'var(--expense)' : undefined}
        />
        {limitEntries.map(([cur, val]) => (
          <StatCard key={`l-${cur}`} label={`Toplam Limit (${cur})`} value={fmt(val as number, cur)} />
        ))}
        {debtEntries.map(([cur, val]) => (
          <StatCard key={`d-${cur}`} label={`Toplam Borç (${cur})`} value={fmt(val as number, cur)} color="var(--expense)" />
        ))}
      </div>

      {/* Overall utilization bar */}
      {overallUtil != null && (
        <div className="card" style={{ padding: 'var(--space-4)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
            <SectionLabel>Genel Kullanım Oranı</SectionLabel>
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontWeight: 700,
              fontSize: 'var(--font-size-md)',
              color: overallUtil > 70 ? 'var(--expense)' : overallUtil > 40 ? '#f59e0b' : 'var(--income)',
            }}>
              {overallUtil.toFixed(1)}%
            </span>
          </div>
          <div style={{ height: 12, background: 'var(--bg-overlay)', borderRadius: 6, overflow: 'hidden' }}>
            <div style={{
              height: '100%',
              width: `${Math.min(overallUtil, 100)}%`,
              borderRadius: 6,
              background: overallUtil > 70 ? 'var(--expense)' : overallUtil > 40 ? '#f59e0b' : 'var(--income)',
              transition: 'width 0.4s ease',
            }} />
          </div>
        </div>
      )}

      {/* Individual card details */}
      {cards.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <SectionLabel>Kartlar</SectionLabel>
          {cards.map((card: any, i: number) => {
            const util = card.utilization ?? (card.limit > 0 ? (card.debt / card.limit) * 100 : 0)
            const barColor = util > 70 ? 'var(--expense)' : util > 40 ? '#f59e0b' : 'var(--income)'
            return (
              <div key={i} className="card" style={{ padding: 'var(--space-4)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-3)' }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 'var(--font-size-md)' }}>
                      {card.name || card.bank || `Kart ${i + 1}`}
                    </div>
                    {card.bank && card.name && (
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>{card.bank}</div>
                    )}
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>Kullanım</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: barColor }}>
                      {util.toFixed(1)}%
                    </div>
                  </div>
                </div>
                {/* Limit bar */}
                {card.limit > 0 && (
                  <div style={{ marginBottom: 'var(--space-3)' }}>
                    <div style={{ height: 6, background: 'var(--bg-overlay)', borderRadius: 3, overflow: 'hidden' }}>
                      <div style={{
                        height: '100%',
                        width: `${Math.min(util, 100)}%`,
                        background: barColor,
                        borderRadius: 3,
                        transition: 'width 0.4s ease',
                      }} />
                    </div>
                  </div>
                )}
                <div style={{ display: 'flex', gap: 'var(--space-5)', fontSize: 'var(--font-size-sm)' }}>
                  {card.debt != null && (
                    <div>
                      <span style={{ color: 'var(--text-tertiary)' }}>Borç: </span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--expense)' }}>
                        {fmt(card.debt, card.currency)}
                      </span>
                    </div>
                  )}
                  {card.limit != null && (
                    <div>
                      <span style={{ color: 'var(--text-tertiary)' }}>Limit: </span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                        {fmt(card.limit, card.currency)}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ) : limitEntries.length === 0 ? (
        <EmptyState text="Kredi kartı bulunamadı." />
      ) : null}
    </div>
  )
}

// ── Varlık Raporu ─────────────────────────────────────────────────────────────

function AssetsReport({ d }: { d: any }) {
  const byType: Record<string, any> = d.by_type || {}
  const pieData = Object.entries(byType)
    .map(([k, v]: [string, any]) => ({
      name: ASSET_TYPE_LABELS[k] || k,
      value: v.total_current_value || 0,
    }))
    .filter(x => x.value > 0)

  const unreal = d.unrealized_gain_loss ?? 0
  const real = d.realized_gain_loss ?? 0
  const c = d.currency

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* Stat cards */}
      <div style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
        <StatCard label="Toplam Varlık"       value={`${d.asset_count ?? 0} adet`} />
        <StatCard label="Satılan Varlık"      value={`${d.sold_count ?? 0} adet`} />
        <StatCard label="Alış Değeri"         value={fmt(d.total_purchase_value ?? 0, c)} />
        <StatCard label="Güncel Değer"        value={fmt(d.total_current_value ?? 0, c)} />
        <StatCard
          label="Gerçekleşmemiş K/Z"
          value={fmt(unreal, c)}
          color={unreal >= 0 ? 'var(--income)' : 'var(--expense)'}
        />
        <StatCard
          label="Gerçekleşen K/Z"
          value={fmt(real, c)}
          color={real >= 0 ? 'var(--income)' : 'var(--expense)'}
        />
      </div>

      {pieData.length > 0 ? (
        <>
          {/* Donut + ranked list */}
          <div>
            <SectionLabel>Tür Dağılımı</SectionLabel>
            <div className="card" style={{ padding: 'var(--space-4)' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 'var(--space-6)', alignItems: 'center' }}>
                <ResponsiveContainer width={220} height={220}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={58}
                      outerRadius={95}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {pieData.map((_: any, i: number) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v: any) => fmt(Number(v), c)} />
                  </PieChart>
                </ResponsiveContainer>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                  {Object.entries(byType).map(([k, v]: [string, any], i: number) => {
                    const gl = (v.total_current_value || 0) - (v.total_purchase_value || 0)
                    return (
                      <div key={k} style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: '6px 0',
                        borderBottom: '1px solid var(--border)',
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                          <div style={{
                            width: 10,
                            height: 10,
                            borderRadius: '50%',
                            background: CHART_COLORS[i % CHART_COLORS.length],
                            flexShrink: 0,
                          }} />
                          <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500 }}>
                            {ASSET_TYPE_LABELS[k] || k}
                          </span>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', fontWeight: 600 }}>
                            {fmt(v.total_current_value || 0, c)}
                          </div>
                          {gl !== 0 && (
                            <div style={{
                              fontSize: 'var(--font-size-xs)',
                              color: gl >= 0 ? 'var(--income)' : 'var(--expense)',
                              fontFamily: 'var(--font-mono)',
                            }}>
                              {gl >= 0 ? '+' : ''}{fmt(gl, c)}
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          </div>

          {/* Net gain/loss highlight */}
          {(unreal !== 0 || real !== 0) && (
            <div className="card" style={{
              padding: 'var(--space-4)',
              borderLeft: `4px solid ${unreal + real >= 0 ? 'var(--income)' : 'var(--expense)'}`,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <span style={{ fontWeight: 600, fontSize: 'var(--font-size-md)' }}>Net Kazanç / Kayıp{c ? ` (${c})` : ''}</span>
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontWeight: 700,
                fontSize: 'var(--font-size-lg)',
                color: unreal + real >= 0 ? 'var(--income)' : 'var(--expense)',
              }}>
                {unreal + real >= 0 ? '+' : ''}{fmt(unreal + real, c)}
              </span>
            </div>
          )}
        </>
      ) : d.asset_count === 0 ? (
        <EmptyState text="Kayıtlı varlık bulunamadı." />
      ) : null}
    </div>
  )
}

// ── Yatırım Performansı ───────────────────────────────────────────────────────

function InvestmentPerformanceReport({ d }: { d: any }) {
  const portfolios: any[] = d.portfolios || []
  const grandReal = d.grand_realized_pl ?? 0
  const grandInc = d.grand_income ?? 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* Stat cards */}
      <div style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
        <StatCard label="Portföy Sayısı" value={`${d.portfolio_count ?? 0} adet`} />
        <StatCard
          label="Gerçekleşen K/Z"
          value={fmt(grandReal)}
          color={grandReal >= 0 ? 'var(--income)' : 'var(--expense)'}
        />
        <StatCard
          label="Temettü / Faiz Geliri"
          value={fmt(grandInc)}
          color="var(--income)"
        />
      </div>

      {portfolios.length === 0 ? (
        <EmptyState text="Portföy bulunamadı." />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {portfolios.map((p: any) => {
            const openPos = Object.entries(p.open_positions || {})
            return (
              <div key={p.portfolio_id} className="card" style={{ padding: 'var(--space-4)' }}>
                {/* Portfolio header */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: 'var(--space-4)',
                }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 'var(--font-size-md)' }}>{p.portfolio_name}</div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>{p.currency}</div>
                  </div>
                  {p.realized_pl != null && (
                    <div style={{
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 700,
                      fontSize: 'var(--font-size-md)',
                      color: p.realized_pl >= 0 ? 'var(--income)' : 'var(--expense)',
                    }}>
                      {p.realized_pl >= 0 ? '+' : ''}{fmt(p.realized_pl, p.currency)}
                    </div>
                  )}
                </div>

                {/* Stat chips */}
                <div style={{
                  display: 'flex',
                  gap: 'var(--space-2)',
                  flexWrap: 'wrap',
                  marginBottom: openPos.length ? 'var(--space-4)' : 0,
                }}>
                  {[
                    { label: 'Yatırılan', value: fmt(p.total_invested, p.currency), color: undefined },
                    { label: 'Satılan', value: fmt(p.total_sold, p.currency), color: undefined },
                    { label: 'Gerçekleşen K/Z', value: fmt(p.realized_pl, p.currency), color: p.realized_pl >= 0 ? 'var(--income)' : 'var(--expense)' },
                    { label: 'Temettü', value: fmt(p.dividend_income, p.currency), color: 'var(--income)' },
                    { label: 'Faiz', value: fmt(p.interest_income, p.currency), color: 'var(--income)' },
                  ].map((chip, ci) => (
                    <div key={ci} style={{
                      padding: '6px 12px',
                      background: 'var(--bg-overlay)',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border)',
                    }}>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 2 }}>
                        {chip.label}
                      </div>
                      <div style={{
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 600,
                        fontSize: 'var(--font-size-sm)',
                        color: chip.color || 'var(--text-primary)',
                      }}>
                        {chip.value}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Open positions table */}
                {openPos.length > 0 && (
                  <div>
                    <SectionLabel>Açık Pozisyonlar</SectionLabel>
                    <div style={{ borderRadius: 'var(--radius-sm)', overflow: 'hidden', border: '1px solid var(--border)' }}>
                      <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                          <tr>
                            <th style={{ padding: '8px 12px', textAlign: 'left', fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', background: 'var(--bg-overlay)', fontWeight: 600 }}>Sembol</th>
                            <th style={{ padding: '8px 12px', textAlign: 'right', fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', background: 'var(--bg-overlay)', fontWeight: 600 }}>Miktar</th>
                            <th style={{ padding: '8px 12px', textAlign: 'right', fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', background: 'var(--bg-overlay)', fontWeight: 600 }}>Maliyet Bazı</th>
                          </tr>
                        </thead>
                        <tbody>
                          {openPos.map(([sym, pos]: [string, any], ri: number) => (
                            <tr key={sym} style={{ background: ri % 2 === 0 ? 'var(--bg-surface)' : 'var(--bg-elevated)' }}>
                              <td style={{ padding: '8px 12px', fontWeight: 600, fontSize: 'var(--font-size-sm)' }}>{sym}</td>
                              <td style={{ padding: '8px 12px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
                                {pos.quantity}
                              </td>
                              <td style={{ padding: '8px 12px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', fontWeight: 600 }}>
                                {fmt(pos.cost_basis, p.currency)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Welcome / no-selection state
// ─────────────────────────────────────────────────────────────────────────────

function WelcomeGrid({ onSelect }: { onSelect: (id: ReportId) => void }) {
  return (
    <div>
      <div style={{
        textAlign: 'center',
        padding: 'var(--space-8) var(--space-4) var(--space-6)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 'var(--space-3)', color: 'var(--text-tertiary)' }}>
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>
        </div>
        <div style={{ fontWeight: 700, fontSize: 'var(--font-size-lg)', color: 'var(--text-primary)', marginBottom: 'var(--space-2)' }}>
          Bir rapor seçin
        </div>
        <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-tertiary)' }}>
          Sol menüden veya aşağıdaki kartlardan incelemek istediğiniz raporu seçin
        </div>
      </div>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: 'var(--space-3)',
      }}>
        {ALL_REPORTS.map(r => (
          <button
            key={r.id}
            onClick={() => onSelect(r.id)}
            style={{
              background: 'var(--bg-surface)',
              border: `1px solid var(--border)`,
              borderRadius: 'var(--radius-md)',
              padding: 'var(--space-4)',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'border-color 0.15s, background 0.15s',
              display: 'flex',
              gap: 'var(--space-3)',
              alignItems: 'flex-start',
            }}
            onMouseEnter={e => {
              ;(e.currentTarget as HTMLElement).style.borderColor = REPORT_COLORS[r.id]
              ;(e.currentTarget as HTMLElement).style.background = 'var(--bg-hover)'
            }}
            onMouseLeave={e => {
              ;(e.currentTarget as HTMLElement).style.borderColor = 'var(--border)'
              ;(e.currentTarget as HTMLElement).style.background = 'var(--bg-surface)'
            }}
          >
            <div style={{
              width: 42,
              height: 42,
              borderRadius: 'var(--radius-md)',
              background: `${REPORT_COLORS[r.id]}18`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: REPORT_COLORS[r.id],
              flexShrink: 0,
            }}>
              <span style={{ transform: 'scale(1.3)', display: 'flex' }}>{ReportIcons[r.id]}</span>
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: 'var(--font-size-sm)', color: REPORT_COLORS[r.id], marginBottom: 3 }}>
                {r.title}
              </div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', lineHeight: 1.4 }}>
                {REPORT_DESCRIPTIONS[r.id]}
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Period Picker
// ─────────────────────────────────────────────────────────────────────────────

interface PeriodState {
  month: number   // 0-11
  year: number
  isFullYear: boolean
}

function PeriodPicker({ value, onChange }: { value: PeriodState; onChange: (v: PeriodState) => void }) {
  const currentYear = new Date().getFullYear()
  const years = Array.from({ length: 7 }, (_, i) => currentYear - 3 + i)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', width: '100%' }}>
      {/* Month + Year selectors */}
      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
        <select
          className="form-input"
          style={{ flex: 1, minWidth: 0 }}
          value={value.month}
          disabled={value.isFullYear}
          onChange={e => onChange({ ...value, month: Number(e.target.value), isFullYear: false })}
        >
          {MONTHS_TR.map((m, i) => (
            <option key={i} value={i}>{m}</option>
          ))}
        </select>
        <select
          className="form-input"
          style={{ width: 96 }}
          value={value.year}
          onChange={e => onChange({ ...value, year: Number(e.target.value) })}
        >
          {years.map(y => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Page
// ─────────────────────────────────────────────────────────────────────────────

export function ReportsPage() {
  const today = new Date()
  const [groups, setGroups] = useState<any[]>([])
  const [groupId, setGroupId] = useState<string>('')
  const [period, setPeriod] = useState<PeriodState>({
    month: today.getMonth(),
    year: today.getFullYear(),
    isFullYear: false,
  })
  const [activeReport, setActiveReport] = useState<ReportId | null>(null)
  const [data, setData] = useState<Partial<Record<ReportId, any>>>({})
  const [loading, setLoading] = useState<Partial<Record<ReportId, boolean>>>({})

  // income-expense specific: monthly trend & categories
  const [trendData, setTrendData] = useState<any[] | null>(null)
  const [trendLoading, setTrendLoading] = useState(false)
  const [catIncome, setCatIncome] = useState<any[] | null>(null)
  const [catExpense, setCatExpense] = useState<any[] | null>(null)
  const [catLoading, setCatLoading] = useState(false)

  // loans list (individual loan cards)
  const [loansList, setLoansList] = useState<any[]>([])
  const [loansListLoading, setLoansListLoading] = useState(false)

  // cash-flow months_ahead state (0 = all pending payments, no date limit)
  const [cashFlowMonths, setCashFlowMonths] = useState(0)

  useEffect(() => {
    groupsApi.list().then(r => setGroups(r.data || [])).catch(() => {})
  }, [])

  const fetchReport = async (
    id: ReportId,
    p: PeriodState,
    gid: string,
    months?: number
  ) => {
    setLoading(prev => ({ ...prev, [id]: true }))
    const dates = getPeriodDates(p.month, p.year, p.isFullYear)
    const gp = gid ? { group_id: gid } : {}
    try {
      let res: any
      if (id === 'income-expense')
        res = await reportsApi.incomeExpense({ ...dates, ...gp })
      else if (id === 'category-breakdown')
        res = await reportsApi.categoryBreakdown({ ...dates, ...gp, transaction_type: 'EXPENSE' })
      else if (id === 'cash-flow')
        res = await reportsApi.cashFlow({ months_ahead: months ?? cashFlowMonths, ...gp })
      else if (id === 'loans') {
        res = await reportsApi.loans(gp)
        setLoansListLoading(true)
        loansApi.list({ status: 'ACTIVE', page_size: 100 })
          .then(r => setLoansList(Array.isArray(r.data) ? r.data : []))
          .catch(() => setLoansList([]))
          .finally(() => setLoansListLoading(false))
      }
      else if (id === 'credit-cards')
        res = await reportsApi.creditCards(gp)
      else if (id === 'assets')
        res = await reportsApi.assets(gp)
      else if (id === 'investment-performance')
        res = await reportsApi.investmentPerformance()
      setData(prev => ({ ...prev, [id]: res?.data ?? null }))
    } catch {
      setData(prev => ({ ...prev, [id]: null }))
    }
    setLoading(prev => ({ ...prev, [id]: false }))
  }

  const fetchTrend = async (gid: string) => {
    setTrendLoading(true)
    const gp = gid ? { group_id: gid } : {}
    try {
      const ranges = getLast6MonthRanges()
      const results = await Promise.all(
        ranges.map(r =>
          reportsApi
            .incomeExpense({ period_start: r.period_start, period_end: r.period_end, ...gp })
            .then(res => ({
              label: r.label,
              income: res?.data?.income?.total ?? 0,
              expense: res?.data?.expense?.total ?? 0,
            }))
            .catch(() => ({ label: r.label, income: 0, expense: 0 }))
        )
      )
      setTrendData(results)
    } catch {
      setTrendData([])
    }
    setTrendLoading(false)
  }

  const fetchCategories = async (p: PeriodState, gid: string) => {
    setCatLoading(true)
    const dates = getPeriodDates(p.month, p.year, p.isFullYear)
    const gp = gid ? { group_id: gid } : {}
    try {
      const [expRes, incRes] = await Promise.all([
        reportsApi.categoryBreakdown({ ...dates, ...gp, transaction_type: 'EXPENSE' }),
        reportsApi.categoryBreakdown({ ...dates, ...gp, transaction_type: 'INCOME' }),
      ])
      setCatExpense(expRes?.data ?? [])
      setCatIncome(incRes?.data ?? [])
    } catch {
      setCatExpense([])
      setCatIncome([])
    }
    setCatLoading(false)
  }

  const selectReport = (id: ReportId) => {
    setActiveReport(id)
    fetchReport(id, period, groupId)
    if (id === 'income-expense') {
      setTrendData(null)
      setCatIncome(null)
      setCatExpense(null)
      fetchTrend(groupId)
      fetchCategories(period, groupId)
    }
  }

  // Re-fetch when period/group changes
  useEffect(() => {
    if (!activeReport) return
    setData({})
    setTrendData(null)
    setCatIncome(null)
    setCatExpense(null)
    fetchReport(activeReport, period, groupId)
    if (activeReport === 'income-expense') {
      fetchTrend(groupId)
      fetchCategories(period, groupId)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, groupId])

  const handleCashFlowRefetch = (months: number) => {
    setCashFlowMonths(months)
    // No spinner — update data in the background so the button selection state stays intact
    const gp = groupId ? { group_id: groupId } : {}
    reportsApi
      .cashFlow({ months_ahead: months, ...gp })
      .then(r => setData(prev => ({ ...prev, 'cash-flow': r?.data ?? null })))
      .catch(() => {})
  }

  const activeInfo = ALL_REPORTS.find(r => r.id === activeReport)

  const renderActiveContent = () => {
    if (!activeReport) return null
    const d = data[activeReport]
    const isLoading = loading[activeReport]

    if (isLoading) return <Spinner />
    if (d == null) return <EmptyState text="Veri yüklenemedi veya bu dönem için kayıt yok." />

    if (activeReport === 'income-expense') {
      return (
        <IncomeExpenseReport
          d={d}
          trendData={trendData}
          trendLoading={trendLoading}
          catIncome={catIncome}
          catExpense={catExpense}
          catLoading={catLoading}
        />
      )
    }
    if (activeReport === 'category-breakdown') {
      return (
        <CategoryBreakdownReport
          d={d}
          groupId={groupId}
          periodDates={getPeriodDates(period.month, period.year, period.isFullYear)}
        />
      )
    }
    if (activeReport === 'cash-flow') {
      return (
        <CashFlowReport
          d={d}
          groupId={groupId}
          onRefetch={handleCashFlowRefetch}
          currentMonths={cashFlowMonths}
        />
      )
    }
    if (activeReport === 'loans') {
      return <LoansReport d={d} loans={loansList} loansLoading={loansListLoading} />
    }
    if (activeReport === 'credit-cards') {
      return <CreditCardsReport d={d} />
    }
    if (activeReport === 'assets') {
      return <AssetsReport d={d} />
    }
    if (activeReport === 'investment-performance') {
      return <InvestmentPerformanceReport d={d} />
    }
    return null
  }

  return (
    <div style={{ display: 'flex', gap: 'var(--space-6)', minHeight: '100%', alignItems: 'flex-start' }}>
      {/* ── Left Sidebar ─────────────────────────────────────────────────── */}
        <aside style={{
          width: 220,
          flexShrink: 0,
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--space-3)',
          position: 'sticky',
          top: 80,
          alignSelf: 'flex-start',
        }}>
        {NAV_GROUPS.map(group => (
          <div key={group.label} style={{ marginBottom: 'var(--space-4)' }}>
            <div style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: 'var(--text-tertiary)',
              padding: '0 var(--space-3)',
              marginBottom: 'var(--space-1)',
            }}>
              {group.label}
            </div>
            {group.items.map(item => {
              const isActive = activeReport === item.id
              return (
                <button
                  key={item.id}
                  onClick={() => selectReport(item.id)}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-3)',
                    padding: '8px var(--space-3)',
                    borderRadius: 'var(--radius-sm)',
                    border: 'none',
                    cursor: 'pointer',
                    fontSize: 'var(--font-size-sm)',
                    fontWeight: isActive ? 600 : 400,
                    color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                    background: isActive ? 'var(--accent-subtle)' : 'transparent',
                    transition: 'all 0.15s',
                    textAlign: 'left',
                  }}
                  onMouseEnter={e => {
                    if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'
                  }}
                  onMouseLeave={e => {
                    if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = 'transparent'
                  }}
                >
                  <span style={{ opacity: isActive ? 1 : 0.5, display: 'flex', flexShrink: 0 }}>
                    {ReportIcons[item.id]}
                  </span>
                  {item.title}
                </button>
              )
            })}
          </div>
        ))}
        </aside>

      {/* ── Right Content Area ────────────────────────────────────────────── */}
      <div style={{ flex: 1, minWidth: 0, padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>

        {/* Page header — sticky */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          gap: 'var(--space-4)',
          flexWrap: 'wrap',
          position: 'sticky',
          top: 'calc(-1 * var(--space-6))',
          marginLeft: 'calc(-1 * var(--space-6))',
          marginRight: 'calc(-1 * var(--space-6))',
          paddingLeft: 'var(--space-6)',
          paddingRight: 'var(--space-6)',
          paddingTop: 'var(--space-5)',
          paddingBottom: 'var(--space-5)',
          background: 'var(--bg-base)',
          borderBottom: '1px solid var(--border)',
          zIndex: 10,
          marginBottom: 0,
        }}>
          <div>
            {activeInfo ? (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 4 }}>
                  <span style={{ display: 'flex', color: REPORT_COLORS[activeReport!] }}>{ReportIcons[activeReport!]}</span>
                  <h1 style={{
                    fontSize: 'var(--font-size-xl)',
                    fontWeight: 700,
                    color: 'var(--text-primary)',
                    margin: 0,
                  }}>
                    {activeInfo.title}
                  </h1>
                </div>
                <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--text-tertiary)' }}>
                  {REPORT_DESCRIPTIONS[activeReport!]}
                </p>
              </>
            ) : (
              <>
                <h1 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 4px' }}>
                  Raporlar
                </h1>
                <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--text-tertiary)' }}>
                  Finansal özet ve analizler
                </p>
              </>
            )}
          </div>

          {/* Controls */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', alignItems: 'stretch', width: 320, flexShrink: 0 }}>
            <select
              className="form-input"
              style={{ width: '100%' }}
              value={groupId}
              onChange={e => setGroupId(e.target.value)}
            >
              <option value="">Tüm Gruplar</option>
              {groups.map((g: any) => (
                <option key={g.id} value={g.id}>{g.name}</option>
              ))}
            </select>
            <PeriodPicker value={period} onChange={setPeriod} />
          </div>
        </div>

        {/* Content */}
        <div style={{ flex: 1 }}>
          {!activeReport ? (
            <WelcomeGrid onSelect={selectReport} />
          ) : (
            renderActiveContent()
          )}
        </div>
      </div>
    </div>
  )
}
