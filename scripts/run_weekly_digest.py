"""
Script pour lancer le digest hebdomadaire.

Peut être utilisé dans un cron job :
  0 12 * * 5 cd /path/to/01-newsletter-digest && .venv/bin/python scripts/run_weekly_digest.py

Usage :
  cd projects/01-newsletter-digest
  source .venv/bin/activate
  python scripts/run_weekly_digest.py
  python scripts/run_weekly_digest.py --force  # recrée même si déjà fait
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.db import init_db
from src.output.digest_compiler import run_weekly_digest

if __name__ == "__main__":
    init_db()
    force = "--force" in sys.argv
    run_weekly_digest(force=force)
