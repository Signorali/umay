import React, { useEffect, useState } from 'react'
import { notificationsApi } from '../api/umay'
import { NotificationIcon } from './Icons'

interface Notification {
  id: string
  notification_type: string
  title: string
  body?: string
  action_url?: string
}

export function OverdueModal() {
  const [overdueNotifs, setOverdueNotifs] = useState<Notification[]>([])
  const [open, setOpen] = useState(false)

  useEffect(() => {
    // Only check once per session load
    const checkOverdue = async () => {
      try {
        const res = await notificationsApi.list({ unread_only: true, page_size: 100 })
        const items: Notification[] = res.data?.items || []
        const overdue = items.filter(n => n.notification_type === 'PAYMENT_OVERDUE')
        
        if (overdue.length > 0) {
          setOverdueNotifs(overdue)
          setOpen(true)
        }
      } catch (err) {
        // ignore
      }
    }
    checkOverdue()
  }, [])

  if (!open || overdueNotifs.length === 0) return null

  return (
    <>
      <div 
        style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 9999,
          backdropFilter: 'blur(2px)'
        }}
      />
      <div 
        style={{
          position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
          background: 'var(--card-bg)', width: 440, maxWidth: '90vw', borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-lg)', zIndex: 10000, overflow: 'hidden'
        }}
      >
        <div style={{ background: '#ef4444', padding: 'var(--space-4)', color: '#fff', display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <NotificationIcon size={24} />
          <h2 style={{ margin: 0, fontSize: 'var(--font-size-lg)', fontWeight: 600 }}>Gecikmiş Ödeme Uyarısı</h2>
        </div>
        
        <div style={{ padding: 'var(--space-5)', maxHeight: '60vh', overflowY: 'auto' }}>
          <p style={{ margin: '0 0 var(--space-4) 0', color: 'var(--text-secondary)' }}>
            Eksik veya tarihi geçmiş ödemeleriniz bulunuyor. Lütfen aşağıdaki işlemleri tamamlayın.
          </p>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            {overdueNotifs.map(n => (
              <div key={n.id} style={{ padding: 'var(--space-3)', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)' }}>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>{n.title}</div>
                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-tertiary)', marginBottom: 8 }}>{n.body}</div>
                {n.action_url && (
                  <button 
                    className="btn btn-primary btn-sm"
                    onClick={() => {
                      setOpen(false)
                      window.location.href = n.action_url!
                    }}
                  >
                    Ödemeye Git
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
        
        <div style={{ padding: 'var(--space-4)', borderTop: '1px solid var(--border)', background: 'var(--bg-surface)', textAlign: 'right' }}>
          <button className="btn btn-ghost" onClick={() => setOpen(false)}>
            Daha Sonra Hatırlat
          </button>
        </div>
      </div>
    </>
  )
}
