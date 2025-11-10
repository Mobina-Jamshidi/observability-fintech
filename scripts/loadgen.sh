#!/usr/bin/env sh
set -eu

# Base URL of the Flask app inside docker network
BASE_URL="${BASE_URL:-http://fintech_flask:5000}"

# How often to send a transaction (seconds, can be fractional)
SLEEP_SECS="${SLEEP_SECS:-0.3}"

# Every N seconds, send a synthetic alert to generate logs in app
ALERT_EVERY="${ALERT_EVERY:-20}"  # seconds

last_alert_epoch=$(date +%s)

while true; do
  amount=$(( (RANDOM % 900) + 100 ))
  # Fire a transaction (metrics keep flowing)
  curl -s -X POST "$BASE_URL/transaction" \
    -H 'Content-Type: application/json' \
    -d "{\"amount\":$amount}" >/dev/null || true

  # Occasionally trigger webhook to create `alert_received` log in app
  now_epoch=$(date +%s)
  if [ $((now_epoch - last_alert_epoch)) -ge "$ALERT_EVERY" ]; then
    curl -s -X POST "$BASE_URL/alert" \
      -H 'Content-Type: application/json' \
      -d '{"receiver":"synthetic","status":"firing","alerts":[{"status":"firing","labels":{"alertname":"SyntheticLog"},"annotations":{"summary":"synthetic log"}}]}' \
      >/dev/null || true
    last_alert_epoch="$now_epoch"
  fi

  sleep "$SLEEP_SECS"
done

