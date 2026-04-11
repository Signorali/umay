#!/bin/sh
# =============================================================
# Umay — QNAP Konteyner Durdurma/Silme Scripti
# Kullanım: sh scripts/qnap_teardown.sh [--volumes]
# =============================================================
set -e

COMPOSE_FILE="docker-compose.qnap.yml"
REMOVE_VOLUMES=0

if [ "$1" = "--volumes" ]; then
    REMOVE_VOLUMES=1
fi

echo ""
echo "╔══════════════════════════════════════╗"
echo "║  Umay — Servisler Durduruluyor       ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Durdur ve container'ları sil
docker-compose -f "$COMPOSE_FILE" down

if [ "$REMOVE_VOLUMES" = "1" ]; then
    echo "⚠ Veri dizinleri siliniyor (postgres, redis, storage, backups)..."
    echo "Bu işlem GERİ ALINAMAZ. Devam et? (evet/hayır)"
    read -r answer
    if [ "$answer" = "evet" ]; then
        rm -rf data/postgres data/redis data/storage data/backups
        echo "✓ Veri dizinleri silindi."
    else
        echo "İptal edildi — veri dizinleri korundu."
    fi
fi

echo ""
echo "✓ Servisler durduruldu."
echo "  Yeniden başlatmak: sh scripts/qnap_setup.sh"
echo ""
