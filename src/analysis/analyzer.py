"""
Analyse de contenu avec Google Gemini 2.0 Flash.

Ce module prend du contenu extrait (newsletter, YouTube, podcast)
et l'envoie à Gemini pour analyse avec la lentille "partner VC".

V2 : AI Boardroom — 4 board members débattent chaque idée de boîte.
"""

import json
import time

import google.generativeai as genai

from src.config import GEMINI_API_KEY, GEMINI_MODEL
from src.analysis.prompts import (
    ANALYSIS_PROMPT,
    DIGEST_PROMPT,
    IDEA_PROMPT,
    BOARD_MEMBERS,
    BOARDROOM_MEMBER_PROMPT,
    BOARDROOM_SYNTHESIS_PROMPT,
    COMPETITIVE_ANALYSIS_PROMPT,
)


genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 10  # secondes
BOARDROOM_DELAY = 3    # secondes entre chaque appel boardroom


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


def _get_member_verdict(member: dict, idea: dict, source_context: str) -> dict | None:
    """Appelle Gemini pour obtenir le verdict d'un board member sur une idée."""
    prompt = BOARDROOM_MEMBER_PROMPT.format(
        member_name=member["name"],
        member_role=member["role"],
        member_lens=member["lens"],
        member_style=member["style"],
        member_framework=member["framework"],
        idea_name=idea.get("name", ""),
        one_liner=idea.get("one_liner", ""),
        why_now=idea.get("why_now", ""),
        source_context=source_context[:5000],
    )

    try:
        raw_text = _call_gemini_with_retry(prompt)
        raw = _clean_json_response(raw_text)
        verdict = json.loads(raw)
        verdict["member_name"] = member["name"]
        verdict["member_id"] = member["id"]
        verdict["member_emoji"] = member["emoji"]
        return verdict
    except Exception as e:
        print(f"    Erreur verdict {member['name']} : {e}")
        return None


def _synthesize_verdicts(verdicts: list[dict], idea: dict) -> dict:
    """Synthétise les verdicts des board members en un verdict final."""
    verdicts_text = ""
    for v in verdicts:
        verdicts_text += f"""
### {v['member_name']}
- **Verdict :** {v.get('verdict', '?')} (conviction : {v.get('conviction', '?')})
- **Score :** {v.get('score', '?')}/10
- **Pour :** {v.get('argument_for', '')}
- **Contre :** {v.get('argument_against', '')}
- **Question clé :** {v.get('key_question', '')}
"""

    prompt = BOARDROOM_SYNTHESIS_PROMPT.format(
        verdicts_text=verdicts_text,
        idea_name=idea.get("name", ""),
        one_liner=idea.get("one_liner", ""),
    )

    try:
        raw_text = _call_gemini_with_retry(prompt)
        raw = _clean_json_response(raw_text)
        return json.loads(raw)
    except Exception as e:
        print(f"    Erreur synthèse boardroom : {e}")
        return {
            "final_score": 0,
            "consensus": "no_consensus",
            "synthesis": f"[Erreur de synthèse : {e}]",
            "key_debate_point": "",
            "next_steps": [],
        }


def run_boardroom_debate(idea: dict, source_context: str) -> dict:
    """
    Lance le débat AI Boardroom pour une idée de boîte.

    Chaque board member évalue l'idée indépendamment, puis une synthèse
    produit le verdict final du board.

    Args:
        idea: L'idée à évaluer (dict avec name, one_liner, why_now, etc.)
        source_context: Le contenu source d'où vient l'idée (pour le contexte).

    Returns:
        Dict avec 'verdicts' (list) et 'synthesis' (dict).
    """
    print(f"    Boardroom : {idea.get('name', '')}")
    verdicts = []

    for i, member in enumerate(BOARD_MEMBERS):
        if i > 0:
            time.sleep(BOARDROOM_DELAY)

        print(f"      {member['emoji']} {member['name']}...")
        verdict = _get_member_verdict(member, idea, source_context)
        if verdict:
            verdicts.append(verdict)
            v = verdict.get("verdict", "?")
            s = verdict.get("score", "?")
            print(f"        → {v} ({s}/10)")

    if not verdicts:
        print("    Boardroom : aucun verdict obtenu, skip synthèse")
        return {"verdicts": [], "synthesis": {}}

    time.sleep(BOARDROOM_DELAY)
    print(f"      📋 Synthèse du board...")
    synthesis = _synthesize_verdicts(verdicts, idea)
    print(f"        → Score final : {synthesis.get('final_score', '?')}/10 — {synthesis.get('consensus', '?')}")

    return {"verdicts": verdicts, "synthesis": synthesis}


def analyze_competitors(idea_name: str, one_liner: str, why_now: str) -> dict:
    """
    Analyse concurrentielle d'une idée de startup.

    Identifie 3-5 concurrents directs/indirects/adjacents,
    évalue la maturité du marché et les possibilités de moat.

    Returns:
        Dict avec competitors, market_maturity, market_insight, moat_assessment.
    """
    print(f"    Analyse concurrentielle : {idea_name}")
    prompt = COMPETITIVE_ANALYSIS_PROMPT.format(
        idea_name=idea_name,
        one_liner=one_liner,
        why_now=why_now,
    )

    try:
        raw_text = _call_gemini_with_retry(prompt)
        raw = _clean_json_response(raw_text)
        result = json.loads(raw)
        count = len(result.get("competitors", []))
        maturity = result.get("market_maturity", "?")
        print(f"      → {count} concurrents identifiés, marché : {maturity}")
        return result
    except Exception as e:
        print(f"    Erreur analyse concurrentielle : {e}")
        return {
            "competitors": [],
            "market_maturity": "unknown",
            "market_insight": f"[Erreur d'analyse : {e}]",
            "moat_assessment": "",
        }
