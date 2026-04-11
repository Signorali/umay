import React, { useEffect, useRef, useState } from 'react'
import { backupApi } from '../api/umay'
import { BackupIcon, SearchIcon, UploadIcon, DeleteIcon, LockIcon, CalendarIcon } from '../components/Icons'

interface BackupManifest {
  filename: string
  label?: string
  created_at: string
  created_by: string
  size_bytes: number
  checksum_sha256: string
  encrypted?: boolean
}

const fmtSize = (bytes: number) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}
const fmtDate = (iso: string) => new Date(iso).toLocaleString('tr-TR')

export function BackupPage() {
  const [backups, setBackups] = useState<BackupManifest[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [verifying, setVerifying] = useState<string | null>(null)
  const [verifyResult, setVerifyResult] = useState<Record<string, any>>({})
  const [confirmRestore, setConfirmRestore] = useState<string | null>(null)
  const [restoring, setRestoring] = useState<string | null>(null)
  const [downloading, setDownloading] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)

  // Upload restore
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploadRestoring, setUploadRestoring] = useState(false)
  const [confirmUpload, setConfirmUpload] = useState<File | null>(null)

  // Purge
  const [showPurge, setShowPurge] = useState(false)
  const [purgeFrom, setPurgeFrom] = useState('')
  const [purgeTo, setPurgeTo] = useState('')
  const [purging, setPurging] = useState(false)
  const [confirmPurge, setConfirmPurge] = useState(false)

  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => { loadBackups() }, [])

  const loadBackups = async () => {
    setLoading(true)
    try {
      const res = await backupApi.list()
      setBackups(Array.isArray(res.data) ? res.data : [])
    } catch { setError('Yedekler yüklenemedi.') }
    setLoading(false)
  }

  const alert = (msg: string, type: 'error' | 'success') => {
    if (type === 'error') { setError(msg); setSuccess('') }
    else { setSuccess(msg); setError('') }
    setTimeout(() => { setError(''); setSuccess('') }, 8000)
  }

  const createBackup = async () => {
    setCreating(true)
    try {
      await backupApi.create()
      alert('Yedek başarıyla oluşturuldu ve şifrelendi.', 'success')
      await loadBackups()
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Yedek oluşturulamadı.', 'error')
    }
    setCreating(false)
  }

  const verifyBackup = async (filename: string) => {
    setVerifying(filename)
    try {
      const res = await backupApi.verify(filename)
      setVerifyResult(prev => ({ ...prev, [filename]: res.data }))
    } catch (e: any) {
      alert('Doğrulama başarısız: ' + (e?.response?.data?.detail || 'Bilinmeyen hata'), 'error')
    }
    setVerifying(null)
  }

  const downloadBackup = async (filename: string) => {
    setDownloading(filename)
    try {
      const res = await backupApi.download(filename)
      const url = URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
    } catch (e: any) {
      alert('İndirme başarısız.', 'error')
    }
    setDownloading(null)
  }

  const restoreBackup = async (filename: string) => {
    setRestoring(filename)
    try {
      await backupApi.restore(filename)
      alert('Geri yükleme tamamlandı. Sayfayı yenileyin.', 'success')
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Geri yükleme başarısız.', 'error')
    }
    setRestoring(null)
    setConfirmRestore(null)
  }

  const deleteBackup = async (filename: string) => {
    setDeleting(filename)
    try {
      await backupApi.delete(filename)
      alert('Yedek silindi.', 'success')
      await loadBackups()
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Silme başarısız.', 'error')
    }
    setDeleting(null)
    setConfirmDelete(null)
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.name.endsWith('.sql') && !file.name.endsWith('.sql.enc')) {
      alert('Geçersiz dosya türü. Sadece .sql veya .sql.enc dosyaları kabul edilir.', 'error')
      return
    }
    setConfirmUpload(file)
  }

  const doUploadRestore = async () => {
    if (!confirmUpload) return
    setUploadRestoring(true)
    try {
      await backupApi.uploadRestore(confirmUpload)
      alert('Yedekten geri yükleme tamamlandı. Sayfayı yenileyin.', 'success')
      await loadBackups()
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Yükleme/geri yükleme başarısız.', 'error')
    }
    setUploadRestoring(false)
    setConfirmUpload(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const doPurge = async () => {
    if (!purgeFrom || !purgeTo) { alert('Tarih aralığı seçiniz.', 'error'); return }
    setPurging(true)
    try {
      const res = await backupApi.purgeTransactions(purgeFrom, purgeTo)
      alert(`${res.data.purged_count} işlem silindi (${purgeFrom} – ${purgeTo}).`, 'success')
      setShowPurge(false)
      setConfirmPurge(false)
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Silme işlemi başarısız.', 'error')
    }
    setPurging(false)
  }

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1000 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>Yedekleme Yönetimi</h1>
          <p style={{ margin: '6px 0 0', color: 'var(--text-secondary)', fontSize: 14 }}>
            Fernet şifreli yedekler — sadece bu uygulama açabilir
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button onClick={() => setShowPurge(true)} style={{
            padding: '10px 16px', borderRadius: 10, border: '1px solid #ef444466',
            background: '#ef444411', cursor: 'pointer', color: '#ef4444', fontWeight: 600, fontSize: 13,
            display: 'inline-flex', alignItems: 'center', gap: 6,
          }}>
            <DeleteIcon size={13} /> İşlem Temizle
          </button>
          <label style={{
            padding: '10px 16px', borderRadius: 10, border: '1px solid var(--border)',
            background: 'var(--surface-secondary)', cursor: 'pointer', color: 'var(--text-primary)', fontWeight: 600, fontSize: 13,
            display: 'inline-flex', alignItems: 'center', gap: 6,
          }}>
            <UploadIcon size={13} /> Yedek Yükle
            <input ref={fileInputRef} type="file" accept=".sql,.sql.enc" style={{ display: 'none' }} onChange={handleFileSelect} />
          </label>
          <button onClick={createBackup} disabled={creating} style={{
            padding: '10px 20px', borderRadius: 10, border: 'none', cursor: creating ? 'not-allowed' : 'pointer',
            background: creating ? 'var(--surface-secondary)' : 'var(--accent)', color: '#fff', fontWeight: 700, fontSize: 14,
          }}>
            {creating ? '⏳ Yedekleniyor...' : '+ Yeni Yedek'}
          </button>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div style={{ background: '#ef444422', border: '1px solid #ef4444', borderRadius: 10,
          padding: '12px 16px', color: '#ef4444', marginBottom: 16, fontSize: 14 }}>⚠️ {error}</div>
      )}
      {success && (
        <div style={{ background: '#22c55e22', border: '1px solid #22c55e', borderRadius: 10,
          padding: '12px 16px', color: '#22c55e', marginBottom: 16, fontSize: 14 }}>✅ {success}</div>
      )}

      {/* Warning */}
      <div style={{ background: '#f59e0b11', border: '1px solid #f59e0b44', borderRadius: 10,
        padding: '12px 16px', marginBottom: 24, fontSize: 13, color: '#f59e0b' }}>
        ⚠️ <strong>Uyarı:</strong> Geri yükleme işlemi geri alınamaz. Yedekler Fernet şifreli olup sadece
        bu uygulama (aynı şifreleme anahtarıyla) açabilir.
      </div>

      {/* Backup list */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 48, color: 'var(--text-secondary)' }}>Yükleniyor...</div>
      ) : backups.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 48, color: 'var(--text-secondary)' }}>
          <div style={{ fontSize: 48, marginBottom: 16, color: 'var(--text-tertiary)' }}><BackupIcon size={48} /></div>
          <div>Henüz yedek yok. Yukarıdan yeni yedek oluşturun.</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {backups.map((b, idx) => {
            const vr = verifyResult[b.filename]
            return (
              <div key={b.filename} style={{
                background: 'var(--surface)', border: '1px solid var(--border)',
                borderRadius: 14, padding: '18px 22px',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
                      {b.label || b.filename}
                      {idx === 0 && <span style={{ background: '#22c55e22', color: '#22c55e', fontSize: 11, padding: '2px 8px', borderRadius: 10, fontWeight: 700 }}>EN YENİ</span>}
                      {b.encrypted && <span style={{ background: '#6366f122', color: '#818cf8', fontSize: 11, padding: '2px 8px', borderRadius: 10, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 4 }}><LockIcon size={10} /> ŞİFRELİ</span>}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><CalendarIcon size={11} /> {fmtDate(b.created_at)}</span>
                      <span>{fmtSize(b.size_bytes)}</span>
                      <span style={{ fontFamily: 'monospace' }}>SHA256: {b.checksum_sha256.substring(0, 16)}...</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button onClick={() => verifyBackup(b.filename)} disabled={verifying === b.filename}
                      style={btnStyle()}>
                      {verifying === b.filename ? '...' : <><SearchIcon size={12} /> Doğrula</>}
                    </button>
                    <button onClick={() => downloadBackup(b.filename)} disabled={downloading === b.filename}
                      style={btnStyle()}>
                      {downloading === b.filename ? '...' : '⬇ İndir'}
                    </button>
                    <button onClick={() => setConfirmRestore(b.filename)}
                      style={btnStyle('#f59e0b', '#f59e0b22')}>
                      ↩ Geri Yükle
                    </button>
                    <button onClick={() => setConfirmDelete(b.filename)} disabled={deleting === b.filename}
                      style={btnStyle('#ef4444', '#ef444411')}>
                      <DeleteIcon size={13} />
                    </button>
                  </div>
                </div>
                {vr && (
                  <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 8, fontSize: 12,
                    background: vr.valid ? '#22c55e11' : '#ef444411',
                    border: `1px solid ${vr.valid ? '#22c55e44' : '#ef444444'}`,
                    color: vr.valid ? '#22c55e' : '#ef4444' }}>
                    {vr.valid ? '✅ Checksum geçerli — yedek bütünlüğü doğrulandı' : '❌ Checksum uyuşmuyor — dosya bozulmuş olabilir'}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Restore Confirm Modal */}
      {confirmRestore && (
        <ConfirmModal
          title="↩ Geri Yükleme Onayı"
          color="#f59e0b"
          message={<>
            <strong>{confirmRestore}</strong> yedeğini geri yüklemek üzeresiniz.<br />
            <span style={{ color: '#ef4444', fontWeight: 600 }}>Bu işlem GERİ ALINAMAZ. Mevcut tüm veriler yedekteki verilerle değiştirilecek.</span>
          </>}
          confirmLabel={restoring === confirmRestore ? 'Geri Yükleniyor...' : 'Evet, Geri Yükle'}
          disabled={restoring === confirmRestore}
          onConfirm={() => restoreBackup(confirmRestore)}
          onCancel={() => setConfirmRestore(null)}
        />
      )}

      {/* Delete Confirm Modal */}
      {confirmDelete && (
        <ConfirmModal
          title="Yedek Sil"
          color="#ef4444"
          message={<><strong>{confirmDelete}</strong> dosyası kalıcı olarak silinecek.</>}
          confirmLabel={deleting === confirmDelete ? 'Siliniyor...' : 'Evet, Sil'}
          disabled={deleting === confirmDelete}
          onConfirm={() => deleteBackup(confirmDelete)}
          onCancel={() => setConfirmDelete(null)}
        />
      )}

      {/* Upload Restore Confirm Modal */}
      {confirmUpload && (
        <ConfirmModal
          title="Yedekten Geri Yükle"
          color="#f59e0b"
          message={<>
            <strong>{confirmUpload.name}</strong> dosyasından geri yükleme yapılacak.<br />
            <span style={{ color: '#ef4444', fontWeight: 600 }}>Mevcut tüm veriler bu yedekteki verilerle değiştirilecek. GERİ ALINAMAZ.</span>
          </>}
          confirmLabel={uploadRestoring ? 'Geri Yükleniyor...' : 'Evet, Geri Yükle'}
          disabled={uploadRestoring}
          onConfirm={doUploadRestore}
          onCancel={() => { setConfirmUpload(null); if (fileInputRef.current) fileInputRef.current.value = '' }}
        />
      )}

      {/* Purge Modal */}
      {showPurge && (
        <div style={overlayStyle}>
          <div style={{ ...modalStyle, borderColor: '#ef4444', maxWidth: 480 }}>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#ef4444', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}><DeleteIcon size={16} /> Tarih Aralığında İşlem Temizle</div>
            <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 16 }}>
              Seçilen tarih aralığındaki tüm işlemler ve ledger kayıtları silinecek.
              Hesap bakiyeleri otomatik güncellenir.
            </p>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>Başlangıç *</label>
                <input type="date" value={purgeFrom} onChange={e => setPurgeFrom(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface-secondary)', color: 'var(--text-primary)', fontSize: 14 }} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>Bitiş *</label>
                <input type="date" value={purgeTo} onChange={e => setPurgeTo(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface-secondary)', color: 'var(--text-primary)', fontSize: 14 }} />
              </div>
            </div>
            {purgeFrom && purgeTo && !confirmPurge && (
              <div style={{ background: '#ef444411', border: '1px solid #ef444444', borderRadius: 8,
                padding: '10px 14px', marginBottom: 16, fontSize: 13, color: '#ef4444' }}>
                ⚠️ <strong>{purgeFrom}</strong> – <strong>{purgeTo}</strong> arasındaki tüm işlemler silinecek. Bu işlem geri alınamaz.
                <br /><label style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                  <input type="checkbox" checked={confirmPurge} onChange={e => setConfirmPurge(e.target.checked)} />
                  Anladım, onaylıyorum
                </label>
              </div>
            )}
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button onClick={() => { setShowPurge(false); setConfirmPurge(false) }} style={btnStyle()}>İptal</button>
              <button onClick={doPurge} disabled={purging || !confirmPurge || !purgeFrom || !purgeTo}
                style={{ ...btnStyle('#ef4444', '#ef444422'), opacity: (!confirmPurge || !purgeFrom || !purgeTo) ? 0.5 : 1 }}>
                {purging ? 'Siliniyor...' : 'Sil'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── helpers ── */
function btnStyle(color = 'var(--text-secondary)', bg = 'var(--surface-secondary)'): React.CSSProperties {
  return {
    padding: '7px 14px', borderRadius: 8,
    border: `1px solid ${color}44`, background: bg,
    cursor: 'pointer', fontSize: 12, fontWeight: 600, color,
  }
}

const overlayStyle: React.CSSProperties = {
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)',
  display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
}

const modalStyle: React.CSSProperties = {
  background: 'var(--surface)', borderRadius: 16, padding: 28,
  width: '90%', border: '2px solid var(--border)',
}

function ConfirmModal({ title, color, message, confirmLabel, disabled, onConfirm, onCancel }: {
  title: string; color: string; message: React.ReactNode
  confirmLabel: string; disabled: boolean
  onConfirm: () => void; onCancel: () => void
}) {
  return (
    <div style={overlayStyle}>
      <div style={{ ...modalStyle, borderColor: color, maxWidth: 460 }}>
        <div style={{ fontSize: 18, fontWeight: 800, color, marginBottom: 12 }}>{title}</div>
        <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, fontSize: 14, marginBottom: 24 }}>{message}</p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
          <button onClick={onCancel} style={btnStyle()}>İptal</button>
          <button onClick={onConfirm} disabled={disabled}
            style={{ padding: '10px 24px', borderRadius: 8, border: 'none', cursor: disabled ? 'not-allowed' : 'pointer',
              background: color, color: '#fff', fontWeight: 700, fontSize: 14, opacity: disabled ? 0.7 : 1 }}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

export default BackupPage
