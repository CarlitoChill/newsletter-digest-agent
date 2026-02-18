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


def _build_verdict_blocks(boardroom: dict) -> list[dict]:
    """Construit les blocs Notion pour le verdict du board + next steps (section 1)."""
    blocks = []
    synthesis = boardroom.get("synthesis", {})
    if not synthesis:
        return blocks

    verdict_emojis = {"invest": "✅", "pass": "❌", "no_consensus": "🔍"}

    final_score = synthesis.get("final_score", "?")
    consensus = synthesis.get("consensus", "?")
    consensus_emoji = verdict_emojis.get(consensus, "❓")

    blocks.append({"type": "divider", "divider": {}})
    blocks.append({
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": f"Verdict du Board — {consensus_emoji} {consensus} ({final_score}/10)"}}]
        },
    })

    synth_text = synthesis.get("synthesis", "")
    if synth_text:
        blocks.append({
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": synth_text}}],
                "icon": {"type": "emoji", "emoji": "📋"},
                "color": "purple_background",
            },
        })

    debate_point = synthesis.get("key_debate_point", "")
    if debate_point:
        blocks.append({
            "type": "paragraph",
            "paragraph": {"rich_text": [
                {"type": "text", "text": {"content": "Point de friction : "}, "annotations": {"bold": True}},
                {"type": "text", "text": {"content": debate_point}},
            ]},
        })

    next_steps = synthesis.get("next_steps", [])
    if next_steps:
        blocks.append({
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": "Next steps"}}]
            },
        })
        for step in next_steps:
            blocks.append({
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": step}}],
                    "checked": False,
                },
            })

    return blocks


def _build_member_blocks(boardroom: dict) -> list[dict]:
    """Construit les blocs Notion pour les avis individuels des board members (section 2)."""
    blocks = []
    verdicts = boardroom.get("verdicts", [])
    if not verdicts:
        return blocks

    verdict_emojis = {"invest": "✅", "pass": "❌", "dig_deeper": "🔍"}

    blocks.append({"type": "divider", "divider": {}})
    blocks.append({
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "Avis du Board"}}]
        },
    })

    for v in verdicts:
        emoji = v.get("member_emoji", "👤")
        name = v.get("member_name", "?")
        verdict = v.get("verdict", "?")
        verdict_emoji = verdict_emojis.get(verdict, "❓")
        score = v.get("score", "?")
        conviction = v.get("conviction", "?")

        blocks.append({
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": f"{emoji} {name} — {verdict_emoji} {verdict} ({score}/10)"}}]
            },
        })

        blocks.append({
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": f"Conviction : {conviction}"}}],
                "icon": {"type": "emoji", "emoji": verdict_emoji},
                "color": {
                    "invest": "green_background",
                    "pass": "red_background",
                    "dig_deeper": "blue_background",
                }.get(verdict, "gray_background"),
            },
        })

        arg_for = v.get("argument_for", "")
        if arg_for:
            blocks.append({
                "type": "paragraph",
                "paragraph": {"rich_text": [
                    {"type": "text", "text": {"content": "Pour : "}, "annotations": {"bold": True}},
                    {"type": "text", "text": {"content": arg_for}},
                ]},
            })

        arg_against = v.get("argument_against", "")
        if arg_against:
            blocks.append({
                "type": "paragraph",
                "paragraph": {"rich_text": [
                    {"type": "text", "text": {"content": "Contre : "}, "annotations": {"bold": True}},
                    {"type": "text", "text": {"content": arg_against}},
                ]},
            })

        key_q = v.get("key_question", "")
        if key_q:
            blocks.append({
                "type": "paragraph",
                "paragraph": {"rich_text": [
                    {"type": "text", "text": {"content": "Question clé : "}, "annotations": {"bold": True, "italic": True}},
                    {"type": "text", "text": {"content": key_q}, "annotations": {"italic": True}},
                ]},
            })

        alt = v.get("startup_alternative", "")
        if alt:
            blocks.append({
                "type": "callout",
                "callout": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "Ma startup : "}, "annotations": {"bold": True}},
                        {"type": "text", "text": {"content": alt}},
                    ],
                    "icon": {"type": "emoji", "emoji": "🚀"},
                    "color": "yellow_background",
                },
            })

    return blocks


