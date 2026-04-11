# =============================================================
# Umay — Windows'tan QNAP'a Aktarım Scripti
# Kullanım: .\scripts\deploy_to_qnap.ps1 -QnapIP 192.168.1.100
# Gereksinim: OpenSSH (Windows 10/11'de built-in)
# =============================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$QnapIP,

    [string]$QnapUser = "admin",

    [string]$QnapPath = "/share/Container/umay",

    [string]$ProjectRoot = "$PSScriptRoot\..",

    [switch]$SkipBuild,
    [switch]$MigrateOnly
)

$ErrorActionPreference = "Stop"

# Renkli çıktı
function OK   { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function WARN { param($msg) Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function INFO { param($msg) Write-Host "  [>>] $msg" -ForegroundColor Cyan }
function FAIL { param($msg) Write-Host "  [FAIL] $msg" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Umay — QNAP Deployment                              ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host "  Hedef: ${QnapUser}@${QnapIP}:${QnapPath}"
Write-Host ""

# SSH bağlantı testi
INFO "SSH bağlantısı test ediliyor..."
$sshTest = ssh -o "ConnectTimeout=5" -o "StrictHostKeyChecking=no" "${QnapUser}@${QnapIP}" "echo OK" 2>&1
if ($sshTest -ne "OK") {
    FAIL "SSH bağlantısı başarısız. QNAP IP ve SSH servisini kontrol et."
}
OK "SSH bağlantısı başarılı"

# Uzak dizinleri oluştur
INFO "Uzak dizinler oluşturuluyor..."
$mkdirCmd = @"
mkdir -p ${QnapPath}/data/postgres ${QnapPath}/data/redis ${QnapPath}/data/storage ${QnapPath}/data/backups ${QnapPath}/logs ${QnapPath}/scripts
chown -R 999:999 ${QnapPath}/data/postgres 2>/dev/null || true
chmod 700 ${QnapPath}/data/postgres 2>/dev/null || true
echo DONE
"@
$result = ssh "${QnapUser}@${QnapIP}" $mkdirCmd
if ($result -match "DONE") { OK "Dizinler hazır" } else { WARN "Dizin oluşturma uyarısı (normal olabilir)" }

if (-not $MigrateOnly) {
    # Proje dosyalarını kopyala
    INFO "Proje dosyaları kopyalanıyor..."

    # Node_modules ve __pycache__ hariç kopyala
    $excludes = @(
        "--exclude=node_modules",
        "--exclude=__pycache__",
        "--exclude=*.pyc",
        "--exclude=.git",
        "--exclude=frontend/dist",
        "--exclude=frontend/.vite"
    )

    $rsyncArgs = $excludes + @(
        "-avz", "--progress",
        "$ProjectRoot/",
        "${QnapUser}@${QnapIP}:${QnapPath}/"
    )

    # rsync varsa kullan, yoksa scp
    if (Get-Command rsync -ErrorAction SilentlyContinue) {
        & rsync @rsyncArgs
        OK "rsync ile aktarım tamamlandı"
    } else {
        INFO "rsync bulunamadı, scp kullanılıyor (daha yavaş)..."
        # Temel dosyaları kopyala
        $filesToCopy = @(
            "docker-compose.qnap.yml",
            ".env.qnap",
            "QNAP_DEPLOY.md",
            "DELIVERY_GATE.md"
        )
        foreach ($f in $filesToCopy) {
            $src = Join-Path $ProjectRoot $f
            if (Test-Path $src) {
                scp "$src" "${QnapUser}@${QnapIP}:${QnapPath}/"
                OK "  $f"
            }
        }

        # Migration dosyaları
        Get-ChildItem -Path $ProjectRoot -Filter "migration_*.sql" | ForEach-Object {
            scp $_.FullName "${QnapUser}@${QnapIP}:${QnapPath}/"
            OK "  $($_.Name)"
        }

        # Klasörler
        foreach ($dir in @("backend", "frontend", "scripts")) {
            $srcDir = Join-Path $ProjectRoot $dir
            if (Test-Path $srcDir) {
                INFO "  $dir/ kopyalanıyor..."
                scp -r "$srcDir" "${QnapUser}@${QnapIP}:${QnapPath}/"
                OK "  $dir/"
            }
        }
    }
}

# .env kontrolü ve oluşturma
INFO ".env dosyası kontrol ediliyor..."
$envExists = ssh "${QnapUser}@${QnapIP}" "[ -f ${QnapPath}/.env ] && echo yes || echo no"
if ($envExists -eq "no") {
    ssh "${QnapUser}@${QnapIP}" "[ -f ${QnapPath}/.env.qnap ] && cp ${QnapPath}/.env.qnap ${QnapPath}/.env && echo 'copied' || echo 'missing'"
    WARN ".env.qnap, .env olarak kopyalandı. SSH ile açıp şifreleri değiştirmen gerekiyor!"
    WARN "Komut: ssh ${QnapUser}@${QnapIP} nano ${QnapPath}/.env"
} else {
    OK ".env mevcut"
}

if (-not $SkipBuild -and -not $MigrateOnly) {
    # Build ve başlat
    INFO "Docker image'lar build ediliyor (5-10 dakika)..."
    ssh "${QnapUser}@${QnapIP}" "cd ${QnapPath} && docker-compose -f docker-compose.qnap.yml build --parallel"
    OK "Build tamamlandı"

    INFO "Servisler başlatılıyor..."
    ssh "${QnapUser}@${QnapIP}" "cd ${QnapPath} && docker-compose -f docker-compose.qnap.yml up -d"
    OK "Servisler başlatıldı"

    INFO "Servislerin hazır olması bekleniyor (30 saniye)..."
    Start-Sleep -Seconds 30
}

# Migration'ları uygula
INFO "Migration'lar uygulanıyor..."
$migrations = @(
    "migration_0002.sql", "migration_0003.sql", "migration_0004.sql",
    "migration_0005.sql", "migration_0006.sql", "migration_0007.sql",
    "migration_0008.sql", "migration_0009.sql", "migration_0010.sql",
    "migration_0011.sql", "migration_0012.sql", "migration_0013.sql",
    "migration_0014_mfa.sql"
)

foreach ($mig in $migrations) {
    $migPath = "${QnapPath}/${mig}"
    $exists = ssh "${QnapUser}@${QnapIP}" "[ -f $migPath ] && echo yes || echo no"
    if ($exists -eq "yes") {
        $migResult = ssh "${QnapUser}@${QnapIP}" "docker exec -i umay_db psql -U umay -d umay < $migPath 2>&1 | tail -1"
        OK "$mig — $migResult"
    } else {
        WARN "$mig bulunamadı — atlandı"
    }
}

# Sağlık kontrolü
INFO "Sağlık kontrolü yapılıyor..."
Start-Sleep -Seconds 5
$health = ssh "${QnapUser}@${QnapIP}" "curl -fs http://localhost:8000/api/v1/health 2>/dev/null || echo UNREACHABLE"
if ($health -match '"status"') {
    OK "Backend API cevap veriyor"
    Write-Host "  Cevap: $health" -ForegroundColor DarkGray
} else {
    WARN "Backend henüz cevap vermiyor. 1 dakika bekleyip tekrar dene."
    WARN "Log için: ssh ${QnapUser}@${QnapIP} docker logs umay_backend --tail=50"
}

# Özet
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  Deployment Tamamlandı!                              ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  Web Arayüzü : http://${QnapIP}:8080" -ForegroundColor White
Write-Host "  Backend API : http://${QnapIP}:8000/api/v1" -ForegroundColor White
Write-Host "  API Docs    : http://${QnapIP}:8000/docs" -ForegroundColor White
Write-Host "  Health      : http://${QnapIP}:8000/api/v1/health" -ForegroundColor White
Write-Host ""
Write-Host "  Kurulum sihirbazını tamamlamak için web arayüzüne git." -ForegroundColor Yellow
Write-Host ""
