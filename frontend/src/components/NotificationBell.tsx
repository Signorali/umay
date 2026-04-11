import { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { notificationsApi } from '../api/umay'
import './NotificationBell.css'
import { NOTIFICATION_TYPE_ICONS, NotificationIcon, CloseIcon } from './Icons'

interface Notification {
  id: string
  notification_type: string
  priority: string
  title: string
  body?: string
  action_url?: string
  is_read: boolean
  created_at: string
}

interface NotifList {
  items: Notification[]
  total: number
  unread_count: number
}

const PRIORITY_COLORS: Record<string, string> = {
  URGENT: '#ef4444',
  HIGH: '#f97316',
  MEDIUM: '#6366f1',
  LOW: '#94a3b8',
}


function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'şimdi'
  if (m < 60) return `${m}dk önce`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}sa önce`
  return `${Math.floor(h / 24)}g önce`
}

export function NotificationBell() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [data, setData] = useState<NotifList | null>(null)
  const [loading, setLoading] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)
  const panelRef = useRef<HTMLDivElement>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchCount = useCallback(async () => {
    try {
      const res = await notificationsApi.getCount()
      setUnreadCount(res.data.count)
    } catch {}
  }, [])

  const fetchNotifications = useCallback(async () => {
    setLoading(true)
    try {
      const res = await notificationsApi.list({ page_size: 20 })
      setData(res.data)
      setUnreadCount(res.data.unread_count)
    } catch {} finally {
      setLoading(false)
    }
  }, [])

  // Poll badge count every 60s
  useEffect(() => {
    fetchCount()
    pollRef.current = setInterval(fetchCount, 60000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [fetchCount])

  // Load when opening panel
  useEffect(() => {
    if (open) fetchNotifications()
  }, [open, fetchNotifications])

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    if (open) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  const handleMarkRead = async (id: string) => {
    try {
      await notificationsApi.markRead(id)
      setData(prev => prev ? {
        ...prev,
        unread_count: Math.max(0, prev.unread_count - 1),
        items: prev.items.map(n => n.id === id ? { ...n, is_read: true } : n),
      } : null)
      setUnreadCount(c => Math.max(0, c - 1))
    } catch {}
  }

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead()
      setData(prev => prev ? {
        ...prev,
        unread_count: 0,
        items: prev.items.map(n => ({ ...n, is_read: true })),
      } : null)
      setUnreadCount(0)
    } catch {}
  }

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await notificationsApi.delete(id)
      setData(prev => prev ? {
        ...prev,
        total: prev.total - 1,
        items: prev.items.filter(n => n.id !== id),
        unread_count: prev.items.find(n => n.id === id && !n.is_read) 
          ? prev.unread_count - 1 : prev.unread_count,
      } : null)
    } catch {}
  }

  return (
    <div className="notif-bell-wrapper" ref={panelRef}>
      {/* Bell button */}
      <button
        className={`notif-bell-btn ${open ? 'active' : ''}`}
        onClick={() => setOpen(v => !v)}
        aria-label="Bildirimler"
      >
        <span className="notif-bell-icon"><NotificationIcon size={18} /></span>
        {unreadCount > 0 && (
          <span className="notif-badge">{unreadCount > 99 ? '99+' : unreadCount}</span>
        )}
      </button>

      {/* Panel */}
      {open && (
        <div className="notif-panel">
          {/* Header */}
          <div className="notif-panel-header">
            <div className="notif-panel-title">
              Bildirimler
              {data && data.unread_count > 0 && (
                <span className="notif-unread-pill">{data.unread_count} okunmamış</span>
              )}
            </div>
            {data && data.unread_count > 0 && (
              <button className="notif-mark-all" onClick={handleMarkAllRead}>
                Tümünü oku
              </button>
            )}
          </div>

          {/* Content */}
          <div className="notif-panel-body">
            {loading && (
              <div className="notif-loading">
                <div className="loading-spinner" />
              </div>
            )}

            {!loading && data && data.items.length === 0 && (
              <div className="notif-empty">
                <span><NotificationIcon size={24} /></span>
                <p>Yeni bildiriminiz yok</p>
              </div>
            )}

            {!loading && data && data.items.map(notif => (
              <div
                key={notif.id}
                className={`notif-item ${notif.is_read ? 'read' : 'unread'}`}
                onClick={() => {
                  if (!notif.is_read) handleMarkRead(notif.id)
                  if (notif.action_url) window.location.href = notif.action_url
                }}
              >
                {/* Priority stripe */}
                <div
                  className="notif-priority-stripe"
                  style={{ background: PRIORITY_COLORS[notif.priority] }}
                />

                <div className="notif-item-icon">
                  {NOTIFICATION_TYPE_ICONS[notif.notification_type] || <NotificationIcon />}
                </div>

                <div className="notif-item-content">
                  <div className="notif-item-title">{notif.title}</div>
                  {notif.body && (
                    <div className="notif-item-body">{notif.body}</div>
                  )}
                  <div className="notif-item-time">{timeAgo(notif.created_at)}</div>
                </div>

                <div className="notif-item-actions">
                  {!notif.is_read && (
                    <div className="notif-unread-dot" title="Okunmamış" />
                  )}
                  <button
                    className="notif-delete-btn"
                    onClick={(e) => handleDelete(notif.id, e)}
                    title="Sil"
                  >
                    <CloseIcon size={12} />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Footer */}
          {data && data.total > 20 && (
            <div className="notif-panel-footer">
              <a href="/notifications" className="notif-see-all">
                Tüm bildirimleri gör ({data.total})
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
