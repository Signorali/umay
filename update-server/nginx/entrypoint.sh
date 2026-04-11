#!/bin/sh
# Nginx'i başlat, her 24 saatte bir reload yap (sertifika yenileme için)

nginx -g "daemon off;" &
NGINX_PID=$!

# Her 24 saatte bir reload — QNAP sertifikayı yenilediğinde nginx otomatik yükler
while true; do
    sleep 86400
    echo "[entrypoint] Sertifika yenilemesi kontrolü: nginx reload..."
    nginx -s reload
done &

wait $NGINX_PID
