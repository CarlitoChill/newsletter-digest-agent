"""
Envoi du digest par email via Gmail API.

Envoie un email HTML formaté au destinataire configuré (USER_EMAIL) avec :
- Le résumé de la semaine
- Les top insights
- Les idées de boîtes
- Un lien vers la page Notion
"""

import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from datetime import datetime, timedelta

from src.config import (
    GMAIL_TOKEN_FILE,
    GMAIL_SCOPES,
    USER_EMAIL,
    NOTION_IDEAS_PAGE_ID,
)


def _monday_label(week_number: int, year: int) -> str:
    """
    Retourne le label du lundi de la semaine, en français.
    Ex: "Lundi 16 février 2026"
    """
    jan1 = datetime(year, 1, 1)
    days_offset = (week_number * 7) - jan1.weekday()
    monday = jan1 + timedelta(days=days_offset)
    monday_str = monday.strftime("%A %d %B %Y")

    translations = {
        "monday": "lundi", "tuesday": "mardi", "wednesday": "mercredi",
        "thursday": "jeudi", "friday": "vendredi", "saturday": "samedi", "sunday": "dimanche",
        "january": "janvier", "february": "février", "march": "mars", "april": "avril",
        "may": "mai", "june": "juin", "july": "juillet", "august": "août",
        "september": "septembre", "october": "octobre", "november": "novembre", "december": "décembre",
    }
    for en, fr in translations.items():
        monday_str = monday_str.lower().replace(en, fr)
    return monday_str.capitalize()


def _get_gmail_service():
    """Crée un service Gmail pour l'envoi."""
    creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN_FILE), GMAIL_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        GMAIL_TOKEN_FILE.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def _build_html(
    week_number: int,
    year: int,
    digest: dict,
    notion_url: str,
) -> str:
    """Construit le HTML de l'email du digest."""

    # Top insights
    insights_html = ""
    for i, ins in enumerate(digest.get("top_insights", []), 1):
        deep_dive = ins.get('deep_dive', ins.get('why_it_matters', ''))
        advisor_angle = ins.get('advisor_angle', '')
        advisor_block = f"""
                <div style="background: #f0f7ff; padding: 10px 14px; border-left: 3px solid #2563eb; border-radius: 4px; margin-top: 8px;">
                    <span style="font-size: 11px; color: #2563eb; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Advisory angle</span><br>
                    <span style="color: #1e40af; font-size: 14px;">{advisor_angle}</span>
                </div>""" if advisor_angle else ""
        insights_html += f"""
        <tr>
            <td style="padding: 16px 0; border-bottom: 1px solid #eee;">
                <strong style="font-size: 15px;">{i}. {ins.get('insight', '')}</strong><br>
                <span style="color: #888; font-size: 12px; text-transform: uppercase; letter-spacing: 0.3px;">Source: {ins.get('source', '')}</span>
                <p style="color: #333; font-size: 14px; line-height: 1.6; margin: 8px 0;">{deep_dive}</p>
                {advisor_block}
            </td>
        </tr>
        """

    # Top ideas
    ideas_html = ""
    for idea in digest.get("top_ideas", []):
        conviction = idea.get("conviction_level", "")
        color = {"high": "#22c55e", "medium": "#f59e0b", "low": "#94a3b8"}.get(conviction, "#94a3b8")
        quick_take = idea.get("quick_take", "")
        quick_take_block = f"<br><span style='color: #555; font-size: 13px; line-height: 1.5;'>{quick_take}</span>" if quick_take else ""
        ideas_html += f"""
        <li style="margin-bottom: 14px;">
            <strong>{idea.get('name', '')}</strong>
            <span style="background: {color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 6px;">{conviction}</span>
            <br><span style="color: #333;">{idea.get('one_liner', '')}</span>
            {quick_take_block}
        </li>
        """

    # Themes
    themes_html = ""
    for theme in digest.get("recurring_themes", []):
        signals = ", ".join(theme.get("signals", []))
        thesis = theme.get("thesis", theme.get("implication", ""))
        themes_html += f"""
        <li style="margin-bottom: 14px;">
            <strong style="font-size: 15px;">{theme.get('theme', '')}</strong><br>
            <span style="color: #888; font-size: 12px;">{signals}</span>
            <p style="color: #333; font-size: 14px; line-height: 1.5; margin: 6px 0 0 0;">{thesis}</p>
        </li>
        """

    rfs_url = f"https://www.notion.so/{NOTION_IDEAS_PAGE_ID.replace('-', '')}"

    monday_label = _monday_label(week_number, year)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 640px; margin: 0 auto; padding: 20px; color: #1a1a1a; line-height: 1.6;">

        <h1 style="font-size: 22px; border-bottom: 2px solid #000; padding-bottom: 8px;">
            Newsletter Digest — Semaine {week_number} — {monday_label}
        </h1>

        <p style="font-size: 15px; color: #444; background: #f8f9fa; padding: 16px; border-radius: 8px; border-left: 4px solid #000;">
            {digest.get('week_summary', '')}
        </p>

        <h2 style="font-size: 18px; margin-top: 32px;">Top Insights</h2>
        <table style="width: 100%; border-collapse: collapse;">
            {insights_html}
        </table>

        {"<h2 style='font-size: 18px; margin-top: 32px;'>Thèmes récurrents</h2><ul>" + themes_html + "</ul>" if themes_html else ""}

        <h2 style="font-size: 18px; margin-top: 32px;">Playbook Advisor</h2>
        <p style="background: #f0f7ff; padding: 16px; border-radius: 8px; border-left: 4px solid #2563eb;">
            {digest.get('advisor_playbook', '')}
        </p>

        {"<h2 style='font-size: 18px; margin-top: 32px;'>Idées de boîtes</h2><ul>" + ideas_html + "</ul>" if ideas_html else ""}

        <div style="margin-top: 32px; padding: 16px; background: #f8f9fa; border-radius: 8px; text-align: center;">
            <a href="{notion_url}" style="display: inline-block; padding: 10px 24px; background: #000; color: white; text-decoration: none; border-radius: 6px; margin-right: 8px;">
                Voir le digest complet
            </a>
            <a href="{rfs_url}" style="display: inline-block; padding: 10px 24px; background: #2563eb; color: white; text-decoration: none; border-radius: 6px;">
                Request for Startups
            </a>
        </div>

        <p style="color: #999; font-size: 12px; margin-top: 32px; text-align: center;">
            Newsletter Digest Agent — généré automatiquement chaque vendredi
        </p>

    </body>
    </html>
    """
    return html


def send_digest_email(
    week_number: int,
    year: int,
    digest: dict,
    notion_url: str,
):
    """
    Envoie le digest par email au destinataire configuré (USER_EMAIL).

    Args:
        week_number: Numéro de la semaine.
        year: Année.
        digest: Le digest compilé.
        notion_url: URL de la page Notion du digest.
    """
    service = _get_gmail_service()

    html_content = _build_html(week_number, year, digest, notion_url)

    message = MIMEMultipart("alternative")
    message["to"] = USER_EMAIL
    monday_label = _monday_label(week_number, year)
    message["subject"] = f"Newsletter Digest — Semaine {week_number} — {monday_label}"
    message.attach(MIMEText(html_content, "html"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    service.users().messages().send(
        userId="me",
        body={"raw": raw},
    ).execute()

    print(f"  Email digest envoyé à {USER_EMAIL}")
