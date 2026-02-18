"""
Script one-time pour autoriser l'accès Gmail.

Lance ce script une seule fois. Il ouvre ton navigateur pour te connecter
à ton compte Google et autorise l'app Newsletter Digest
à lire tes emails et en envoyer.

Le token est sauvegardé dans token.json — plus besoin de refaire l'auth après.

Usage :
    cd projects/01-newsletter-digest
    source .venv/bin/activate
    python scripts/setup_gmail_oauth.py
"""

import sys
from pathlib import Path

# Ajouter le dossier parent au path pour importer src/
sys.path.insert(0, str(Path(__file__).parent.parent))

from google_auth_oauthlib.flow import InstalledAppFlow
from src.config import GMAIL_SCOPES, GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE, USER_EMAIL


def main():
    print("=== Setup Gmail OAuth ===\n")

    if not GMAIL_CREDENTIALS_FILE.exists():
        print(f"ERREUR : {GMAIL_CREDENTIALS_FILE} introuvable.")
        print("Télécharge-le depuis Google Cloud Console > Credentials > OAuth 2.0 Client IDs")
        sys.exit(1)

    if GMAIL_TOKEN_FILE.exists():
        print(f"Le fichier {GMAIL_TOKEN_FILE} existe déjà.")
        response = input("Veux-tu le recréer ? (o/n) : ")
        if response.lower() != "o":
            print("OK, on garde le token existant.")
            return

    print("Ouverture du navigateur pour l'authentification Google...")
    print(f"Connecte-toi avec {USER_EMAIL} et autorise l'accès.\n")

    flow = InstalledAppFlow.from_client_secrets_file(
        str(GMAIL_CREDENTIALS_FILE), GMAIL_SCOPES
    )
    creds = flow.run_local_server(port=0)

    GMAIL_TOKEN_FILE.write_text(creds.to_json())
    print(f"\nToken sauvegardé dans {GMAIL_TOKEN_FILE}")
    print("L'authentification Gmail est configurée.")


if __name__ == "__main__":
    main()
