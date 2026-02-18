#!/bin/bash
# Newsletter Digest Agent — Digest automatique avec rattrapage
# Se lance toutes les 4h. Verifie si on est vendredi (ou samedi avant 9h = rattrapage)
# et si le digest de cette semaine n'a pas deja ete envoye.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="$PROJECT_DIR/.venv/bin/python3"
LOG_FILE="$PROJECT_DIR/data/digest.log"
MARKER_FILE="$PROJECT_DIR/data/.last_digest_week"

mkdir -p "$PROJECT_DIR/data"

DAY_OF_WEEK=$(date +%u)  # 1=lundi ... 5=vendredi, 6=samedi, 7=dimanche
HOUR=$(date +%H)
WEEK_ID=$(date +%Y-%W)

# Verifier si le digest de cette semaine a deja ete envoye
if [ -f "$MARKER_FILE" ] && [ "$(cat "$MARKER_FILE")" = "$WEEK_ID" ]; then
    exit 0
fi

# Lancer le digest si : vendredi apres 12h OU samedi avant 12h (rattrapage)
if [ "$DAY_OF_WEEK" -eq 5 ] && [ "$HOUR" -ge 12 ]; then
    echo "=== Digest started at $(date) (vendredi) ===" >> "$LOG_FILE"
    cd "$PROJECT_DIR" && "$PYTHON" -m src.main digest >> "$LOG_FILE" 2>&1
    echo "$WEEK_ID" > "$MARKER_FILE"
    echo "=== Digest finished at $(date) ===" >> "$LOG_FILE"
elif [ "$DAY_OF_WEEK" -eq 6 ] && [ "$HOUR" -lt 12 ]; then
    echo "=== Digest started at $(date) (rattrapage samedi) ===" >> "$LOG_FILE"
    cd "$PROJECT_DIR" && "$PYTHON" -m src.main digest >> "$LOG_FILE" 2>&1
    echo "$WEEK_ID" > "$MARKER_FILE"
    echo "=== Digest finished at $(date) ===" >> "$LOG_FILE"
fi
