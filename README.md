# Newsletter Digest Agent

An AI agent that reads my newsletters, YouTube videos, and podcasts — and delivers a weekly VC-grade briefing with scored startup ideas.

## What it does

1. **Ingests** newsletters forwarded to a dedicated alias (+ YouTube links, podcast links)
2. **Analyzes** each piece of content through a "senior VC partner" lens using Google Gemini 2.0 Flash
3. **Generates startup ideas** with a structured mini-deck, score (/10), TLDR, and tags
4. **AI Boardroom** — 4 virtual board members (Jobs, Miura-Ko, Horowitz, JdLR) debate each idea, score it 1-10, and each propose their own startup alternative
5. **Competitive analysis** — identifies 3-5 direct/indirect competitors, market maturity, and moat assessment
6. **Pushes ideas** to a Notion database ("Request for Startups") with board + competitive analysis included
7. **Compiles a weekly digest** every Friday — top insights, recurring themes, advisor playbook
8. **Sends an email recap** to the user with a link to the Notion digest

## Architecture

```
[newsletters alias → Gmail]
        |
        v  (daily, 6am)
[Gmail API] --> [Content Detection] --> [Extraction] --> [Gemini Flash]
                                                              |
                                                    +---------+---------+
                                                    v                   v
                                                [Analysis]        [AI Boardroom]
                                                (VC partner)      (4 board members)
                                                    |                   |
                                                    |           [Competitive Analysis]
                                                    |                   |
                                              +-----+-----+            |
                                              v           v            v
                                          [SQLite]    [Notion Database + Pages]
                                          (storage)   (ideas + board + competitors)
                                              |
                                              v  (Friday 12pm)
                                      [Digest Compiler]
                                           |
                                           +--> Notion (digest page)
                                           +--> Email (weekly recap)
                                                    |
                                              (Friday 2pm)
                                        Charles reviews ideas:
                                        Love it / Meh / No go
```

## Stack

| Component | Tech |
|-----------|------|
| Language | Python 3.11+ |
| LLM | Google Gemini 2.0 Flash (free tier) |
| Email | Gmail API (read + send) |
| HTML parsing | BeautifulSoup4 + readability-lxml |
| YouTube | youtube-transcript-api |
| Podcasts | yt-dlp + OpenAI Whisper API |
| Storage | SQLite |
| Output | Notion API + Gmail API |
| Scheduling | macOS launchd |

## Setup

### Prerequisites

1. **Google Cloud Console** — OAuth credentials (Gmail) + API key (Gemini)
2. **OpenAI** — API key for Whisper (podcast transcription only)
3. **Notion** — Integration token with access to your workspace

See [SETUP.md](SETUP.md) for the detailed step-by-step guide.

### Installation

```bash
cd projects/01-newsletter-digest
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Copy and fill in your API keys
cp .env.example .env

# Run Gmail OAuth (one-time)
python scripts/setup_gmail_oauth.py
```

### Usage

```bash
# Poll: read new emails, analyze, run AI Boardroom, create idea pages
python -m src.main poll

# Digest: compile and send weekly digest
python -m src.main digest

# Force recreate digest
python -m src.main digest --force
```

### Automation

The agent runs automatically via macOS launchd:
- **Daily at 6am** — `python -m src.main poll`
- **Fridays at 12pm** — `python -m src.main digest`

## Notion Database: Request for Startups

Each idea is stored with:

| Property | Description |
|----------|-------------|
| Name | Idea name |
| Score | /10 final board score |
| Steve | /10 Steve Jobs (Product/UX) |
| Ann | /10 Ann Miura-Ko (Contrarian/Thunder Lizards) |
| Ben | /10 Ben Horowitz (Execution/Scaling) |
| Jean | /10 Jean de La Rochebrochard (Founders/Timing) |
| TLDR | 50-word pitch |
| Tags | SaaS, Marketplace, AI Agency, B2B, FinTech, etc. |
| Source | Where the idea came from |
| Semaine | Week number |
| Status | Nouveau, En exploration, Favori, Rejete, Archive |
| Charles | Personal assessment: Love it, Meh, No go |

## Cost

~$0-5/month. Gemini free tier covers all LLM calls. Whisper API costs ~$0.36/hour of podcast.

## Built by

[Charles Thomas](https://www.linkedin.com/in/charlesjpthomas) — advisor, ex-CEO @ Comet (0 to 60M EUR), building with AI.

## License

MIT
