#!/bin/bash
# ================================================
# Umay - Financial Management System
# Automated Installation Script
# ================================================
# Usage: curl -fsSL https://raw.githubusercontent.com/Signorali/umay/main/install.sh | bash
# Support: alikoken@outlook.com
# ================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="umay"
APP_PORT=1881
COMPOSE_URL="https://raw.githubusercontent.com/Signorali/umay/main/docker-compose.yml"

echo -e "\n${BLUE}================================================${NC}"
echo -e "${BLUE}   Umay - Financial Management System${NC}"
echo -e "${BLUE}   v2.0.1 Installation${NC}"
echo -e "${BLUE}================================================${NC}\n"

# ---- Gereksinim kontrolleri ----
echo -e "${YELLOW}Sistem gereksinimleri kontrol ediliyor...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker kurulu değil.${NC}"
    echo -e "  Kurulum: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker: $(docker --version)${NC}"

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    echo -e "${RED}✗ Docker Compose kurulu değil.${NC}"
    echo -e "  Kurulum: https://docs.docker.com/compose/install/"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose kurulu${NC}"

if ! command -v curl &> /dev/null; then
    echo -e "${RED}✗ curl kurulu değil.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ curl mevcut${NC}\n"

# ---- Kullanıcı bilgileri ----
echo -e "${YELLOW}Yönetici bilgilerini girin:${NC}"
read -p "  Admin e-posta (varsayılan: admin@example.com): " ADMIN_EMAIL
ADMIN_EMAIL=${ADMIN_EMAIL:-admin@example.com}

while true; do
    read -sp "  Admin şifre (boş bırakılırsa otomatik): " ADMIN_PASSWORD
    echo
    if [ -z "$ADMIN_PASSWORD" ]; then
        ADMIN_PASSWORD=$(openssl rand -base64 12 | tr -d '=/+' | head -c 16)
        echo -e "  ${GREEN}Oluşturulan şifre: $ADMIN_PASSWORD${NC}"
        break
    elif [ ${#ADMIN_PASSWORD} -ge 8 ]; then
        break
    else
        echo -e "  ${RED}Şifre en az 8 karakter olmalı.${NC}"
    fi
done

read -p "  Organizasyon adı (varsayılan: Benim Şirketim): " TENANT_NAME
TENANT_NAME=${TENANT_NAME:-"Benim Şirketim"}

echo ""

# ---- Gizli anahtarlar ----
echo -e "${YELLOW}Güvenlik anahtarları oluşturuluyor...${NC}"
APP_SECRET=$(openssl rand -base64 32)
JWT_SECRET=$(openssl rand -base64 32)
DB_PASSWORD=$(openssl rand -base64 16 | tr -d '=/+')
echo -e "${GREEN}✓ Anahtarlar oluşturuldu${NC}\n"

# ---- Kurulum dizini ----
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Mevcut kurulum dizini bulundu, güncelleniyor...${NC}"
else
    mkdir -p "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"

# ---- docker-compose.yml indir ----
echo -e "${YELLOW}docker-compose.yml indiriliyor...${NC}"
curl -fsSL "$COMPOSE_URL" -o docker-compose.yml
echo -e "${GREEN}✓ docker-compose.yml hazır${NC}"

# ---- .env oluştur ----
echo -e "${YELLOW}.env dosyası oluşturuluyor...${NC}"
cat > .env << EOF
APP_SECRET_KEY=$APP_SECRET
JWT_SECRET_KEY=$JWT_SECRET
POSTGRES_USER=umay
POSTGRES_PASSWORD=$DB_PASSWORD
POSTGRES_DB=umay
DATABASE_URL=postgresql+asyncpg://umay:$DB_PASSWORD@postgres:5432/umay
REDIS_URL=redis://redis:6379/0
FIRST_ADMIN_EMAIL=$ADMIN_EMAIL
FIRST_ADMIN_PASSWORD=$ADMIN_PASSWORD
DEFAULT_TENANT_NAME=$TENANT_NAME
DEFAULT_TENANT_SLUG=default
FRONTEND_PORT=$APP_PORT
BACKEND_PORT=1923
APP_ENV=production
APP_VERSION=2.0.1
EOF

mkdir -p storage backups
echo -e "${GREEN}✓ Yapılandırma hazır${NC}\n"

# ---- Servisleri başlat ----
echo -e "${YELLOW}Servisler başlatılıyor...${NC}"
if docker compose version &> /dev/null 2>&1; then
    docker compose pull
    docker compose up -d
else
    docker-compose pull
    docker-compose up -d
fi

# ---- Hazır olmasını bekle ----
echo -e "\n${YELLOW}Backend hazır olana kadar bekleniyor (max 90s)...${NC}"
for i in $(seq 1 90); do
    if curl -sf http://localhost:1923/health > /dev/null 2>&1; then
        echo -e "\n${GREEN}✓ Backend hazır!${NC}"
        break
    fi
    if [ $i -eq 90 ]; then
        echo -e "\n${RED}✗ Backend başlatılamadı. Logları kontrol edin: docker compose logs backend${NC}"
        exit 1
    fi
    printf "."
    sleep 1
done

# ---- Başarı mesajı ----
echo -e "\n${GREEN}================================================${NC}"
echo -e "${GREEN}   ✓ Kurulum tamamlandı!${NC}"
echo -e "${GREEN}================================================${NC}"
echo -e "\n  ${YELLOW}Erişim Bilgileri:${NC}"
echo -e "  URL      : ${GREEN}http://localhost:$APP_PORT${NC}"
echo -e "  E-posta  : ${GREEN}$ADMIN_EMAIL${NC}"
echo -e "  Şifre    : ${GREEN}$ADMIN_PASSWORD${NC}"
echo -e "\n  ${RED}Bu bilgileri güvenli bir yerde saklayın!${NC}"
echo -e "\n  ${YELLOW}Faydalı komutlar:${NC}"
echo -e "  Loglar   : docker compose logs -f"
echo -e "  Durdur   : docker compose down"
echo -e "  Başlat   : docker compose up -d"
echo -e "\n  Destek  : alikoken@outlook.com\n"
