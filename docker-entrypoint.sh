#!/usr/bin/env bash
set -euo pipefail

# If MONGODB_URL provided, run index creation to ensure indexes exist
if [ -n "${MONGODB_URL:-}" ]; then
  echo "MONGODB_URL detected — creating indexes..."
  python resort_backend/scripts/create_indexes.py || true
else
  echo "MONGODB_URL not set — skipping index creation."
fi

exec "$@"
#!/usr/bin/env bash
set -euo pipefail

# If MONGODB_URL is provided, run create_indexes.py (idempotent)
if [ -n "${MONGODB_URL:-}" ]; then
  echo "MONGODB_URL provided — creating indexes if needed"
  python /app/resort_backend/scripts/create_indexes.py || echo "Index creation failed (non-fatal)"
else
  echo "MONGODB_URL not set — skipping index creation"
fi

# Allow passing arbitrary CMD (uvicorn or other)
exec "$@"
