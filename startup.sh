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

# Qdrant's local storage uses a single .lock file at the root of the
# storage path, tied to a live process's file handle - it's not supposed
# to survive a process actually dying. But if a previous container got
# killed abruptly (e.g. during a Railway redeploy overlap, or a stuck/
# duplicate deployment), that lock can be left behind and block every
# future startup with "already accessed by another instance." Since
# nothing in THIS fresh container has opened the storage yet, it's
# always safe to clear it here - qdrant-client recreates it cleanly the
# moment it actually acquires the lock.
if [ -f "$VOLUME_PATH/qdrant_data/.lock" ]; then
  echo "Clearing a stale Qdrant lock file before starting..."
  rm -f "$VOLUME_PATH/qdrant_data/.lock"
fi

exec uvicorn api:app --host 0.0.0.0 --port "$PORT"