def _build_competitor_blocks(competitors: dict) -> list[dict]:
    """Construit les blocs Notion pour l'analyse concurrentielle (section 4)."""
    blocks = []
    if not competitors or not competitors.get("competitors"):
        return blocks

    blocks.append({"type": "divider", "divider": {}})
    blocks.append({
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "Analyse concurrentielle"}}]
        },
    })

    market_insight = competitors.get("market_insight", "")
    maturity = competitors.get("market_maturity", "")
    if market_insight:
        maturity_label = {
            "nascent": "Naissant", "emerging": "Émergent", "growing": "En croissance",
            "mature": "Mature", "saturated": "Saturé",
        }.get(maturity, maturity)
        blocks.append({
            "type": "callout",
            "callout": {
                "rich_text": [
                    {"type": "text", "text": {"content": f"Marché : {maturity_label}\n"}, "annotations": {"bold": True}},
                    {"type": "text", "text": {"content": market_insight}},
                ],
                "icon": {"type": "emoji", "emoji": "🏟️"},
                "color": "blue_background",
            },
        })

    threat_emojis = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    type_labels = {"direct": "Direct", "indirect": "Indirect", "adjacent": "Adjacent"}

    for comp in competitors.get("competitors", []):
        name = comp.get("name", "?")
        comp_type = type_labels.get(comp.get("type", ""), "?")
        threat = comp.get("threat_level", "?")
        threat_emoji = threat_emojis.get(threat, "⚪")
        url = comp.get("url", "")
        desc = comp.get("description", "")
        funding = comp.get("funding", "")
        diff = comp.get("differentiation", "")

        header = f"{threat_emoji} {name} — {comp_type}"
        if url:
            header = f"{threat_emoji} {name} ({url}) — {comp_type}"

        blocks.append({
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": header}}]
            },
        })

        body_parts = []
        if desc:
            body_parts.append(desc)
        if funding:
            body_parts.append(f"Financement : {funding}")
        if diff:
            body_parts.append(f"Notre différence : {diff}")

        if body_parts:
            blocks.append({
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": "\n".join(body_parts)}}]},
            })

    moat = competitors.get("moat_assessment", "")
    if moat:
        blocks.append({
            "type": "callout",
            "callout": {
                "rich_text": [
                    {"type": "text", "text": {"content": "Moat : "}, "annotations": {"bold": True}},
                    {"type": "text", "text": {"content": moat}},
                ],
                "icon": {"type": "emoji", "emoji": "🏰"},
                "color": "green_background",
            },
        })

    return blocks


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
    boardroom: dict | None = None,
    competitors: dict | None = None,
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
        boardroom: Résultats du AI Boardroom (verdicts + synthesis).

    Returns:
        URL de la page Notion créée.
    """
    # Callout jaune TLDR + score en haut de la page
    callout_blocks = []

    # Si boardroom, le score affiché est le score final du board
    display_score = score
    if boardroom and boardroom.get("synthesis", {}).get("final_score"):
        display_score = boardroom["synthesis"]["final_score"]

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
        callout_blocks.append({"type": "divider", "divider": {}})

    # Générer le mini-deck avec Gemini
    deck_markdown = generate_idea_deck(idea_name, one_liner, why_now, sources)

    # Ajouter les liens sources à la fin du deck
    if source_urls:
        deck_markdown += "\n\n---\n\n## Sources\n\n"
        for url in source_urls:
            deck_markdown += f"- {url}\n"

    deck_blocks = _markdown_to_notion_blocks(deck_markdown)

    # Boardroom : verdict du board (section 1) + avis individuels (section 2)
    verdict_blocks = []
    member_blocks = []
    if boardroom and boardroom.get("verdicts"):
        verdict_blocks = _build_verdict_blocks(boardroom)
        member_blocks = _build_member_blocks(boardroom)

    # Analyse concurrentielle (section 4)
    competitor_blocks = []
    if competitors:
        competitor_blocks = _build_competitor_blocks(competitors)

    # Ordre : callout → verdict & next steps → avis individuels → mini-deck → concurrence
    all_blocks = callout_blocks + verdict_blocks + member_blocks + deck_blocks + competitor_blocks
    children = all_blocks[:100]

    # Propriétés de la database — format API Notion (type wrappers obligatoires)
    properties = {
        "title": {"title": [{"text": {"content": idea_name}}]},
    }
    if tldr:
        properties["TLDR"] = {"rich_text": [{"text": {"content": tldr[:2000]}}]}
    if tags:
        valid_tags = [
            "SaaS", "Marketplace", "AI Agency", "AI-Powered Agency",
            "Platform", "Infrastructure", "B2B", "B2C",
            "HealthTech", "EdTech", "Gaming", "FinTech", "SpaceTech", "DeepTech",
        ]
        filtered_tags = [t for t in tags if t in valid_tags]
        if filtered_tags:
            properties["Tags"] = {"multi_select": [{"name": t} for t in filtered_tags]}
    if sources:
        properties["Source"] = {"rich_text": [{"text": {"content": sources[:2000]}}]}
    if week_label:
        properties["Semaine"] = {"rich_text": [{"text": {"content": week_label}}]}
    properties["Status"] = {"select": {"name": "Nouveau"}}

    if boardroom and boardroom.get("verdicts"):
        member_to_column = {
            "steve_jobs": "Steve",
            "ann_miura_ko": "Ann",
            "ben_horowitz": "Ben",
            "jdlr": "Jean",
        }
        for v in boardroom["verdicts"]:
            column = member_to_column.get(v.get("member_id", ""))
            member_score = v.get("score")
            if column and member_score is not None:
                properties[column] = {"number": member_score}

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
    board_label = f" [Board: {boardroom['synthesis'].get('consensus', '?')}]" if boardroom and boardroom.get("synthesis") else ""
    print(f"  Page idée créée : {idea_name} ({display_score}/10){board_label} → {url}")
    return url
