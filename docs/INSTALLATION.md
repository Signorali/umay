# Kurulum Kılavuzu

## Hızlı Kurulum (Otomatik)

### Linux / QNAP / Docker ortamı için tek komut:

```bash
curl -fsSL https://raw.githubusercontent.com/Signorali/umay/main/install.sh | bash
```

Bu komut şunları yapar:
- Docker ve Docker Compose kontrolü
- Admin e-posta ve şifre istemi
- Güvenli .env dosyası oluşturur
- Docker imajlarını indirir
- Servisleri başlatır
- http://localhost:1880 adresinden erişim

---

## Manuel Kurulum

### Gereksinimler
- Docker 20.10+
- Docker Compose 2.0+
- Git
- 2 GB RAM
- 1 GB disk alanı

### Adımlar

**1. Repoyu klonla**
```bash
git clone https://github.com/Signorali/umay.git
cd umay
```

**2. Ortam dosyasını oluştur**
```bash
cp .env.example .env
# .env dosyasını düzenle
nano .env
```

**3. Servisleri başlat**
```bash
docker-compose up -d
```

**4. Uygulamaya eriş**
- Arayüz: http://localhost:1880
- API: http://localhost:8000/api/v1/docs

---

## QNAP NAS Kurulumu

1. QNAP'ta **Container Station** açık olmalı
2. SSH ile QNAP'a bağlan
3. Yukarıdaki otomatik kurulum komutunu çalıştır
4. QNAP IP adresi ile erişim: `http://[QNAP-IP]:1880`

---

## Sorun Giderme

### Servisler başlamıyor
```bash
docker-compose logs
docker-compose restart
```

### Veritabanı hatası
```bash
docker-compose down -v
docker-compose up -d
```

### Port çakışması
`.env` dosyasında `FRONTEND_PORT` ve `BACKEND_PORT` değerlerini değiştir.

### Backend hazır olmuyor
```bash
docker-compose logs backend
```

---

## Destek

- E-posta: alikoken@outlook.com
- GitHub Issues: https://github.com/Signorali/umay/issues
