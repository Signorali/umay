import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

const getCookie = (name: string) => document.cookie.split('; ').reduce((acc, p) => { const [k, v] = p.split('='); return k === name ? decodeURIComponent(v || '') : acc }, '')
const api = (url: string, opts?: RequestInit) => {
  const tenantId = getCookie('umay_tenant_id')
  return fetch(`/api/v1${url}`, {
    ...opts,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(tenantId ? { 'X-Tenant-Id': tenantId } : {}),
      ...(opts?.headers || {}),
    },
  }).then(r => r.ok ? r.json() : r.json().then(e => Promise.reject(e)))
}

interface Role {
  id: string; name: string; description: string | null; is_system: boolean; is_active: boolean
}

interface Permission {
  id: string; module: string; action: string; description: string | null
}

function groupByModule(perms: Permission[]) {
  const g: Record<string, Permission[]> = {}
  perms.forEach(p => {
    if (!g[p.module]) g[p.module] = []
    g[p.module].push(p)
  })
  return g
}

function CreateRoleModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const { t } = useTranslation()
  const [form, setForm] = useState({ name: '', description: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    if (!form.name) { setError(t('roles.modal.roleNameRequired')); return }
    setSaving(true)
    try {
      await api('/roles', { method: 'POST', body: JSON.stringify(form) })
      onSaved()
    } catch (e: any) {
      setError(e?.error?.message || t('roles.modal.createFailed'))
    } finally { setSaving(false) }
  }

  return (
    <div className="modal-backdrop" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <span className="modal-title">{t('roles.modal.createTitle')}</span>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          {error && <div className="alert alert-danger">{error}</div>}
          <div className="form-group">
            <label className="form-label">{t('roles.modal.roleName')} <span className="required">*</span></label>
            <input className="form-input" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder={t('roles.modal.roleNamePlaceholder')} />
          </div>
          <div className="form-group">
            <label className="form-label">{t('roles.modal.description')}</label>
            <input className="form-input" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder={t('roles.modal.descriptionPlaceholder')} />
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>{t('common.cancel')}</button>
          <button className="btn btn-primary" onClick={submit} disabled={saving}>
            {saving ? <><span className="spinner spinner-sm" /> {t('common.saving')}</> : t('roles.modal.create')}
          </button>
        </div>
      </div>
    </div>
  )
}

