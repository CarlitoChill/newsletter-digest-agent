"""
Script one-shot : lit toutes les pages de la database Request for Startups,
envoie le contenu à Gemini pour obtenir Score, TLDR, Tags et Source,
puis met à jour les propriétés Notion.

Usage :
  cd projects/01-newsletter-digest
  source .venv/bin/activate
  python scripts/classify_all_ideas.py
"""

import json
import os
import sys
import time
from pathlib import Path

# Force unbuffered output
os.environ["PYTHONUNBUFFERED"] = "1"
sys.stdout.reconfigure(line_buffering=True)

sys.path.insert(0, str(Path(__file__).parent.parent))

import google.generativeai as genai
from notion_client import Client

from src.config import GEMINI_API_KEY, NOTION_TOKEN

# Database ID (from the URL, NOT the data_source/collection ID)
NOTION_IDEAS_DATABASE_ID = "f15fbfbd42334268a6e37af3c0c17adc"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")
notion = Client(auth=NOTION_TOKEN)

VALID_TAGS = [
    "SaaS", "Marketplace", "AI Agency", "AI-Powered Agency",
    "Platform", "Infrastructure", "B2B", "B2C",
    "HealthTech", "EdTech", "Gaming", "FinTech", "SpaceTech", "DeepTech",
]

CLASSIFY_PROMPT = """Tu es un partner VC senior. On te montre une idée de startup. Tu dois la classifier.

## L'idée

**Titre :** {title}

**Contenu :**
{content}

## Output attendu (JSON strict)

```json
{{
  "score": 7,
  "tldr": "TLDR de 50 mots max. Le pitch express : quel problème, quelle solution, pourquoi c'est le bon moment.",
  "tags": ["SaaS", "B2B"],
  "source": "Source probable de l'idée (newsletter, podcast, réflexion personnelle...)"
}}
```

## Règles

- score : entier de 0 à 10. 0 = nulle, 5 = intéressant, 8 = très prometteur, 10 = idée de l'année. Sois exigeant.
- tldr : 50 mots max, en français, direct et percutant.
- tags : 2-4 parmi {valid_tags}. UNIQUEMENT ces valeurs.
- source : devine d'où vient l'idée. Si tu ne sais pas, mets "Newsletter Digest Agent".
- Réponds UNIQUEMENT avec le JSON, pas de texte autour, pas de ```json.
"""


def get_all_pages():
    """Récupère toutes les pages de la database via l'API brute."""
    import requests

    pages = []
    start_cursor = None
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    while True:
        body = {"page_size": 100}
        if start_cursor:
            body["start_cursor"] = start_cursor

        resp = requests.post(
            f"https://api.notion.com/v1/databases/{NOTION_IDEAS_DATABASE_ID}/query",
            headers=headers,
            json=body,
        )
        data = resp.json()
        pages.extend(data.get("results", []))

        if not data.get("has_more"):
            break
        start_cursor = data.get("next_cursor")

    return pages


def get_page_content(page_id):
    """Récupère le contenu texte d'une page Notion."""
    blocks = notion.blocks.children.list(block_id=page_id)["results"]
    text_parts = []

    for block in blocks[:30]:
        block_type = block["type"]
        if block_type in ("paragraph", "heading_2", "heading_3", "bulleted_list_item", "callout"):
            rich_text = block.get(block_type, {}).get("rich_text", [])
            for rt in rich_text:
                text_parts.append(rt.get("plain_text", ""))

    return "\n".join(text_parts)[:3000]


def page_needs_update(page):
    """Vérifie si une page a besoin de classification (pas de score ou pas de TLDR)."""
    props = page["properties"]

    score = props.get("Score", {}).get("number")
    tldr_list = props.get("TLDR", {}).get("rich_text", [])
    tldr = tldr_list[0]["plain_text"] if tldr_list else ""
    tags = props.get("Tags", {}).get("multi_select", [])

    has_score = score is not None
    has_tldr = bool(tldr)
    has_tags = len(tags) > 0

    return not (has_score and has_tldr and has_tags)


def classify_with_gemini(title, content):
    """Appelle Gemini pour classifier une idée."""
    prompt = CLASSIFY_PROMPT.format(
        title=title,
        content=content[:2000],
        valid_tags=json.dumps(VALID_TAGS),
    )

    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]
            return json.loads(text)
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                delay = 15 * (2 ** attempt)
                print(f"    Rate limit, retry dans {delay}s...")
                time.sleep(delay)
            else:
                print(f"    Erreur Gemini : {e}")
                return None
    return None


def update_page_properties(page_id, classification):
    """Met à jour les propriétés d'une page Notion."""
    props = {}

    score = classification.get("score")
    if score is not None:
        props["Score"] = {"number": int(score)}

    tldr = classification.get("tldr", "")
    if tldr:
        props["TLDR"] = {"rich_text": [{"text": {"content": tldr[:2000]}}]}

    tags = classification.get("tags", [])
    filtered = [t for t in tags if t in VALID_TAGS]
    if filtered:
        props["Tags"] = {"multi_select": [{"name": t} for t in filtered]}

    source = classification.get("source", "")
    if source:
        props["Source"] = {"rich_text": [{"text": {"content": source[:2000]}}]}

    props["Status"] = {"select": {"name": "Nouveau"}}

    if props:
        notion.pages.update(page_id=page_id, properties=props)


def main():
    print("\n=== Classification de toutes les idées RFS ===\n")

    pages = get_all_pages()
    print(f"  {len(pages)} pages dans la database")

    to_update = []
    for page in pages:
        title_parts = page["properties"].get("Name", {}).get("title", [])
        title = title_parts[0]["plain_text"] if title_parts else "Sans titre"

        if page_needs_update(page):
            to_update.append((page["id"], title))

    print(f"  {len(to_update)} pages à classifier\n")

    for i, (page_id, title) in enumerate(to_update, 1):
        print(f"--- {i}/{len(to_update)} : {title}")

        content = get_page_content(page_id)
        if not content or len(content) < 20:
            print("    Contenu trop court, skip")
            continue

        classification = classify_with_gemini(title, content)
        if not classification:
            print("    Classification échouée, skip")
            continue

        score = classification.get("score", "?")
        tags = classification.get("tags", [])
        print(f"    → Score: {score}/10, Tags: {tags}")

        update_page_properties(page_id, classification)
        print(f"    ✓ Propriétés mises à jour")

        if i < len(to_update):
            time.sleep(4)

    print(f"\n=== Terminé : {len(to_update)} pages classifiées ===\n")


if __name__ == "__main__":
    main()
