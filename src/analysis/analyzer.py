"""
Analyse de contenu avec Google Gemini 2.0 Flash.

Ce module prend du contenu extrait (newsletter, YouTube, podcast)
et l'envoie à Gemini pour analyse avec la lentille "partner VC".
"""

import json
import time

import google.generativeai as genai

from src.config import GEMINI_API_KEY, GEMINI_MODEL
from src.analysis.prompts import ANALYSIS_PROMPT, DIGEST_PROMPT, IDEA_PROMPT


genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 10  # secondes


def _clean_json_response(text: str) -> str:
    """
    Nettoie la réponse de Gemini pour extraire le JSON.
    Gemini entoure parfois le JSON de ```json ... ```.
    """
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _call_gemini_with_retry(prompt: str) -> str:
    """
    Appelle Gemini avec retry automatique sur les erreurs 429 (rate limit).
    Backoff exponentiel : 10s, 20s, 40s.
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e) and attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                print(f"    Rate limit Gemini, retry dans {delay}s...")
                time.sleep(delay)
            else:
                raise


def analyze_content(
    content: str,
    title: str,
    source: str,
    content_type: str,
) -> dict:
    """
    Analyse un contenu individuel avec Gemini.

    Args:
        content: Le texte extrait (newsletter, transcription, etc.)
        title: Le titre du contenu.
        source: La source (expéditeur, chaîne YouTube, etc.)
        content_type: "newsletter", "youtube", "podcast_spotify", "podcast_apple"

    Returns:
        Dict avec takeaways, so_what_advisor, ideas, signal_strength, topics.
    """
    prompt = ANALYSIS_PROMPT.format(
        source=source,
        title=title,
        content_type=content_type,
        content=content[:100_000],  # Limite de sécurité (Gemini supporte 1M mais on reste raisonnable)
    )

    try:
        raw_text = _call_gemini_with_retry(prompt)
        raw = _clean_json_response(raw_text)
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  Erreur parsing JSON Gemini : {e}")
        print(f"  Réponse brute : {raw_text[:200]}")
        return {
            "takeaways": ["[Erreur d'analyse — réponse non-JSON de Gemini]"],
            "so_what_advisor": "",
            "ideas": [],
            "signal_strength": "weak",
            "topics": [],
        }
    except Exception as e:
        print(f"  Erreur Gemini : {e}")
        return {
            "takeaways": [f"[Erreur Gemini : {e}]"],
            "so_what_advisor": "",
            "ideas": [],
            "signal_strength": "weak",
            "topics": [],
        }


def compile_digest(analyses_text: str) -> dict:
    """
    Compile les analyses de la semaine en un digest hebdomadaire.

    Args:
        analyses_text: Texte formaté de toutes les analyses de la semaine.

    Returns:
        Dict avec week_summary, top_insights, recurring_themes, advisor_playbook, top_ideas.
    """
    prompt = DIGEST_PROMPT.format(analyses=analyses_text)

    try:
        raw_text = _call_gemini_with_retry(prompt)
        raw = _clean_json_response(raw_text)
        return json.loads(raw)
    except Exception as e:
        print(f"  Erreur compilation digest : {e}")
        return {
            "week_summary": f"[Erreur de compilation : {e}]",
            "top_insights": [],
            "recurring_themes": [],
            "advisor_playbook": "",
            "top_ideas": [],
        }


def generate_idea_deck(
    idea_name: str,
    one_liner: str,
    why_now: str,
    sources: str,
) -> str:
    """
    Génère un mini-deck structuré pour une idée de boîte.

    Returns:
        Texte Markdown du mini-deck (format pitch deck JdLR).
    """
    prompt = IDEA_PROMPT.format(
        idea_name=idea_name,
        one_liner=one_liner,
        why_now=why_now,
        sources=sources,
    )

    try:
        return _call_gemini_with_retry(prompt).strip()
    except Exception as e:
        print(f"  Erreur génération idée : {e}")
        return f"[Erreur de génération : {e}]"
