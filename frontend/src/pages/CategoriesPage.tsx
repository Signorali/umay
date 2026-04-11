import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { categoriesApi, groupsApi } from '../api/umay'
import { normalizeFormText } from '../utils/textNormalization'
import { CategoriesIcon, CloseIcon } from '../components/Icons'

export function CategoriesPage() {
  const { t } = useTranslation()
  const [cats, setCats] = useState<any[]>([])
  const [groups, setGroups] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'ALL' | 'INCOME' | 'EXPENSE' | 'TRANSFER'>('EXPENSE')
  // 'ALL' = tümü, diğerleri group_id
  const [groupFilter, setGroupFilter] = useState<string>('__default__')

  // Modals
  const [showModal, setShowModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const [form, setForm] = useState({ name: '', category_type: 'EXPENSE', description: '', group_id: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const load = () => {
    setLoading(true)
    Promise.all([
      categoriesApi.list({ skip: 0, limit: 500 }),
      groupsApi.list({ skip: 0, limit: 100 })
    ])
      .then(([c, g]) => {
        setCats(c.data)
        const groupList = g.data
        setGroups(groupList)
        // Varsayılan grup: ilk grup (yoksa 'ALL')
        if (groupList.length > 0) {
          setGroupFilter(prev => prev === '__default__' ? groupList[0].id : prev)
          setForm(f => ({ ...f, group_id: f.group_id || groupList[0].id }))
        } else {
          setGroupFilter('ALL')
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  // Tip filtresi
  const byType = tab === 'ALL' ? cats : cats.filter(c => c.category_type === tab)

  // Grup filtresi
  const filtered = groupFilter === 'ALL'
    ? byType
    : byType.filter(c => c.group_id === groupFilter)

  const handleEdit = (cat: any) => {
    setEditing(cat)
    setForm({
      name: cat.name,
      category_type: cat.category_type,
      description: cat.description || '',
      group_id: cat.group_id || (groups.length > 0 ? groups[0].id : '')
    })
    setShowModal(true)
  }

  const confirmDelete = (id: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDeletingId(id)
    setShowDeleteModal(true)
  }

  const handleDelete = async () => {
    if (!deletingId) return
    setSaving(true)
    setError('')
    try {
      await categoriesApi.delete(deletingId)
      setShowDeleteModal(false)
      setDeletingId(null)
      load()
    } catch (err: any) {
      setError(err.response?.data?.error?.message || t('common.error'))
    } finally {
      setSaving(false)
    }
  }

  const save = async () => {
    if (!form.name.trim()) { setError(t('common.required')); return }
    if (!form.group_id) { setError(t('common.required')); return }

    setSaving(true)
    setError('')
    try {
      const normalizedForm = {
        ...form,
        name: normalizeFormText(form.name),
        description: form.description ? normalizeFormText(form.description) : '',
      }
      if (editing) {
        await categoriesApi.update(editing.id, normalizedForm)
      } else {
        await categoriesApi.create(normalizedForm)
      }
      setShowModal(false)
      load()
    } catch (err: any) {
      setError(err.response?.data?.error?.message || t('common.error'))
    } finally {
      setSaving(false)
    }
  }

  const openNew = () => {
    setEditing(null)
    // Yeni kategori için aktif grup filtresi veya ilk grup
    const defaultGroup = groupFilter !== 'ALL' ? groupFilter : (groups.length > 0 ? groups[0].id : '')
    setForm({
      name: '',
      category_type: tab === 'ALL' ? 'EXPENSE' : tab,
      description: '',
      group_id: defaultGroup,
    })
    setShowModal(true)
  }

  // Sayaçlar (seçili gruba göre)
  const countByType = (type: string) =>
    (groupFilter === 'ALL' ? cats : cats.filter(c => c.group_id === groupFilter))
      .filter(c => c.category_type === type).length

  const totalCount = groupFilter === 'ALL' ? cats.length : cats.filter(c => c.group_id === groupFilter).length

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">{t('categories.title')}</h1>
          <p className="page-subtitle">{totalCount} {t('common.total', 'kayıt')}</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          {/* Grup filtresi */}
          <div style={{ display: 'flex', gap: 'var(--space-1)', alignItems: 'center' }}>
            <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginRight: 'var(--space-1)' }}>
              Grup:
            </span>
            <button
              className={`btn btn-sm ${groupFilter === 'ALL' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setGroupFilter('ALL')}
            >
              Tümü
            </button>
            {groups.map(g => (
              <button
                key={g.id}
                className={`btn btn-sm ${groupFilter === g.id ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setGroupFilter(g.id)}
              >
                {g.name}
              </button>
            ))}
          </div>
          <button className="btn btn-primary" onClick={openNew}>{t('categories.newCategory')}</button>
        </div>
      </div>

      {/* Tip sekmeleri */}
      <div className="tabs" style={{ marginBottom: 'var(--space-5)' }}>
        <button className={`tab${tab === 'ALL' ? ' active' : ''}`} onClick={() => setTab('ALL')}>
          Tümü ({totalCount})
        </button>
        <button className={`tab${tab === 'EXPENSE' ? ' active' : ''}`} onClick={() => setTab('EXPENSE')}>
          ↓ {t('categories.expense')} ({countByType('EXPENSE')})
        </button>
        <button className={`tab${tab === 'INCOME' ? ' active' : ''}`} onClick={() => setTab('INCOME')}>
          ↑ {t('categories.income')} ({countByType('INCOME')})
        </button>
        <button className={`tab${tab === 'TRANSFER' ? ' active' : ''}`} onClick={() => setTab('TRANSFER')}>
          ⇄ Transfer ({countByType('TRANSFER')})
        </button>
      </div>

      {loading ? <div className="loading-state"><div className="spinner" /></div> :
        filtered.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon"><CategoriesIcon size={48} /></div>
            <div className="empty-state-title">{t('categories.noCategories')}</div>
            <button className="btn btn-primary" onClick={openNew}>
              + {t('common.add')}
            </button>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 'var(--space-3)' }}>
            {filtered.map(c => (
              <div key={c.id} className="card card-sm clickable" onClick={() => handleEdit(c)} style={{ position: 'relative' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                    <div style={{ width: 36, height: 36, borderRadius: 'var(--radius-sm)', background: c.category_type === 'INCOME' ? 'var(--success-soft)' : c.category_type === 'TRANSFER' ? 'var(--info-soft, #e0f0ff)' : 'var(--danger-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16 }}>
                      {c.category_type === 'INCOME' ? '↑' : c.category_type === 'TRANSFER' ? '⇄' : '↓'}
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 'var(--font-size-sm)' }}>{c.name}</div>
                      <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
                        {c.group_id && groupFilter === 'ALL' && (
                          <span className="badge badge-neutral" style={{ fontSize: 10 }}>
                            {groups.find(g => g.id === c.group_id)?.name || '...'}
                          </span>
                        )}
                        {c.is_system && <span className="badge badge-draft" style={{ fontSize: 10 }}>Sistem</span>}
                      </div>
                    </div>
                  </div>
                  {!c.is_system && (
                    <button
                      className="btn btn-ghost btn-icon btn-sm"
                      onClick={(e) => confirmDelete(c.id, e)}
                      style={{ color: 'var(--expense)', zIndex: 10 }}
                    >
                      <CloseIcon size={13} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )
      }

      {/* Edit/Create Modal */}
      {showModal && (
        <div className="modal-backdrop" onClick={e => e.target === e.currentTarget && setShowModal(false)}>
          <div className="modal modal-sm">
            <div className="modal-header">
              <span className="modal-title">{editing ? t('common.edit') : t('categories.newCategory')}</span>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setShowModal(false)}><CloseIcon size={14} /></button>
            </div>
            <div className="modal-body">
              {error && <div className="alert alert-danger" style={{ marginBottom: 'var(--space-4)' }}>{error}</div>}

              <div className="form-group">
                <label className="form-label">{t('categories.form.name', 'Ad')} <span className="required">*</span></label>
                <input className="form-input" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} autoFocus />
              </div>

              <div className="form-group">
                <label className="form-label">{t('common.group')} <span className="required">*</span></label>
                <select className="form-select" value={form.group_id} onChange={e => setForm(f => ({ ...f, group_id: e.target.value }))}>
                  <option value="">-- {t('common.selectGroup')} --</option>
                  {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">{t('common.type')}</label>
                <select className="form-select" value={form.category_type} onChange={e => setForm(f => ({ ...f, category_type: e.target.value as any }))} disabled={!!editing}>
                  <option value="EXPENSE">{t('categories.expense')}</option>
                  <option value="INCOME">{t('categories.income')}</option>
                  <option value="TRANSFER">Transfer</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">{t('common.description')}</label>
                <textarea className="form-input" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={2} />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>{t('common.cancel')}</button>
              <button className="btn btn-primary" onClick={save} disabled={saving}>
                {saving ? <><span className="spinner spinner-sm" /> {t('common.saving')}</> : (editing ? t('common.save') : t('common.create'))}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="modal-backdrop" onClick={() => setShowDeleteModal(false)} style={{ zIndex: 110 }}>
          <div className="modal modal-sm" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">{t('common.confirmDelete', 'Silme Onayı')}</span>
            </div>
            <div className="modal-body">
              {error && <div className="alert alert-danger">{error}</div>}
              <p style={{ textAlign: 'center' }}>
                {t('categories.deleteConfirmText', 'Bu kategoriyi silmek istediğinize emin misiniz?')}
              </p>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowDeleteModal(false)}>{t('common.cancel')}</button>
              <button className="btn btn-danger" onClick={handleDelete} disabled={saving}>
                {saving ? <span className="spinner spinner-sm" /> : t('common.delete', 'Sil')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
