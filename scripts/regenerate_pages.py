#!/usr/bin/env python3
"""
Régénère le contenu de toutes les pages de la DB "Request for Startups".

Pour chaque page :
1. Récupère les données originales de l'idée depuis SQLite
2. Supprime tous les blocs existants
3. Relance le boardroom debate (avec startup_alternative)
4. Lance l'analyse concurrentielle
5. Génère le mini-deck
6. Reconstruit tous les blocs dans le bon ordre
7. Met à jour les propriétés (scores des board members)

Usage:
  cd projects/01-newsletter-digest
  source .venv/bin/activate
  python scripts/regenerate_pages.py
  python scripts/regenerate_pages.py --dry-run   # affiche ce qui serait fait sans rien modifier
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from notion_client import Client
from notion_client.errors import APIResponseError

from src.config import NOTION_TOKEN, NOTION_IDEAS_DB_ID
from src.analysis.analyzer import (
    run_boardroom_debate,
    analyze_competitors,
    generate_idea_deck,
)
from src.output.notion_writer import (
    _build_verdict_blocks,
    _build_member_blocks,
    _build_competitor_blocks,
    _markdown_to_notion_blocks,
)
from src.storage.db import _get_connection


notion = Client(auth=NOTION_TOKEN)

INTER_PAGE_DELAY = 10
POST_BOARDROOM_DELAY = 5
NOTION_CALL_DELAY = 0.4


def _notion_call(fn, *args, **kwargs):
    """Appel Notion simple avec retry uniquement sur 429."""
    for attempt in range(3):
        try:
            result = fn(*args, **kwargs)
            time.sleep(NOTION_CALL_DELAY)
            return result
        except APIResponseError as e:
            if e.status == 429:
                delay = 3 * (2 ** attempt)
                print(f"    Rate limit Notion, retry dans {delay}s...")
                time.sleep(delay)
                continue
            raise
        except Exception:
            raise
    raise RuntimeError("Notion rate limit après 3 retries")


# ---------------------------------------------------------------------------
# Notion helpers
# ---------------------------------------------------------------------------

def get_all_notion_pages() -> list[dict]:
    """Récupère toutes les pages de la DB Request for Startups."""
    pages = []
    response = notion.data_sources.query(data_source_id=NOTION_IDEAS_DB_ID)
    pages.extend(response["results"])
    while response.get("has_more"):
        response = notion.data_sources.query(
            data_source_id=NOTION_IDEAS_DB_ID,
            start_cursor=response["next_cursor"],
        )
        pages.extend(response["results"])
    return pages


def get_page_title(page: dict) -> str:
    title_prop = page["properties"].get("Name", {})
    if "title" in title_prop:
        return "".join(t["plain_text"] for t in title_prop["title"])
    return ""


def get_page_text_property(page: dict, prop_name: str) -> str:
    prop = page["properties"].get(prop_name, {})
    prop_type = prop.get("type", "")
    if prop_type == "rich_text":
        return "".join(t["plain_text"] for t in prop.get("rich_text", []))
    if prop_type == "title":
        return "".join(t["plain_text"] for t in prop.get("title", []))
    return ""


def read_page_text(page_id: str) -> str:
    """Lit tout le contenu texte d'une page (blocs top-level) pour le contexte."""
    text_parts = []
    cursor = None
    while True:
        kwargs = {"block_id": page_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        try:
            response = _notion_call(
                notion.blocks.children.list, **kwargs
            )
        except Exception:
            break
        for block in response["results"]:
            if block.get("archived"):
                continue
            block_type = block["type"]
            block_data = block.get(block_type, {})
            for rt in block_data.get("rich_text", []):
                text_parts.append(rt.get("plain_text", ""))
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
    return "\n".join(text_parts)


def delete_all_blocks(page_id: str):
    """
    Supprime tous les blocs non-archivés d'une page.
    Phase 1 : collecte tous les IDs (lecture seule, curseur stable).
    Phase 2 : supprime chaque bloc (skip instantané sur "ghost" blocks archivés).
    """
    # Phase 1 : collecter tous les block IDs non-archivés
    all_ids = []
    cursor = None
    while True:
        kwargs = {"block_id": page_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        try:
            response = _notion_call(notion.blocks.children.list, **kwargs)
        except Exception as e:
            print(f"    ⚠ Erreur listing: {e}")
            break
        for block in response["results"]:
            if not block.get("archived"):
                all_ids.append(block["id"])
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")

    if not all_ids:
        return

    print(f"    {len(all_ids)} blocs à supprimer...")

    # Phase 2 : supprimer chaque bloc
    deleted = 0
    ghost = 0
    for block_id in all_ids:
        try:
            _notion_call(notion.blocks.delete, block_id=block_id)
            deleted += 1
        except APIResponseError as e:
            if "archived" in str(e).lower():
                ghost += 1
            elif e.status == 429:
                time.sleep(5)
                try:
                    _notion_call(notion.blocks.delete, block_id=block_id)
                    deleted += 1
                except Exception:
                    pass
        except Exception:
            pass

    parts = [f"{deleted} supprimés"]
    if ghost:
        parts.append(f"{ghost} fantômes ignorés")
    print(f"    {', '.join(parts)}")


def append_blocks(page_id: str, blocks: list[dict]):
    """Ajoute des blocs à une page par chunks de 100."""
    for i in range(0, len(blocks), 100):
        _notion_call(
            notion.blocks.children.append,
            block_id=page_id,
            children=blocks[i : i + 100],
        )


# ---------------------------------------------------------------------------
# SQLite lookup
# ---------------------------------------------------------------------------

def get_all_ideas_from_sqlite() -> dict[str, dict]:
    """Charge toutes les idées depuis SQLite, indexées par nom."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT a.ideas, c.raw_text, c.source, c.title "
        "FROM analyses a JOIN contents c ON a.content_id = c.id"
    ).fetchall()
    conn.close()

    ideas_map: dict[str, dict] = {}
    for row in rows:
        ideas_list = json.loads(row["ideas"]) if row["ideas"] else []
        for idea in ideas_list:
            name = idea.get("name", "")
            if name:
                ideas_map[name] = {
                    **idea,
                    "source_context": row["raw_text"] or "",
                    "source_label": f"{row['source']} — {row['title']}",
                }
    return ideas_map


# ---------------------------------------------------------------------------
# Block construction
# ---------------------------------------------------------------------------

def build_page_blocks(
    tldr: str,
    display_score,
    boardroom: dict,
    deck_markdown: str,
    competitors: dict,
    source_urls: list[str] | None = None,
) -> list[dict]:
    """Construit tous les blocs d'une page dans l'ordre voulu."""

    # 1. Callout TLDR + score
    callout_blocks = []
    if tldr or display_score is not None:
        score_display = f" {display_score}/10" if display_score is not None else ""
        callout_text = f"{score_display}  —  {tldr}" if tldr else f"{score_display}"
        callout_blocks.append({
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": callout_text.strip()}}],
                "icon": {"type": "emoji", "emoji": "💡"},
                "color": "yellow_background",
            },
        })

    # 2. Verdict du board & next steps
    verdict_blocks = _build_verdict_blocks(boardroom) if boardroom.get("verdicts") else []

    # 3. Avis individuels
    member_blocks = _build_member_blocks(boardroom) if boardroom.get("verdicts") else []

    # 4. Mini-deck
    if source_urls:
        deck_markdown += "\n\n---\n\n## Sources\n\n"
        for url in source_urls:
            deck_markdown += f"- {url}\n"

    deck_blocks = []
    if deck_markdown:
        deck_blocks.append({"type": "divider", "divider": {}})
        deck_blocks.extend(_markdown_to_notion_blocks(deck_markdown))

    # 5. Analyse concurrentielle
    competitor_blocks = _build_competitor_blocks(competitors) if competitors else []

    return callout_blocks + verdict_blocks + member_blocks + deck_blocks + competitor_blocks


# ---------------------------------------------------------------------------
# Page regeneration
# ---------------------------------------------------------------------------

def regenerate_page(page: dict, idea_data: dict):
    """Régénère le contenu et les propriétés d'une seule page."""
    page_id = page["id"]
    idea_name = idea_data["name"]
    one_liner = idea_data.get("one_liner", "")
    why_now = idea_data.get("why_now", "")
    tldr = idea_data.get("tldr", "")
    source_context = idea_data.get("source_context", "")
    source_label = idea_data.get("source_label", "")

    # --- Supprimer le contenu existant ---
    print("  [1/5] Suppression des blocs existants...")
    delete_all_blocks(page_id)

    # --- Boardroom debate ---
    print("  [2/5] Boardroom debate...")
    idea_dict = {"name": idea_name, "one_liner": one_liner, "why_now": why_now}
    boardroom = run_boardroom_debate(idea_dict, source_context)
    time.sleep(POST_BOARDROOM_DELAY)

    # --- Analyse concurrentielle ---
    print("  [3/5] Analyse concurrentielle...")
    competitors = analyze_competitors(idea_name, one_liner, why_now)
    time.sleep(POST_BOARDROOM_DELAY)

    # --- Mini-deck ---
    print("  [4/5] Génération du mini-deck...")
    deck_markdown = generate_idea_deck(idea_name, one_liner, why_now, source_label)

    # --- Construire et écrire les blocs ---
    print("  [5/5] Écriture des blocs Notion...")
    display_score = boardroom.get("synthesis", {}).get("final_score")
    all_blocks = build_page_blocks(
        tldr=tldr,
        display_score=display_score,
        boardroom=boardroom,
        deck_markdown=deck_markdown,
        competitors=competitors,
    )

    if all_blocks:
        append_blocks(page_id, all_blocks)

    # --- Mettre à jour les propriétés (scores des membres) ---
    properties: dict = {}
    member_to_column = {
        "steve_jobs": "Steve",
        "ann_miura_ko": "Ann",
        "ben_horowitz": "Ben",
        "jdlr": "Jean",
    }
    if boardroom and boardroom.get("verdicts"):
        for v in boardroom["verdicts"]:
            column = member_to_column.get(v.get("member_id", ""))
            member_score = v.get("score")
            if column and member_score is not None:
                properties[column] = {"number": member_score}

    if properties:
        _notion_call(
            notion.pages.update, page_id=page_id, properties=properties
        )

    # --- Résumé ---
    consensus = boardroom.get("synthesis", {}).get("consensus", "?")
    comp_count = len(competitors.get("competitors", [])) if competitors else 0
    score_label = f"{display_score}/10" if display_score else "?"
    print(f"  -> {len(all_blocks)} blocs | score {score_label} | {consensus} | {comp_count} concurrents")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    dry_run = "--dry-run" in sys.argv

    sep = "=" * 60
    print(f"\n{sep}")
    print("  RÉGÉNÉRATION — Request for Startups")
    mode_label = "DRY RUN (aucune modification)" if dry_run else "PRODUCTION"
    print(f"  Mode : {mode_label}")
    print(sep)

    # Charger les données SQLite
    print("\nChargement des idées depuis SQLite...")
    ideas_map = get_all_ideas_from_sqlite()
    print(f"  {len(ideas_map)} idées trouvées en base")

    # Récupérer les pages Notion
    print("\nRécupération des pages Notion...")
    pages = get_all_notion_pages()
    print(f"  {len(pages)} pages dans la database")

    # Matcher et préparer les données pour chaque page
    plan: list[tuple[dict, dict]] = []
    from_sqlite = 0
    from_notion = 0

    for page in pages:
        title = get_page_title(page)
        idea_data = ideas_map.get(title)
        if idea_data:
            plan.append((page, idea_data))
            from_sqlite += 1
        else:
            # Pas de données SQLite : on utilise les propriétés de la page
            tldr = get_page_text_property(page, "TLDR")
            source = get_page_text_property(page, "Source")
            plan.append((page, {
                "name": title,
                "one_liner": tldr or title,
                "why_now": "",
                "tldr": tldr,
                "source_context": None,  # sera lu depuis la page avant suppression
                "source_label": source or "Unknown",
            }))
            from_notion += 1

    print(f"\n  {len(plan)} pages à traiter :")
    print(f"    - {from_sqlite} avec données SQLite complètes")
    print(f"    - {from_notion} avec données extraites de Notion")
    for _, idea_data in plan:
        src = "SQLite" if idea_data.get("source_context") is not None else "Notion"
        print(f"    [{src}] {idea_data['name']}")

    if dry_run:
        print("\n[DRY RUN] Aucune modification effectuée.")
        return

    # Régénérer chaque page
    success = 0
    errors = []

    for i, (page, idea_data) in enumerate(plan, 1):
        name = idea_data["name"]
        page_id = page["id"]
        sep = "=" * 60
        print(f"\n{sep}")
        print(f"[{i}/{len(plan)}] {name}")
        print(sep)

        # Si pas de source_context (page sans SQLite), lire le contenu existant
        if idea_data.get("source_context") is None:
            print("  [0] Lecture du contenu existant comme contexte...")
            idea_data["source_context"] = read_page_text(page_id)

        try:
            regenerate_page(page, idea_data)
            success += 1
        except Exception as e:
            print(f"  ERREUR : {e}")
            import traceback
            traceback.print_exc()
            errors.append(name)

        if i < len(plan):
            print(f"  Pause {INTER_PAGE_DELAY}s...")
            time.sleep(INTER_PAGE_DELAY)

    # Résumé final
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  RÉSULTAT : {success}/{len(plan)} pages régénérées")
    if errors:
        print(f"  Erreurs ({len(errors)}) :")
        for e in errors:
            print(f"    - {e}")
    print(sep + "\n")


if __name__ == "__main__":
    main()
