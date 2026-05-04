#!/usr/bin/env bash
# Daily wearable sync — invoked by cron at 6am ET.
set -euo pipefail

cd "$(dirname "$0")"
source venv/bin/activate
set -a; source .env; set +a

python sync_oura.py  --days 3
python sync_whoop.py --days 3
echo "[$(date -u +%FT%TZ)] daily sync ok"
