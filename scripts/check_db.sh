#!/usr/bin/env bash
set -euo pipefail
API_BASE=${API_BASE:-http://localhost:8000}
INTERNAL_KEY=${INTERNAL_KEY:-}
URL="$API_BASE/internal/db-status"

if [ -n "$INTERNAL_KEY" ]; then
  RESP=$(curl -s -H "X-Internal-Key: $INTERNAL_KEY" "$URL")
else
  RESP=$(curl -s "$URL")
fi

DB_CONNECTED=$(echo "$RESP" | jq -r '.db_connected // false')
if [ "$DB_CONNECTED" != "true" ]; then
  echo "DB not connected or unavailable: $RESP" >&2
  exit 1
fi

echo "DB connected: $RESP"
