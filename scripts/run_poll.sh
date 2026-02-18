#!/bin/bash
# Newsletter Digest Agent — Poll automatique
# Execute par launchd tous les jours a 6h

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="$PROJECT_DIR/.venv/bin/python3"
LOG_FILE="$PROJECT_DIR/data/poll.log"

mkdir -p "$PROJECT_DIR/data"

echo "=== Poll started at $(date) ===" >> "$LOG_FILE"
cd "$PROJECT_DIR" && "$PYTHON" -m src.main poll >> "$LOG_FILE" 2>&1
echo "=== Poll finished at $(date) ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
