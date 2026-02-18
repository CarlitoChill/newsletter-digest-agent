from __future__ import annotations

"""
Compilation du digest hebdomadaire.

Orchestre les étapes :
1. Récupère les analyses de la semaine depuis SQLite
2. Appelle Gemini pour la synthèse cross-contenu
3. Crée les pages Notion (digest + idées)
4. Envoie l'email
"""

import json
from datetime import datetime

import pytz

from src.config import TIMEZONE, USER_EMAIL
from src.storage.db import get_analyses_since, get_last_digest_date, save_digest, digest_exists
from src.analysis.analyzer import compile_digest
from src.output.notion_writer import create_digest_page
from src.output.email_sender import send_digest_email


def _format_analyses_for_llm(analyses: list[dict]) -> str:
    """Formate les analyses en texte lisible pour le prompt de compilation."""
    parts = []
    for i, a in enumerate(analyses, 1):
        part = f"""
---
### Contenu {i}: {a['title']}
**Source:** {a['source']}
**Type:** {a['content_type']}
**Signal:** {a['signal_strength']}
**Topics:** {', '.join(a.get('topics', []))}

**Takeaways:**
"""
        for t in a.get("takeaways", []):
            part += f"- {t}\n"

        part += f"\n**So what (advisor):** {a.get('so_what_advisor', '')}\n"

        ideas = a.get("ideas", [])
        if ideas:
            part += "\n**Idées:**\n"
            for idea in ideas:
                part += f"- {idea.get('name', '')}: {idea.get('one_liner', '')}\n"

        parts.append(part)

    return "\n".join(parts)


def run_weekly_digest(force: bool = False):
    """
    Lance la compilation et l'envoi du digest hebdomadaire.

    Le digest compile TOUT ce qui a été ingéré depuis le dernier digest envoyé.
    Cycle réel : vendredi midi → vendredi midi (pas lundi → dimanche).
    Aucun contenu ne tombe dans le vide.

    Args:
        force: Si True, recrée le digest même s'il existe déjà cette semaine.
    """
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)

    # Le week_number sert juste pour le label (affichage + clé unique en base)
    week_number = int(now.strftime("%W"))
    year = now.year

    print(f"\n=== Digest Semaine {week_number} — {year} ===\n")

    if not force and digest_exists(week_number, year):
        print(f"  Le digest de la semaine {week_number}/{year} existe déjà. Utilise --force pour le recréer.")
        return

    # 1. Trouver le point de référence : date du dernier digest envoyé
    last_digest_date = get_last_digest_date()
    if last_digest_date:
        print(f"  Dernier digest envoyé le : {last_digest_date}")
    else:
        print("  Premier digest — on compile tout ce qui est en base")

    # 2. Récupérer toutes les analyses depuis le dernier digest
    analyses = get_analyses_since(last_digest_date)
    if not analyses:
        print("  Aucune analyse trouvée depuis le dernier digest. Rien à compiler.")
        return

    print(f"  {len(analyses)} contenus à compiler")

    # 3. Compiler le digest avec Gemini
    print("  Compilation du digest avec Gemini...")
    analyses_text = _format_analyses_for_llm(analyses)
    digest = compile_digest(analyses_text)

    print(f"  → {len(digest.get('top_insights', []))} top insights")
    print(f"  → {len(digest.get('recurring_themes', []))} thèmes récurrents")
    print(f"  → {len(digest.get('top_ideas', []))} idées de boîtes")

    # 4. Créer la page Notion du digest
    print("  Création de la page Notion...")
    notion_url = create_digest_page(week_number, year, digest, analyses)

    # Note : les pages d'idées sont créées au fil de l'eau pendant le poll,
    # pas ici. Ça évite le rate limit Gemini et étale la charge dans le temps.

    # 5. Envoyer l'email
    print("  Envoi de l'email...")
    send_digest_email(week_number, year, digest, notion_url)

    # 6. Sauvegarder en base (sent_at = maintenant, c'est le nouveau point de référence)
    save_digest(week_number, year, digest, notion_url)

    print(f"\n  Digest semaine {week_number}/{year} terminé !")
    print(f"  → Notion : {notion_url}")
    print(f"  → Email envoyé à {USER_EMAIL}")
