# Newsletter Digest Agent — Plan technique (V1)

> **Setup :** Suis le guide [SETUP.md](SETUP.md) pour configurer Google Cloud, OpenAI et Notion avant de lancer.

## Architecture

```
USER_EMAIL — label "Newsletters-Digest"
(alias newsletters, auto-archive par filtre Gmail)
        |
        v
+------------------------+
|  Gmail API (polling)    |  <-- Cron 1x/jour a 6h — emails des 14 derniers jours non traites
+----------+-------------+
           |
           v
+------------------------+
|  Content Detection      |  <-- Newsletter HTML ? Lien YouTube ? Lien Podcast ?
+----------+-------------+
           |
           +-- Newsletter HTML --> BeautifulSoup + readability-lxml (HTML -> texte)
           +-- Lien YouTube -----> youtube-transcript-api (transcription)
           +-- Lien Podcast -----> yt-dlp + Whisper API (audio -> transcription)
           |
           v
+------------------------+
|  Gemini 2.0 Flash       |  <-- Prompt "partner VC senior"
|  - Key takeaways        |     Output JSON structure :
|  - So what (advisor)    |     takeaways, ideas (avec score, tldr, tags),
|  - Idees de boites      |     signal_strength, topics
|  - Score & TLDR         |
+----------+-------------+
           |
           +---> SQLite (sauvegarde analyses)
           |
           +---> Notion Database "Request for Startups"
                 (Name, Score, TLDR, Tags, Source, Semaine, Status, Charles)
                 + page avec callout TLDR + mini-deck JdLR
           |
           v  (Vendredi 12h — heure de Paris)
+------------------------+
|  Digest Compiler        |  <-- Compile tout depuis le dernier digest (cycle vendredi->vendredi)
+----------+-------------+
           |
           +---> Notion --> Page "Digest Semaine XX — YYYY" dans "Newsletters Digests"
           +---> Email  --> USER_EMAIL (sujet avec lundi de la semaine)
```

## Stack technique

| Composant | Techno | Pourquoi |
|-----------|--------|----------|
| Langage | Python 3.11+ | Simple, ecosysteme riche |
| Email (lecture) | Gmail API (google-api-python-client) | Lit le label "Newsletters-Digest", fenetre 14j |
| HTML parsing | BeautifulSoup4 + readability-lxml | Extraction propre du texte de newsletters HTML |
| YouTube | youtube-transcript-api | Transcriptions YouTube sans API key |
| Podcasts | yt-dlp + OpenAI Whisper API | Download audio + transcription ($0.006/min) |
| LLM | Google Gemini 2.0 Flash | Free tier suffisant, contexte 1M tokens |
| Stockage | SQLite (built-in Python) | Zero setup, suffisant pour le volume |
| Notion | notion-client (SDK) + requests (database queries) | Database inline avec proprietes |
| Email (envoi) | Gmail API | Digest vers USER_EMAIL |
| Orchestration | macOS launchd | Poll quotidien 6h + digest vendredi 12h, automatique |

## Structure du code

```
projects/01-newsletter-digest/
+-- PRD.md                        <-- Product Requirements (V1)
+-- PLAN.md                       <-- Ce fichier
+-- SETUP.md                      <-- Guide de setup pas-a-pas
+-- CHANGELOG.md                  <-- Historique des versions
+-- README.md                     <-- README pour GitHub
+-- .env                          <-- API keys (jamais committe)
+-- .env.example                  <-- Template des variables d'environnement
+-- .gitignore                    <-- Exclut .env, credentials.json, token.json, data/
+-- requirements.txt              <-- Dependances Python
+-- credentials.json              <-- OAuth Gmail (jamais committe)
+-- token.json                    <-- Token Gmail auto-genere (jamais committe)
+-- src/
|   +-- __init__.py
|   +-- main.py                   <-- Entry point CLI : poll et digest
|   +-- config.py                 <-- Config & env vars (API keys, IDs Notion, paths)
|   +-- ingestion/
|   |   +-- __init__.py
|   |   +-- email_reader.py       <-- Gmail API : polling emails non traites (14j)
|   |   +-- content_detector.py   <-- Detection type contenu (HTML, YouTube, podcast)
|   |   +-- html_parser.py        <-- Newsletter HTML -> texte (BeautifulSoup)
|   |   +-- youtube_extractor.py  <-- YouTube -> transcription
|   |   +-- podcast_extractor.py  <-- Podcast -> audio -> transcription Whisper
|   +-- analysis/
|   |   +-- __init__.py
|   |   +-- analyzer.py           <-- Appels Gemini (analyse + mini-deck) avec retry
|   |   +-- prompts.py            <-- Prompts LLM (analyse, digest, deck)
|   +-- storage/
|   |   +-- __init__.py
|   |   +-- db.py                 <-- SQLite CRUD (contents, analyses, digests)
|   +-- output/
|       +-- __init__.py
|       +-- notion_writer.py      <-- Notion : digest page + idees dans database
|       +-- email_sender.py       <-- Email digest avec date du lundi
|       +-- digest_compiler.py    <-- Compilation hebdo (vendredi->vendredi)
+-- scripts/
|   +-- setup_gmail_oauth.py      <-- Auth Gmail initiale (one-time)
|   +-- run_weekly_digest.py      <-- Lancer le digest manuellement
|   +-- classify_all_ideas.py     <-- Migration one-shot : classifier les idees existantes
+-- data/
    +-- newsletter_digest.db      <-- SQLite (jamais committe)
```

