import { useState, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { importApi } from '../api/umay'
import '../styles/import.css'
import { CreditCardIcon, BankIcon, DocumentsIcon, DownloadIcon, SearchIcon } from '../components/Icons'

type ImportMode = 'transactions' | 'accounts'
type Step = 'upload' | 'preview' | 'importing' | 'done'

interface RowError {
  row: number
  field: string
  message: string
}

interface PreviewData {
  total_rows: number
  valid_count: number
  error_count: number
  errors: RowError[]
  preview: Record<string, string>[]
}

export default function ImportPage() {
  const { t } = useTranslation()
  const [mode, setMode] = useState<ImportMode>('transactions')
  const [step, setStep] = useState<Step>('upload')
  const [file, setFile] = useState<File | null>(null)
  const [asDraft, setAsDraft] = useState(true)
  const [preview, setPreview] = useState<PreviewData | null>(null)
  const [result, setResult] = useState<{ created: number; skipped: number; errors: RowError[] } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) setFile(dropped)
  }, [])

  const handlePreview = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = mode === 'transactions'
        ? await importApi.previewTransactions(form)
        : await importApi.previewAccounts(form)
      setPreview(res.data)
      setStep('preview')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Önizleme alınamadı')
    } finally {
      setLoading(false)
    }
  }

  const handleImport = async () => {
    if (!file) return
    setLoading(true)
    setStep('importing')
    setError(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = mode === 'transactions'
        ? await importApi.importTransactions(form, asDraft)
        : await importApi.importAccounts(form)
      setResult(res.data)
      setStep('done')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'İçe aktarma başarısız oldu')
      setStep('preview')
    } finally {
      setLoading(false)
    }
  }

  const resetAll = () => {
    setStep('upload')
    setFile(null)
    setPreview(null)
    setResult(null)
    setError(null)
  }

  const previewColumns = preview?.preview[0] ? Object.keys(preview.preview[0]) : []

  return (
    <div className="import-page">
      {/* Header */}
      <div className="import-header">
        <div className="import-header-text">
          <h1>CSV İçe Aktarma</h1>
          <p>İşlem ve hesap verilerinizi CSV dosyasından hızlıca aktarın</p>
        </div>
        <div className="import-breadcrumb">
          {(['upload', 'preview', 'done'] as Step[]).map((s, i) => (
            <div key={s} className={`breadcrumb-step ${step === s ? 'active' : ''} ${
              (['upload', 'preview', 'done'] as Step[]).indexOf(step) > i ? 'done-step' : ''
            }`}>
              <span className="breadcrumb-num">{i + 1}</span>
              <span className="breadcrumb-label">
                {s === 'upload' ? 'Dosya' : s === 'preview' ? 'Önizleme' : 'Tamamlandı'}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Step: Upload */}
      {step === 'upload' && (
        <div className="import-upload-card">
          {/* Mode toggle */}
          <div className="mode-toggle">
            <button
              className={`mode-btn ${mode === 'transactions' ? 'active' : ''}`}
              onClick={() => setMode('transactions')}
            >
              <CreditCardIcon size={14} /> İşlemler
            </button>
            <button
              className={`mode-btn ${mode === 'accounts' ? 'active' : ''}`}
              onClick={() => setMode('accounts')}
            >
              <BankIcon size={14} /> Hesaplar
            </button>
          </div>

          {/* Drop zone */}
          <div
            className={`drop-zone ${dragOver ? 'drag-over' : ''} ${file ? 'has-file' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".csv,text/csv"
              style={{ display: 'none' }}
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            {file ? (
              <div className="file-selected">
                <span className="file-icon"><DocumentsIcon size={28} /></span>
                <div>
                  <div className="file-name">{file.name}</div>
                  <div className="file-size">{(file.size / 1024).toFixed(1)} KB</div>
                </div>
                <button className="remove-file" onClick={(e) => { e.stopPropagation(); setFile(null) }}>✕</button>
              </div>
            ) : (
              <div className="drop-hint">
                <span className="drop-icon"><DownloadIcon size={36} /></span>
                <div className="drop-text">
                  <strong>CSV dosyasını sürükleyin</strong> ya da tıklayın
                </div>
                <div className="drop-sub">UTF-8 veya UTF-8-BOM, max 10MB</div>
              </div>
            )}
          </div>

          {/* Column guide */}
          <div className="column-guide">
            <div className="guide-title">Beklenen sütunlar ({mode === 'transactions' ? 'işlemler' : 'hesaplar'})</div>
            <div className="guide-cols">
              {mode === 'transactions'
                ? ['tarih', 'tür', 'tutar', 'para birimi', 'kaynak hesap', 'hedef hesap', 'kategori', 'açıklama'].map(c => (
                    <span key={c} className="guide-col">{c}</span>
                  ))
                : ['ad', 'tür', 'para birimi', 'başlangıç bakiyesi', 'banka', 'iban', 'açıklama'].map(c => (
                    <span key={c} className="guide-col">{c}</span>
                  ))
              }
            </div>
          </div>

          {/* Draft option */}
          {mode === 'transactions' && (
            <label className="draft-toggle">
              <input
                type="checkbox"
                checked={asDraft}
                onChange={(e) => setAsDraft(e.target.checked)}
              />
              <span>İşlemleri <strong>taslak</strong> olarak oluştur (onay gerektirir)</span>
            </label>
          )}

          {error && <div className="import-error">{error}</div>}

          <button
            className="btn-primary import-btn"
            onClick={handlePreview}
            disabled={!file || loading}
          >
            {loading ? '⌛ Önizleniyor…' : <><SearchIcon size={13} /> Önizle</>}
          </button>
        </div>
      )}

      {/* Step: Preview */}
      {step === 'preview' && preview && (
        <div className="import-preview-card">
          {/* Stats */}
          <div className="preview-stats">
            <div className="stat-box total">
              <div className="stat-num">{preview.total_rows}</div>
              <div className="stat-label">Toplam Satır</div>
            </div>
            <div className="stat-box valid">
              <div className="stat-num">{preview.valid_count}</div>
              <div className="stat-label">Geçerli</div>
            </div>
            <div className="stat-box error">
              <div className="stat-num">{preview.error_count}</div>
              <div className="stat-label">Hatalı</div>
            </div>
          </div>

          {/* Errors */}
          {preview.errors.length > 0 && (
            <div className="preview-errors">
              <div className="errors-title">⚠️ Doğrulama Hataları</div>
              <div className="errors-list">
                {preview.errors.slice(0, 20).map((e, i) => (
                  <div key={i} className="error-row">
                    <span className="error-row-num">Satır {e.row}</span>
                    <span className="error-field">{e.field}</span>
                    <span className="error-msg">{e.message}</span>
                  </div>
                ))}
                {preview.errors.length > 20 && (
                  <div className="errors-more">+{preview.errors.length - 20} daha fazla hata</div>
                )}
              </div>
            </div>
          )}

          {/* Data preview table */}
          {preview.preview.length > 0 && (
            <div className="preview-table-wrap">
              <div className="preview-table-title">
                İlk {Math.min(preview.preview.length, 20)} geçerli satır
              </div>
              <div className="preview-table-scroll">
                <table className="preview-table">
                  <thead>
                    <tr>
                      {previewColumns.map(col => <th key={col}>{col}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.preview.slice(0, 20).map((row, i) => (
                      <tr key={i}>
                        {previewColumns.map(col => (
                          <td key={col}>{String(row[col] ?? '')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {error && <div className="import-error">{error}</div>}

          <div className="preview-actions">
            <button className="btn-secondary" onClick={resetAll}>← Geri</button>
            <button
              className="btn-primary"
              onClick={handleImport}
              disabled={preview.valid_count === 0 || loading}
            >
              {loading ? '⌛ Aktarılıyor…' : `✅ ${preview.valid_count} satırı aktar`}
            </button>
          </div>
        </div>
      )}

      {/* Step: Importing */}
      {step === 'importing' && (
        <div className="import-loading-card">
          <div className="loading-spinner large" />
          <h2>İçe aktarılıyor…</h2>
          <p>Lütfen bekleyin, veriler işleniyor.</p>
        </div>
      )}

      {/* Step: Done */}
      {step === 'done' && result && (
        <div className="import-done-card">
          <div className="done-icon">✅</div>
          <h2>İçe Aktarma Tamamlandı</h2>
          <div className="done-stats">
            <div className="done-stat green">
              <strong>{result.created}</strong> kayıt oluşturuldu
            </div>
            <div className="done-stat yellow">
              <strong>{result.skipped}</strong> satır atlandı
            </div>
          </div>
          {result.errors.length > 0 && (
            <div className="done-errors">
              <div className="errors-title">Atlanan Satırlar</div>
              {result.errors.slice(0, 5).map((e, i) => (
                <div key={i} className="error-row">
                  <span className="error-row-num">Satır {e.row}</span>
                  <span className="error-msg">{e.message}</span>
                </div>
              ))}
            </div>
          )}
          {mode === 'transactions' && asDraft && (
            <div className="done-note">
              💡 İşlemler <strong>Taslak</strong> olarak oluşturuldu. İşlemler sayfasından tek tek onaylayabilirsiniz.
            </div>
          )}
          <button className="btn-primary" onClick={resetAll}>Yeni İçe Aktarma</button>
        </div>
      )}
    </div>
  )
}
