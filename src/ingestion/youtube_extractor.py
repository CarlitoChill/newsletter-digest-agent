from __future__ import annotations

"""
Extraction de transcriptions YouTube.

Utilise youtube-transcript-api pour récupérer les sous-titres.
Fallback : si pas de sous-titres, on pourrait utiliser Whisper,
mais c'est rarement nécessaire (YouTube génère des sous-titres auto).
"""

import re

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter


def _extract_video_id(url: str) -> str | None:
    """Extrait l'ID vidéo depuis une URL YouTube."""
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/live/)([a-zA-Z0-9_-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def extract_youtube_transcript(url: str) -> dict:
    """
    Récupère la transcription d'une vidéo YouTube.

    Args:
        url: URL de la vidéo YouTube.

    Returns:
        Dict avec 'title' (l'URL pour l'instant), 'content' (transcription texte).
    """
    video_id = _extract_video_id(url)
    if not video_id:
        return {
            "title": url,
            "content": f"[Impossible d'extraire l'ID vidéo depuis {url}]",
        }

    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=["fr", "en"])
        formatter = TextFormatter()
        text = formatter.format_transcript(transcript)

        return {
            "title": f"YouTube: {video_id}",
            "content": text,
        }
    except Exception as e:
        return {
            "title": f"YouTube: {video_id}",
            "content": f"[Erreur transcription YouTube : {e}]",
        }
