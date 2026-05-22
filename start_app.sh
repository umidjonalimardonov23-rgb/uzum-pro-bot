#!/bin/bash
set -e
cd "$(dirname "$0")"

export WEB_APP_URL="https://${REPLIT_DEV_DOMAIN}"
echo "WEB_APP_URL: $WEB_APP_URL"

exec python app.py
