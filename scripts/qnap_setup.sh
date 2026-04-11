#!/bin/sh
set -e

DATA_ROOT="/share/CACHEDEV1_DATA/Container/umay/data"

echo "==> [1/6] Dizinler oluşturuluyor..."
mkdir -p "$DATA_ROOT/postgres"
mkdir -p "$DATA_ROOT/redis"
mkdir -p "$DATA_ROOT/storage"
mkdir -p "$DATA_ROOT/backups"
chown -R 999:999 "$DATA_ROOT/postgres" 2>/dev/null || true

echo "==> [2/6] .env kontrol ediliyor..."
if [ ! -f ".env.qnap" ]; then
    echo "HATA: .env.qnap dosyası bulunamadı."
    echo "      Bu scripti proje kök dizininden çalıştırın."
    exit 1
fi
if [ ! -f ".env" ]; then
    cp .env.qnap .env
    echo "    .env.qnap -> .env kopyalandı."
    echo "    UYARI: .env içindeki CHANGE_ME değerlerini değiştirin!"
fi

echo "==> [3/6] Image'lar build ediliyor (--no-cache, temiz build)..."
docker compose -f docker-compose.qnap.yml build --no-cache

echo "==> [4/6] Servisler başlatılıyor..."
docker compose -f docker-compose.qnap.yml up -d

echo "==> [5/6] 10 saniye bekleniyor..."
sleep 10

echo "==> [6/6] Sağlık kontrolleri..."

BACKEND_UP=0
FRONTEND_UP=0

result=$(curl -sf http://127.0.0.1:18080/api/v1/health 2>/dev/null) && {
    echo "    Backend  OK: $result"
    BACKEND_UP=1
} || {
    echo "    Backend  HENÜZ HAZIR DEĞİL - son 20 log satırı:"
    docker logs umay_backend --tail=20 2>&1 | sed 's/^/      /'
}

status_line=$(curl -sI http://127.0.0.1:1880 2>/dev/null | head -1)
case "$status_line" in
    *200*|*301*|*302*)
        echo "    Frontend OK ($status_line)"
        FRONTEND_UP=1
        ;;
    *)
        echo "    Frontend HENÜZ HAZIR DEĞİL"
        docker logs umay_frontend --tail=10 2>&1 | sed 's/^/      /'
        ;;
esac

echo ""
echo "Container durumları:"
docker compose -f docker-compose.qnap.yml ps

echo ""
if [ "$BACKEND_UP" = "1" ] && [ "$FRONTEND_UP" = "1" ]; then
    NAS_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '/src/{print $7}' | head -1)
    NAS_IP=${NAS_IP:-"<NAS-IP>"}
    echo "Kurulum tamamlandı!"
    echo "  Frontend : http://$NAS_IP:1880"
    echo "  Backend  : http://$NAS_IP:18080/api/v1/health"
else
    echo "Bazı servisler henüz hazır değil. Backend 30-60 saniye içinde hazır olabilir."
    echo "Takip: docker compose -f docker-compose.qnap.yml logs -f"
fi
