#!/bin/bash
# Newsletter Digest Agent — Digest hebdomadaire
# Execute par launchd tous les vendredis a 12h

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="$PROJECT_DIR/.venv/bin/python3"
LOG_FILE="$PROJECT_DIR/data/digest.log"

mkdir -p "$PROJECT_DIR/data"

echo "=== Digest started at $(date) ===" >> "$LOG_FILE"
cd "$PROJECT_DIR" && "$PYTHON" -m src.main digest >> "$LOG_FILE" 2>&1
echo "=== Digest finished at $(date) ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
