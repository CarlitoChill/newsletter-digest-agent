"""
Écriture dans Notion : digest hebdomadaire + idées de boîtes.

- Le digest va dans "Newsletters Digests" (sous Dashboard Largo)
- Les idées vont dans la database "Request for Startups" (inline, avec propriétés)
"""

import json
import re

from notion_client import Client

from src.config import NOTION_TOKEN, NOTION_DIGESTS_PAGE_ID, NOTION_IDEAS_DB_ID
from src.analysis.analyzer import generate_idea_deck


notion = Client(auth=NOTION_TOKEN)


def _markdown_to_notion_blocks(markdown: str) -> list[dict]:
    """
    Convertit du Markdown simple en blocs Notion.
    Supporte : headings (##), paragraphes, listes (-), dividers (---), bold (**).
    """
    blocks = []
    lines = markdown.split("\n")

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        if stripped == "---":
            blocks.append({"type": "divider", "divider": {}})
            continue

        if stripped.startswith("## "):
            blocks.append({
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[3:]}}]
                },
            })
            continue

        if stripped.startswith("### "):
            blocks.append({
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[4:]}}]
                },
            })
            continue

        if stripped.startswith("- ") or stripped.startswith("• "):
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[2:]}}]
                },
            })
            continue

        # Paragraphe par défaut — on gère le bold **text**
        rich_text = _parse_rich_text(stripped)
        blocks.append({
            "type": "paragraph",
            "paragraph": {"rich_text": rich_text},
        })

    return blocks


def _parse_rich_text(text: str) -> list[dict]:
    """Parse le bold (**text**) dans un texte pour créer du rich_text Notion."""
    parts = re.split(r"(\*\*.*?\*\*)", text)
    rich_text = []
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            rich_text.append({
                "type": "text",
                "text": {"content": part[2:-2]},
                "annotations": {"bold": True},
            })
        elif part:
            rich_text.append({
                "type": "text",
                "text": {"content": part},
            })
    return rich_text


def create_digest_page(
    week_number: int,
    year: int,
    digest: dict,
    analyses: list[dict],
) -> str:
    """
    Crée la page de digest hebdomadaire dans Notion.

    Args:
        week_number: Numéro de la semaine.
        year: Année.
        digest: Le digest compilé (JSON du LLM).
        analyses: Les analyses individuelles de la semaine.

    Returns:
        URL de la page Notion créée.
    """
    title = f"Digest Semaine {week_number} — {year}"

    # Construire le contenu Markdown
    md = f"## Résumé de la semaine\n\n{digest.get('week_summary', '')}\n\n---\n\n"

    md += "## Top Insights\n\n"
    for i, insight in enumerate(digest.get("top_insights", []), 1):
        md += f"### {i}. {insight.get('insight', '')}\n"
        md += f"**Source :** {insight.get('source', '')}\n\n"
        deep_dive = insight.get('deep_dive', insight.get('why_it_matters', ''))
        if deep_dive:
            md += f"{deep_dive}\n\n"
        advisor_angle = insight.get('advisor_angle', '')
        if advisor_angle:
            md += f"**Advisory angle :** {advisor_angle}\n\n"

    themes = digest.get("recurring_themes", [])
    if themes:
        md += "---\n\n## Thèmes récurrents\n\n"
        for theme in themes:
            md += f"### {theme.get('theme', '')}\n"
            for signal in theme.get("signals", []):
                md += f"- {signal}\n"
            thesis = theme.get("thesis", theme.get("implication", ""))
            md += f"\n{thesis}\n\n"

    md += "---\n\n## Playbook Advisor\n\n"
    md += f"{digest.get('advisor_playbook', '')}\n\n"

    top_ideas = digest.get("top_ideas", [])
    if top_ideas:
        md += "---\n\n## Idées de boîtes\n\n"
        for idea in top_ideas:
            conviction = idea.get("conviction_level", "")
            md += f"### {idea.get('name', '')} ({conviction})\n"
            md += f"{idea.get('one_liner', '')}\n"
            quick_take = idea.get("quick_take", "")
            if quick_take:
                md += f"\n{quick_take}\n\n"

    md += "\n---\n\n## Sources analysées cette semaine\n\n"
    for a in analyses:
        md += f"- {a.get('source', '')} — *{a.get('title', '')}*\n"

    blocks = _markdown_to_notion_blocks(md)

    # Notion API limite à 100 blocs par appel
    children = blocks[:100]

    page = notion.pages.create(
        parent={"page_id": NOTION_DIGESTS_PAGE_ID},
        properties={
            "title": [{"text": {"content": title}}],
        },
        children=children,
    )

    # Si plus de 100 blocs, ajouter le reste
    if len(blocks) > 100:
        for i in range(100, len(blocks), 100):
            notion.blocks.children.append(
                block_id=page["id"],
                children=blocks[i : i + 100],
            )

    url = page.get("url", "")
    print(f"  Page digest créée : {url}")
    return url


