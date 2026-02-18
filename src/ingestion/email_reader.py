from __future__ import annotations

"""
Lecture des emails Gmail avec le label "Newsletters-Digest".

Ce module se connecte à Gmail via l'API, lit les emails non traités
du label "Newsletters-Digest", et retourne leur contenu brut.
"""

import base64
import json
from dataclasses import dataclass

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src.config import GMAIL_TOKEN_FILE, GMAIL_SCOPES, GMAIL_LABEL_NAME


@dataclass
class RawEmail:
    """Un email brut récupéré depuis Gmail."""
    message_id: str
    subject: str
    sender: str
    date: str
    html_body: str
    text_body: str


def _get_gmail_service():
    """Crée et retourne un service Gmail authentifié."""
    if not GMAIL_TOKEN_FILE.exists():
        raise FileNotFoundError(
            f"{GMAIL_TOKEN_FILE} introuvable. "
            "Lance d'abord : python scripts/setup_gmail_oauth.py"
        )

    creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN_FILE), GMAIL_SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        GMAIL_TOKEN_FILE.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _get_label_id(service) -> str:
    """Trouve l'ID du label "Newsletters-Digest"."""
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])

    for label in labels:
        if label["name"] == GMAIL_LABEL_NAME:
            return label["id"]

    raise ValueError(
        f"Label '{GMAIL_LABEL_NAME}' introuvable dans Gmail. "
        "Vérifie que le filtre Gmail est bien configuré."
    )


def _extract_body(payload: dict) -> tuple[str, str]:
    """
    Extrait le body HTML et texte d'un email.
    Gmail peut imbriquer les parties de différentes façons (multipart, etc.).
    """
    html_body = ""
    text_body = ""

    if "parts" in payload:
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")
            if mime_type == "text/html":
                data = part["body"].get("data", "")
                html_body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            elif mime_type == "text/plain":
                data = part["body"].get("data", "")
                text_body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            elif mime_type.startswith("multipart/"):
                sub_html, sub_text = _extract_body(part)
                if sub_html:
                    html_body = sub_html
                if sub_text:
                    text_body = sub_text
    else:
        mime_type = payload.get("mimeType", "")
        data = payload.get("body", {}).get("data", "")
        if data:
            decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            if mime_type == "text/html":
                html_body = decoded
            elif mime_type == "text/plain":
                text_body = decoded

    return html_body, text_body


def _get_header(headers: list, name: str) -> str:
    """Récupère une valeur de header email (Subject, From, Date)."""
    for header in headers:
        if header["name"].lower() == name.lower():
            return header["value"]
    return ""


def fetch_unread_emails(processed_ids: set[str] | None = None, days_back: int = 14) -> list[RawEmail]:
    """
    Récupère les emails récents du label "Newsletters-Digest" qui n'ont pas
    encore été traités (basé sur les IDs déjà stockés en base).

    Optimisation : ne scanne que les emails des X derniers jours (par défaut 14).
    Ça évite de paginer tout l'historique Gmail qui grossit au fil du temps.

    Args:
        processed_ids: Set d'IDs de messages déjà traités (depuis SQLite).
        days_back: Nombre de jours en arrière à scanner (défaut : 14).

    Returns:
        Liste de RawEmail à traiter.
    """
    if processed_ids is None:
        processed_ids = set()

    service = _get_gmail_service()
    label_id = _get_label_id(service)

    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")
    query = f"after:{cutoff}"

    emails = []
    page_token = None

    while True:
        results = (
            service.users()
            .messages()
            .list(userId="me", labelIds=[label_id], q=query, pageToken=page_token)
            .execute()
        )

        messages = results.get("messages", [])
        if not messages:
            break

        for msg_ref in messages:
            msg_id = msg_ref["id"]
            if msg_id in processed_ids:
                continue

            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )

            payload = msg.get("payload", {})
            headers = payload.get("headers", [])
            html_body, text_body = _extract_body(payload)

            emails.append(
                RawEmail(
                    message_id=msg_id,
                    subject=_get_header(headers, "Subject"),
                    sender=_get_header(headers, "From"),
                    date=_get_header(headers, "Date"),
                    html_body=html_body,
                    text_body=text_body,
                )
            )

        page_token = results.get("nextPageToken")
        if not page_token:
            break

    print(f"  {len(emails)} nouveaux emails trouvés dans '{GMAIL_LABEL_NAME}'")
    return emails
