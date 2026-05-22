#!/bin/bash
set -e
cd "$(dirname "$0")"

export WEB_APP_URL="https://${REPLIT_DEV_DOMAIN}"
echo "Bot ishga tushmoqda..."
echo "WEB_APP_URL: $WEB_APP_URL"

exec python bot.py
