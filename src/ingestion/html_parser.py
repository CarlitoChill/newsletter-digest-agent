"""
Extraction de texte propre depuis les newsletters HTML.

Utilise readability-lxml (même algo que le mode lecture de Firefox)
pour extraire le contenu principal, puis BeautifulSoup pour nettoyer.
"""

import re

from bs4 import BeautifulSoup
from readability import Document


def parse_newsletter_html(html: str, fallback_text: str = "") -> dict:
    """
    Extrait le texte propre d'une newsletter HTML.

    Args:
        html: Le body HTML de l'email.
        fallback_text: Le body texte brut (utilisé si le HTML ne donne rien).

    Returns:
        Dict avec 'title' et 'content' (texte nettoyé).
    """
    if not html or len(html.strip()) < 50:
        return {
            "title": "",
            "content": fallback_text.strip() if fallback_text else "",
        }

    try:
        doc = Document(html)
        title = doc.title() or ""
        summary_html = doc.summary()
    except Exception:
        title = ""
        summary_html = html

    soup = BeautifulSoup(summary_html, "lxml")

    for tag in soup(["script", "style", "meta", "link", "img", "svg"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    lines = []
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned:
            lines.append(cleaned)
    text = "\n".join(lines)

    text = re.sub(r"\n{3,}", "\n\n", text)

    if len(text.strip()) < 50 and fallback_text:
        text = fallback_text.strip()

    return {
        "title": title.strip(),
        "content": text.strip(),
    }
