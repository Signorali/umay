import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { institutionsApi, groupsApi } from '../api/umay'
import { usePermissions } from '../hooks/usePermissions'

const TYPE_ICON: Record<string, string> = {
  BANK: '🏦', BROKERAGE: '📈', EXCHANGE: '🔄', INSURANCE: '🛡️', OTHER: '🏛️',
}

function Modal({ open, onClose, children }: { open: boolean; onClose: () => void; children: React.ReactNode }) {
  if (!open) return null
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>{children}</div>
    </div>
  )
}

const EMPTY_FORM = {
  name: '', institution_type: 'BROKERAGE', country: 'TR', swift_code: '', website: '', notes: '',
  rep_name: '', rep_phone: '', rep_email: '', group_ids: [] as string[],
}

export function InstitutionsPage() {
  const { t } = useTranslation()
  const { can } = usePermissions()
  const canCreate = can('institutions', 'create') || can('institutions', 'manage')
  const canUpdate = can('institutions', 'update') || can('institutions', 'manage')
  const canDelete = can('institutions', 'delete') || can('institutions', 'manage')
  const [institutions, setInstitutions] = useState<any[]>([])
  const [groups, setGroups] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingInstitution, setEditingInstitution] = useState<any | null>(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState<Record<string, any>>(EMPTY_FORM)

  const load = () => {
    setLoading(true)
    institutionsApi.list({ skip: 0, limit: 100 })
      .then(r => setInstitutions(r.data)).catch(() => {}).finally(() => setLoading(false))
  }
  useEffect(() => {
    load()
    groupsApi.list({ page: 1, page_size: 100 }).then(r => setGroups(r.data?.items || r.data || [])).catch(() => {})
  }, [])

  const resetForm = () => setForm(EMPTY_FORM)

  const openEdit = (inst: any) => {
    setEditingInstitution(inst)
    setForm({
      name: inst.name || '',
      institution_type: inst.institution_type || 'BROKERAGE',
      country: inst.country || 'TR',
      swift_code: inst.swift_code || '',
      website: inst.website || '',
      notes: inst.notes || '',
      rep_name: inst.rep_name || '',
      rep_phone: inst.rep_phone || '',
      rep_email: inst.rep_email || '',
      group_ids: (inst.group_ids || []).map(String),
    })
    setShowModal(true)
  }

  const closeModal = () => {
    setShowModal(false)
    setEditingInstitution(null)
    resetForm()
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (editingInstitution) {
        await institutionsApi.update(editingInstitution.id, form)
      } else {
        await institutionsApi.create(form)
      }
      closeModal()
      load()
    } catch (err: any) {
      alert(err?.response?.data?.detail || err?.response?.data?.error?.message || t('common.error'))
    } finally { setSaving(false) }
  }

  const handleDelete = async (id: string) => {
    if (!confirm(t('common.delete') + '?')) return
    await institutionsApi.delete(id).catch(() => {})
    load()
  }

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">{t('institutions.title')}</h1>
          <p className="page-subtitle">{t('institutions.subtitle')}</p>
        </div>
        {canCreate && <button className="btn btn-primary" onClick={() => setShowModal(true)}>{t('institutions.newInstitution')}</button>}
      </div>

      {/* Content */}
      {loading ? (
        <div className="loading-state"><div className="spinner" /></div>
      ) : institutions.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🏛️</div>
          <div className="empty-state-title">{t('institutions.noInstitutions')}</div>
          <div className="empty-state-desc">{t('institutions.noInstitutionsDesc')}</div>
          {canCreate && <button className="btn btn-primary" onClick={() => setShowModal(true)}>+ {t('institutions.addInstitution')}</button>}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 'var(--space-4)' }}>
          {institutions.map((inst: any) => (
            <div key={inst.id} className="card" style={{ position: 'relative' }}>
              <div style={{ position: 'absolute', top: 'var(--space-3)', right: 'var(--space-3)', display: 'flex', gap: 4 }}>
                {canUpdate && (
                  <button
                    className="btn btn-ghost btn-sm"
                    style={{ color: 'var(--accent)', padding: '2px 6px' }}
                    onClick={() => openEdit(inst)}
                  >✎</button>
                )}
                {canDelete && (
                  <button
                    className="btn btn-ghost btn-sm"
                    style={{ color: 'var(--danger)', padding: '2px 6px' }}
                    onClick={() => handleDelete(inst.id)}
                  >✕</button>
                )}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
                <div style={{
                  width: 48, height: 48, borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-elevated)', display: 'flex', alignItems: 'center',
                  justifyContent: 'center', fontSize: 24, flexShrink: 0,
                }}>
                  {TYPE_ICON[inst.institution_type] || '🏛️'}
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 'var(--font-size-md)' }}>{inst.name}</div>
                  <div style={{ display: 'flex', gap: 'var(--space-2)', marginTop: 4, flexWrap: 'wrap' }}>
                    <span className="badge badge-accent">{t('institutions.types.' + inst.institution_type)}</span>
                    {inst.country && <span className="badge badge-neutral">{inst.country}</span>}
                    {(inst.group_ids || []).map((gid: string) => {
                      const g = groups.find((x: any) => x.id === gid)
                      return g ? <span key={gid} className="badge" style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>{g.name}</span> : null
                    })}
                  </div>
                </div>
              </div>

              {/* Representative info */}
              {(inst.rep_name || inst.rep_phone || inst.rep_email) && (
                <div style={{
                  padding: 'var(--space-3)', marginBottom: 'var(--space-3)',
                  background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)',
                  fontSize: 'var(--font-size-xs)',
                }}>
                  <div style={{ fontWeight: 600, marginBottom: 4, color: 'var(--text-secondary)' }}>Temsilci</div>
                  {inst.rep_name && <div>{inst.rep_name}</div>}
                  {inst.rep_phone && (
                    <div>
                      <a href={`tel:${inst.rep_phone}`} style={{ color: 'var(--accent)' }}>{inst.rep_phone}</a>
                    </div>
                  )}
                  {inst.rep_email && (
                    <div>
                      <a href={`mailto:${inst.rep_email}`} style={{ color: 'var(--accent)' }}>{inst.rep_email}</a>
                    </div>
                  )}
                </div>
              )}

              {inst.swift_code && (
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', marginBottom: 'var(--space-2)', fontFamily: 'monospace' }}>
                  {inst.swift_code}
                </div>
              )}
              {inst.website && (
                <a href={inst.website} target="_blank" rel="noreferrer"
                  style={{ fontSize: 'var(--font-size-xs)', color: 'var(--accent)', display: 'block', marginBottom: 'var(--space-2)' }}>
                  {inst.website}
                </a>
              )}
              {inst.notes && (
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>{inst.notes}</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      <Modal open={showModal} onClose={closeModal}>
        <div className="modal-header">
          <div className="modal-title">{editingInstitution ? t('common.edit') + ': ' + editingInstitution.name : t('institutions.newInstitution')}</div>
          <button className="modal-close" onClick={closeModal}>✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="form-grid">
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label className="form-label">{t('common.name')} *</label>
                <input className="form-input" required placeholder={t('institutions.form.namePlaceholder') as string}
                  value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">{t('common.type')} *</label>
                <select className="form-input" value={form.institution_type} onChange={e => setForm({ ...form, institution_type: e.target.value })}>
                  <option value="BANK">{t('institutions.types.BANK')}</option>
                  <option value="BROKERAGE">{t('institutions.types.BROKERAGE')}</option>
                  <option value="EXCHANGE">{t('institutions.types.EXCHANGE')}</option>
                  <option value="INSURANCE">{t('institutions.types.INSURANCE')}</option>
                  <option value="OTHER">{t('institutions.types.OTHER')}</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">{t('institutions.form.country')}</label>
                <input className="form-input" placeholder="TR"
                  value={form.country} onChange={e => setForm({ ...form, country: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">IBAN / SWIFT</label>
                <input className="form-input" placeholder="TR00 0000 0000 0000 00"
                  value={form.swift_code || ''} onChange={e => setForm({ ...form, swift_code: e.target.value })} />
              </div>

              {/* Representative section */}
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <div style={{ borderTop: '1px solid var(--border)', paddingTop: 'var(--space-3)', marginTop: 'var(--space-1)' }}>
                  <label className="form-label" style={{ fontWeight: 600 }}>Temsilci Bilgileri</label>
                </div>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label className="form-label">Ad Soyad</label>
                <input className="form-input" placeholder="Ali Yilmaz"
                  value={form.rep_name} onChange={e => setForm({ ...form, rep_name: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Telefon</label>
                <input className="form-input" type="tel" placeholder="0532 123 4567"
                  value={form.rep_phone} onChange={e => setForm({ ...form, rep_phone: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">E-posta</label>
                <input className="form-input" type="email" placeholder="temsilci@kurum.com"
                  value={form.rep_email} onChange={e => setForm({ ...form, rep_email: e.target.value })} />
              </div>

              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label className="form-label">{t('institutions.form.website')}</label>
                <input className="form-input" type="url" placeholder="https://..."
                  value={form.website} onChange={e => setForm({ ...form, website: e.target.value })} />
              </div>
              {groups.length > 0 && (
                <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                  <label className="form-label">Gruplar <span style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>(birden fazla seçilebilir)</span></label>
                  <select className="form-input"
                    onChange={e => {
                      const id = e.target.value
                      if (!id || form.group_ids.includes(id)) return
                      setForm({ ...form, group_ids: [...form.group_ids, id] })
                      e.target.value = ''
                    }}>
                    <option value="">+ Grup ekle</option>
                    {groups.filter((g: any) => !form.group_ids.includes(g.id)).map((g: any) => (
                      <option key={g.id} value={g.id}>{g.name}</option>
                    ))}
                  </select>
                  {form.group_ids.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
                      {form.group_ids.map((id: string) => {
                        const g = groups.find((x: any) => x.id === id)
                        return (
                          <span key={id} className="badge badge-accent" style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                            {g ? g.name : id}
                            <span onClick={() => setForm({ ...form, group_ids: form.group_ids.filter((x: string) => x !== id) })} style={{ fontWeight: 700, marginLeft: 2 }}>×</span>
                          </span>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label className="form-label">{t('common.notes')}</label>
                <textarea className="form-input" rows={2} placeholder={t('common.optional') as string}
                  value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} />
              </div>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={closeModal}>{t('common.cancel')}</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? t('common.saving') : editingInstitution ? t('common.save') : t('institutions.addInstitution')}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
