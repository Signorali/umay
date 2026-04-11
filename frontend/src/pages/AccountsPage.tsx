import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { accountsApi, groupsApi } from '../api/umay'
import { normalizeFormText } from '../utils/textNormalization'
import { usePermissions } from '../hooks/usePermissions'

import { CURRENCIES, getCurrencySymbol } from '../constants/currencies'
import { ACCOUNT_TYPE_ICONS, UsersIcon, CloseIcon } from '../components/Icons'

interface Account {
  id: string; name: string; account_type: string
  currency: string; current_balance: number; institution_name?: string; iban?: string; group_id?: string; group_name?: string; group_names?: string[]; is_active: boolean; allow_negative_balance?: boolean; is_own_group?: boolean
}


function AccountCard({ account, onEdit, onEditAccount, onDelete, canDelete, canUpdate }: { account: Account; onEdit: () => void; onEditAccount: (e: React.MouseEvent) => void; onDelete: (e: React.MouseEvent) => void; canDelete: boolean; canUpdate: boolean }) {
  const { t } = useTranslation()
  const isNeg = Number(account.current_balance) < 0
  const symbol = getCurrencySymbol(account.currency)
  const canSeeBalance = account.is_own_group !== false
  return (
    <div className="stat-card" style={{ cursor: canSeeBalance ? 'pointer' : 'default', opacity: canSeeBalance ? 1 : 0.75 }} onClick={canSeeBalance ? onEdit : undefined}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <span style={{ display: 'flex', opacity: 0.7 }}>{ACCOUNT_TYPE_ICONS[account.account_type] || ACCOUNT_TYPE_ICONS['BANK']}</span>
          <span className="badge badge-neutral" style={{ fontSize: 11 }}>
            {t(`accounts.types.${account.account_type}`, account.account_type)}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          {account.allow_negative_balance && <span className="badge badge-accent">KMH</span>}
          {!account.is_active && <span className="badge badge-draft">{t('common.passive')}</span>}
          {canSeeBalance && canUpdate && (
            <button className="btn btn-ghost btn-icon btn-sm" onClick={onEditAccount} title="Düzenle" style={{ color: 'var(--text-secondary)' }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </button>
          )}
          {canSeeBalance && canDelete && (
            <button className="btn btn-ghost btn-icon btn-sm" onClick={onDelete} style={{ color: 'var(--expense)' }} title={t('common.delete')}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
            </button>
          )}
        </div>
      </div>
      <div style={{ fontWeight: 600, fontSize: 'var(--font-size-md)', marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {account.name}
      </div>
      {account.institution_name && (
        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 4 }}>
          {account.institution_name}
        </div>
      )}
      {account.iban && (
        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)', marginBottom: 4, fontFamily: 'monospace' }}>
          {account.iban}
        </div>
      )}
      {((account.group_names && account.group_names.length > 0) || account.group_name) && (
        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', marginBottom: 'var(--space-3)', display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
          <UsersIcon />
          {(account.group_names && account.group_names.length > 0
            ? account.group_names
            : [account.group_name!]
          ).map((g, i) => (
            <span key={i} className="badge" style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>{g}</span>
          ))}
        </div>
      )}
      {canSeeBalance ? (
        <div className="stat-card-value" style={{ fontSize: 'var(--font-size-xl)', color: isNeg ? 'var(--expense)' : undefined }}>
          {isNeg ? '-' : ''}{symbol} {Math.abs(Number(account.current_balance)).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
        </div>
      ) : (
        <div className="stat-card-value" style={{ fontSize: 'var(--font-size-xl)', color: 'var(--text-tertiary)', letterSpacing: 2 }}>
          {symbol} ••••
        </div>
      )}
    </div>
  )
}

function EditAccountModal({ account, onClose, onSaved, groups }: { account: Account; onClose: () => void; onSaved: () => void; groups: any[] }) {
  const { t } = useTranslation()
  const [form, setForm] = useState({
    name: account.name,
    institution_name: account.institution_name || '',
    iban: account.iban || '',
    group_id: account.group_id || '',
    is_active: account.is_active,
    allow_negative_balance: account.allow_negative_balance ?? false,
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const set = (k: string, v: any) => setForm(f => ({ ...f, [k]: v }))

  const submit = async () => {
    if (!form.name.trim()) { setError(t('common.required')); return }
    setSaving(true)
    try {
      await accountsApi.update(account.id, {
        name: normalizeFormText(form.name),
        institution_name: form.institution_name.trim() ? normalizeFormText(form.institution_name) : undefined,
        iban: form.iban.trim().toUpperCase() || undefined,
        group_id: form.group_id || undefined,
        is_active: form.is_active,
        allow_negative_balance: form.allow_negative_balance,
      })
      onSaved()
    } catch (e: any) {
      setError(e.response?.data?.error?.message || t('common.error'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <span className="modal-title">Hesabı Düzenle</span>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={onClose}><CloseIcon size={14} /></button>
        </div>
        <div className="modal-body">
          {error && <div className="alert alert-danger">{error}</div>}
          <div className="form-group">
            <label className="form-label">{t('accounts.form.name')} <span className="required">*</span></label>
            <input className="form-input" value={form.name} onChange={e => set('name', e.target.value)} />
          </div>
          <div className="form-row cols-2">
            <div className="form-group">
              <label className="form-label">{t('accounts.form.institution')}</label>
              <input className="form-input" value={form.institution_name} onChange={e => set('institution_name', e.target.value)} placeholder="Örn: Halkbank" />
            </div>
            <div className="form-group">
              <label className="form-label">{t('accounts.form.iban')}</label>
              <input className="form-input" value={form.iban} onChange={e => set('iban', e.target.value)} placeholder="Örn: TR320010000000000000000000" />
            </div>
          </div>
          {groups.length > 0 && (
            <div className="form-group">
              <label className="form-label">{t('common.group')}</label>
              <select className="form-select" value={form.group_id} onChange={e => set('group_id', e.target.value)}>
                <option value="">-- {t('common.noGroup')} --</option>
                {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
              </select>
            </div>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 'var(--space-3)' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input type="checkbox" checked={form.is_active} onChange={e => set('is_active', e.target.checked)} />
              Aktif
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input type="checkbox" checked={form.allow_negative_balance} onChange={e => set('allow_negative_balance', e.target.checked)} />
              KMH Hesabı (Negatif bakiye alabilir)
            </label>
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>{t('common.cancel')}</button>
          <button className="btn btn-primary" onClick={submit} disabled={saving}>
            {saving ? <><span className="spinner spinner-sm" /> {t('common.saving')}</> : t('common.save')}
          </button>
        </div>
      </div>
    </div>
  )
}

function CreateAccountModal({ onClose, onSaved, groups }: { onClose: () => void; onSaved: () => void; groups: any[] }) {
  const { t } = useTranslation()
  const [form, setForm] = useState({
    name: '', account_type: 'BANK', currency: 'TRY',
    initial_balance: '0', institution_name: '', iban: '', group_id: groups.length > 0 ? groups[0].id : '',
    allow_negative_balance: false,
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }))

  const submit = async () => {
    if (!form.name.trim()) { setError(t('common.required')); return }
    if (!form.institution_name.trim()) { setError('Banka adı zorunludur'); return }
    if (!form.iban.trim()) { setError('IBAN zorunludur'); return }
    setSaving(true)
    try {
      await accountsApi.create({
        name: normalizeFormText(form.name),
        account_type: form.account_type,
        currency: form.currency,
        opening_balance: parseFloat(form.initial_balance) || 0,
        institution_name: normalizeFormText(form.institution_name),
        iban: form.iban.trim().toUpperCase(),
        group_id: form.group_id || undefined,
        allow_negative_balance: form.allow_negative_balance,
      })
      onSaved()
    } catch (e: any) {
      setError(e.response?.data?.error?.message || t('common.error'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <span className="modal-title">{t('accounts.newAccount')}</span>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={onClose}><CloseIcon size={14} /></button>
        </div>
        <div className="modal-body">
          {error && <div className="alert alert-danger">{error}</div>}
          <div className="form-row cols-2">
            <div className="form-group">
              <label className="form-label">{t('accounts.form.name')} <span className="required">*</span></label>
              <input className="form-input" value={form.name} onChange={e => set('name', e.target.value)} placeholder={t('accounts.form.namePlaceholder') as string} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('common.type')}</label>
              <select className="form-select" value={form.account_type} onChange={e => set('account_type', e.target.value)}>
               {['BANK', 'CASH', 'FX', 'CREDIT', 'CREDIT_CARD', 'INVESTMENT', 'SAVINGS', 'OTHER'].map(k => (
                 <option key={k} value={k}>{t(`accounts.types.${k}`, k)}</option>
               ))}
              </select>
            </div>
          </div>
          <div className="form-row cols-2">
            <div className="form-group">
              <label className="form-label">{t('common.currency')}</label>
              <select className="form-select" value={form.currency} onChange={e => set('currency', e.target.value)}>
                {CURRENCIES.map(c => (
                  <option key={c.code} value={c.code}>
                    {c.trName} ({c.symbol})
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">{t('accounts.form.openingBalance')}</label>
              <div className="amount-input-wrap">
                <span className="currency-prefix">{getCurrencySymbol(form.currency)}</span>
                <input type="number" className="form-input" value={form.initial_balance} onChange={e => set('initial_balance', e.target.value)} />
              </div>
            </div>
          </div>

          <div className="form-row cols-2">
            <div className="form-group">
              <label className="form-label">{t('accounts.form.institution')} <span className="required">*</span></label>
              <input className="form-input" value={form.institution_name} onChange={e => set('institution_name', e.target.value)} placeholder="Örn: Halkbank" />
            </div>
            <div className="form-group">
              <label className="form-label">{t('accounts.form.iban')} <span className="required">*</span></label>
              <input className="form-input" value={form.iban} onChange={e => set('iban', e.target.value)} placeholder="Örn: TR320010000000000000000000" />
            </div>
          </div>
          {groups.length > 0 && (
            <div className="form-group" style={{ marginTop: 'var(--space-3)' }}>
              <label className="form-label">{t('common.group')}</label>
              <select className="form-select" value={form.group_id} onChange={e => set('group_id', e.target.value)}>
                <option value="">-- {t('common.noGroup')} --</option>
                {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
              </select>
            </div>
          )}
          <div className="form-group" style={{ marginTop: 'var(--space-3)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <input
              type="checkbox"
              checked={form.allow_negative_balance}
              onChange={e => setForm(f => ({ ...f, allow_negative_balance: e.target.checked }))}
              id="allow_negative_balance"
            />
            <label htmlFor="allow_negative_balance" style={{ cursor: 'pointer', margin: 0 }}>
              KMH Hesabı (Negatif bakiye alabilir)
            </label>
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>{t('common.cancel')}</button>
          <button className="btn btn-primary" onClick={submit} disabled={saving}>
            {saving ? <><span className="spinner spinner-sm" /> {t('common.saving')}</> : t('common.create')}
          </button>
        </div>
      </div>
    </div>
  )
}

export function AccountsPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { can } = usePermissions()
  const [accounts, setAccounts] = useState<Account[]>([])
  const [groups, setGroups] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [editingAccount, setEditingAccount] = useState<Account | null>(null)
  const [selectedTab, setSelectedTab] = useState('BANK')

  const load = () => {
    setLoading(true)
    Promise.all([
      accountsApi.list({ skip: 0, limit: 100 }),
      groupsApi.list({ skip: 0, limit: 100 })
    ])
      .then(([a, g]) => {
        // Sistem hesaplarını ve kendi grubuna ait olmayanları gizle
        const visibleAccounts = a.data.filter((acc: Account) =>
          !acc.name.startsWith('__SYS_') && acc.is_own_group !== false
        )
        setAccounts(visibleAccounts)
        setGroups(g.data)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (window.confirm(t('accounts.deleteConfirm'))) {
      setLoading(true)
      accountsApi.delete(id)
        .then(() => load())
        .catch(err => {
          alert(err.response?.data?.error?.message || t('common.error'))
          setLoading(false)
        })
    }
  }

  const accountTypes = ['BANK', 'CASH', 'SAVINGS', 'INVESTMENT', 'CREDIT_CARD', 'CREDIT', 'FX', 'OTHER']
  const filteredAccounts = accounts.filter(a => a.account_type === selectedTab)

  const totalByType = accounts
    .filter(a => a.is_active !== false && a.is_own_group !== false) // Sadece aktif ve kendi grubuna ait olanları toplamda göster
    .reduce((acc, a) => {
      acc[a.currency] = (acc[a.currency] || 0) + Number(a.current_balance)
      return acc
    }, {} as Record<string, number>)

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">{t('accounts.title')}</h1>
          <p className="page-subtitle">{t('accounts.subtitle_one', { count: accounts.length })}</p>
        </div>
        <div className="page-actions">
          {can('accounts', 'create') && (
            <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
              {t('accounts.newAccount')}
            </button>
          )}
        </div>
      </div>

      {/* Summary row */}
      {Object.keys(totalByType).length > 0 && (
        <div className="stats-grid" style={{ marginBottom: 'var(--space-6)' }}>
          {Object.entries(totalByType).map(([cur, total]) => (
            <div key={cur} className="stat-card">
              <div className="stat-card-label">{t('common.total')} {cur}</div>
              <div className="stat-card-value" style={{ color: total < 0 ? 'var(--expense)' : undefined }}>
                {total < 0 ? '-' : ''}{getCurrencySymbol(cur)}{Math.abs(total).toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div style={{ marginBottom: 'var(--space-6)', display: 'flex', gap: 'var(--space-1)', flexWrap: 'wrap' }}>
        {accountTypes.map(type => {
          const count = accounts.filter(a => a.account_type === type).length
          const isActive = selectedTab === type
          return (
            <button
              key={type}
              className={`btn btn-sm ${isActive ? 'btn-primary' : 'btn-ghost'}`}
              style={{ whiteSpace: 'nowrap' }}
              onClick={() => setSelectedTab(type)}
            >
              <span style={{ display: 'inline-flex', marginRight: 6, verticalAlign: 'middle', opacity: 0.7 }}>{ACCOUNT_TYPE_ICONS[type]}</span>
              {t(`accounts.types.${type}`, type)}
              {count > 0 && <span style={{ marginLeft: 6, opacity: 0.6, fontSize: '0.8em' }}>({count})</span>}
            </button>
          )
        })}
      </div>

      {loading ? (
        <div className="loading-state"><div className="spinner" /></div>
      ) : filteredAccounts.length === 0 ? (
        <div className="empty-state" style={{ minHeight: '30vh' }}>
          <div className="empty-state-icon" style={{ width: 64, height: 64 }}>
            <span style={{ transform: 'scale(1.8)', display: 'flex' }}>{ACCOUNT_TYPE_ICONS[selectedTab]}</span>
          </div>
          <div className="empty-state-title">
            {t(`accounts.types.${selectedTab}`, selectedTab)} {t('common.not_found', 'bulunamadı')}
          </div>
          <div className="empty-state-desc">
            {t('accounts.no_accounts_in_category', 'Bu kategoride henüz bir hesabınız bulunmuyor.')}
          </div>
          {can('accounts', 'create') && (
            <button className="btn btn-secondary" onClick={() => setShowCreate(true)}>+ {t('accounts.newAccount')}</button>
          )}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 'var(--space-4)' }}>
          {filteredAccounts.map(a => (
            <AccountCard key={a.id} account={a} onEdit={() => navigate(`/accounts/${a.id}`)} onEditAccount={(e) => { e.stopPropagation(); setEditingAccount(a) }} onDelete={(e) => handleDelete(a.id, e)} canDelete={can('accounts', 'delete')} canUpdate={can('accounts', 'update')} />
          ))}
        </div>
      )}

      {showCreate && (
        <CreateAccountModal groups={groups} onClose={() => setShowCreate(false)} onSaved={() => { setShowCreate(false); load() }} />
      )}
      {editingAccount && (
        <EditAccountModal account={editingAccount} groups={groups} onClose={() => setEditingAccount(null)} onSaved={() => { setEditingAccount(null); load() }} />
      )}
    </div>
  )
}
