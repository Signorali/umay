import React, { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { usersApi, groupsApi } from '../api/umay'
import { SearchIcon, UsersIcon, LockIcon, DeleteIcon, CloseIcon } from '../components/Icons'

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

interface User {
  id: string; email: string; full_name: string; is_active: boolean
  is_superuser: boolean; is_tenant_admin: boolean; role_id: string | null
  last_login_at: string | null; created_at: string
}

interface Role {
  id: string; name: string; description: string | null; is_system: boolean; is_active: boolean
}

interface Group {
  id: string; name: string; description: string | null; is_active: boolean
}

function InviteModal({ roles, groups, onClose, onSaved }: {
  roles: Role[]; groups: Group[]; onClose: () => void; onSaved: () => void
}) {
  const [form, setForm] = useState({ email: '', full_name: '', password: '', role_id: '', is_tenant_admin: false })
  const [selectedGroups, setSelectedGroups] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const set = (k: string, v: any) => setForm(f => ({ ...f, [k]: v }))

  const toggleGroup = (id: string) =>
    setSelectedGroups(prev => prev.includes(id) ? prev.filter(g => g !== id) : [...prev, id])

  const submit = async () => {
    if (!form.email || !form.full_name || !form.password) { setError('Email, ad ve şifre zorunludur'); return }
    setSaving(true)
    try {
      const res = await api('/users', { method: 'POST', body: JSON.stringify({ ...form, role_id: form.role_id || null }) })
      // Add user to selected groups
      if (selectedGroups.length > 0) {
        await Promise.all(selectedGroups.map(gid => groupsApi.addMember(gid, res.id)))
      }
      onSaved()
    } catch (e: any) {
      setError(e?.error?.message || e?.detail || 'Kullanıcı oluşturulamadı')
    } finally { setSaving(false) }
  }

  const activeGroups = groups.filter(g => g.is_active)

  return (
    <div className="modal-backdrop" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{ maxWidth: 520 }}>
        <div className="modal-header">
          <span className="modal-title">Kullanıcı Davet Et</span>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={onClose}><CloseIcon size={14} /></button>
        </div>
        <div className="modal-body">
          {error && <div className="alert alert-danger">{error}</div>}
          <div className="form-group">
            <label className="form-label">Ad Soyad <span className="required">*</span></label>
            <input className="form-input" value={form.full_name} onChange={e => set('full_name', e.target.value)} placeholder="Ahmet Yılmaz" />
          </div>
          <div className="form-group">
            <label className="form-label">E-posta <span className="required">*</span></label>
            <input className="form-input" type="email" value={form.email} onChange={e => set('email', e.target.value)} placeholder="ahmet@sirket.com" />
          </div>
          <div className="form-group">
            <label className="form-label">Şifre <span className="required">*</span></label>
            <input className="form-input" type="password" value={form.password} onChange={e => set('password', e.target.value)} placeholder="En az 8 karakter" />
          </div>
          <div className="form-row cols-2">
            <div className="form-group">
              <label className="form-label">Rol</label>
              <select className="form-select" value={form.role_id} onChange={e => set('role_id', e.target.value)}>
                <option value="">Rol yok</option>
                {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
              </select>
            </div>
            <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end', paddingBottom: 2 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input type="checkbox" checked={form.is_tenant_admin} onChange={e => set('is_tenant_admin', e.target.checked)} />
                <span className="form-label" style={{ margin: 0 }}>Tenant Admin</span>
              </label>
            </div>
          </div>

          {activeGroups.length > 0 && (
            <div className="form-group">
              <label className="form-label">Gruplar</label>
              <div style={{
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                padding: '8px 12px',
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
                maxHeight: 160,
                overflowY: 'auto',
              }}>
                {activeGroups.map(g => (
                  <label key={g.id} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={selectedGroups.includes(g.id)}
                      onChange={() => toggleGroup(g.id)}
                    />
                    <span style={{ fontSize: 'var(--font-size-sm)' }}>{g.name}</span>
                    {g.description && (
                      <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>— {g.description}</span>
                    )}
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>İptal</button>
          <button className="btn btn-primary" onClick={submit} disabled={saving}>
            {saving ? <><span className="spinner spinner-sm" /> Kaydediliyor...</> : '+ Davet Et'}
          </button>
        </div>
      </div>
    </div>
  )
}

function ResetPasswordModal({ userId, userName, onClose }: { userId: string; userName: string; onClose: () => void }) {
  const [newPassword, setNewPassword] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)

  const submit = async () => {
    if (!newPassword || newPassword.length < 8) { setError('Şifre en az 8 karakter olmalıdır'); return }
    setSaving(true)
    try {
      await usersApi.adminResetPassword(userId, newPassword)
      setDone(true)
    } catch (e: any) {
      setError(e?.response?.data?.message || 'Şifre sıfırlama başarısız')
    } finally { setSaving(false) }
  }

  return (
    <div className="modal-backdrop" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <span className="modal-title">Şifre Sıfırla — {userName}</span>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={onClose}><CloseIcon size={14} /></button>
        </div>
        <div className="modal-body">
          {done ? (
            <div style={{ color: 'var(--income)', textAlign: 'center', padding: 16 }}>
              ✓ Şifre başarıyla sıfırlandı. Kullanıcı bir sonraki girişinde değiştirmek zorunda kalacak.
            </div>
          ) : (
            <>
              {error && <div className="alert alert-danger">{error}</div>}
              <div className="form-group">
                <label className="form-label">Yeni Şifre</label>
                <input
                  className="form-input"
                  type="password"
                  value={newPassword}
                  onChange={e => setNewPassword(e.target.value)}
                  placeholder="Min. 8 karakter"
                  autoFocus
                />
              </div>
            </>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>{done ? 'Kapat' : 'İptal'}</button>
          {!done && (
            <button className="btn btn-primary" onClick={submit} disabled={saving}>
              {saving ? 'Sıfırlanıyor...' : 'Şifreyi Sıfırla'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export function UsersPage() {
  const { user: me } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [groups, setGroups] = useState<Group[]>([])
  const [loading, setLoading] = useState(true)
  const [showInvite, setShowInvite] = useState(false)
  const [search, setSearch] = useState('')
  const [resetPasswordUser, setResetPasswordUser] = useState<{ id: string; full_name: string } | null>(null)

  const load = () => {
    setLoading(true)
    Promise.all([
      api('/users?page_size=100'),
      api('/roles?page_size=50'),
      api('/groups?page_size=100'),
    ]).then(([uRes, rRes, gRes]) => {
      setUsers(uRes.items || [])
      setRoles(rRes.items || [])
      setGroups(gRes.items || [])
    }).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const filtered = users.filter(u =>
    !search ||
    u.full_name.toLowerCase().includes(search.toLowerCase()) ||
    u.email.toLowerCase().includes(search.toLowerCase())
  )

  const roleMap = Object.fromEntries(roles.map(r => [r.id, r.name]))

  const toggleActive = async (u: User) => {
    await api(`/users/${u.id}/${u.is_active ? 'deactivate' : 'activate'}`, { method: 'POST' })
    load()
  }

  const deleteUser = async (u: User) => {
    if (!window.confirm(`"${u.full_name}" kullanıcısını silmek istediğinizden emin misiniz?\nBu işlem geri alınamaz.`)) return
    try {
      await api(`/users/${u.id}`, { method: 'DELETE' })
      load()
    } catch (e: any) {
      alert(e?.message || e?.detail || 'Kullanıcı silinemedi')
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Kullanıcılar</h1>
          <p className="page-subtitle">{users.length} kullanıcı</p>
        </div>
        <div className="page-actions">
          <button className="btn btn-primary" onClick={() => setShowInvite(true)}>+ Kullanıcı Davet Et</button>
        </div>
      </div>

      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 'var(--space-6)' }}>
        <div className="stat-card">
          <div className="stat-card-label">Toplam</div>
          <div className="stat-card-value">{users.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Aktif</div>
          <div className="stat-card-value" style={{ color: 'var(--income)' }}>{users.filter(u => u.is_active).length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Admin</div>
          <div className="stat-card-value" style={{ color: 'var(--accent)' }}>{users.filter(u => u.is_tenant_admin || u.is_superuser).length}</div>
        </div>
      </div>

      <div className="filter-bar">
        <div className="search-input-wrap">
          <span className="search-icon"><SearchIcon size={14} /></span>
          <input className="form-input" placeholder="Kullanıcı ara..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        {loading ? (
          <div className="loading-state"><div className="spinner" /></div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon"><UsersIcon size={48} /></div>
            <div className="empty-state-title">Kullanıcı bulunamadı</div>
          </div>
        ) : (
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Kullanıcı</th>
                  <th>Rol</th>
                  <th>Yetki</th>
                  <th>Son Giriş</th>
                  <th>Durum</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(u => (
                  <tr key={u.id}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <div className="avatar">{u.full_name.slice(0, 2).toUpperCase()}</div>
                        <div>
                          <div style={{ fontWeight: 500 }}>{u.full_name}</div>
                          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>{u.email}</div>
                        </div>
                      </div>
                    </td>
                    <td>{u.role_id ? <span className="badge badge-neutral">{roleMap[u.role_id] || 'Bilinmiyor'}</span> : <span style={{ color: 'var(--text-tertiary)' }}>—</span>}</td>
                    <td>
                      {u.is_superuser && <span className="badge badge-accent" style={{ marginRight: 4 }}>Superuser</span>}
                      {u.is_tenant_admin && <span className="badge badge-income">Admin</span>}
                      {!u.is_superuser && !u.is_tenant_admin && <span style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-size-xs)' }}>Standart</span>}
                    </td>
                    <td style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>
                      {u.last_login_at ? new Date(u.last_login_at).toLocaleDateString('tr-TR') : '—'}
                    </td>
                    <td>
                      <span className={`badge ${u.is_active ? 'badge-confirmed' : 'badge-draft'}`}>
                        {u.is_active ? 'Aktif' : 'Pasif'}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        {u.id !== me?.id && (
                          <button
                            className={`btn btn-sm ${u.is_active ? 'btn-danger' : 'btn-secondary'}`}
                            onClick={() => toggleActive(u)}
                          >
                            {u.is_active ? 'Devre Dışı' : 'Aktif Et'}
                          </button>
                        )}
                        <button
                          className="btn btn-sm btn-secondary"
                          onClick={() => setResetPasswordUser({ id: u.id, full_name: u.full_name })}
                          title="Şifre sıfırla"
                        >
                          <LockIcon size={13} />
                        </button>
                        {u.id !== me?.id && (
                          <button
                            className="btn btn-sm btn-danger"
                            onClick={() => deleteUser(u)}
                            title="Kullanıcıyı sil"
                          >
                            <DeleteIcon size={13} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showInvite && (
        <InviteModal
          roles={roles}
          groups={groups}
          onClose={() => setShowInvite(false)}
          onSaved={() => { setShowInvite(false); load() }}
        />
      )}

      {resetPasswordUser && (
        <ResetPasswordModal
          userId={resetPasswordUser.id}
          userName={resetPasswordUser.full_name}
          onClose={() => setResetPasswordUser(null)}
        />
      )}
    </div>
  )
}
