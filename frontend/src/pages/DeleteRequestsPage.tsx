import React, { useState, useEffect, useCallback } from 'react'
import { deleteRequestsApi } from '../api/umay'
import { usePermissions } from '../hooks/usePermissions'

interface DeleteRequest {
  id: string
  requested_by_user_id: string
  target_table: string
  target_id: string
  target_label?: string
  reason?: string
  status: string
  reviewed_at?: string
  reject_reason?: string
  created_at: string
}

const STATUS_COLORS: Record<string, string> = {
  pending: '#f59e0b',
  approved: '#10b981',
  rejected: '#ef4444',
}

export function DeleteRequestsPage() {
  const { can } = usePermissions()
  const [requests, setRequests] = useState<DeleteRequest[]>([])
  const [total, setTotal] = useState(0)
  const [status, setStatus] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [rejectModal, setRejectModal] = useState<{ id: string } | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await deleteRequestsApi.list({ status: status || undefined })
      setRequests(res.data.items)
      setTotal(res.data.total)
    } catch {
      setError('Veriler yüklenirken hata oluştu')
    } finally {
      setLoading(false)
    }
  }, [status])

  useEffect(() => { load() }, [load])

  const handleApprove = async (id: string) => {
    try {
      await deleteRequestsApi.approve(id)
      load()
    } catch (e: any) {
      setError(e?.response?.data?.message || 'Onaylama başarısız')
    }
  }

  const handleReject = async () => {
    if (!rejectModal) return
    try {
      await deleteRequestsApi.reject(rejectModal.id, rejectReason)
      setRejectModal(null)
      setRejectReason('')
      load()
    } catch (e: any) {
      setError(e?.response?.data?.message || 'Reddetme başarısız')
    }
  }

  if (!can('delete_requests', 'review')) {
    return <div className="page-content"><p>Bu sayfaya erişim yetkiniz yok.</p></div>
  }

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Silme İstekleri</h1>
        <span style={{ color: 'var(--text-secondary)', fontSize: 14 }}>{total} istek</span>
      </div>

      {error && (
        <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 8, padding: '8px 12px', color: '#ef4444', marginBottom: 16 }}>
          {error}
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {['', 'pending', 'approved', 'rejected'].map(s => (
          <button
            key={s}
            className={`btn ${status === s ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: 13, padding: '4px 12px' }}
            onClick={() => setStatus(s)}
          >
            {s === '' ? 'Tümü' : s === 'pending' ? 'Bekleyen' : s === 'approved' ? 'Onaylanan' : 'Reddedilen'}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}><div className="spinner" /></div>
      ) : requests.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary)' }}>
          Silme isteği bulunamadı.
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                {['Tablo', 'Kayıt', 'Sebep', 'Durum', 'Tarih', 'İşlem'].map(h => (
                  <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: 12, color: 'var(--text-secondary)', fontWeight: 600 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {requests.map(req => (
                <tr key={req.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <td style={{ padding: '10px 16px', fontSize: 13 }}>{req.target_table}</td>
                  <td style={{ padding: '10px 16px', fontSize: 13 }}>
                    <div style={{ fontWeight: 500 }}>{req.target_label || '—'}</div>
                    <div style={{ color: 'var(--text-tertiary)', fontSize: 11 }}>{req.target_id.slice(0, 8)}...</div>
                  </td>
                  <td style={{ padding: '10px 16px', fontSize: 13, color: 'var(--text-secondary)', maxWidth: 200 }}>{req.reason || '—'}</td>
                  <td style={{ padding: '10px 16px' }}>
                    <span style={{
                      background: `${STATUS_COLORS[req.status]}20`,
                      color: STATUS_COLORS[req.status],
                      border: `1px solid ${STATUS_COLORS[req.status]}40`,
                      borderRadius: 6,
                      padding: '2px 8px',
                      fontSize: 12,
                      fontWeight: 600,
                    }}>
                      {req.status === 'pending' ? 'Bekliyor' : req.status === 'approved' ? 'Onaylandı' : 'Reddedildi'}
                    </span>
                  </td>
                  <td style={{ padding: '10px 16px', fontSize: 12, color: 'var(--text-secondary)' }}>
                    {new Date(req.created_at).toLocaleDateString('tr-TR')}
                  </td>
                  <td style={{ padding: '10px 16px' }}>
                    {req.status === 'pending' && (
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button
                          className="btn btn-primary"
                          style={{ fontSize: 12, padding: '4px 10px' }}
                          onClick={() => handleApprove(req.id)}
                        >
                          Onayla
                        </button>
                        <button
                          className="btn btn-danger"
                          style={{ fontSize: 12, padding: '4px 10px' }}
                          onClick={() => setRejectModal({ id: req.id })}
                        >
                          Reddet
                        </button>
                      </div>
                    )}
                    {req.status === 'rejected' && req.reject_reason && (
                      <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{req.reject_reason}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Reject modal */}
      {rejectModal && (
        <div style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,0,0,0.5)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 12, padding: 24, width: 360 }}>
            <h3 style={{ margin: '0 0 16px', fontSize: 16 }}>Silme İsteğini Reddet</h3>
            <div className="form-group" style={{ marginBottom: 16 }}>
              <label className="form-label">Reddetme Sebebi (opsiyonel)</label>
              <textarea
                className="form-input"
                rows={3}
                value={rejectReason}
                onChange={e => setRejectReason(e.target.value)}
                placeholder="Kullanıcıya gösterilecek açıklama..."
              />
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setRejectModal(null)}>İptal</button>
              <button className="btn btn-danger" onClick={handleReject}>Reddet</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