function PermissionMatrix({
  role,
  allPerms,
  rolePerms,
  onToggle,
}: {
  role: Role
  allPerms: Permission[]
  rolePerms: Permission[]
  onToggle: (permId: string, hasIt: boolean) => void
}) {
  const { t } = useTranslation()
  const grouped = groupByModule(allPerms)
  const assignedIds = new Set(rolePerms.map(p => p.id))
  const actions = ['view', 'create', 'update', 'delete', 'approve', 'export', 'manage', 'backup', 'restore', 'reset', 'assign']

  const moduleLabel = (key: string) => t(`roles.modules.${key}`, { defaultValue: key })
  const actionLabel = (key: string) => t(`roles.actions.${key}`, { defaultValue: key })

  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="data-table">
        <thead>
          <tr>
            <th>{t('common.module', { defaultValue: 'Modül' })}</th>
            {actions.map(a => (
              <th key={a} style={{ textAlign: 'center', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {actionLabel(a)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Object.entries(grouped).map(([module, perms]) => (
            <tr key={module}>
              <td style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600 }}>{moduleLabel(module)}</td>
              {actions.map(action => {
                const perm = perms.find(p => p.action === action)
                if (!perm) return <td key={action} style={{ textAlign: 'center' }}><span style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>—</span></td>
                const has = assignedIds.has(perm.id)
                return (
                  <td key={action} style={{ textAlign: 'center' }}>
                    <button
                      disabled={role.is_system}
                      onClick={() => onToggle(perm.id, has)}
                      style={{
                        width: 24, height: 24, borderRadius: 6, border: 'none', cursor: role.is_system ? 'not-allowed' : 'pointer',
                        background: has ? 'var(--accent)' : 'var(--bg-elevated)',
                        color: has ? '#fff' : 'var(--text-tertiary)',
                        fontSize: 13, fontWeight: 700, transition: 'all 0.15s',
                      }}
                    >
                      {has ? '✓' : '·'}
                    </button>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {role.is_system && (
        <div className="alert alert-info" style={{ marginTop: 'var(--space-3)', fontSize: 'var(--font-size-xs)' }}>
          {t('roles.systemRoleNote')}
        </div>
      )}
    </div>
  )
}

export function RolesPage() {
  const { t } = useTranslation()
  const [roles, setRoles] = useState<Role[]>([])
  const [allPerms, setAllPerms] = useState<Permission[]>([])
  const [rolePerms, setRolePerms] = useState<Permission[]>([])
  const [selectedRole, setSelectedRole] = useState<Role | null>(null)
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [rRes, pRes] = await Promise.all([
        api('/roles?page_size=50'),
        api('/permissions'),
      ])
      setRoles(rRes.items || [])
      setAllPerms(Array.isArray(pRes) ? pRes : (pRes.items || []))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const selectRole = async (role: Role) => {
    setSelectedRole(role)
    try {
      const res = await api(`/roles/${role.id}/permissions`)
      setRolePerms(Array.isArray(res) ? res : (res.items || []))
    } catch { setRolePerms([]) }
  }

  const togglePermission = async (permId: string, hasIt: boolean) => {
    if (!selectedRole) return
    try {
      if (hasIt) {
        await api(`/roles/${selectedRole.id}/permissions/${permId}`, { method: 'DELETE' })
      } else {
        await api(`/roles/${selectedRole.id}/permissions`, { method: 'POST', body: JSON.stringify({ permission_id: permId }) })
      }
      await selectRole(selectedRole)
    } catch { /* ignore */ }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">{t('roles.title')}</h1>
          <p className="page-subtitle">{t('roles.subtitle')}</p>
        </div>
        <div className="page-actions">
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>{t('roles.createRole')}</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 'var(--space-5)', alignItems: 'start' }}>
        <div className="card" style={{ padding: 0 }}>
          <div className="card-header">
            <div className="card-title">{t('roles.roleList')}</div>
          </div>
          {loading ? (
            <div className="loading-state" style={{ minHeight: 120 }}><div className="spinner" /></div>
          ) : (
            <div>
              {roles.map(role => {
                const isSelected = selectedRole?.id === role.id
                return (
                  <button
                    key={role.id}
                    onClick={() => selectRole(role)}
                    style={{
                      display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
                      width: '100%', padding: '14px 16px', border: 'none', textAlign: 'left',
                      background: isSelected ? 'var(--accent-soft)' : 'transparent',
                      borderBottom: '1px solid var(--border)',
                      borderLeft: isSelected ? '3px solid var(--accent)' : '3px solid transparent',
                      cursor: 'pointer', transition: 'background 0.15s',
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        fontWeight: 600,
                        fontSize: 'var(--font-size-base)',
                        color: isSelected ? 'var(--accent)' : 'var(--text-primary)',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>{role.name}</div>
                      {role.description && (
                        <div style={{
                          fontSize: 'var(--font-size-xs)',
                          color: isSelected ? 'var(--text-secondary)' : 'var(--text-tertiary)',
                          marginTop: 3,
                          lineHeight: 1.4,
                        }}>{role.description}</div>
                      )}
                      {(role.is_system || !role.is_active) && (
                        <div style={{ display: 'flex', gap: 4, marginTop: 6, flexWrap: 'wrap' }}>
                          {role.is_system && <span className="badge badge-accent" style={{ fontSize: 10 }}>{t('roles.system')}</span>}
                          {!role.is_active && <span className="badge badge-draft" style={{ fontSize: 10 }}>{t('roles.inactive')}</span>}
                        </div>
                      )}
                    </div>
                    {isSelected && (
                      <span style={{ marginLeft: 8, color: 'var(--accent)', fontSize: 16, flexShrink: 0 }}>›</span>
                    )}
                  </button>
                )
              })}
            </div>
          )}
        </div>

        <div className="card">
          {selectedRole ? (
            <>
              <div className="card-header">
                <div>
                  <div className="card-title">{selectedRole.name} — {t('roles.permissionMatrix')}</div>
                  <div className="card-subtitle">{t('roles.clickToToggle')}</div>
                </div>
              </div>
              <PermissionMatrix
                role={selectedRole}
                allPerms={allPerms}
                rolePerms={rolePerms}
                onToggle={togglePermission}
              />
            </>
          ) : (
            <div className="empty-state" style={{ padding: 'var(--space-10) 0' }}>
              <div className="empty-state-icon">🔒</div>
              <div className="empty-state-title">{t('roles.selectRole')}</div>
              <div className="empty-state-desc">{t('roles.selectRoleDesc')}</div>
            </div>
          )}
        </div>
      </div>

      {showCreate && (
        <CreateRoleModal onClose={() => setShowCreate(false)} onSaved={() => { setShowCreate(false); load() }} />
      )}
    </div>
  )
}
