# Umay Platform — Delivery Gate Checklist

## Başlatma Komutları

```bash
# 1. Docker ile başlat
docker-compose up --build -d

# 2. MFA migration uygula
docker exec umay_db psql -U umay -d umay < migration_0014_mfa.sql

# 3. Delivery gate testini çalıştır
pip install httpx
python scripts/umay_delivery_gate.py \
  --url http://localhost:8000 \
  --email admin@example.com \
  --password YOUR_PASSWORD
```

## Bu Session'da Tamamlananlar

### 1 — MFA / TOTP (cloud.md §14)
| Dosya | Açıklama |
|---|---|
| `backend/app/services/mfa_service.py` | TOTP secret, QR code, hashed backup codes |
| `backend/app/api/v1/endpoints/mfa.py` | status, setup, confirm, verify, disable, backup-codes |
| `migration_0014_mfa.sql` | 3 kolon: mfa_enabled, mfa_secret, mfa_backup_codes |
| `backend/app/models/user.py` | MFA alanları eklendi |
| `frontend/src/pages/MfaPage.tsx` | Tam MFA yönetim sayfası |
| `frontend/src/api/umay.ts` | authApi.mfa.* metodları |
| `frontend/src/App.tsx` | /security/mfa route |
| `backend/requirements.txt` | pyotp==2.9.0, qrcode[pil]==7.4.2 |

### 2 — Delivery Gate Script (cloud.md §28)
`scripts/umay_delivery_gate.py` — 8 kategori, 30+ kontrol, exit 0/1

### 3 — Phase 6 CSS (cloud.md §26-27)
`frontend/src/index.css` §23-30: MFA, precheck, skeleton, toast, glass card, progress bar

## Faz Tablosu

| Faz | Durum |
|-----|-------|
| Phase 1: Auth, groups, permissions, setup wizard | ✅ |
| Phase 2: Accounts, transactions, ledger | ✅ |
| Phase 3: Loans, assets, investments, reports | ✅ |
| Phase 4: Documents, OCR, calendar | ✅ |
| Phase 5: Demo, export, import, backup+encrypt | ✅ |
| Phase 6: Design system + MFA UI | ✅ |
| §14 MFA TOTP | ✅ |
| §28 Delivery Gate | ✅ |
