"""
Configuration centrale du Newsletter Digest Agent.
Charge les variables d'environnement et définit les constantes du projet.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Racine du projet = le dossier 01-newsletter-digest/
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# --- API Keys ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")

# --- Gmail ---
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]
GMAIL_CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
GMAIL_TOKEN_FILE = PROJECT_ROOT / "token.json"
GMAIL_LABEL_NAME = "Newsletters-Digest"

# --- Notion ---
NOTION_DIGESTS_PAGE_ID = "30abe8fdc60480f1816bd986b7819909"  # Page parente des digests
NOTION_IDEAS_PAGE_ID = "2dfbe8fdc60480dfae80c741eaa487db"    # Page RFS (utilisée pour le lien email)
NOTION_IDEAS_DB_ID = "b8d9cb5b-5263-4523-903d-3177739631a0"  # Database RFS (data_source_id)

# --- Gemini ---
GEMINI_MODEL = "gemini-2.0-flash"

# --- SQLite ---
DB_PATH = PROJECT_ROOT / "data" / "newsletter_digest.db"

# --- User ---
USER_EMAIL = os.getenv("USER_EMAIL")
TIMEZONE = "Europe/Paris"
