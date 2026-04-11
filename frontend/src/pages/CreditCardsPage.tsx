import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { creditCardsApi, accountsApi, groupsApi, categoriesApi, ccPurchaseTemplatesApi } from '../api/umay'
import {
  CreditCardIcon, ReportsIcon, LockIcon, CategoriesIcon,
  EditIcon, CloseIcon, EyeIcon, EyeOffIcon, PaymentIcon, DeleteIcon,
} from '../components/Icons'

function Modal({ open, onClose, children }: { open: boolean; onClose: () => void; children: React.ReactNode }) {
  if (!open) return null
  return (
    <div className="modal-backdrop" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 640 }}>{children}</div>
    </div>
  )
}

const CARD_GRADIENTS = [
  'linear-gradient(135deg, #6366f1, #7c3aed)',
  'linear-gradient(135deg, #0ea5e9, #0284c7)',
  'linear-gradient(135deg, #10b981, #059669)',
  'linear-gradient(135deg, #f59e0b, #d97706)',
  'linear-gradient(135deg, #ef4444, #dc2626)',
]

const CARD_ACCENT_COLORS = ['#6366f1', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444']

const fmt = (v: number) => Number(v).toLocaleString('tr-TR', { minimumFractionDigits: 2 })

export function CreditCardsPage() {
  const { t } = useTranslation()
  const [cards, setCards] = useState<any[]>([])
  const [accounts, setAccounts] = useState<any[]>([])
  const [groups, setGroups] = useState<any[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCard, setSelectedCard] = useState<any>(null)
  const [activeTab, setActiveTab] = useState<'purchases' | 'statements' | 'card_info'>('purchases')

  // Modals
  const [showCardModal, setShowCardModal] = useState(false)
  const [showPurchaseModal, setShowPurchaseModal] = useState(false)
  const [showStatementModal, setShowStatementModal] = useState(false)
  const [showPayModal, setShowPayModal] = useState(false)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [showCancelModal, setShowCancelModal] = useState(false)
  const [showStatementView, setShowStatementView] = useState(false)

  // Data
  const [purchases, setPurchases] = useState<any[]>([])
  const [statements, setStatements] = useState<any[]>([])
  const [limits, setLimits] = useState<any>(null)
  const [statementDetail, setStatementDetail] = useState<any>(null)

  // Forms
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [cardForm, setCardForm] = useState({
    card_name: '', bank_name: '', credit_limit: '', currency: 'TRY',
    statement_day: '1', due_day: '15', group_id: '', notes: '',
  })
  const [purchaseForm, setPurchaseForm] = useState({
    description: '', total_amount: '', installment_count: '1',
    purchase_date: new Date().toISOString().slice(0, 10),
    category_id: '', currency: 'TRY',
  })
  const [stmtForm, setStmtForm] = useState({
    period_start: '', period_end: '', real_available_limit: '',
  })
  const [stmtPreview, setStmtPreview] = useState<any>(null)
  const [stmtPreviewLoading, setStmtPreviewLoading] = useState(false)
  const [payForm, setPayForm] = useState({ source_account_id: '', amount: '' })
  const [payTarget, setPayTarget] = useState<any>(null)
  const [cancelTarget, setCancelTarget] = useState<any>(null)
  const [cancelScenario, setCancelScenario] = useState('A')

  // Detail lines
  const [detailTarget, setDetailTarget] = useState<any>(null)
  const [detailLines, setDetailLines] = useState<{ category_id: string; description: string; amount: string }[]>([])

  // Card info & sensitive data
  const [showEditCardModal, setShowEditCardModal] = useState(false)
  const [editCardForm, setEditCardForm] = useState({ credit_limit: '', statement_day: '', due_day: '', expiry_month: '', expiry_year: '', last_four_digits: '', notes: '' })
  const [showSensitiveSaveModal, setShowSensitiveSaveModal] = useState(false)
  const [showSensitiveRevealModal, setShowSensitiveRevealModal] = useState(false)
  const [sensitivePassword, setSensitivePassword] = useState('')
  const [sensitiveCardNumber, setSensitiveCardNumber] = useState('')
  const [sensitiveCvv, setSensitiveCvv] = useState('')
  const [sensitiveData, setSensitiveData] = useState<any>(null)
  const [sensitiveError, setSensitiveError] = useState('')
  const [sensitiveLoading, setSensitiveLoading] = useState(false)
  const [showCardNumber, setShowCardNumber] = useState(false)
  const [showCvv, setShowCvv] = useState(false)

  // Purchase templates
  const [purchaseTemplates, setPurchaseTemplates] = useState<any[]>([])
  const [showPurchaseTemplates, setShowPurchaseTemplates] = useState(false)
  const [saveAsTemplate, setSaveAsTemplate] = useState(false)
  const [templateName, setTemplateName] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const [c, a, g, cat, tmpl] = await Promise.all([
        creditCardsApi.list({ skip: 0, limit: 100 }),
        accountsApi.list({ skip: 0, limit: 100 }),
        groupsApi.list({ skip: 0, limit: 100 }),
        categoriesApi.list({ skip: 0, limit: 100 }),
        ccPurchaseTemplatesApi.list(),
      ])
      setCards(c.data)
      setAccounts(a.data)
      setGroups(g.data)
      setCategories(cat.data)
      setPurchaseTemplates(tmpl.data)
      if (c.data.length > 0 && !selectedCard) setSelectedCard(c.data[0])
    } catch { }
    setLoading(false)
  }

  const loadCardData = async (card: any) => {
    if (!card) return
    try {
      const [p, s, l] = await Promise.all([
        creditCardsApi.listPurchases(card.id, { skip: 0, limit: 100 }),
        creditCardsApi.listStatements(card.id, { skip: 0, limit: 100 }),
        creditCardsApi.limits(card.id),
      ])
      setPurchases(p.data)
      setStatements(s.data)
      setLimits(l.data)
    } catch { }
  }

  useEffect(() => { load() }, [])
  useEffect(() => { if (selectedCard) loadCardData(selectedCard) }, [selectedCard])

  useEffect(() => {
    if (showStatementModal && selectedCard && stmtForm.period_end) {
      creditCardsApi.limits(selectedCard.id, stmtForm.period_end).then(r => setLimits(r.data))
    }
  }, [showStatementModal, stmtForm.period_end, selectedCard])

  useEffect(() => {
    const { period_start, period_end, real_available_limit } = stmtForm
    if (!showStatementModal || !selectedCard || !period_start || !period_end || !real_available_limit) {
      setStmtPreview(null)
      return
    }
    // Debounce API call to avoid flickering on every keystroke
    const timeoutId = setTimeout(async () => {
      setStmtPreviewLoading(true)
      try {
        const res = await creditCardsApi.previewStatement(selectedCard.id, {
          period_start,
          period_end,
          real_available_limit: parseFloat(real_available_limit),
        })
        setStmtPreview(res.data)
      } catch {
        setStmtPreview(null)
      } finally {
        setStmtPreviewLoading(false)
      }
    }, 500)
    return () => clearTimeout(timeoutId)
  }, [showStatementModal, stmtForm.period_start, stmtForm.period_end, stmtForm.real_available_limit, selectedCard])

  const paymentAccounts = accounts.filter(a =>
    (a.account_type === 'BANK' || a.account_type === 'CASH') &&
    (!selectedCard || a.currency === selectedCard.currency)
  )

  // ── Card Create ──────────────────────────────────────
  const handleCreateCard = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true); setError('')
    try {
      await creditCardsApi.create({
        ...cardForm,
        credit_limit: parseFloat(cardForm.credit_limit),
        statement_day: parseInt(cardForm.statement_day),
        due_day: parseInt(cardForm.due_day),
        group_id: cardForm.group_id || undefined,
      })
      setShowCardModal(false)
      setCardForm({ card_name: '', bank_name: '', credit_limit: '', currency: 'TRY', statement_day: '1', due_day: '15', group_id: '', notes: '' })
      await load()
    } catch (err: any) { setError(err?.response?.data?.detail?.message || err?.response?.data?.detail || 'Hata') }
    setSaving(false)
  }

  // ── Purchase Create ──────────────────────────────────
  const handleCreatePurchase = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedCard) return
    if (!purchaseForm.category_id) { setError('Kategori seçimi zorunludur'); return }
    setSaving(true); setError('')
    try {
      await creditCardsApi.createPurchase(selectedCard.id, {
        description: purchaseForm.description,
        total_amount: parseFloat(purchaseForm.total_amount),
        installment_count: parseInt(purchaseForm.installment_count),
        purchase_date: purchaseForm.purchase_date,
        category_id: purchaseForm.category_id,
        currency: purchaseForm.currency,
      })
      if (saveAsTemplate && templateName.trim()) {
        await ccPurchaseTemplatesApi.create({
          name: templateName.trim(),
          description: purchaseForm.description,
          installment_count: parseInt(purchaseForm.installment_count),
          currency: purchaseForm.currency,
          category_id: purchaseForm.category_id || null,
        })
        const tmpl = await ccPurchaseTemplatesApi.list()
        setPurchaseTemplates(tmpl.data)
      }
      setShowPurchaseModal(false)
      setSaveAsTemplate(false); setTemplateName('')
      setPurchaseForm({ description: '', total_amount: '', installment_count: '1', purchase_date: new Date().toISOString().slice(0, 10), category_id: '', currency: 'TRY' })
      await load(); await loadCardData(selectedCard)
    } catch (err: any) { setError(err?.response?.data?.detail?.message || err?.response?.data?.detail || 'Hata') }
    setSaving(false)
  }

  // ── Statement Generate ───────────────────────────────
  const handleGenerateStatement = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedCard) return
    setSaving(true); setError('')
    try {
      await creditCardsApi.generateStatement(selectedCard.id, {
        period_start: stmtForm.period_start,
        period_end: stmtForm.period_end,
        real_available_limit: parseFloat(stmtForm.real_available_limit),
      })
      setShowStatementModal(false)
      setStmtForm({ period_start: '', period_end: '', real_available_limit: '' })
      setStmtPreview(null)
      await loadCardData(selectedCard)
    } catch (err: any) { setError(err?.response?.data?.detail?.message || err?.response?.data?.detail || 'Hata') }
    setSaving(false)
  }

  // ── Detail New Spending ──────────────────────────────
  const handleDetailSubmit = async () => {
    if (!selectedCard || !detailTarget) return
    for (const l of detailLines) {
      if (!l.category_id) { setError('Her satır için kategori seçimi zorunludur.'); return }
      if (!l.description.trim()) { setError('Her satır için açıklama zorunludur.'); return }
      if (!l.amount || parseFloat(l.amount) <= 0) { setError('Her satır için geçerli bir tutar giriniz.'); return }
    }
    setSaving(true); setError('')
    try {
      await creditCardsApi.detailStatement(selectedCard.id, detailTarget.id, {
        lines: detailLines.map(l => ({
          category_id: l.category_id,
          description: l.description,
          amount: parseFloat(l.amount),
        })),
      })
      setShowDetailModal(false)
      await loadCardData(selectedCard)
    } catch (err: any) {
      const d = err?.response?.data;
      const msg = d?.error?.message || d?.detail?.message || (typeof d?.detail === 'string' ? d.detail : '') || 'Bir hata oluştu';
      setError(msg)
    }
    setSaving(false)
  }

  // ── Delete Statement ────────────────────────────────
  const handleDeleteStatement = async (stmt: any) => {
    if (!selectedCard || !confirm('Bu ekstreyi silmek istediğinize emin misiniz?')) return
    try {
      await creditCardsApi.deleteStatement(selectedCard.id, stmt.id)
      await loadCardData(selectedCard)
    } catch (err: any) { alert(err?.response?.data?.error?.message || err?.response?.data?.detail?.message || 'Hata') }
  }

  // ── Finalize Statement ───────────────────────────────
  const handleFinalize = async (stmt: any) => {
    if (!selectedCard || !confirm('Bu ekstreyi kesinleştirmek istiyor musunuz?')) return
    try {
      await creditCardsApi.finalizeStatement(selectedCard.id, stmt.id)
      await loadCardData(selectedCard)
    } catch (err: any) { alert(err?.response?.data?.detail?.message || 'Hata') }
  }

  // ── Pay Statement ────────────────────────────────────
  const handlePaySubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedCard || !payTarget) return
    setSaving(true); setError('')
    try {
      await creditCardsApi.payStatement(selectedCard.id, payTarget.id, {
        source_account_id: payForm.source_account_id,
        amount: parseFloat(payForm.amount),
      })
      setShowPayModal(false)
      await load(); await loadCardData(selectedCard)
    } catch (err: any) { setError(err?.response?.data?.detail?.message || err?.response?.data?.detail || 'Hata') }
    setSaving(false)
  }

  // ── Cancel Purchase ──────────────────────────────────
  const handleCancelPurchase = async () => {
    if (!selectedCard || !cancelTarget) return
    setSaving(true); setError('')
    try {
      await creditCardsApi.cancelPurchase(selectedCard.id, cancelTarget.id, { scenario: cancelScenario })
      setShowCancelModal(false)
      await load(); await loadCardData(selectedCard)
    } catch (err: any) { setError(err?.response?.data?.detail?.message || err?.response?.data?.detail || 'Hata') }
    setSaving(false)
  }

  // ── Edit Card Info ───────────────────────────────────
  const openEditCard = () => {
    if (!selectedCard) return
    setEditCardForm({
      credit_limit: String(selectedCard.credit_limit || ''),
      statement_day: String(selectedCard.statement_day || ''),
      due_day: String(selectedCard.due_day || ''),
      expiry_month: String(selectedCard.expiry_month || ''),
      expiry_year: String(selectedCard.expiry_year || ''),
      last_four_digits: selectedCard.last_four_digits || '',
      notes: selectedCard.notes || '',
    })
    setError(''); setShowEditCardModal(true)
  }

  const handleEditCard = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError('')
    try {
      const payload: any = {}
      if (editCardForm.credit_limit) payload.credit_limit = parseFloat(editCardForm.credit_limit)
      if (editCardForm.statement_day) payload.statement_day = parseInt(editCardForm.statement_day)
      if (editCardForm.due_day) payload.due_day = parseInt(editCardForm.due_day)
      if (editCardForm.expiry_month) payload.expiry_month = parseInt(editCardForm.expiry_month)
      if (editCardForm.expiry_year) payload.expiry_year = parseInt(editCardForm.expiry_year)
      if (editCardForm.last_four_digits) payload.last_four_digits = editCardForm.last_four_digits
      if (editCardForm.notes !== undefined) payload.notes = editCardForm.notes
      await creditCardsApi.update(selectedCard.id, payload)
      setShowEditCardModal(false)
      await load()
    } catch (err: any) { setError(err?.response?.data?.detail?.message || err?.response?.data?.detail || 'Hata') }
    setSaving(false)
  }

  // ── Sensitive Data Save ──────────────────────────────
  const handleSensitiveSave = async (e: React.FormEvent) => {
    e.preventDefault(); setSensitiveLoading(true); setSensitiveError('')
    try {
      const body: any = { password: sensitivePassword }
      if (sensitiveCardNumber.trim()) body.card_number = sensitiveCardNumber.replace(/\s/g, '')
      if (sensitiveCvv.trim()) body.cvv = sensitiveCvv
      await creditCardsApi.saveSensitive(selectedCard.id, body)
      setShowSensitiveSaveModal(false)
      setSensitivePassword(''); setSensitiveCardNumber(''); setSensitiveCvv('')
      await load()
    } catch (err: any) {
      setSensitiveError(err?.response?.data?.error?.message || err?.response?.data?.detail || 'Şifre yanlış veya hata oluştu')
    }
    setSensitiveLoading(false)
  }

  // ── Sensitive Data Reveal ────────────────────────────
  const handleSensitiveReveal = async (e: React.FormEvent) => {
    e.preventDefault(); setSensitiveLoading(true); setSensitiveError('')
    try {
      const res = await creditCardsApi.revealSensitive(selectedCard.id, { password: sensitivePassword })
      setSensitiveData(res.data)
      setShowSensitiveRevealModal(false)
      setSensitivePassword('')
      setShowCardNumber(false); setShowCvv(false)
    } catch (err: any) {
      setSensitiveError(err?.response?.data?.error?.message || err?.response?.data?.detail || 'Şifre yanlış')
    }
    setSensitiveLoading(false)
  }

  // ── View Statement Detail ────────────────────────────
  const handleViewStatement = async (stmt: any) => {
    if (!selectedCard) return
    try {
      const res = await creditCardsApi.getStatement(selectedCard.id, stmt.id)
      setStatementDetail(res.data)
      setShowStatementView(true)
    } catch { }
  }

  if (loading) return <div className="loading-state"><div className="spinner" /></div>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div className="page-header" style={{
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
        zIndex: 20,
      }}>
        <div>
          <h1 className="page-title">{t('creditCards.title')}</h1>
          <p className="page-subtitle">{cards.length} kart</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCardModal(true)}>+ Yeni Kart</button>
      </div>

      {/* Body */}
      {cards.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><CreditCardIcon size={48} /></div>
          <div className="empty-state-title">Henüz kredi kartı eklenmemiş</div>
          <button className="btn btn-primary" onClick={() => setShowCardModal(true)}>+ Kart Ekle</button>
        </div>
      ) : (
        <div style={{ display: 'flex', gap: 'var(--space-6)', flex: 1, minWidth: 0, paddingTop: 'var(--space-5)' }}>

          {/* ── LEFT: Card list sidebar ─────────────── */}
          <aside style={{
            width: 220, flexShrink: 0,
            display: 'flex', flexDirection: 'column', gap: 'var(--space-2)',
            position: 'sticky', top: 80, alignSelf: 'flex-start',
          }}>
            <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 'var(--space-1)' }}>
              Kartlarım
            </div>
            {cards.map((card: any, idx: number) => {
              const isSelected = selectedCard?.id === card.id
              const accent = CARD_ACCENT_COLORS[idx % CARD_ACCENT_COLORS.length]
              const debt = Number(card.current_debt)
              const group = groups.find(g => g.id === card.group_id)
              return (
                <div key={card.id} onClick={() => setSelectedCard(card)} style={{
                  position: 'relative',
                  borderRadius: 'var(--radius-md)',
                  border: `1px solid ${isSelected ? accent + '66' : 'var(--border)'}`,
                  borderLeft: `3px solid ${accent}`,
                  background: isSelected ? accent + '11' : 'transparent',
                  padding: 'var(--space-3) var(--space-3)',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}>
                  {group && (
                    <span className="badge badge-neutral" style={{ position: 'absolute', top: 6, right: 6, fontSize: 9, padding: '2px 4px' }}>
                      {group.name}
                    </span>
                  )}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                    <span style={{ color: accent, display: 'flex' }}><CreditCardIcon size={13} /></span>
                    <span style={{ fontWeight: isSelected ? 700 : 500, fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)' }}>{card.card_name}</span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 4 }}>{card.bank_name}</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                    <span style={{ color: 'var(--text-tertiary)' }}>Limit: <span style={{ fontFamily: 'var(--font-mono)' }}>{fmt(Number(card.credit_limit))}</span></span>
                    {debt > 0 && <span style={{ color: 'var(--expense)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{fmt(debt)}</span>}
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginTop: 3 }}>
                    Kesim {card.statement_day} · Son {card.due_day}
                  </div>
                </div>
              )
            })}
          </aside>

          {/* ── RIGHT: Card detail ──────────────────── */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {!selectedCard ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200, color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)' }}>
                Soldan bir kart seçin
              </div>
            ) : (
              <>
                {/* Selected card mini header */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: CARD_ACCENT_COLORS[cards.findIndex((c: any) => c.id === selectedCard.id) % CARD_ACCENT_COLORS.length], flexShrink: 0 }} />
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 'var(--font-size-md)' }}>{selectedCard.card_name}</div>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>{selectedCard.bank_name} · {selectedCard.currency}</div>
                    </div>
                  </div>
                  <button className="btn btn-ghost btn-sm" onClick={openEditCard}>
                    <EditIcon size={13} /> Düzenle
                  </button>
                </div>

                {/* Limits KPI */}
                {limits && (
                  <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 'var(--space-5)' }}>
                    <div className="stat-card"><div className="stat-card-label">Toplam Limit</div><div className="stat-card-value">{selectedCard.currency} {fmt(Number(limits.total_limit))}</div></div>
                    <div className="stat-card"><div className="stat-card-label">Taksitlerden Bağlı</div><div className="stat-card-value" style={{ color: 'var(--warning)' }}>{selectedCard.currency} {fmt(Number(limits.committed_limit))}</div></div>
                    <div className="stat-card"><div className="stat-card-label">Teorik Boş Limit</div><div className="stat-card-value" style={{ color: 'var(--income)' }}>{selectedCard.currency} {fmt(Number(limits.theoretical_available))}</div></div>
                    <div className="stat-card"><div className="stat-card-label">Toplam Borç</div><div className="stat-card-value" style={{ color: 'var(--expense)' }}>{selectedCard.currency} {fmt(Number(limits.current_debt))}</div></div>
                  </div>
                )}

                {/* Sub-tabs */}
                <div style={{ display: 'flex', gap: 'var(--space-1)', borderBottom: '1px solid var(--border)', marginBottom: 'var(--space-4)' }}>
                  {[
                    { key: 'purchases' as const, label: 'Alışverişler' },
                    { key: 'statements' as const, label: 'Ekstre Oluştur' },
                    { key: 'card_info' as const, label: 'Kart Bilgileri' },
                  ].map(tab => (
                    <button key={tab.key}
                      className={`btn btn-sm ${activeTab === tab.key ? 'btn-primary' : 'btn-ghost'}`}
                      onClick={() => { setActiveTab(tab.key); setSensitiveData(null) }}
                    >{tab.label}</button>
                  ))}
                </div>

          {/* ── Tab: Purchases ──────────────────────────── */}
          {activeTab === 'purchases' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
                <h2 style={{ fontSize: 'var(--font-size-md)', fontWeight: 600 }}>Alışverişler</h2>
                <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                  <button className="btn btn-secondary btn-sm" onClick={() => setShowPurchaseTemplates(true)}>
                    Kayıtlı {purchaseTemplates.length > 0 && <span style={{ marginLeft: 4, background: 'var(--accent)', color: '#fff', borderRadius: 10, padding: '1px 6px', fontSize: 11 }}>{purchaseTemplates.length}</span>}
                  </button>
                  <button className="btn btn-primary btn-sm" onClick={() => { setError(''); setSaveAsTemplate(false); setTemplateName(''); setShowPurchaseModal(true) }}>+ Yeni Alışveriş</button>
                </div>
              </div>

              {purchases.length === 0 ? (
                <div className="empty-state" style={{ minHeight: '20vh' }}>
                  <div className="empty-state-icon"><CategoriesIcon size={48} /></div>
                  <div className="empty-state-title">Taksitli alışveriş bulunamadı</div>
                </div>
              ) : (
                <div className="card" style={{ padding: 0 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Açıklama</th>
                        <th>Tarih</th>
                        <th style={{ textAlign: 'right' }}>Toplam</th>
                        <th style={{ textAlign: 'center' }}>Ödeme</th>
                        <th style={{ textAlign: 'right' }}>Taksit Tutarı</th>
                        <th style={{ textAlign: 'center' }}>Kalan</th>
                        <th>Durum</th>
                        <th style={{ width: 80 }}></th>
                      </tr>
                    </thead>
                    <tbody>
                      {purchases.map((p: any) => (
                        <tr key={p.id} style={{ opacity: p.status !== 'ACTIVE' ? 0.5 : 1 }}>
                          <td style={{ fontWeight: 500 }}>{p.description}</td>
                          <td style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)' }}>{p.purchase_date}</td>
                          <td className="text-right" style={{ fontFamily: 'var(--font-mono)' }}>{p.currency} {fmt(Number(p.total_amount))}</td>
                          <td style={{ textAlign: 'center' }}>
                            {p.installment_count === 1
                              ? <span className="badge badge-neutral">Peşin</span>
                              : <span>{p.installment_count} Taksit</span>}
                          </td>
                          <td className="text-right" style={{ fontFamily: 'var(--font-mono)' }}>{p.currency} {fmt(Number(p.installment_amount))}</td>
                          <td style={{ textAlign: 'center', fontWeight: 600, color: p.remaining_installments > 0 ? 'var(--warning)' : 'var(--income)' }}>
                            {p.installment_count === 1 ? '—' : `${p.remaining_installments}/${p.installment_count}`}
                          </td>
                          <td><span className={`badge ${p.status === 'ACTIVE' ? 'badge-confirmed' : p.status === 'CANCELLED' ? 'badge-expense' : 'badge-warning'}`}>{p.status === 'ACTIVE' ? 'Aktif' : p.status === 'CANCELLED' ? 'İptal' : 'İade'}</span></td>
                          <td>
                            {p.status === 'ACTIVE' && (
                              <button className="btn btn-ghost btn-sm" style={{ color: 'var(--expense)', fontSize: 11 }} onClick={() => { setCancelTarget(p); setCancelScenario('A'); setError(''); setShowCancelModal(true) }}>İptal</button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* ── Tab: Statements ─────────────────────────── */}
          {activeTab === 'statements' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
                <h2 style={{ fontSize: 'var(--font-size-md)', fontWeight: 600 }}>Ekstreler</h2>
                <button className="btn btn-primary btn-sm" onClick={() => {
                  if (!selectedCard) return
                  const now = new Date()
                  const sd = selectedCard.statement_day
                  let ps: Date, pe: Date
                  if (now.getDate() > sd) {
                    ps = new Date(now.getFullYear(), now.getMonth(), sd + 1)
                    pe = new Date(now.getFullYear(), now.getMonth() + 1, sd)
                  } else {
                    ps = new Date(now.getFullYear(), now.getMonth() - 1, sd + 1)
                    pe = new Date(now.getFullYear(), now.getMonth(), sd)
                  }
                  setStmtForm({
                    period_start: ps.toISOString().slice(0, 10),
                    period_end: pe.toISOString().slice(0, 10),
                    real_available_limit: '',
                  })
                  setError('')
                  setShowStatementModal(true)
                }}>+ Ekstre Oluştur</button>
              </div>

              {statements.length === 0 ? (
                <div className="empty-state" style={{ minHeight: '20vh' }}>
                  <div className="empty-state-icon"><ReportsIcon size={48} /></div>
                  <div className="empty-state-title">Ekstre bulunamadı</div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                  {statements.map((stmt: any) => (
                    <div key={stmt.id} className="card" style={{ padding: 'var(--space-4)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
                            <span style={{ fontWeight: 600 }}>{stmt.period_start} → {stmt.period_end}</span>
                            <span className={`badge ${stmt.status === 'PAID' ? 'badge-confirmed' : stmt.status === 'CLOSED' ? 'badge-warning' : stmt.status === 'OPEN' ? 'badge-pending' : 'badge-expense'}`}>
                              {stmt.status === 'PAID' ? 'Ödendi' : stmt.status === 'CLOSED' ? 'Kesinleşti' : stmt.status === 'OPEN' ? 'Açık' : stmt.status}
                            </span>
                          </div>
                          <div style={{ display: 'flex', gap: 'var(--space-6)', fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
                            <div>Toplam: <strong style={{ color: 'var(--expense)' }}>{selectedCard?.currency} {fmt(Number(stmt.total_spending))}</strong></div>
                            <div>Ödenen: <strong style={{ color: 'var(--income)' }}>{selectedCard?.currency} {fmt(Number(stmt.paid_amount))}</strong></div>
                            {Number(stmt.new_spending) > 0 && <div>Yeni Harcama: <strong>{selectedCard?.currency} {fmt(Number(stmt.new_spending))}</strong></div>}
                            <div>Son Ödeme: <strong>{stmt.due_date}</strong></div>
                          </div>
                          {stmt.payment_date && <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 'var(--space-1)' }}>Ödeme tarihi: {stmt.payment_date}</div>}
                        </div>
                        <div style={{ display: 'flex', gap: 'var(--space-2)', flexShrink: 0 }}>
                          <button className="btn btn-ghost btn-sm" onClick={() => handleViewStatement(stmt)}>Detay</button>
                          {stmt.status === 'OPEN' && Number(stmt.new_spending) > 0 && (
                            <button className="btn btn-secondary btn-sm" onClick={() => {
                              setDetailTarget(stmt)
                              setDetailLines([{ category_id: '', description: 'Yeni harcama', amount: String(Number(stmt.new_spending)) }])
                              setError('')
                              setShowDetailModal(true)
                            }}>Detaylandır</button>
                          )}
                          {stmt.status === 'OPEN' && (
                            <>
                              <button className="btn btn-secondary btn-sm" style={{ color: 'var(--warning)' }} onClick={() => handleFinalize(stmt)}><LockIcon size={13} /> Kesinleştir</button>
                              <button className="btn btn-ghost btn-sm" style={{ color: 'var(--expense)' }} onClick={() => handleDeleteStatement(stmt)}><DeleteIcon size={13} /> Sil</button>
                            </>
                          )}
                          {(stmt.status === 'CLOSED' || stmt.status === 'PARTIALLY_PAID') && (
                            <button className="btn btn-primary btn-sm" onClick={() => {
                              setPayTarget(stmt)
                              setPayForm({ source_account_id: '', amount: String(Number(stmt.total_spending) - Number(stmt.paid_amount)) })
                              setError('')
                              setShowPayModal(true)
                            }}>Öde</button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── Tab: Kart Bilgileri ─────────────────────── */}
          {activeTab === 'card_info' && selectedCard && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)', maxWidth: 600 }}>

              {/* Genel bilgiler kartı */}
              <div className="card" style={{ padding: 'var(--space-5)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
                  <h3 style={{ fontWeight: 600, fontSize: 'var(--font-size-md)', margin: 0 }}>Kart Detayları</h3>
                  <button className="btn btn-secondary btn-sm" onClick={openEditCard}><EditIcon size={13} /> Düzenle</button>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
                  {[
                    ['Kart Adı', selectedCard.card_name],
                    ['Banka', selectedCard.bank_name],
                    ['Ağ', selectedCard.network],
                    ['Para Birimi', selectedCard.currency],
                    ['Limit', `${selectedCard.currency} ${fmt(Number(selectedCard.credit_limit))}`],
                    ['Son 4 Hane', selectedCard.last_four_digits ? `**** ${selectedCard.last_four_digits}` : '—'],
                    ['Hesap Kesim Günü', `Her ayın ${selectedCard.statement_day}. günü`],
                    ['Son Ödeme Günü', `Her ayın ${selectedCard.due_day}. günü`],
                    ['Son Kullanım', selectedCard.expiry_month && selectedCard.expiry_year ? `${String(selectedCard.expiry_month).padStart(2,'0')}/${selectedCard.expiry_year}` : '—'],
                    ['Durum', selectedCard.status],
                  ].map(([label, val]) => (
                    <div key={label}>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 2 }}>{label}</div>
                      <div style={{ fontWeight: 500 }}>{val}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Hassas bilgiler kartı */}
              <div className="card" style={{ padding: 'var(--space-5)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
                  <h3 style={{ fontWeight: 600, fontSize: 'var(--font-size-md)', margin: 0, display: 'flex', alignItems: 'center', gap: 6 }}><LockIcon size={15} /> Hassas Bilgiler</h3>
                  <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => { setSensitivePassword(''); setSensitiveCardNumber(''); setSensitiveCvv(''); setSensitiveError(''); setShowSensitiveSaveModal(true) }}><EditIcon size={13} /> Güncelle</button>
                    {!sensitiveData && (
                      <button className="btn btn-primary btn-sm" onClick={() => { setSensitivePassword(''); setSensitiveError(''); setShowSensitiveRevealModal(true) }}><EyeIcon size={13} /> Görüntüle</button>
                    )}
                    {sensitiveData && (
                      <button className="btn btn-ghost btn-sm" onClick={() => setSensitiveData(null)}><EyeOffIcon size={13} /> Gizle</button>
                    )}
                  </div>
                </div>

                {!sensitiveData ? (
                  <div style={{ textAlign: 'center', padding: 'var(--space-6)', color: 'var(--text-tertiary)' }}>
                    <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 'var(--space-2)' }}><LockIcon size={28} /></div>
                    <div style={{ fontSize: 'var(--font-size-sm)' }}>Kart numarası ve güvenlik kodunu görüntülemek için şifrenizi girmeniz gerekir</div>
                  </div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
                    <div>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 4 }}>Kart Numarası</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-md)', fontWeight: 600, letterSpacing: 2, display: 'flex', alignItems: 'center', gap: 8 }}>
                        {sensitiveData.card_number
                          ? (showCardNumber
                            ? sensitiveData.card_number.replace(/(\d{4})/g, '$1 ').trim()
                            : '•••• •••• •••• ' + sensitiveData.card_number.slice(-4))
                          : '—'}
                        {sensitiveData.card_number && (
                          <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowCardNumber(v => !v)}>{showCardNumber ? <EyeOffIcon size={13} /> : <EyeIcon size={13} />}</button>
                        )}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 4 }}>Son Kullanım Tarihi</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                        {sensitiveData.expiry_month && sensitiveData.expiry_year
                          ? `${String(sensitiveData.expiry_month).padStart(2,'0')} / ${sensitiveData.expiry_year}`
                          : '—'}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 4 }}>Güvenlik Kodu (CVV)</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
                        {sensitiveData.cvv ? (showCvv ? sensitiveData.cvv : '•••') : '—'}
                        {sensitiveData.cvv && (
                          <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowCvv(v => !v)}>{showCvv ? <EyeOffIcon size={13} /> : <EyeIcon size={13} />}</button>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
              </>
            )}
          </div>
        </div>
      )}

      {/* ── Edit Card Info Modal ──────────────────────── */}
      <Modal open={showEditCardModal} onClose={() => setShowEditCardModal(false)}>
        <div className="modal-header">
          <span className="modal-title">Kart Bilgilerini Düzenle</span>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowEditCardModal(false)}><CloseIcon size={14} /></button>
        </div>
        <form onSubmit={handleEditCard}>
          <div className="modal-body">
            {error && <div className="alert alert-danger">{error}</div>}
            <div className="form-row cols-2">
              <div className="form-group"><label className="form-label">Limit</label><input className="form-input" type="number" step="0.01" value={editCardForm.credit_limit} onChange={e => setEditCardForm({ ...editCardForm, credit_limit: e.target.value })} /></div>
              <div className="form-group"><label className="form-label">Son 4 Hane</label><input className="form-input" maxLength={4} placeholder="1234" value={editCardForm.last_four_digits} onChange={e => setEditCardForm({ ...editCardForm, last_four_digits: e.target.value })} /></div>
            </div>
            <div className="form-row cols-2">
              <div className="form-group"><label className="form-label">Hesap Kesim Günü</label><input className="form-input" type="number" min="1" max="31" value={editCardForm.statement_day} onChange={e => setEditCardForm({ ...editCardForm, statement_day: e.target.value })} /></div>
              <div className="form-group"><label className="form-label">Son Ödeme Günü</label><input className="form-input" type="number" min="1" max="31" value={editCardForm.due_day} onChange={e => setEditCardForm({ ...editCardForm, due_day: e.target.value })} /></div>
            </div>
            <div className="form-row cols-2">
              <div className="form-group"><label className="form-label">Son Kullanım Ay</label><input className="form-input" type="number" min="1" max="12" placeholder="MM" value={editCardForm.expiry_month} onChange={e => setEditCardForm({ ...editCardForm, expiry_month: e.target.value })} /></div>
              <div className="form-group"><label className="form-label">Son Kullanım Yıl</label><input className="form-input" type="number" min="2024" max="2040" placeholder="YYYY" value={editCardForm.expiry_year} onChange={e => setEditCardForm({ ...editCardForm, expiry_year: e.target.value })} /></div>
            </div>
            <div className="form-group"><label className="form-label">Notlar</label><textarea className="form-input" rows={2} value={editCardForm.notes} onChange={e => setEditCardForm({ ...editCardForm, notes: e.target.value })} /></div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setShowEditCardModal(false)}>Vazgeç</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? <span className="spinner spinner-sm" /> : 'Kaydet'}</button>
          </div>
        </form>
      </Modal>

      {/* ── Sensitive Save Modal ──────────────────────── */}
      <Modal open={showSensitiveSaveModal} onClose={() => setShowSensitiveSaveModal(false)}>
        <div className="modal-header">
          <span className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}><LockIcon size={15} /> Hassas Kart Bilgilerini Kaydet</span>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowSensitiveSaveModal(false)}><CloseIcon size={14} /></button>
        </div>
        <form onSubmit={handleSensitiveSave}>
          <div className="modal-body">
            {sensitiveError && <div className="alert alert-danger" style={{ marginBottom: 'var(--space-3)' }}>{sensitiveError}</div>}
            <div style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', padding: 'var(--space-3)', marginBottom: 'var(--space-4)', fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
              Bilgiler sunucuda şifrelenmiş olarak saklanır. Görüntülemek için her seferinde şifreniz istenir.
            </div>
            <div className="form-group">
              <label className="form-label">Kart Numarası</label>
              <input className="form-input" placeholder="1234 5678 9012 3456" value={sensitiveCardNumber} onChange={e => setSensitiveCardNumber(e.target.value)} maxLength={19} style={{ fontFamily: 'var(--font-mono)', letterSpacing: 2 }} />
            </div>
            <div className="form-group">
              <label className="form-label">Güvenlik Kodu (CVV)</label>
              <input className="form-input" type="password" placeholder="•••" value={sensitiveCvv} onChange={e => setSensitiveCvv(e.target.value)} maxLength={4} style={{ width: 120 }} />
            </div>
            <div className="form-group">
              <label className="form-label">Mevcut Şifreniz <span className="required">*</span></label>
              <input className="form-input" type="password" required placeholder="Şifrenizi girin" value={sensitivePassword} onChange={e => setSensitivePassword(e.target.value)} autoFocus />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setShowSensitiveSaveModal(false)}>Vazgeç</button>
            <button type="submit" className="btn btn-primary" disabled={sensitiveLoading}>{sensitiveLoading ? <span className="spinner spinner-sm" /> : <><LockIcon size={13} /> Şifreli Kaydet</>}</button>
          </div>
        </form>
      </Modal>

      {/* ── Sensitive Reveal Modal ────────────────────── */}
      <Modal open={showSensitiveRevealModal} onClose={() => setShowSensitiveRevealModal(false)}>
        <div className="modal-header">
          <span className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}><LockIcon size={15} /> Kart Bilgilerini Görüntüle</span>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowSensitiveRevealModal(false)}><CloseIcon size={14} /></button>
        </div>
        <form onSubmit={handleSensitiveReveal}>
          <div className="modal-body">
            {sensitiveError && <div className="alert alert-danger" style={{ marginBottom: 'var(--space-3)' }}>{sensitiveError}</div>}
            <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-4)' }}>
              Kart numarası ve güvenlik kodunu görüntülemek için giriş şifrenizi girin.
            </p>
            <div className="form-group">
              <label className="form-label">Şifreniz <span className="required">*</span></label>
              <input className="form-input" type="password" required autoFocus placeholder="Şifrenizi girin" value={sensitivePassword} onChange={e => setSensitivePassword(e.target.value)} />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setShowSensitiveRevealModal(false)}>Vazgeç</button>
            <button type="submit" className="btn btn-primary" disabled={sensitiveLoading}>{sensitiveLoading ? <span className="spinner spinner-sm" /> : <><EyeIcon size={13} /> Görüntüle</>}</button>
          </div>
        </form>
      </Modal>

      {/* ── Card Create Modal ──────────────────────────── */}
      <Modal open={showCardModal} onClose={() => setShowCardModal(false)}>
        <div className="modal-header">
          <span className="modal-title">Yeni Kredi Kartı</span>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowCardModal(false)}><CloseIcon size={14} /></button>
        </div>
        <form onSubmit={handleCreateCard}>
          <div className="modal-body">
            {error && <div className="alert alert-danger">{error}</div>}
            <div className="form-row cols-2">
              <div className="form-group"><label className="form-label">Kart Adı *</label><input className="form-input" required value={cardForm.card_name} onChange={e => setCardForm({ ...cardForm, card_name: e.target.value })} /></div>
              <div className="form-group"><label className="form-label">Banka *</label><input className="form-input" required value={cardForm.bank_name} onChange={e => setCardForm({ ...cardForm, bank_name: e.target.value })} /></div>
            </div>
            <div className="form-row cols-2">
              <div className="form-group"><label className="form-label">Limit *</label><input className="form-input" type="number" step="0.01" required value={cardForm.credit_limit} onChange={e => setCardForm({ ...cardForm, credit_limit: e.target.value })} /></div>
              <div className="form-group"><label className="form-label">Para Birimi</label><select className="form-select" value={cardForm.currency} onChange={e => setCardForm({ ...cardForm, currency: e.target.value })}>{['TRY', 'USD', 'EUR', 'GBP'].map(c => <option key={c}>{c}</option>)}</select></div>
            </div>
            <div className="form-row cols-2">
              <div className="form-group"><label className="form-label">Hesap Kesim Günü *</label><input className="form-input" type="number" min="1" max="31" required value={cardForm.statement_day} onChange={e => setCardForm({ ...cardForm, statement_day: e.target.value })} /></div>
              <div className="form-group"><label className="form-label">Son Ödeme Günü *</label><input className="form-input" type="number" min="1" max="31" required value={cardForm.due_day} onChange={e => setCardForm({ ...cardForm, due_day: e.target.value })} /></div>
            </div>
            {groups.length > 0 && (
              <div className="form-group"><label className="form-label">Grup</label><select className="form-select" value={cardForm.group_id} onChange={e => setCardForm({ ...cardForm, group_id: e.target.value })}><option value="">-- Seçiniz --</option>{groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}</select></div>
            )}
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setShowCardModal(false)}>Vazgeç</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Kaydediliyor...' : 'Oluştur'}</button>
          </div>
        </form>
      </Modal>

      {/* ── Purchase Create Modal ──────────────────────── */}
      <Modal open={showPurchaseModal} onClose={() => setShowPurchaseModal(false)}>
        <div className="modal-header">
          <span className="modal-title">
            {parseInt(purchaseForm.installment_count) === 1 ? 'Peşin Alışveriş' : 'Taksitli Alışveriş'}
          </span>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowPurchaseModal(false)}><CloseIcon size={14} /></button>
        </div>
        <form onSubmit={handleCreatePurchase}>
          <div className="modal-body">
            {error && <div className="alert alert-danger">{error}</div>}

            {/* Şablon seç */}
            {purchaseTemplates.length > 0 && (
              <div className="form-group" style={{ marginBottom: 'var(--space-4)', padding: 'var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                <label className="form-label" style={{ fontSize: 'var(--font-size-xs)', marginBottom: 'var(--space-2)' }}>Kayıtlı şablondan seç</label>
                <select className="form-select" defaultValue="" onChange={e => {
                  const tmpl = purchaseTemplates.find((t: any) => t.id === e.target.value)
                  if (!tmpl) return
                  setPurchaseForm(f => ({
                    ...f,
                    description: tmpl.description || '',
                    installment_count: String(tmpl.installment_count),
                    currency: tmpl.currency || 'TRY',
                    category_id: tmpl.category_id || '',
                    total_amount: '',
                  }))
                }}>
                  <option value="">— Şablon seç —</option>
                  {purchaseTemplates.map((tmpl: any) => (
                    <option key={tmpl.id} value={tmpl.id}>
                      {tmpl.name} ({tmpl.installment_count === 1 ? 'Peşin' : `${tmpl.installment_count} Taksit`})
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="form-group"><label className="form-label">Açıklama *</label><input className="form-input" required value={purchaseForm.description} onChange={e => setPurchaseForm({ ...purchaseForm, description: e.target.value })} /></div>
            <div className="form-row cols-2">
              <div className="form-group"><label className="form-label">Toplam Tutar *</label><input className="form-input" type="number" step="0.01" min="0.01" required value={purchaseForm.total_amount} onChange={e => setPurchaseForm({ ...purchaseForm, total_amount: e.target.value })} /></div>
              <div className="form-group">
                <label className="form-label">Taksit Sayısı *</label>
                <input className="form-input" type="number" min="1" max="60" required value={purchaseForm.installment_count} onChange={e => setPurchaseForm({ ...purchaseForm, installment_count: e.target.value })} />
              </div>
            </div>
            {Number(purchaseForm.total_amount) > 0 && Number(purchaseForm.installment_count) > 0 && (
              <div style={{ padding: 'var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', marginBottom: 'var(--space-3)', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)' }}>
                {parseInt(purchaseForm.installment_count) === 1
                  ? <>Tutar: <strong>{fmt(Number(purchaseForm.total_amount))}</strong> (Peşin)</>
                  : <>Aylık Taksit: <strong>{fmt(Number(purchaseForm.total_amount) / Number(purchaseForm.installment_count))}</strong></>
                }
              </div>
            )}
            <div className="form-row cols-2">
              <div className="form-group"><label className="form-label">Tarih</label><input className="form-input" type="date" value={purchaseForm.purchase_date} onChange={e => setPurchaseForm({ ...purchaseForm, purchase_date: e.target.value })} /></div>
              <div className="form-group"><label className="form-label">Kategori <span className="required">*</span></label><select className="form-select" value={purchaseForm.category_id} onChange={e => setPurchaseForm({ ...purchaseForm, category_id: e.target.value })}><option value="">Seçiniz...</option>{categories.filter(c => c.category_type === 'EXPENSE').map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
            </div>

            {/* Şablon kaydet */}
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: 'var(--space-3)', marginTop: 'var(--space-2)' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', cursor: 'pointer', fontSize: 'var(--font-size-sm)' }}>
                <input type="checkbox" checked={saveAsTemplate} onChange={e => setSaveAsTemplate(e.target.checked)} />
                Bu alışverişi şablon olarak kaydet
              </label>
              {saveAsTemplate && (
                <input className="form-input" style={{ marginTop: 'var(--space-2)' }}
                  placeholder="Şablon adı (örn: Sigorta Ödemesi, Netflix)" value={templateName}
                  onChange={e => setTemplateName(e.target.value)} />
              )}
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setShowPurchaseModal(false)}>Vazgeç</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Kaydediliyor...' : parseInt(purchaseForm.installment_count) === 1 ? 'Peşin Alışverişi Kaydet' : 'Taksitli Alışverişi Kaydet'}
            </button>
          </div>
        </form>
      </Modal>

      {/* ── Statement Generate Modal ───────────────────── */}
      <Modal open={showStatementModal} onClose={() => setShowStatementModal(false)}>
        <div className="modal-header">
          <span className="modal-title">Ekstre Oluştur</span>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowStatementModal(false)}><CloseIcon size={14} /></button>
        </div>
        <form onSubmit={handleGenerateStatement}>
          <div className="modal-body">
            {error && <div className="alert alert-danger">{error}</div>}
            {limits && (
              <div style={{ padding: 'var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', marginBottom: 'var(--space-4)' }}>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 4 }}>
                  {stmtForm.period_end ? `${stmtForm.period_end} Tarihindeki Teorik Boş Limit` : 'Teorik Boş Limit'}
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 'var(--font-size-lg)', color: 'var(--income)' }}>
                  {selectedCard?.currency} {fmt(Number(limits.theoretical_available))}
                </div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 4 }}>
                  Toplam ({fmt(Number(limits.total_limit))}) - Bağlı ({fmt(Number(limits.committed_limit))})
                </div>
              </div>
            )}
            <div className="form-row cols-2">
              <div className="form-group"><label className="form-label">Dönem Başlangıcı *</label><input className="form-input" type="date" required value={stmtForm.period_start} onChange={e => setStmtForm({ ...stmtForm, period_start: e.target.value })} /></div>
              <div className="form-group"><label className="form-label">Dönem Bitişi *</label><input className="form-input" type="date" required value={stmtForm.period_end} onChange={e => setStmtForm({ ...stmtForm, period_end: e.target.value })} /></div>
            </div>
            <div className="form-group">
              <label className="form-label">Gerçek Kullanılabilir Limit *</label>
              <input className="form-input" type="number" step="0.01" min="0" required placeholder="Bankadan gördüğünüz boş limit" value={stmtForm.real_available_limit} onChange={e => setStmtForm({ ...stmtForm, real_available_limit: e.target.value })} />
            </div>
            {stmtPreviewLoading && (
              <div style={{ padding: 'var(--space-3)', color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>Hesaplanıyor...</div>
            )}
            {stmtPreview && !stmtPreviewLoading && (
              <div style={{ padding: 'var(--space-3)', background: 'rgba(var(--expense-rgb,239,68,68),0.08)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(var(--expense-rgb,239,68,68),0.2)' }}>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 'var(--space-1)' }}>Tahmini Ekstre Tutarı</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 'var(--font-size-lg)', color: 'var(--expense)' }}>
                  {selectedCard?.currency} {fmt(stmtPreview.total_spending)}
                </div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 'var(--space-1)' }}>
                  {fmt(stmtPreview.total_limit)} − {fmt(stmtPreview.future_committed)} − {fmt(stmtPreview.real_available)} = {fmt(stmtPreview.total_spending)}
                </div>
                {stmtPreview.installment_total > 0 && (
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 2 }}>
                    Taksit: {selectedCard?.currency} {fmt(stmtPreview.installment_total)}
                    {stmtPreview.new_spending > 0 && ` + Yeni Harcama: ${selectedCard?.currency} ${fmt(stmtPreview.new_spending)}`}
                  </div>
                )}
              </div>
            )}
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setShowStatementModal(false)}>Vazgeç</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Oluşturuluyor...' : 'Ekstre Oluştur'}</button>
          </div>
        </form>
      </Modal>

      {/* ── Detail New Spending Modal ──────────────────── */}
      <Modal open={showDetailModal} onClose={() => setShowDetailModal(false)}>
        <div className="modal-header">
          <span className="modal-title">Yeni Harcamayı Detaylandır</span>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowDetailModal(false)}><CloseIcon size={14} /></button>
        </div>
        <div className="modal-body">
          {error && <div className="alert alert-danger">{error}</div>}
          {detailTarget && (
            <div style={{ padding: 'var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', marginBottom: 'var(--space-4)' }}>
              <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>Toplam Harcama: </span>
              <strong style={{ fontFamily: 'var(--font-mono)' }}>{selectedCard?.currency} {fmt(Number(detailTarget.new_spending))}</strong>
              <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginLeft: 8 }}>— Detaylandırmadığınız kalan "Diğer harcamalar" olarak kaydedilir.</span>
            </div>
          )}
          {detailLines.map((line, idx) => (
            <div key={idx} style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-2)' }}>
                <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>Satır {idx + 1}</span>
                {detailLines.length > 1 && <button className="btn btn-ghost btn-sm" style={{ color: 'var(--expense)', fontSize: 11 }} onClick={() => setDetailLines(detailLines.filter((_, i) => i !== idx))}>Sil</button>}
              </div>
              <div className="form-group"><label className="form-label">Kategori *</label><select className="form-select" required value={line.category_id} onChange={e => { const nl = [...detailLines]; nl[idx].category_id = e.target.value; setDetailLines(nl) }}><option value="">-- Kategori Seçin --</option>{categories.filter(c => c.category_type === 'EXPENSE').map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
              <div className="form-row cols-2">
                <div className="form-group"><label className="form-label">Açıklama *</label><input className="form-input" required value={line.description} onChange={e => { const nl = [...detailLines]; nl[idx].description = e.target.value; setDetailLines(nl) }} /></div>
                <div className="form-group"><label className="form-label">Tutar *</label><input className="form-input" type="number" step="0.01" min="0.01" required value={line.amount} onChange={e => { const nl = [...detailLines]; nl[idx].amount = e.target.value; setDetailLines(nl) }} /></div>
              </div>
            </div>
          ))}
          <button className="btn btn-secondary btn-sm" style={{ marginBottom: 'var(--space-3)' }} onClick={() => setDetailLines([...detailLines, { category_id: '', description: '', amount: '' }])}>+ Satır Ekle</button>
          {(() => {
            const total = detailLines.reduce((s, l) => s + (parseFloat(l.amount) || 0), 0)
            const target = Number(detailTarget?.new_spending || 0)
            const remainder = target - total
            const over = total > target + 0.01
            return (
              <div style={{ padding: 'var(--space-2)', background: over ? 'rgba(239,68,68,0.1)' : 'rgba(34,197,94,0.08)', borderRadius: 'var(--radius-sm)', fontSize: 'var(--font-size-sm)', fontFamily: 'var(--font-mono)' }}>
                {over
                  ? `Girilen tutar toplamı (${fmt(total)}) harcamayı (${fmt(target)}) aşıyor`
                  : remainder > 0.01
                    ? `Detaylandırıldı: ${fmt(total)} — Kalan "Diğer": ${fmt(remainder)}`
                    : `Toplam: ${fmt(total)} ✓`
                }
              </div>
            )
          })()}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={() => setShowDetailModal(false)}>Vazgeç</button>
          <button className="btn btn-primary" disabled={saving} onClick={handleDetailSubmit}>{saving ? 'Kaydediliyor...' : 'Detayları Kaydet'}</button>
        </div>
      </Modal>

      {/* ── Purchase Templates Modal ──────────────────── */}
      <Modal open={showPurchaseTemplates} onClose={() => setShowPurchaseTemplates(false)}>
        <div className="modal-header">
          <span className="modal-title">Kayıtlı Alışverişler</span>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowPurchaseTemplates(false)}><CloseIcon size={14} /></button>
        </div>
        <div className="modal-body">
          {purchaseTemplates.length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--text-tertiary)', padding: 'var(--space-6)' }}>
              Henüz kayıtlı alışveriş şablonu yok.<br />
              <small>Yeni alışveriş kaydederken "Şablon olarak kaydet" seçeneğini kullanabilirsiniz.</small>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {purchaseTemplates.map((tmpl: any) => (
                <div key={tmpl.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 'var(--space-3)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', background: 'var(--bg-elevated)' }}>
                  <div>
                    <div style={{ fontWeight: 600 }}>{tmpl.name}</div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 2 }}>
                      {tmpl.installment_count === 1 ? 'Peşin' : `${tmpl.installment_count} Taksit`}
                      {tmpl.description && ` · ${tmpl.description}`}
                      {tmpl.currency && ` · ${tmpl.currency}`}
                    </div>
                  </div>
                  <button className="btn btn-ghost btn-icon btn-sm" style={{ color: 'var(--expense)' }}
                    onClick={async () => {
                      await ccPurchaseTemplatesApi.delete(tmpl.id)
                      const r = await ccPurchaseTemplatesApi.list()
                      setPurchaseTemplates(r.data)
                    }} title="Şablonu sil"><CloseIcon size={12} /></button>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={() => setShowPurchaseTemplates(false)}>Kapat</button>
        </div>
      </Modal>

      {/* ── Pay Statement Modal ────────────────────────── */}
      <Modal open={showPayModal} onClose={() => setShowPayModal(false)}>
        <div className="modal-header">
          <span className="modal-title">Ekstre Öde</span>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowPayModal(false)}><CloseIcon size={14} /></button>
        </div>
        <form onSubmit={handlePaySubmit}>
          <div className="modal-body">
            {error && <div className="alert alert-danger">{error}</div>}
            {payTarget && (
              <div style={{ padding: 'var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', marginBottom: 'var(--space-4)' }}>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>Kalan Borç</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 'var(--font-size-lg)', color: 'var(--expense)' }}>
                  {selectedCard?.currency} {fmt(Number(payTarget.total_spending) - Number(payTarget.paid_amount))}
                </div>
              </div>
            )}
            <div className="form-group"><label className="form-label">Ödemenin Çıkacağı Hesap *</label>
              <select className="form-select" required value={payForm.source_account_id} onChange={e => setPayForm({ ...payForm, source_account_id: e.target.value })}>
                <option value="">-- Hesap Seçin --</option>
                {paymentAccounts.map((a: any) => <option key={a.id} value={a.id}>{a.name} ({a.currency} {fmt(Number(a.current_balance))})</option>)}
              </select>
            </div>
            <div className="form-group"><label className="form-label">Ödeme Tutarı *</label><input className="form-input" type="number" step="0.01" min="0.01" required value={payForm.amount} onChange={e => setPayForm({ ...payForm, amount: e.target.value })} /></div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setShowPayModal(false)}>Vazgeç</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Ödeniyor...' : 'Ödemeyi Gerçekleştir'}</button>
          </div>
        </form>
      </Modal>

      {/* ── Cancel Purchase Modal ──────────────────────── */}
      <Modal open={showCancelModal} onClose={() => setShowCancelModal(false)}>
        <div className="modal-header">
          <span className="modal-title">Alışveriş İptal / İade</span>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowCancelModal(false)}><CloseIcon size={14} /></button>
        </div>
        <div className="modal-body">
          {error && <div className="alert alert-danger">{error}</div>}
          {cancelTarget && (
            <div style={{ padding: 'var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', marginBottom: 'var(--space-4)' }}>
              <strong>{cancelTarget.description}</strong> — {selectedCard?.currency} {fmt(Number(cancelTarget.total_amount))}
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginTop: 4 }}>Kalan taksit: {cancelTarget.remaining_installments}/{cancelTarget.installment_count}</div>
            </div>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-3)', padding: 'var(--space-3)', border: cancelScenario === 'A' ? '2px solid var(--accent)' : '1px solid var(--border)', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }} onClick={() => setCancelScenario('A')}>
              <input type="radio" checked={cancelScenario === 'A'} onChange={() => setCancelScenario('A')} />
              <div><strong>Senaryo A — Tam İptal</strong><div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>Kalan taksitler tamamen silinir, bağlı limit anında açılır.</div></div>
            </label>
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-3)', padding: 'var(--space-3)', border: cancelScenario === 'B' ? '2px solid var(--accent)' : '1px solid var(--border)', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }} onClick={() => setCancelScenario('B')}>
              <input type="radio" checked={cancelScenario === 'B'} onChange={() => setCancelScenario('B')} />
              <div><strong>Senaryo B — Taksitli İade</strong><div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>Banka iadeyi taksit taksit yansıtır, kalan aylara gelir satırları dağıtılır.</div></div>
            </label>
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={() => setShowCancelModal(false)}>Vazgeç</button>
          <button className="btn btn-primary" style={{ background: 'var(--expense)' }} disabled={saving} onClick={handleCancelPurchase}>{saving ? 'İşleniyor...' : 'İptal Et'}</button>
        </div>
      </Modal>

      {/* ── Statement Detail View ─────────────────────── */}
      <Modal open={showStatementView} onClose={() => setShowStatementView(false)}>
        <div className="modal-header">
          <span className="modal-title">Ekstre Detayı</span>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowStatementView(false)}><CloseIcon size={14} /></button>
        </div>
        <div className="modal-body">
          {statementDetail && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
                <div><div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>Dönem</div><div style={{ fontWeight: 600 }}>{statementDetail.period_start} → {statementDetail.period_end}</div></div>
                <div><div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>Son Ödeme</div><div style={{ fontWeight: 600 }}>{statementDetail.due_date}</div></div>
                <div><div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>Toplam Harcama</div><div style={{ fontWeight: 700, color: 'var(--expense)', fontFamily: 'var(--font-mono)' }}>{selectedCard?.currency} {fmt(Number(statementDetail.total_spending))}</div></div>
                <div><div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>Ödenen</div><div style={{ fontWeight: 700, color: 'var(--income)', fontFamily: 'var(--font-mono)' }}>{selectedCard?.currency} {fmt(Number(statementDetail.paid_amount))}</div></div>
              </div>

              {statementDetail.lines && statementDetail.lines.length > 0 ? (
                <table className="data-table" style={{ fontSize: 'var(--font-size-xs)' }}>
                  <thead>
                    <tr>
                      <th>Tür</th>
                      <th>Açıklama</th>
                      <th style={{ textAlign: 'center' }}>Taksit</th>
                      <th style={{ textAlign: 'right' }}>Tutar</th>
                    </tr>
                  </thead>
                  <tbody>
                    {statementDetail.lines.map((line: any) => (
                      <tr key={line.id}>
                        <td><span className={`badge ${line.line_type === 'INSTALLMENT' ? 'badge-pending' : line.line_type === 'REFUND' ? 'badge-confirmed' : 'badge-warning'}`}>{line.line_type === 'INSTALLMENT' ? 'Taksit' : line.line_type === 'REFUND' ? 'İade' : 'Harcama'}</span></td>
                        <td>{line.description}</td>
                        <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)' }}>{line.installment_number ? `${line.installment_number}/${line.total_installments}` : '—'}</td>
                        <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{selectedCard?.currency} {fmt(Number(line.amount))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div style={{ textAlign: 'center', color: 'var(--text-tertiary)', padding: 'var(--space-4)' }}>Detay satırı bulunamadı</div>
              )}
            </>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={() => setShowStatementView(false)}>Kapat</button>
        </div>
      </Modal>
    </div>
  )
}
