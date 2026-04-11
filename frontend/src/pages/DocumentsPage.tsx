import React, { useEffect, useRef, useState } from 'react'
import { documentsApi } from '../api/umay'
import { ReportsIcon, MarketIcon, DocumentsIcon, EditIcon, CloseIcon, UploadIcon } from '../components/Icons'

function ExtIcon({ ext, size = 20 }: { ext: string; size?: number }) {
  if (['jpg', 'jpeg', 'png', 'gif'].includes(ext)) {
    return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
  }
  if (['csv', 'xlsx', 'xls'].includes(ext)) return <MarketIcon size={size} />
  if (['doc', 'docx', 'txt'].includes(ext)) return <EditIcon size={size} />
  if (ext === 'pdf') return <ReportsIcon size={size} />
  return <DocumentsIcon size={size} />
}

const EXT_BG: Record<string, string> = {
  pdf: '#ef444420', jpg: '#6366f120', jpeg: '#6366f120', png: '#6366f120',
  csv: '#22c55e20', xlsx: '#22c55e20',
}

type ViewMode = 'grid' | 'list'

function formatSize(bytes: number) {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

export function DocumentsPage() {
  const [docs, setDocs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [filterExt, setFilterExt] = useState('ALL')
  const [progress, setProgress] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const load = () => {
    setLoading(true)
    documentsApi.list({ skip: 0, limit: 200 })
      .then(r => setDocs(r.data)).catch(() => {}).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    setUploading(true)
    setProgress(0)
    let uploaded = 0
    for (const file of Array.from(files)) {
      const formData = new FormData()
      formData.append('file', file)
      await documentsApi.upload(formData).catch(err => {
        alert(`Failed to upload ${file.name}: ${err?.response?.data?.detail || 'Upload error'}`)
      })
      uploaded++
      setProgress(Math.round((uploaded / files.length) * 100))
    }
    setUploading(false)
    setProgress(0)
    if (fileInputRef.current) fileInputRef.current.value = ''
    load()
  }

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete "${name}"?`)) return
    await documentsApi.delete(id).catch(() => {})
    setDocs(prev => prev.filter(d => d.id !== id))
  }

  const allExts = Array.from(new Set(docs.map(d => (d.filename || d.original_filename || '').split('.').pop()?.toLowerCase() || 'other')))
  const filtered = filterExt === 'ALL' ? docs : docs.filter(d => {
    const ext = (d.filename || d.original_filename || '').split('.').pop()?.toLowerCase() || 'other'
    return ext === filterExt
  })

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Documents</h1>
          <p className="page-subtitle">{docs.length} files stored</p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
          <button
            className="btn btn-secondary"
            onClick={() => setViewMode(v => v === 'grid' ? 'list' : 'grid')}
          >
            {viewMode === 'grid' ? 'List' : 'Grid'}
          </button>
          <label className="btn btn-primary" htmlFor="doc-upload" style={{ cursor: 'pointer', margin: 0 }}>
            {uploading ? `Uploading ${progress}%...` : <><UploadIcon size={13} /> Upload</>}
          </label>
          <input
            id="doc-upload"
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.jpg,.jpeg,.png,.csv,.xlsx,.xls,.doc,.docx,.txt"
            onChange={handleUpload}
            style={{ display: 'none' }}
          />
        </div>
      </div>

      {/* Upload progress bar */}
      {uploading && (
        <div style={{ marginBottom: 'var(--space-4)', height: 4, background: 'var(--bg-elevated)', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${progress}%`, background: 'var(--accent)', transition: 'width 0.3s' }} />
        </div>
      )}

      {/* Type filters */}
      {docs.length > 0 && (
        <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', marginBottom: 'var(--space-4)' }}>
          <button
            className={`btn btn-sm ${filterExt === 'ALL' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilterExt('ALL')}
          >
            All ({docs.length})
          </button>
          {allExts.map(ext => (
            <button
              key={ext}
              className={`btn btn-sm ${filterExt === ext ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setFilterExt(ext)}
            >
              <ExtIcon ext={ext} size={13} /> .{ext} ({docs.filter(d => (d.filename || d.original_filename || '').split('.').pop()?.toLowerCase() === ext).length})
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="loading-state"><div className="spinner" /></div>
      ) : docs.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><DocumentsIcon size={48} /></div>
          <div className="empty-state-title">No documents uploaded</div>
          <div className="empty-state-desc">Upload PDFs, images, and spreadsheets to link them to financial records.</div>
          <label className="btn btn-primary" htmlFor="doc-upload" style={{ cursor: 'pointer', display: 'inline-block' }}>
            <UploadIcon size={13} /> Upload Document
          </label>
        </div>
      ) : viewMode === 'grid' ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 'var(--space-4)' }}>
          {filtered.map((d: any) => {
            const ext = (d.filename || d.original_filename || '').split('.').pop()?.toLowerCase() || 'file'
            const name = d.original_filename || d.filename || 'unnamed'
            return (
              <div key={d.id} className="card card-sm" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', position: 'relative' }}>
                <button
                  className="btn btn-ghost btn-sm"
                  style={{ position: 'absolute', top: 4, right: 4, color: 'var(--danger)', padding: '2px 6px', fontSize: 10 }}
                  onClick={() => handleDelete(d.id, name)}
                ><CloseIcon size={12} /></button>
                <div style={{
                  width: 48, height: 48, borderRadius: 'var(--radius-md)',
                  background: EXT_BG[ext] || 'var(--bg-elevated)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  <ExtIcon ext={ext} size={24} />
                </div>
                <div style={{ overflow: 'hidden' }}>
                  <div style={{
                    fontWeight: 500, fontSize: 'var(--font-size-xs)',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }} title={name}>{name}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginTop: 2 }}>
                    {formatSize(d.file_size_bytes)}
                  </div>
                  {d.created_at && (
                    <div style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>
                      {new Date(d.created_at).toLocaleDateString('tr-TR')}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="card" style={{ padding: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th style={{ textAlign: 'right' }}>Size</th>
                <th>Uploaded</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((d: any) => {
                const ext = (d.filename || d.original_filename || '').split('.').pop()?.toLowerCase() || 'file'
                const name = d.original_filename || d.filename || 'unnamed'
                return (
                  <tr key={d.id}>
                    <td style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                      <ExtIcon ext={ext} size={16} />
                      <span style={{ fontWeight: 500, fontSize: 'var(--font-size-sm)' }}>{name}</span>
                    </td>
                    <td><span className="badge badge-neutral">.{ext}</span></td>
                    <td className="text-right" style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)' }}>
                      {formatSize(d.file_size_bytes)}
                    </td>
                    <td style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>
                      {d.created_at ? new Date(d.created_at).toLocaleDateString('tr-TR') : '—'}
                    </td>
                    <td>
                      <button
                        className="btn btn-ghost btn-sm"
                        style={{ color: 'var(--danger)' }}
                        onClick={() => handleDelete(d.id, name)}
                      ><CloseIcon size={13} /> Delete</button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
