#!/bin/bash
# Скрипт перезапуска сервисов AlliTrader

set -e

LOG_FILE="/var/www/allitrader/deploy.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "Restarting AlliTrader services..."

# Перезапуск всех сервисов allitrader
supervisorctl restart allitrader:*

log "All services restarted successfully!"
