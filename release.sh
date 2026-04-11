#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Umay Release Script
# Kullanım: ./release.sh <versiyon> [changelog satırları...]
#
# Örnek:
#   ./release.sh 1.1.0 "Yeni özellik: X" "Hata düzeltmesi: Y"
#
# Ne yapar:
#   1. version.txt günceller
#   2. Docker imajlarını build eder (backend + frontend)
#   3. Docker Hub'a push eder (signorali/umay-*)
#   4. latest.json günceller
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Değişkenler ───────────────────────────────────────────────────────────────
VERSION="${1:-}"
DOCKER_USER="${DOCKER_HUB_USER:-signorali}"
DATE=$(date +%Y-%m-%d)

if [ -z "$VERSION" ]; then
  echo "❌ Kullanım: ./release.sh <versiyon> [changelog...]"
  echo "   Örnek: ./release.sh 1.1.0 \"Yeni özellik\" \"Hata düzeltmesi\""
  exit 1
fi

# Changelog satırları (2. argümandan itibaren)
shift 1 || true
CHANGELOG_ITEMS=("$@")

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Umay Release v${VERSION}"
echo "  Registry: Docker Hub (${DOCKER_USER})"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 1. version.txt güncelle ──────────────────────────────────────────────────
echo "▶ version.txt güncelleniyor → ${VERSION}"
echo "${VERSION}" > version.txt

# ── 2. Backend build + push ──────────────────────────────────────────────────
echo ""
echo "▶ Backend build ediliyor..."
docker build \
  --build-arg APP_VERSION="${VERSION}" \
  -t "${DOCKER_USER}/umay-backend:${VERSION}" \
  -t "${DOCKER_USER}/umay-backend:latest" \
  -f backend/Dockerfile \
  ./backend

echo "▶ Backend push ediliyor..."
docker push "${DOCKER_USER}/umay-backend:${VERSION}"
docker push "${DOCKER_USER}/umay-backend:latest"

# ── 3. Frontend build + push ─────────────────────────────────────────────────
echo ""
echo "▶ Frontend build ediliyor..."
docker build \
  --build-arg APP_VERSION="${VERSION}" \
  -t "${DOCKER_USER}/umay-frontend:${VERSION}" \
  -t "${DOCKER_USER}/umay-frontend:latest" \
  -f frontend/Dockerfile.prod \
  ./frontend

echo "▶ Frontend push ediliyor..."
docker push "${DOCKER_USER}/umay-frontend:${VERSION}"
docker push "${DOCKER_USER}/umay-frontend:latest"

# ── 4. latest.json güncelle ──────────────────────────────────────────────────
echo ""
echo "▶ latest.json güncelleniyor..."

VERSIONS_DIR="update-server/versions"
mkdir -p "$VERSIONS_DIR"

# Changelog JSON array oluştur
CHANGELOG_JSON="["
if [ ${#CHANGELOG_ITEMS[@]} -eq 0 ]; then
  CHANGELOG_JSON+="\"v${VERSION} yayınlandı\""
else
  for i in "${!CHANGELOG_ITEMS[@]}"; do
    [ $i -gt 0 ] && CHANGELOG_JSON+=","
    # Basit JSON escape
    ITEM="${CHANGELOG_ITEMS[$i]//\"/\\\"}"
    CHANGELOG_JSON+="\"${ITEM}\""
  done
fi
CHANGELOG_JSON+="]"

cat > "${VERSIONS_DIR}/latest.json" << EOF
{
  "version": "${VERSION}",
  "released_at": "${DATE}",
  "min_plan": "starter",
  "changelog": ${CHANGELOG_JSON}
}
EOF

echo "   latest.json → ${VERSIONS_DIR}/latest.json"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ v${VERSION} başarıyla yayınlandı!"
echo ""
echo "  İmajlar:"
echo "    ${DOCKER_USER}/umay-backend:${VERSION}"
echo "    ${DOCKER_USER}/umay-frontend:${VERSION}"
echo ""
echo "  QNAP güncelleme:"
echo "    Settings → System → Güncelle butonuna basın."
echo "    (veya SSH: docker compose -f docker-compose.qnap.yml pull && docker compose up -d)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
