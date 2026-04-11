import React, { useState } from 'react'
import { useAuth } from '../context/AuthContext'

const FEEDBACK_EMAIL = 'destek@umay.app'

const TYPES = [
  { value: 'bug',     label: '🐛 Hata Bildirimi' },
  { value: 'feature', label: '💡 Öneri' },
  { value: 'other',   label: '💬 Diğer' },
]

export function FeedbackButton() {
  const { user } = useAuth()
  const [open, setOpen]       = useState(false)
  const [type, setType]       = useState('bug')
  const [message, setMessage] = useState('')

  const handleSend = () => {
    if (!message.trim()) return

    const typeLabel = TYPES.find(t => t.value === type)?.label ?? type
    const page      = window.location.pathname
    const userInfo  = user ? `${user.full_name ?? ''} <${user.email}>` : 'Bilinmeyen kullanıcı'

    const subject = encodeURIComponent(`[Umay ${typeLabel}] ${page}`)
    const body    = encodeURIComponent(
      `Tür: ${typeLabel}\n` +
      `Sayfa: ${window.location.href}\n` +
      `Kullanıcı: ${userInfo}\n` +
      `\n` +
      `---\n` +
      `${message}\n`
    )

    window.location.href = `mailto:${FEEDBACK_EMAIL}?subject=${subject}&body=${body}`
    setOpen(false)
    setMessage('')
  }

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen(true)}
        title="Geri Bildirim Gönder"
        style={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          zIndex: 200,
          width: 44,
          height: 44,
          borderRadius: '50%',
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          color: 'var(--text-secondary)',
          fontSize: 18,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 2px 12px rgba(0,0,0,0.3)',
          transition: 'all 0.15s',
        }}
        onMouseEnter={e => {
          (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'
          ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)'
          ;(e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--accent)'
        }}
        onMouseLeave={e => {
          (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-elevated)'
          ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)'
          ;(e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border)'
        }}
      >
        ✉
      </button>

      {/* Modal */}
      {open && (
        <div
          className="modal-backdrop"
          onClick={() => setOpen(false)}
          style={{ zIndex: 300 }}
        >
          <div
            className="modal modal-sm"
            onClick={e => e.stopPropagation()}
          >
            <div className="modal-header">
              <span className="modal-title">Geri Bildirim Gönder</span>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setOpen(false)}>✕</button>
            </div>

            <div className="modal-body">
              <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-4)' }}>
                Mesajınız, mail istemcinizde hazır şekilde açılacak. Göndermek için sadece
                <strong> Gönder</strong>'e basmanız yeterli.
              </p>

              {/* Type selector */}
              <div className="form-group">
                <label className="form-label">Tür</label>
                <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                  {TYPES.map(t => (
                    <button
                      key={t.value}
                      className={`btn btn-sm ${type === t.value ? 'btn-primary' : 'btn-secondary'}`}
                      onClick={() => setType(t.value)}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Message */}
              <div className="form-group" style={{ marginTop: 'var(--space-3)' }}>
                <label className="form-label">Mesaj <span className="required">*</span></label>
                <textarea
                  className="form-input"
                  rows={5}
                  autoFocus
                  placeholder={
                    type === 'bug'
                      ? 'Hatayı açıklayın: ne yapıyordunuz, ne oldu, ne olmasını bekliyordunuz...'
                      : type === 'feature'
                      ? 'Önerinizi açıklayın...'
                      : 'Mesajınızı yazın...'
                  }
                  value={message}
                  onChange={e => setMessage(e.target.value)}
                />
              </div>

              {/* Context info */}
              <div style={{
                fontSize: 'var(--font-size-xs)',
                color: 'var(--text-tertiary)',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                padding: 'var(--space-2) var(--space-3)',
                marginTop: 'var(--space-2)',
              }}>
                📎 Otomatik eklenenler: sayfa ({window.location.pathname}),
                kullanıcı ({user?.email ?? '—'})
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setOpen(false)}>İptal</button>
              <button
                className="btn btn-primary"
                onClick={handleSend}
                disabled={!message.trim()}
              >
                ✉ Mail İstemcisinde Aç
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
