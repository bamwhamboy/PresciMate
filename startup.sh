#!/bin/bash
# Runs once when the container starts, before uvicorn. Railway's disk is
# ephemeral by default - only the mounted Volume survives a redeploy. This
# copies the knowledge base (built locally via build_knowledge_base.ipynb,
# committed to the repo) into that persistent volume ONE TIME - after
# that, the "if not already there" checks mean it won't overwrite real
# user signups or saved prescription history on later redeploys.
set -e

VOLUME_PATH="${RAILWAY_VOLUME_MOUNT_PATH:-/data}"

if [ ! -d "$VOLUME_PATH/qdrant_data" ]; then
  echo "First run - seeding qdrant_data into the persistent volume..."
  cp -r qdrant_data "$VOLUME_PATH/qdrant_data"
else
  echo "qdrant_data already on the volume - leaving it alone."
fi

if [ ! -f "$VOLUME_PATH/prescribot.db" ]; then
  echo "First run - seeding prescribot.db into the persistent volume..."
  cp prescribot.db "$VOLUME_PATH/prescribot.db"
else
  echo "prescribot.db already on the volume - leaving it alone."
fi

exec uvicorn api:app --host 0.0.0.0 --port "$PORT"
