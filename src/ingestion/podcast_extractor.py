from __future__ import annotations

"""
Extraction et transcription de podcasts.

1. Télécharge l'audio avec yt-dlp (supporte Spotify, Apple Podcasts, RSS)
2. Transcrit avec OpenAI Whisper API

Coût : ~$0.006/min soit ~$0.36 pour 1h de podcast.
"""

import os
import tempfile
import subprocess
from pathlib import Path

from openai import OpenAI

from src.config import OPENAI_API_KEY


def _download_audio(url: str, output_dir: str) -> str | None:
    """
    Télécharge l'audio d'un podcast avec yt-dlp.
    Retourne le chemin du fichier audio, ou None si échec.
    """
    output_path = os.path.join(output_dir, "podcast.%(ext)s")

    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "5",  # Qualité suffisante pour la transcription
                "--output", output_path,
                "--no-playlist",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=600,  # 10 min max pour le téléchargement
        )

        if result.returncode != 0:
            print(f"  Erreur yt-dlp : {result.stderr[:200]}")
            return None

        for f in os.listdir(output_dir):
            if f.startswith("podcast."):
                return os.path.join(output_dir, f)

        return None

    except subprocess.TimeoutExpired:
        print("  Timeout yt-dlp (>10 min)")
        return None
    except FileNotFoundError:
        print("  yt-dlp non trouvé. Installe-le avec : pip install yt-dlp")
        return None


def _transcribe_audio(audio_path: str) -> str:
    """
    Transcrit un fichier audio avec OpenAI Whisper API.
    Whisper supporte des fichiers jusqu'à 25 MB. Pour les gros fichiers,
    on pourrait découper, mais la plupart des podcasts en MP3 quality 5
    font moins de 25 MB pour 1h.
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    file_size = os.path.getsize(audio_path)
    print(f"  Transcription Whisper ({file_size / 1024 / 1024:.1f} MB)...")

    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="fr",  # Priorité français, Whisper détecte aussi l'anglais
        )

    return transcript.text


def extract_podcast_transcript(url: str) -> dict:
    """
    Télécharge et transcrit un podcast.

    Args:
        url: URL Spotify, Apple Podcasts, ou RSS du podcast.

    Returns:
        Dict avec 'title' et 'content' (transcription).
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        print(f"  Téléchargement audio depuis {url[:60]}...")
        audio_path = _download_audio(url, tmp_dir)

        if not audio_path:
            return {
                "title": f"Podcast: {url}",
                "content": f"[Impossible de télécharger l'audio depuis {url}]",
            }

        try:
            text = _transcribe_audio(audio_path)
            return {
                "title": f"Podcast: {url}",
                "content": text,
            }
        except Exception as e:
            return {
                "title": f"Podcast: {url}",
                "content": f"[Erreur transcription Whisper : {e}]",
            }
