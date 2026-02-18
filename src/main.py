"""
Newsletter Digest Agent — Point d'entrée principal.

Deux modes :
  python -m src.main poll     → Lit les nouveaux emails, analyse, lance le AI Boardroom, crée les idées dans Notion
  python -m src.main digest   → Compile le digest hebdo, push Notion, envoie email

Workflow :
  - Content envoyé à newsletters@largo.cool en continu
  - Le poll tourne 1x/jour à 6h : extraction → analyse → boardroom → idées Notion
  - Chaque idée passe devant le AI Boardroom (4 board members) dès sa création
  - Vendredi 12h : digest hebdo
  - Vendredi 14h : Charles review les idées de la semaine (Love it / Meh / No go)

Usage :
  cd projects/01-newsletter-digest
  source .venv/bin/activate
  python -m src.main poll
  python -m src.main digest
"""

import sys
import time

import pytz
from datetime import datetime

from src.config import TIMEZONE
from src.storage.db import (
    init_db, get_processed_message_ids, save_content, save_analysis,
)
from src.ingestion.email_reader import fetch_unread_emails
from src.ingestion.content_detector import detect_content, ContentType
from src.ingestion.html_parser import parse_newsletter_html
from src.ingestion.youtube_extractor import extract_youtube_transcript
from src.ingestion.podcast_extractor import extract_podcast_transcript
from src.analysis.analyzer import analyze_content, run_boardroom_debate, analyze_competitors
from src.output.notion_writer import create_idea_page
from src.output.digest_compiler import run_weekly_digest


def _get_current_week() -> tuple[int, int]:
    """Retourne (week_number, year) aligné avec SQLite strftime('%W')."""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    return int(now.strftime("%W")), now.year


def poll():
    """
    Mode poll : lit les nouveaux emails du label "Newsletters-Digest",
    détecte le type de contenu, extrait le texte, analyse avec Gemini,
    crée les pages d'idées dans Notion, et stocke le tout en base.
    """
    print("\n=== Newsletter Digest Agent — Poll ===\n")

    # 1. Récupérer les emails non traités
    processed_ids = get_processed_message_ids()
    print(f"  {len(processed_ids)} emails déjà traités en base")

    emails = fetch_unread_emails(processed_ids)
    if not emails:
        print("  Aucun nouvel email à traiter.")
        return

    week_number, year = _get_current_week()
    week_label = f"Semaine {week_number}"

    # 2. Traiter chaque email
    for i, email in enumerate(emails, 1):
        print(f"\n--- Email {i}/{len(emails)} ---")
        print(f"  Subject: {email.subject}")
        print(f"  From: {email.sender}")

        # 2a. Détecter le type de contenu
        detected = detect_content(email)
        print(f"  Type détecté : {detected.content_type.value}")

        # 2b. Extraire le contenu selon le type
        if detected.content_type == ContentType.YOUTUBE:
            print(f"  Extraction transcription YouTube : {detected.url}")
            extracted = extract_youtube_transcript(detected.url)
        elif detected.content_type in (ContentType.PODCAST_SPOTIFY, ContentType.PODCAST_APPLE):
            print(f"  Extraction podcast : {detected.url}")
            extracted = extract_podcast_transcript(detected.url)
        else:
            extracted = parse_newsletter_html(email.html_body, email.text_body)

        title = extracted.get("title", "")
        if not title or title == "[no-title]":
            title = email.subject
        content = extracted.get("content", "")

        if not content or len(content) < 50:
            print(f"  Contenu trop court ({len(content)} chars), skip.")
            save_content(
                message_id=email.message_id,
                content_type=detected.content_type.value,
                source=email.sender,
                title=title,
                raw_text=content,
                url=detected.url,
                received_at=email.date,
            )
            continue

        print(f"  Contenu extrait : {len(content)} caractères")

        # 2c. Analyser avec Gemini
        print("  Analyse avec Gemini...")
        analysis = analyze_content(
            content=content,
            title=title,
            source=email.sender,
            content_type=detected.content_type.value,
        )

        # 2d. Sauvegarder en base
        content_id = save_content(
            message_id=email.message_id,
            content_type=detected.content_type.value,
            source=email.sender,
            title=title,
            raw_text=content,
            url=detected.url,
            received_at=email.date,
        )

        if content_id:
            save_analysis(
                content_id=content_id,
                takeaways=analysis.get("takeaways", []),
                so_what_advisor=analysis.get("so_what_advisor", ""),
                ideas=analysis.get("ideas", []),
                signal_strength=analysis.get("signal_strength", "weak"),
                topics=analysis.get("topics", []),
            )

        takeaways = analysis.get("takeaways", [])
        ideas = analysis.get("ideas", [])
        strength = analysis.get("signal_strength", "?")
        print(f"  → {len(takeaways)} takeaways, {len(ideas)} idées, signal: {strength}")

        # 2e. Créer les pages d'idées dans la database Notion (au fil de l'eau)
        if ideas:
            source_urls = [detected.url] if detected.url else []
            source_label = f"{email.sender} — {title}"

            for j, idea in enumerate(ideas):
                if j > 0:
                    time.sleep(3)
                idea_score = idea.get("score")
                if isinstance(idea_score, str):
                    try:
                        idea_score = int(idea_score)
                    except (ValueError, TypeError):
                        idea_score = None
                idea_tags = idea.get("tags", [])
                if isinstance(idea_tags, str):
                    idea_tags = [idea_tags]

                print(f"  Création idée Notion : {idea.get('name', '')} ({idea_score}/10)")
                boardroom = run_boardroom_debate(idea, content)

                time.sleep(3)
                competitors = analyze_competitors(
                    idea_name=idea.get("name", ""),
                    one_liner=idea.get("one_liner", ""),
                    why_now=idea.get("why_now", ""),
                )

                create_idea_page(
                    idea_name=idea.get("name", "Sans titre"),
                    one_liner=idea.get("one_liner", ""),
                    why_now=idea.get("why_now", ""),
                    sources=source_label,
                    source_urls=source_urls,
                    tldr=idea.get("tldr", ""),
                    score=idea_score,
                    tags=idea_tags,
                    week_label=week_label,
                    boardroom=boardroom,
                    competitors=competitors,
                )

    print(f"\n=== Poll terminé : {len(emails)} emails traités ===\n")


def digest(force: bool = False):
    """
    Mode digest : compile et envoie le digest hebdomadaire.
    Compile tout ce qui a été ingéré depuis le dernier digest envoyé.
    Cycle réel : vendredi midi → vendredi midi.
    """
    run_weekly_digest(force=force)


def main():
    """Point d'entrée CLI."""
    init_db()

    if len(sys.argv) < 2:
        print("Usage :")
        print("  python -m src.main poll      — Lit et analyse les nouveaux emails + crée les idées")
        print("  python -m src.main digest     — Compile et envoie le digest hebdo")
        print("  python -m src.main digest --force  — Recrée le digest")
        sys.exit(1)

    command = sys.argv[1]

    if command == "poll":
        poll()
    elif command == "digest":
        force = "--force" in sys.argv
        digest(force=force)
    else:
        print(f"Commande inconnue : {command}")
        print("Utilise 'poll' ou 'digest'.")
        sys.exit(1)


if __name__ == "__main__":
    main()