## Base de donnees SQLite

### Table `contents`
| Colonne | Type | Description |
|---------|------|-------------|
| id | INTEGER PK | Auto-increment |
| message_id | TEXT UNIQUE | ID Gmail (anti-retraitement) |
| content_type | TEXT | newsletter, youtube, podcast_spotify, podcast_apple |
| source | TEXT | Expediteur / source |
| title | TEXT | Titre extrait |
| raw_text | TEXT | Contenu brut extrait |
| url | TEXT | URL du contenu (si applicable) |
| received_at | TEXT | Date de reception |
| created_at | TEXT | Date d'insertion en base |

### Table `analyses`
| Colonne | Type | Description |
|---------|------|-------------|
| id | INTEGER PK | Auto-increment |
| content_id | INTEGER FK | Reference vers contents |
| takeaways | TEXT (JSON) | Liste des key takeaways |
| so_what_advisor | TEXT | Insight advisor contextualise |
| ideas | TEXT (JSON) | Idees de boites avec score, tldr, tags |
| signal_strength | TEXT | weak / medium / strong / very_strong |
| topics | TEXT (JSON) | Topics identifies |
| analyzed_at | TEXT | Date de l'analyse |

### Table `digests`
| Colonne | Type | Description |
|---------|------|-------------|
| id | INTEGER PK | Auto-increment |
| week_number | INTEGER | Numero de semaine |
| year | INTEGER | Annee |
| digest_json | TEXT (JSON) | Contenu compile du digest |
| notion_url | TEXT | URL de la page Notion |
| sent_at | TEXT | Date d'envoi (point de reference pour le prochain cycle) |

## Database Notion "Request for Startups"

| Propriete | Type | Description |
|-----------|------|-------------|
| Name | title | Nom de l'idee |
| Score | number | Note /10 par le "partner VC" (0=nulle, 8+=prometteur, 10=idee de l'annee) |
| TLDR | text | Pitch express 50 mots |
| Tags | multi_select | SaaS, Marketplace, AI Agency, AI-Powered Agency, Platform, Infrastructure, B2B, B2C, HealthTech, EdTech, Gaming, FinTech, SpaceTech, DeepTech |
| Source | text | D'ou vient l'idee (newsletter, podcast...) |
| Semaine | text | Semaine du digest (ex: "Semaine 7") |
| Status | select | Nouveau, En exploration, Favori, Rejete, Archive |
| Charles | select | Love it, Meh, No go — assessment personnel de Charles |
| Cree le | created_time | Date de creation automatique |

## Commandes CLI

```bash
cd projects/01-newsletter-digest
source .venv/bin/activate

# Polling : lit les nouveaux emails, analyse, cree les idees
python -m src.main poll

# Digest : compile et envoie le digest hebdo
python -m src.main digest

# Digest force : recree meme s'il existe deja
python -m src.main digest --force
```

## Automatisation (launchd)

Le poll et le digest tournent automatiquement via macOS launchd :
- **Poll** : tous les jours a 6h (heure de Paris)
- **Digest** : tous les vendredis a 12h (heure de Paris)

Les fichiers plist sont dans `~/Library/LaunchAgents/`. Voir SETUP.md pour le detail.

## Credentials & API keys

> **Guide detaille :** Voir [SETUP.md](SETUP.md) pour le step-by-step complet.

| Service | Ce qu'il faut | Statut |
|---------|---------------|--------|
| Google Workspace | Alias newsletters + filtre Gmail "Newsletters-Digest" | FAIT |
| Google Cloud | Projet "Newsletter Digest" + OAuth (Gmail) + API key (Gemini) | FAIT |
| OpenAI | API key Whisper (pour podcasts) | FAIT |
| Notion | Integration token + acces aux pages Dashboard Largo | FAIT |

## Estimation couts mensuels

| Poste | Estimation | Detail |
|-------|-----------|--------|
| Gemini 2.0 Flash | ~$0 (free tier) | Appels etales, free tier largement suffisant |
| Whisper API (podcasts) | ~$2-5/mois | ~2-5 podcasts/mois x 1h x $0.36/h |
| Notion API | Gratuit | Inclus dans le plan Notion |
| Gmail API | Gratuit | Quotas largement suffisants |
| **Total** | **~$2-5/mois** | Principalement le cout Whisper pour les podcasts |

## Roadmap V2 — AI Boardroom

Le concept : au lieu d'un seul prompt "partner VC" qui score une idee, on lance un **boardroom de 3 agents IA** qui debattent, inspires de vraies personnalites :

| Agent | Persona | Role | Angle |
|-------|---------|------|-------|
| Elon Musk | First-principles, 10x scale | Visionnaire | "Can this scale to billions? What's the physics?" |
| Sam Altman | AI-native investor, moat obsessed | Strategist | "What's the defensibility? How does AI reshape this?" |
| Steve Jobs | Product purist, user obsessed | Quality check | "Is this simple? Beautiful? Would anyone love it?" |

Chaque idee recevrait les arguments pour/contre de chaque persona + un verdict final argumente. Inspire du concept "AI Boardroom" (Allie K. Miller).

## Risques techniques

1. **Podcasts Spotify** : Pas de download direct. Workaround : flux RSS ou show notes.
2. **YouTube sans sous-titres** : Fallback yt-dlp + Whisper API.
3. **Newsletters visuelles** : Peu de texte exploitable. V2 : vision (GPT-4V).
4. **Token limits** : Non-probleme avec Gemini 2.0 Flash (1M tokens).
