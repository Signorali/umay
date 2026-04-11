#!/usr/bin/env sh
# ──────────────────────────────────────────────────────────────────────────────
# Umay Güncelleme Scripti — Müşteri QNAP'ında çalıştırılır
#
# Kullanım:
#   cd /share/CACHEDEV1_DATA/Container/umay
#   sh update.sh
#
# Yapılanlar:
#   1. Update server'dan lisansı doğrula
#   2. Yeni versiyon var mı kontrol et
#   3. Registry'ye giriş yap (lisanstan dönen token ile)
#   4. Yeni imajları çek
#   5. Database migration uygula
#   6. Servisleri yeniden başlat
# ──────────────────────────────────────────────────────────────────────────────

set -e

UMAY_DIR="/share/CACHEDEV1_DATA/Container/umay"
UMAY_UPDATE_DIR="/share/CACHEDEV1_DATA/Container/umay-update"
UPDATE_SERVER="https://koken.myqnapcloud.com/update"
COMPOSE_FILE="${UMAY_DIR}/docker-compose.yml"
ENV_FILE="${UMAY_DIR}/.env"
LICENSE_FILE="${UMAY_DIR}/data/storage/license.key"

# Renk çıktıları
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { printf "${GREEN}▶ %s${NC}\n" "$1"; }
warn()    { printf "${YELLOW}⚠ %s${NC}\n" "$1"; }
error()   { printf "${RED}✗ %s${NC}\n" "$1"; exit 1; }

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Umay Güncelleme Aracı"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Lisans dosyasını kontrol et ──────────────────────────────────────────
if [ ! -f "$LICENSE_FILE" ]; then
  error "Lisans dosyası bulunamadı: ${LICENSE_FILE}"
fi
LICENSE_KEY=$(cat "$LICENSE_FILE" | tr -d '[:space:]')
info "Lisans dosyası okundu"

# ── 2. Mevcut versiyonu öğren ─────────────────────────────────────────────
CURRENT_VERSION="0.0.0"
if [ -f "${UMAY_DIR}/version.txt" ]; then
  CURRENT_VERSION=$(cat "${UMAY_DIR}/version.txt" | tr -d '[:space:]')
fi
info "Mevcut versiyon: ${CURRENT_VERSION}"

# ── 3. Update server'a lisansı doğrulat ───────────────────────────────────
info "Update server bağlantısı kuruluyor..."
RESPONSE=$(curl -sf -X POST "${UPDATE_SERVER}/check" \
  -H "Content-Type: application/json" \
  -d "{\"license_key\": \"${LICENSE_KEY}\", \"current_version\": \"${CURRENT_VERSION}\"}" \
  2>/dev/null) || error "Update server'a ulaşılamadı. İnternet bağlantısını kontrol edin."

# JSON parse
VALID=$(echo "$RESPONSE"       | grep -o '"valid":[^,}]*'          | cut -d: -f2 | tr -d ' "')
HAS_UPDATE=$(echo "$RESPONSE"  | grep -o '"has_update":[^,}]*'     | cut -d: -f2 | tr -d ' "')
LATEST=$(echo "$RESPONSE"      | grep -o '"latest_version":"[^"]*"'| cut -d'"' -f4)
REG_USER=$(echo "$RESPONSE"    | grep -o '"username":"[^"]*"'      | cut -d'"' -f4)
REG_PASS=$(echo "$RESPONSE"    | grep -o '"password":"[^"]*"'      | cut -d'"' -f4)
REG_HOST=$(echo "$RESPONSE"    | grep -o '"host":"[^"]*"'          | cut -d'"' -f4)

if [ "$VALID" != "true" ]; then
  error "Lisans doğrulaması başarısız. Lisans anahtarınızı kontrol edin."
fi
info "Lisans geçerli ✓"

if [ "$HAS_UPDATE" != "true" ]; then
  echo ""
  echo "  ✓ Sistem güncel (${CURRENT_VERSION})"
  echo ""
  exit 0
fi

echo ""
warn "Yeni sürüm mevcut: ${CURRENT_VERSION} → ${LATEST}"
echo ""

# Changelog göster
echo "$RESPONSE" | grep -o '"changelog":\[[^]]*\]' | \
  grep -o '"[^"]*"' | grep -v 'changelog' | \
  while read line; do echo "  • $(echo $line | tr -d '"')"; done
echo ""

printf "Güncellemeyi uygulamak istiyor musunuz? [E/h] "
read CONFIRM
case "$CONFIRM" in
  [hH]) echo "Güncelleme iptal edildi."; exit 0 ;;
esac

# ── 4. Registry'ye giriş yap ─────────────────────────────────────────────
info "Registry'ye giriş yapılıyor..."
echo "$REG_PASS" | docker login "$REG_HOST" -u "$REG_USER" --password-stdin \
  || error "Registry girişi başarısız"

# ── 5. Yeni imajları çek ─────────────────────────────────────────────────
info "Yeni imajlar indiriliyor (v${LATEST})..."
UMAY_VERSION="$LATEST" docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull backend frontend
info "İmajlar indirildi ✓"

# ── 6. Database migration ───────────────────────────────────────────────
info "Veritabanı migration çalıştırılıyor..."
docker run --rm \
  --network "$(docker inspect umay_backend --format='{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}' 2>/dev/null || echo umay_umay_net)" \
  --env-file "$ENV_FILE" \
  -e POSTGRES_HOST=umay_db \
  "${REG_HOST}/umay/backend:${LATEST}" \
  alembic upgrade head \
  && info "Migration tamamlandı ✓" \
  || warn "Migration başarısız veya gerekli değil, devam ediliyor..."

# ── 7. Servisleri yeniden başlat ────────────────────────────────────────
info "Servisler yeniden başlatılıyor..."
UMAY_VERSION="$LATEST" docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d backend frontend

# ── 8. version.txt güncelle ─────────────────────────────────────────────
echo "$LATEST" > "${UMAY_DIR}/version.txt"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "  ${GREEN}✅ v${LATEST} başarıyla yüklendi!${NC}\n"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
