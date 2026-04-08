import React, { useEffect, useState } from 'react'
import { groupsApi, usersApi } from '../api/umay'
import { useTranslation } from 'react-i18next'

interface Group {
  id: string
  name: string
  description: string | null
  created_at: string
}

interface User {
  id: string
  email: string
  full_name: string
}

function CreateGroupModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const { t } = useTranslation()
  const [form, setForm] = useState({ name: '', description: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    if (!form.name.trim()) { setError(t('groups.errors.nameRequired')); return }
    setSaving(true)
    try {
      await groupsApi.create(form)
      onSaved()
    } catch (e: any) {
      setError(e.response?.data?.error?.message || t('groups.errors.createFailed'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <span className="modal-title">{t('groups.newGroupTitle')}</span>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          {error && <div className="alert alert-danger">{error}</div>}
          <div className="form-group">
            <label className="form-label">{t('groups.form.name')} <span className="required">*</span></label>
            <input 
              className="form-input" 
              value={form.name} 
              onChange={e => setForm({ ...form, name: e.target.value })} 
              placeholder={t('groups.form.namePlaceholder')}
            />
          </div>
          <div className="form-group">
            <label className="form-label">{t('groups.form.description')}</label>
            <textarea 
              className="form-input" 
              rows={3}
              value={form.description} 
              onChange={e => setForm({ ...form, description: e.target.value })} 
              placeholder={t('groups.form.descriptionPlaceholder')}
            />
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>{t('common.cancel')}</button>
          <button className="btn btn-primary" onClick={submit} disabled={saving}>
            {saving ? t('common.saving') : t('groups.createGroup')}
          </button>
        </div>
      </div>
    </div>
  )
}

function AddMemberModal({ group, onClose, onSaved }: { group: Group; onClose: () => void; onSaved: () => void }) {
  const { t } = useTranslation()
  const [users, setUsers] = useState<User[]>([])
  const [selectedUser, setSelectedUser] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    usersApi.list({ page_size: 100 })
      .then(r => setUsers(r.data?.items || r.data || []))
      .catch(() => setError(t('groups.errors.usersLoadFailed')))
      .finally(() => setLoading(false))
  }, [])

  const submit = async () => {
    if (!selectedUser) { setError(t('groups.errors.userNotSelected')); return }
    setSaving(true)
    try {
      await groupsApi.addMember(group.id, selectedUser)
      onSaved()
    } catch (e: any) {
      setError(e.response?.data?.error?.message || t('groups.errors.addMemberFailed'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <span className="modal-title">{t('groups.addMemberTitle', { name: group.name })}</span>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          {error && <div className="alert alert-danger">{error}</div>}
          {loading ? (
            <div className="loading-state"><div className="spinner" /></div>
          ) : (
            <div className="form-group">
              <label className="form-label">{t('groups.selectUser')}</label>
              <select className="form-select" value={selectedUser} onChange={e => setSelectedUser(e.target.value)}>
                <option value="">-- {t('common.select')} --</option>
                {users.map(u => (
                  <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>
                ))}
              </select>
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>{t('common.cancel')}</button>
          <button className="btn btn-primary" onClick={submit} disabled={saving || loading}>
            {saving ? t('groups.adding') : t('groups.addMember')}
          </button>
        </div>
      </div>
    </div>
  )
}

export function GroupsPage() {
  const { t } = useTranslation()
  const [groups, setGroups] = useState<Group[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [selectedGroup, setSelectedGroup] = useState<Group | null>(null)

  const load = () => {
    setLoading(true)
    groupsApi.list({ page_size: 100 })
      .then(res => setGroups(Array.isArray(res.data) ? res.data : []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleDelete = async (id: string, name: string) => {
    if (window.confirm(t('groups.deleteConfirm', { name }))) {
      try {
        await groupsApi.delete(id)
        load()
      } catch (e: any) {
        alert(e.response?.data?.error?.message || t('groups.errors.deleteFailed'))
      }
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">{t('groups.title')}</h1>
          <p className="page-subtitle">{t('groups.pageSubtitle')}</p>
        </div>
        <div className="page-actions">
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
            {t('groups.newGroup')}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-state"><div className="spinner" /></div>
      ) : groups.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">👥</div>
          <div className="empty-state-title">{t('groups.noGroups')}</div>
          <div className="empty-state-desc">{t('groups.noGroupsDescExtended')}</div>
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>{t('groups.newGroup')}</button>
        </div>
      ) : (
        <div className="card" style={{ padding: 0 }}>
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t('groups.table.name')}</th>
                  <th>{t('groups.table.description')}</th>
                  <th>{t('groups.table.createdAt')}</th>
                  <th style={{ textAlign: 'right' }}>{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {groups.map(g => (
                  <tr key={g.id}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{g.name}</div>
                    </td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                      {g.description || '—'}
                    </td>
                    <td style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>
                      {new Date(g.created_at).toLocaleDateString('tr-TR')}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                        <button className="btn btn-secondary btn-sm" onClick={() => setSelectedGroup(g)}>
                          {t('groups.addMember')}
                        </button>
                        <button className="btn btn-ghost btn-danger btn-sm" onClick={() => handleDelete(g.id, g.name)}>
                          {t('common.delete')}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showCreate && (
        <CreateGroupModal 
          onClose={() => setShowCreate(false)} 
          onSaved={() => { setShowCreate(false); load() }} 
        />
      )}

      {selectedGroup && (
        <AddMemberModal 
          group={selectedGroup} 
          onClose={() => setSelectedGroup(null)} 
          onSaved={() => { setSelectedGroup(null); load() }} 
        />
      )}
    </div>
  )
}
