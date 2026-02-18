from __future__ import annotations

"""
Base de données SQLite pour stocker les contenus, analyses et digests.

3 tables :
- contents : les emails/contenus bruts ingérés
- analyses : les analyses LLM de chaque contenu
- digests : les digests hebdomadaires générés
"""

import json
import sqlite3
from datetime import datetime

from src.config import DB_PATH


def _get_connection() -> sqlite3.Connection:
    """Crée et retourne une connexion SQLite. Crée le dossier data/ si nécessaire."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crée les tables si elles n'existent pas."""
    conn = _get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS contents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE NOT NULL,
            content_type TEXT NOT NULL,
            source TEXT,
            title TEXT,
            raw_text TEXT,
            url TEXT,
            received_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER NOT NULL,
            takeaways TEXT,
            so_what_advisor TEXT,
            ideas TEXT,
            signal_strength TEXT,
            topics TEXT,
            analyzed_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (content_id) REFERENCES contents(id)
        );

        CREATE TABLE IF NOT EXISTS digests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_number INTEGER NOT NULL,
            year INTEGER NOT NULL,
            digest_json TEXT,
            notion_url TEXT,
            sent_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(week_number, year)
        );
    """)
    conn.commit()
    conn.close()


def get_processed_message_ids() -> set[str]:
    """Retourne les IDs Gmail déjà traités."""
    conn = _get_connection()
    rows = conn.execute("SELECT message_id FROM contents").fetchall()
    conn.close()
    return {row["message_id"] for row in rows}


def save_content(
    message_id: str,
    content_type: str,
    source: str,
    title: str,
    raw_text: str,
    url: str | None = None,
    received_at: str | None = None,
) -> int:
    """Sauvegarde un contenu ingéré. Retourne l'ID du contenu."""
    conn = _get_connection()
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO contents (message_id, content_type, source, title, raw_text, url, received_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (message_id, content_type, source, title, raw_text, url, received_at),
    )
    conn.commit()
    content_id = cursor.lastrowid
    conn.close()
    return content_id


def save_analysis(
    content_id: int,
    takeaways: list,
    so_what_advisor: str,
    ideas: list,
    signal_strength: str,
    topics: list,
):
    """Sauvegarde une analyse LLM."""
    conn = _get_connection()
    conn.execute(
        """
        INSERT INTO analyses (content_id, takeaways, so_what_advisor, ideas, signal_strength, topics)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            content_id,
            json.dumps(takeaways, ensure_ascii=False),
            so_what_advisor,
            json.dumps(ideas, ensure_ascii=False),
            signal_strength,
            json.dumps(topics, ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()


def save_digest(week_number: int, year: int, digest_json: dict, notion_url: str = ""):
    """Sauvegarde un digest hebdomadaire."""
    conn = _get_connection()
    conn.execute(
        """
        INSERT OR REPLACE INTO digests (week_number, year, digest_json, notion_url, sent_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        """,
        (week_number, year, json.dumps(digest_json, ensure_ascii=False), notion_url),
    )
    conn.commit()
    conn.close()


def get_last_digest_date() -> str | None:
    """
    Retourne la date du dernier digest envoyé (sent_at), ou None si aucun digest n'existe.
    C'est le point de référence pour savoir quels contenus inclure dans le prochain digest.
    """
    conn = _get_connection()
    row = conn.execute(
        "SELECT MAX(sent_at) as last_sent FROM digests WHERE sent_at IS NOT NULL"
    ).fetchone()
    conn.close()
    if row and row["last_sent"]:
        return row["last_sent"]
    return None


def get_analyses_since(since: str | None = None) -> list[dict]:
    """
    Récupère toutes les analyses depuis une date donnée.
    Si since est None, récupère TOUT (premier digest).
    
    Le cycle digest est vendredi midi → vendredi midi.
    On se base sur created_at (= moment de l'ingestion par le poll).
    """
    conn = _get_connection()

    if since:
        rows = conn.execute(
            """
            SELECT
                c.title, c.source, c.content_type, c.url,
                a.takeaways, a.so_what_advisor, a.ideas, a.signal_strength, a.topics
            FROM analyses a
            JOIN contents c ON a.content_id = c.id
            WHERE c.created_at > ?
            ORDER BY a.signal_strength DESC, a.analyzed_at ASC
            """,
            (since,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT
                c.title, c.source, c.content_type, c.url,
                a.takeaways, a.so_what_advisor, a.ideas, a.signal_strength, a.topics
            FROM analyses a
            JOIN contents c ON a.content_id = c.id
            ORDER BY a.signal_strength DESC, a.analyzed_at ASC
            """
        ).fetchall()

    conn.close()

    results = []
    for row in rows:
        results.append({
            "title": row["title"],
            "source": row["source"],
            "content_type": row["content_type"],
            "url": row["url"],
            "takeaways": json.loads(row["takeaways"]) if row["takeaways"] else [],
            "so_what_advisor": row["so_what_advisor"],
            "ideas": json.loads(row["ideas"]) if row["ideas"] else [],
            "signal_strength": row["signal_strength"],
            "topics": json.loads(row["topics"]) if row["topics"] else [],
        })

    return results


def digest_exists(week_number: int, year: int) -> bool:
    """Vérifie si un digest existe déjà pour cette semaine."""
    conn = _get_connection()
    row = conn.execute(
        "SELECT id FROM digests WHERE week_number = ? AND year = ?",
        (week_number, year),
    ).fetchone()
    conn.close()
    return row is not None
