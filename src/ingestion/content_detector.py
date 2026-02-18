from __future__ import annotations

"""
Détection du type de contenu d'un email.

Analyse le body de l'email pour déterminer s'il contient :
- Un lien YouTube → extraction de transcription
- Un lien Spotify/Apple Podcasts → download audio + Whisper
- Du contenu newsletter HTML → parsing HTML
"""

import re
from dataclasses import dataclass
from enum import Enum

from src.ingestion.email_reader import RawEmail


class ContentType(Enum):
    NEWSLETTER = "newsletter"
    YOUTUBE = "youtube"
    PODCAST_SPOTIFY = "podcast_spotify"
    PODCAST_APPLE = "podcast_apple"


@dataclass
class DetectedContent:
    """Résultat de la détection de contenu."""
    content_type: ContentType
    url: str | None = None  # URL extraite (YouTube, Spotify, Apple Podcasts)
    raw_email: RawEmail | None = None


# Patterns pour détecter les URLs
YOUTUBE_PATTERNS = [
    r"https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)",
    r"https?://youtu\.be/([a-zA-Z0-9_-]+)",
    r"https?://(?:www\.)?youtube\.com/live/([a-zA-Z0-9_-]+)",
]

SPOTIFY_PATTERNS = [
    r"https?://open\.spotify\.com/episode/([a-zA-Z0-9]+)",
    r"https?://open\.spotify\.com/show/([a-zA-Z0-9]+)",
]

APPLE_PODCAST_PATTERNS = [
    r"https?://podcasts\.apple\.com/.+/id\d+",
]


def _find_url(text: str, patterns: list[str]) -> str | None:
    """Cherche la première URL matchant un des patterns dans le texte."""
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None


def detect_content(email: RawEmail) -> DetectedContent:
    """
    Analyse un email et détermine son type de contenu.

    Logique de priorité :
    1. Si on trouve un lien YouTube → YouTube
    2. Si on trouve un lien Spotify → Podcast Spotify
    3. Si on trouve un lien Apple Podcasts → Podcast Apple
    4. Sinon → Newsletter HTML
    """
    search_text = f"{email.subject} {email.text_body} {email.html_body}"

    youtube_url = _find_url(search_text, YOUTUBE_PATTERNS)
    if youtube_url:
        return DetectedContent(
            content_type=ContentType.YOUTUBE,
            url=youtube_url,
            raw_email=email,
        )

    spotify_url = _find_url(search_text, SPOTIFY_PATTERNS)
    if spotify_url:
        return DetectedContent(
            content_type=ContentType.PODCAST_SPOTIFY,
            url=spotify_url,
            raw_email=email,
        )

    apple_url = _find_url(search_text, APPLE_PODCAST_PATTERNS)
    if apple_url:
        return DetectedContent(
            content_type=ContentType.PODCAST_APPLE,
            url=apple_url,
            raw_email=email,
        )

    return DetectedContent(
        content_type=ContentType.NEWSLETTER,
        raw_email=email,
    )
