import React, { useCallback, useEffect, useRef, useState } from 'react'
import { authApi } from '../api/umay'

const mfaApi = authApi.mfa

// ── TOTP 6-digit input component ─────────────────────────────────────────────

function TotpInput({ onComplete }: { onComplete: (code: string) => void }) {
  const [digits, setDigits] = useState(['', '', '', '', '', ''])
  const inputs = useRef<(HTMLInputElement | null)[]>([])

  const handleChange = (idx: number, val: string) => {
    const d = val.replace(/\D/g, '').slice(-1)
    const next = [...digits]
    next[idx] = d
    setDigits(next)
    if (d && idx < 5) inputs.current[idx + 1]?.focus()
    if (next.every(x => x !== '')) onComplete(next.join(''))
  }

  const handleKey = (idx: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !digits[idx] && idx > 0) {
      inputs.current[idx - 1]?.focus()
    }
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    const text = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
    if (text.length === 6) {
      setDigits(text.split(''))
      onComplete(text)
    }
    e.preventDefault()
  }

  return (
    <div className="totp-input-wrap">
      {digits.map((d, i) => (
        <input
          key={i}
          ref={el => { inputs.current[i] = el }}
          className={`totp-input${d ? ' filled' : ''}`}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={d}
          onChange={e => handleChange(i, e.target.value)}
          onKeyDown={e => handleKey(i, e)}
          onPaste={handlePaste}
          autoFocus={i === 0}
        />
      ))}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

type Step = 'loading' | 'status' | 'setup-qr' | 'setup-confirm' | 'backup-shown' | 'disable' | 'regen'

interface MfaStatus {
  mfa_enabled: boolean
  backup_codes_remaining: number
}

interface SetupData {
  qr_data_url: string
  secret: string
  backup_codes: string[]
}

export function MfaPage() {
  const [step, setStep] = useState<Step>('loading')
  const [status, setStatus] = useState<MfaStatus | null>(null)
  const [setupData, setSetupData] = useState<SetupData | null>(null)
  const [backupCodes, setBackupCodes] = useState<string[]>([])
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [busy, setBusy] = useState(false)

  const loadStatus = useCallback(async () => {
    try {
      const r = await mfaApi.status()
      setStatus(r.data)
      setStep('status')
    } catch {
      setError('Could not load MFA status.')
      setStep('status')
    }
  }, [])

  useEffect(() => { loadStatus() }, [loadStatus])

  const handleSetup = async () => {
    setBusy(true); setError('')
    try {
      const r = await mfaApi.setup()
      setSetupData(r.data)
      setStep('setup-qr')
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Setup failed')
    }
    setBusy(false)
  }

  const handleConfirm = async (code: string) => {
    setBusy(true); setError('')
    try {
      await mfaApi.confirm(code)
      setBackupCodes(setupData?.backup_codes ?? [])
      setStep('backup-shown')
      setSuccess('MFA activated! Save your backup codes.')
    } catch {
      setError('Invalid code. Try again.')
    }
    setBusy(false)
  }

  const handleDisable = async (code: string) => {
    setBusy(true); setError('')
    try {
      await mfaApi.disable(code)
      setSuccess('MFA disabled.')
      await loadStatus()
    } catch {
      setError('Invalid code.')
    }
    setBusy(false)
  }

  const handleRegen = async (code: string) => {
    setBusy(true); setError('')
    try {
      const r = await mfaApi.regenBackupCodes(code)
      setBackupCodes(r.data.backup_codes)
      setStep('backup-shown')
      setSuccess('Backup codes regenerated.')
    } catch {
      setError('Invalid code.')
    }
    setBusy(false)
  }

  const copyBackupCodes = () => {
    navigator.clipboard.writeText(backupCodes.join('\n'))
    setSuccess('Copied to clipboard!')
  }

  // ── Renders ─────────────────────────────────────────────────────────────────

  if (step === 'loading') {
    return (
      <div className="loading-state">
        <div className="spinner" />
        <span>Loading MFA settings…</span>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Two-Factor Authentication</h1>
          <p className="page-subtitle">
            Protect your account with a TOTP authenticator app (Google Authenticator, Authy, etc.)
          </p>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: 'var(--space-4)' }}>
          {error}
        </div>
      )}
      {success && (
        <div className="alert alert-success" style={{ marginBottom: 'var(--space-4)' }}>
          {success}
        </div>
      )}

      {/* ── Status card ── */}
      {(step === 'status') && status && (
        <div className="mfa-setup-card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: 'var(--font-size-md)', marginBottom: 'var(--space-1)' }}>
                Authenticator App (TOTP)
              </div>
              <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
                {status.mfa_enabled
                  ? `MFA is active — ${status.backup_codes_remaining} backup code(s) remaining`
                  : 'MFA is not configured on this account'}
              </div>
            </div>
            <span className={`mfa-status-badge ${status.mfa_enabled ? 'enabled' : 'disabled'}`}>
              {status.mfa_enabled ? '● Active' : '○ Off'}
            </span>
          </div>

          {!status.mfa_enabled ? (
            <button className="btn btn-primary btn-lg" onClick={handleSetup} disabled={busy} style={{ width: '100%' }}>
              {busy ? <span className="spinner-sm spinner" /> : '🔐 Enable Two-Factor Authentication'}
            </button>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              <button className="btn btn-secondary" onClick={() => { setStep('regen'); setError(''); setSuccess('') }}>
                🔄 Regenerate Backup Codes
              </button>
              <button className="btn btn-danger" onClick={() => { setStep('disable'); setError(''); setSuccess('') }}>
                Disable MFA
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── QR screen ── */}
      {step === 'setup-qr' && setupData && (
        <div className="mfa-setup-card">
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontWeight: 700, fontSize: 'var(--font-size-lg)', marginBottom: 'var(--space-2)' }}>
              Step 1 — Scan QR Code
            </div>
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
              Open your authenticator app and scan the code below.
            </p>
          </div>

          <div className="mfa-qr-wrap">
            <div className="mfa-qr-frame">
              <img src={setupData.qr_data_url} alt="TOTP QR Code" />
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', textAlign: 'center' }}>
              Can't scan? Enter this key manually:
            </div>
            <div className="mfa-secret-display">{setupData.secret}</div>
          </div>

          <div style={{ textAlign: 'center' }}>
            <div style={{ fontWeight: 600, marginBottom: 'var(--space-3)' }}>Step 2 — Confirm</div>
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-4)' }}>
              Enter the 6-digit code from your authenticator app to activate MFA.
            </p>
            <TotpInput onComplete={handleConfirm} />
            {busy && <div className="spinner" style={{ margin: 'var(--space-4) auto 0' }} />}
          </div>
        </div>
      )}

      {/* ── Backup codes ── */}
      {step === 'backup-shown' && (
        <div className="mfa-setup-card">
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 32, marginBottom: 'var(--space-2)' }}>🔑</div>
            <div style={{ fontWeight: 700, fontSize: 'var(--font-size-lg)', marginBottom: 'var(--space-2)' }}>
              Save Your Backup Codes
            </div>
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
              Each code can only be used once. Store them securely — they won't be shown again.
            </p>
          </div>

          <div className="mfa-backup-codes">
            {backupCodes.map((code, i) => (
              <div key={i} className="mfa-backup-code">{code}</div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
            <button className="btn btn-secondary" style={{ flex: 1 }} onClick={copyBackupCodes}>
              📋 Copy codes
            </button>
            <button className="btn btn-primary" style={{ flex: 1 }} onClick={loadStatus}>
              Done
            </button>
          </div>
        </div>
      )}

      {/* ── Disable flow ── */}
      {step === 'disable' && (
        <div className="mfa-setup-card">
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 32, marginBottom: 'var(--space-2)' }}>⚠️</div>
            <div style={{ fontWeight: 700, fontSize: 'var(--font-size-lg)', marginBottom: 'var(--space-2)' }}>
              Disable Two-Factor Authentication
            </div>
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
              Enter your current TOTP code to confirm.
            </p>
          </div>
          <TotpInput onComplete={handleDisable} />
          {busy && <div className="spinner" style={{ margin: 'var(--space-2) auto' }} />}
          <button className="btn btn-ghost" onClick={loadStatus}>Cancel</button>
        </div>
      )}

      {/* ── Regenerate backup codes ── */}
      {step === 'regen' && (
        <div className="mfa-setup-card">
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 32, marginBottom: 'var(--space-2)' }}>🔄</div>
            <div style={{ fontWeight: 700, fontSize: 'var(--font-size-lg)', marginBottom: 'var(--space-2)' }}>
              Regenerate Backup Codes
            </div>
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
              All existing backup codes will be invalidated. Confirm with your TOTP code.
            </p>
          </div>
          <TotpInput onComplete={handleRegen} />
          {busy && <div className="spinner" style={{ margin: 'var(--space-2) auto' }} />}
          <button className="btn btn-ghost" onClick={loadStatus}>Cancel</button>
        </div>
      )}
    </div>
  )
}