def create_idea_page(
    idea_name: str,
    one_liner: str,
    why_now: str,
    sources: str,
    source_urls: list[str] | None = None,
    tldr: str = "",
    score: int | None = None,
    tags: list[str] | None = None,
    week_label: str = "",
) -> str:
    """
    Crée une entrée dans la database "Request for Startups" avec le mini-deck.

    Args:
        idea_name: Nom de l'idée.
        one_liner: Description en une phrase.
        why_now: Pourquoi maintenant.
        sources: Sources d'où vient l'idée.
        source_urls: URLs des contenus sources (newsletters, YouTube, podcasts).
        tldr: TLDR de 50 mots (affiché dans un callout jaune en haut + propriété DB).
        score: Note de 0 à 10 attribuée par le "partner VC".
        tags: Liste de tags (SaaS, Marketplace, AI Agency, etc.).
        week_label: Label de la semaine (ex: "Semaine 7").

    Returns:
        URL de la page Notion créée.
    """
    # Callout jaune TLDR + score en haut de la page
    callout_blocks = []
    if tldr or score is not None:
        score_display = f" {score}/10" if score is not None else ""
        callout_text = f"{score_display}  —  {tldr}" if tldr else f"{score_display}"
        callout_blocks.append({
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": callout_text.strip()}}],
                "icon": {"type": "emoji", "emoji": "💡"},
                "color": "yellow_background",
            },
        })
        callout_blocks.append({"type": "divider", "divider": {}})

    # Générer le mini-deck avec Gemini
    deck_markdown = generate_idea_deck(idea_name, one_liner, why_now, sources)

    # Ajouter les liens sources à la fin du deck
    if source_urls:
        deck_markdown += "\n\n---\n\n## Sources\n\n"
        for url in source_urls:
            deck_markdown += f"- {url}\n"

    deck_blocks = _markdown_to_notion_blocks(deck_markdown)

    # Callout en premier, puis le deck
    all_blocks = callout_blocks + deck_blocks
    children = all_blocks[:100]

    # Propriétés de la database
    properties = {
        "title": [{"text": {"content": idea_name}}],
    }
    if score is not None:
        properties["Score"] = score
    if tldr:
        properties["TLDR"] = tldr
    if tags:
        valid_tags = [
            "SaaS", "Marketplace", "AI Agency", "AI-Powered Agency",
            "Platform", "Infrastructure", "B2B", "B2C",
            "HealthTech", "EdTech", "Gaming", "FinTech", "SpaceTech", "DeepTech",
        ]
        filtered_tags = [t for t in tags if t in valid_tags]
        if filtered_tags:
            properties["Tags"] = json.dumps(filtered_tags)
    if sources:
        properties["Source"] = sources
    if week_label:
        properties["Semaine"] = week_label
    properties["Status"] = "Nouveau"

    page = notion.pages.create(
        parent={"database_id": NOTION_IDEAS_DB_ID},
        properties=properties,
        children=children,
    )

    if len(all_blocks) > 100:
        for i in range(100, len(all_blocks), 100):
            notion.blocks.children.append(
                block_id=page["id"],
                children=all_blocks[i : i + 100],
            )

    url = page.get("url", "")
    print(f"  Page idée créée : {idea_name} ({score}/10) → {url}")
    return url
