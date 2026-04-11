# Umay — QNAP Kurulum

## Kopyalanacak Dosyalar

```
/share/CACHEDEV1_DATA/Container/umay/
├── backend/
├── frontend/
├── docker-compose.qnap.yml
├── .env.qnap
└── scripts/
    └── qnap_setup.sh
```

## Kurulum

```sh
ssh admin@<QNAP-IP>
cd /share/CACHEDEV1_DATA/Container/umay

# .env şifrelerini düzenle (zorunlu)
cp .env.qnap .env
vi .env   # CHANGE_ME değerlerini değiştir

# Kur ve başlat
sh scripts/qnap_setup.sh
```

## Portlar

| Servis   | Port |
|----------|------|
| Frontend | 1880 |
| Backend  | 18080 |

## Adresler

- Uygulama: `http://QNAP_IP:1880`
- API sağlık: `http://QNAP_IP:18080/api/v1/health`

## Notlar

- API çağrıları: frontend nginx → `/api/` → `backend:8000` (container içi proxy)
- `POSTGRES_PASSWORD` ve `APP_SECRET_KEY` mutlaka değiştirilmeli
- Worker devre dışı (docker-compose.qnap.yml içinde yorum satırı)
- Migration container açılışında otomatik çalışır
