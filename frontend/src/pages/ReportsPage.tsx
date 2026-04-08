import React, { useState, useEffect } from 'react'
import {
  BarChart, Bar, AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { reportsApi, groupsApi } from '../api/umay'

const CHART_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#38bdf8', '#a78bfa', '#fb7185']

const fmt = (v: number, currency?: string) =>
  (currency ? `${currency} ` : '') +
  Number(v).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

function periodDates(period: string): { period_start: string; period_end: string } {
  const today = new Date()
  const iso = (d: Date) => d.toISOString().split('T')[0]
  const end = iso(today)
  let start: Date
  if (period === 'week') {
    start = new Date(today); start.setDate(today.getDate() - 6)
  } else if (period === 'month') {
    start = new Date(today.getFullYear(), today.getMonth(), 1)
  } else if (period === 'quarter') {
    const qm = Math.floor(today.getMonth() / 3) * 3
    start = new Date(today.getFullYear(), qm, 1)
  } else {
    start = new Date(today.getFullYear(), 0, 1)
  }
  return { period_start: iso(start), period_end: end }
}

function ChartTooltip({ active, payload, label }: any) {
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
      {sub && <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

function EmptyState({ text }: { text: string }) {
  return (
    <div style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: 'var(--space-8) 0', fontSize: 'var(--font-size-sm)' }}>
      {text}
    </div>
  )
}

type ReportId = 'income-expense' | 'category-breakdown' | 'cash-flow' | 'loans' | 'credit-cards' | 'assets' | 'investment-performance'

const REPORTS: { id: ReportId; title: string; icon: string; desc: string; color: string }[] = [
  { id: 'income-expense',        title: 'Gelir / Gider',               icon: '📊', desc: 'Seçili dönemdeki gelir ve gider karşılaştırması',         color: '#6366f1' },
  { id: 'category-breakdown',    title: 'Kategori Dağılımı',           icon: '🏷️', desc: 'Harcamalar ve gelirlerin kategorilere göre dağılımı',     color: '#f59e0b' },
  { id: 'cash-flow',             title: 'Nakit Akışı Projeksiyonu',    icon: '💧', desc: 'Bekleyen planlı ödemelere göre nakit akış tahmini',       color: '#38bdf8' },
  { id: 'loans',                 title: 'Kredi Özeti',                 icon: '🏦', desc: 'Aktif krediler, toplam borç ve gecikmiş taksitler',        color: '#22c55e' },
  { id: 'credit-cards',          title: 'Kredi Kartı Özeti',           icon: '💳', desc: 'Kart limitleri, borçlar ve kullanım oranları',             color: '#ef4444' },
  { id: 'assets',                title: 'Varlık Raporu',               icon: '🏠', desc: 'Varlık portföyü, kazanç/kayıp analizi',                   color: '#a78bfa' },
  { id: 'investment-performance', title: 'Yatırım Performansı',        icon: '📈', desc: 'Portföy bazlı gerçekleşen kazanç, temettü ve faiz geliri', color: '#fb7185' },
]

const ASSET_TYPE_LABELS: Record<string, string> = {
  REAL_ESTATE: 'Gayrimenkul', VEHICLE: 'Araç', FINANCIAL: 'Finansal',
  SECURITY: 'Menkul Kıymet', CRYPTO: 'Kripto', COLLECTIBLE: 'Koleksiyon', OTHER: 'Diğer',
}

export function ReportsPage() {
  const [groups, setGroups] = useState<any[]>([])
  const [groupId, setGroupId] = useState<string>('')
  const [period, setPeriod] = useState('month')
  const [openReport, setOpenReport] = useState<ReportId | null>(null)
  const [data, setData] = useState<Partial<Record<ReportId, any>>>({})
  const [loading, setLoading] = useState<Partial<Record<ReportId, boolean>>>({})

  useEffect(() => {
    groupsApi.list().then(r => setGroups(r.data || [])).catch(() => {})
  }, [])

  const doFetch = async (id: ReportId, currentPeriod: string, currentGroupId: string) => {
    setLoading(prev => ({ ...prev, [id]: true }))
    try {
      const dates = periodDates(currentPeriod)
      const gp = currentGroupId ? { group_id: currentGroupId } : {}
      let res: any
      if (id === 'income-expense')
        res = await reportsApi.incomeExpense({ ...dates, ...gp })
      else if (id === 'category-breakdown')
        res = await reportsApi.categoryBreakdown({ ...dates, ...gp, transaction_type: 'EXPENSE' })
      else if (id === 'cash-flow')
        res = await reportsApi.cashFlow({ months_ahead: 3, ...gp })
      else if (id === 'loans')
        res = await reportsApi.loans(gp)
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

  // When period or group changes: clear cache and re-fetch the open report
  useEffect(() => {
    setData({})
    if (openReport) {
      doFetch(openReport, period, groupId)
    }
  }, [period, groupId])

  const fetchReport = (id: ReportId) => {
    if (openReport === id) { setOpenReport(null); return }
    setOpenReport(id)
    doFetch(id, period, groupId)
  }

  const renderContent = (id: ReportId) => {
    const d = data[id]
    if (d == null) return <EmptyState text="Veri yüklenemedi veya bu dönem için kayıt yok." />

    // ── Gelir / Gider ──────────────────────────────────────────────────────
    if (id === 'income-expense') {
      const income = d.income?.total ?? 0
      const expense = d.expense?.total ?? 0
      const net = d.net ?? (income - expense)
      const chartData = [
        { name: 'Gelir', value: income, fill: '#22c55e' },
        { name: 'Gider', value: expense, fill: '#ef4444' },
      ]
      return (
        <div style={{ marginTop: 'var(--space-4)' }}>
          <div style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-5)', flexWrap: 'wrap' }}>
            <StatCard label="Toplam Gelir"  value={fmt(income)}  color="var(--income)"  sub={`${d.income?.count ?? 0} işlem`} />
            <StatCard label="Toplam Gider"  value={fmt(expense)} color="var(--expense)" sub={`${d.expense?.count ?? 0} işlem`} />
            <StatCard label="Net Durum"     value={fmt(net)}     color={net >= 0 ? 'var(--income)' : 'var(--expense)'} />
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: 'var(--text-tertiary)', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="value" name="Tutar" radius={[6, 6, 0, 0]}>
                {chartData.map((c, i) => <Cell key={i} fill={c.fill} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )
    }

    // ── Kategori Dağılımı ─────────────────────────────────────────────────
    if (id === 'category-breakdown') {
      const rows: any[] = Array.isArray(d) ? d : []
      if (rows.length === 0) return <EmptyState text="Bu dönem için kategori verisi bulunamadı." />
      const pieData = rows.slice(0, 7).map((c: any) => ({
        name: c.category_name || '—',
        value: Math.abs(c.total || 0),
      }))
      return (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-5)', marginTop: 'var(--space-4)' }}>
          <ResponsiveContainer width="100%" height={230}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={3} dataKey="value">
                {pieData.map((_: any, i: number) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
              </Pie>
              <Tooltip formatter={(v: any) => fmt(Number(v))} />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', justifyContent: 'center' }}>
            {rows.slice(0, 7).map((c: any, i: number) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '5px 0', borderBottom: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: CHART_COLORS[i % CHART_COLORS.length], flexShrink: 0 }} />
                  <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500 }}>{c.category_name || '—'}</span>
                </div>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--expense)', fontWeight: 600, marginLeft: 8 }}>
                  {fmt(Math.abs(c.total || 0))}
                </span>
              </div>
            ))}
          </div>
        </div>
      )
    }

    // ── Nakit Akışı ───────────────────────────────────────────────────────
    if (id === 'cash-flow') {
      const rows: any[] = Array.isArray(d) ? d : []
      if (rows.length === 0) return <EmptyState text="Önümüzdeki dönem için bekleyen planlı ödeme bulunamadı." />
      const totalIn = rows.filter(r => r.type === 'INCOME').reduce((s: number, r: any) => s + (r.amount || 0), 0)
      const totalOut = rows.filter(r => r.type !== 'INCOME').reduce((s: number, r: any) => s + (r.amount || 0), 0)
      return (
        <div style={{ marginTop: 'var(--space-4)' }}>
          <div style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-5)', flexWrap: 'wrap' }}>
            <StatCard label="Beklenen Giriş" value={fmt(totalIn)}  color="var(--income)" />
            <StatCard label="Beklenen Çıkış" value={fmt(totalOut)} color="var(--expense)" />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {rows.map((r: any, i: number) => (
              <div key={i} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '8px 12px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)',
                borderLeft: `3px solid ${r.type === 'INCOME' ? 'var(--income)' : 'var(--expense)'}`,
              }}>
                <div>
                  <div style={{ fontWeight: 500, fontSize: 'var(--font-size-sm)' }}>{r.title}</div>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>{r.date}</div>
                </div>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 'var(--font-size-sm)',
                  color: r.type === 'INCOME' ? 'var(--income)' : 'var(--expense)',
                }}>
                  {r.type === 'INCOME' ? '+' : '-'}{fmt(r.amount || 0, r.currency)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )
    }

    // ── Kredi Özeti ───────────────────────────────────────────────────────
    if (id === 'loans') {
      const principalEntries = Object.entries(d.total_principal || {})
      const remainingEntries = Object.entries(d.total_remaining || {})
      return (
        <div style={{ marginTop: 'var(--space-4)' }}>
          <div style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-5)', flexWrap: 'wrap' }}>
            <StatCard label="Aktif Kredi"        value={`${d.active_loan_count ?? 0} adet`} />
            <StatCard label="Gecikmiş Taksit"    value={`${d.overdue_installments ?? 0} adet`} color={d.overdue_installments ? 'var(--expense)' : undefined} />
            {principalEntries.map(([cur, val]) => (
              <StatCard key={`p-${cur}`} label={`Ana Para (${cur})`} value={fmt(val as number, cur)} />
            ))}
            {remainingEntries.map(([cur, val]) => (
              <StatCard key={`r-${cur}`} label={`Kalan Borç (${cur})`} value={fmt(val as number, cur)} color="var(--expense)" />
            ))}
          </div>
          {principalEntries.length === 0 && <EmptyState text="Aktif kredi bulunamadı." />}
        </div>
      )
    }

    // ── Kredi Kartı Özeti ─────────────────────────────────────────────────
    if (id === 'credit-cards') {
      const limitEntries = Object.entries(d.total_limit || {})
      const debtEntries  = Object.entries(d.total_debt || {})
      const utilEntries  = Object.entries(d.utilization || {})
      return (
        <div style={{ marginTop: 'var(--space-4)' }}>
          <div style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-5)', flexWrap: 'wrap' }}>
            <StatCard label="Kart Sayısı"         value={`${d.card_count ?? 0} adet`} />
            <StatCard label="Gecikmiş Ekstre"     value={`${d.overdue_statements ?? 0} adet`} color={d.overdue_statements ? 'var(--expense)' : undefined} />
            {limitEntries.map(([cur, val]) => (
              <StatCard key={`l-${cur}`} label={`Toplam Limit (${cur})`} value={fmt(val as number, cur)} />
            ))}
            {debtEntries.map(([cur, val]) => (
              <StatCard key={`d-${cur}`} label={`Toplam Borç (${cur})`} value={fmt(val as number, cur)} color="var(--expense)" />
            ))}
          </div>
          {utilEntries.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Kullanım Oranı</div>
              {utilEntries.map(([cur, pct]) => {
                const p = pct as number
                return (
                  <div key={cur} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                    <span style={{ minWidth: 40, fontSize: 'var(--font-size-sm)', fontWeight: 500 }}>{cur}</span>
                    <div style={{ flex: 1, height: 8, background: 'var(--bg-subtle)', borderRadius: 4, overflow: 'hidden' }}>
                      <div style={{
                        height: '100%', width: `${Math.min(p, 100)}%`, borderRadius: 4,
                        background: p > 70 ? 'var(--danger)' : p > 40 ? 'var(--warning)' : 'var(--income)',
                        transition: 'width 0.4s ease',
                      }} />
                    </div>
                    <span style={{ minWidth: 44, fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', fontWeight: 600 }}>{p.toFixed(1)}%</span>
                  </div>
                )
              })}
            </div>
          )}
          {limitEntries.length === 0 && <EmptyState text="Kredi kartı bulunamadı." />}
        </div>
      )
    }

    // ── Varlık Raporu ─────────────────────────────────────────────────────
    if (id === 'assets') {
      const byType: Record<string, any> = d.by_type || {}
      const pieData = Object.entries(byType).map(([k, v]: [string, any]) => ({
        name: ASSET_TYPE_LABELS[k] || k,
        value: v.total_current_value || 0,
      })).filter(x => x.value > 0)
      const unreal = d.unrealized_gain_loss ?? 0
      const real   = d.realized_gain_loss ?? 0
      return (
        <div style={{ marginTop: 'var(--space-4)' }}>
          <div style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-5)', flexWrap: 'wrap' }}>
            <StatCard label="Toplam Varlık"    value={`${d.asset_count ?? 0} adet`} />
            <StatCard label="Satılan Varlık"   value={`${d.sold_count ?? 0} adet`} />
            <StatCard label="Alış Değeri"      value={fmt(d.total_purchase_value ?? 0)} />
            <StatCard label="Güncel Değer"     value={fmt(d.total_current_value ?? 0)} />
            <StatCard label="Gerçekleşmemiş K/Z" value={fmt(unreal)} color={unreal >= 0 ? 'var(--income)' : 'var(--expense)'} />
            <StatCard label="Gerçekleşen K/Z"    value={fmt(real)}   color={real >= 0 ? 'var(--income)' : 'var(--expense)'} />
          </div>
          {pieData.length > 0 && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-5)' }}>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={85} paddingAngle={3} dataKey="value">
                    {pieData.map((_: any, i: number) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v: any) => fmt(Number(v))} />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', justifyContent: 'center' }}>
                {pieData.map((item, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid var(--border)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                      <div style={{ width: 10, height: 10, borderRadius: '50%', background: CHART_COLORS[i % CHART_COLORS.length] }} />
                      <span style={{ fontSize: 'var(--font-size-sm)' }}>{item.name}</span>
                    </div>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', fontWeight: 600 }}>{fmt(item.value)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {d.asset_count === 0 && <EmptyState text="Kayıtlı varlık bulunamadı." />}
        </div>
      )
    }

    // ── Yatırım Performansı ───────────────────────────────────────────────
    if (id === 'investment-performance') {
      const portfolios: any[] = d.portfolios || []
      const grandReal = d.grand_realized_pl ?? 0
      const grandInc  = d.grand_income ?? 0
      return (
        <div style={{ marginTop: 'var(--space-4)' }}>
          <div style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-5)', flexWrap: 'wrap' }}>
            <StatCard label="Portföy Sayısı"      value={`${d.portfolio_count ?? 0} adet`} />
            <StatCard label="Toplam Gerçekleşen K/Z" value={fmt(grandReal)} color={grandReal >= 0 ? 'var(--income)' : 'var(--expense)'} />
            <StatCard label="Toplam Temettü/Faiz"    value={fmt(grandInc)}  color="var(--income)" />
          </div>
          {portfolios.length === 0 && <EmptyState text="Portföy bulunamadı." />}
          {portfolios.map((p: any) => {
            const openPos = Object.entries(p.open_positions || {})
            return (
              <div key={p.portfolio_id} style={{ marginBottom: 'var(--space-4)', padding: 'var(--space-3)', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontWeight: 600, marginBottom: 'var(--space-3)', color: 'var(--text-primary)' }}>
                  {p.portfolio_name} <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', fontWeight: 400 }}>({p.currency})</span>
                </div>
                <div style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap', marginBottom: openPos.length ? 'var(--space-3)' : 0 }}>
                  <StatCard label="Yatırılan"       value={fmt(p.total_invested, p.currency)} />
                  <StatCard label="Satılan"          value={fmt(p.total_sold, p.currency)} />
                  <StatCard label="Gerçekleşen K/Z"  value={fmt(p.realized_pl, p.currency)} color={p.realized_pl >= 0 ? 'var(--income)' : 'var(--expense)'} />
                  <StatCard label="Temettü"          value={fmt(p.dividend_income, p.currency)} color="var(--income)" />
                  <StatCard label="Faiz"             value={fmt(p.interest_income, p.currency)} color="var(--income)" />
                </div>
                {openPos.length > 0 && (
                  <div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', fontWeight: 600, marginBottom: 'var(--space-2)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Açık Pozisyonlar</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      {openPos.map(([sym, pos]: [string, any]) => (
                        <div key={sym} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-sm)', padding: '4px 0', borderBottom: '1px solid var(--border)' }}>
                          <span style={{ fontWeight: 500 }}>{sym}</span>
                          <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                            {pos.quantity} adet — maliyet {fmt(pos.cost_basis, p.currency)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )
    }

    return null
  }

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Raporlar</h1>
          <p className="page-subtitle">Finansal özet ve analizler</p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <select
            className="form-input"
            style={{ width: 'auto', minWidth: 140 }}
            value={groupId}
            onChange={e => setGroupId(e.target.value)}
          >
            <option value="">Tüm Gruplar</option>
            {groups.map((g: any) => (
              <option key={g.id} value={g.id}>{g.name}</option>
            ))}
          </select>
          <select
            className="form-input"
            style={{ width: 'auto', minWidth: 140 }}
            value={period}
            onChange={e => setPeriod(e.target.value)}
          >
            <option value="week">Bu Hafta</option>
            <option value="month">Bu Ay</option>
            <option value="quarter">Bu Çeyrek</option>
            <option value="year">Bu Yıl</option>
          </select>
        </div>
      </div>

      {/* Report Accordion Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        {REPORTS.map(report => (
          <div key={report.id} className="card" style={{ overflow: 'hidden' }}>
            <div
              style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', cursor: 'pointer' }}
              onClick={() => fetchReport(report.id)}
            >
              <div style={{
                width: 46, height: 46, borderRadius: 'var(--radius-md)', flexShrink: 0,
                background: `${report.color}18`, display: 'flex', alignItems: 'center',
                justifyContent: 'center', fontSize: 20,
              }}>
                {report.icon}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 'var(--font-size-md)', color: report.color }}>
                  {report.title}
                </div>
                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-tertiary)' }}>{report.desc}</div>
              </div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', flexShrink: 0 }}>
                {openReport === report.id ? '▲ Kapat' : '▶ Görüntüle'}
              </div>
            </div>

            {openReport === report.id && (
              <div style={{ borderTop: '1px solid var(--border)', marginTop: 'var(--space-4)', paddingTop: 'var(--space-2)' }}>
                {loading[report.id] ? (
                  <div className="loading-state" style={{ padding: 'var(--space-8) 0' }}>
                    <div className="spinner" />
                  </div>
                ) : (
                  renderContent(report.id) || <EmptyState text="Bu rapor için veri bulunamadı." />
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
