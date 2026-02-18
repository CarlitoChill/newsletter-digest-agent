# Newsletter Digest Agent — Changelog

## V2.1 — Board Scores, Startup Alternatives & Competitive Analysis (18 fevrier 2026)

- **Scores individuels** : colonnes Steve, Ann, Ben, Jean dans la DB Notion — chacune un score /10 (1 = pas convaincu, 10 = je lance cette boite)
- **Startup alternative** : chaque board member propose sa propre startup sur le meme pain/play, avec son angle a lui
- **Analyse concurrentielle** : Gemini identifie 3-5 concurrents (directs/indirects/adjacents), evalue la maturite du marche et le moat possible
- **Nouvelle structure des pages** :
  1. Callout TLDR + score
  2. Verdict du Board & next steps (synthese)
  3. Avis du Board (4 members avec verdict + startup alternative)
  4. Mini-deck (pitch structure)
  5. Analyse concurrentielle (concurrents, marche, moat)
- Backfill des scores numeriques sur les 12 pages existantes

---

## V2.0 — AI Boardroom (18 fevrier 2026)

- **AI Boardroom** : 4 board members virtuels debattent chaque idee de boite
  - Steve Jobs (Product/UX/Simplicite)
  - Ann Miura-Ko (Thunder Lizards/Contrarian)
  - Ben Horowitz (Execution/Hard Things)
  - Jean de La Rochebrochard (Founders/Timing/Marche)
- **Boardroom inline** : le board tourne sur chaque idee pendant le poll (pas de commande separee)
- Chaque board member produit un verdict (invest/pass/dig_deeper), un score /10, des arguments pour/contre, et une question cle
- Synthese automatique : score final pondere par conviction, consensus du board, point de friction, next steps concrets
- Pages Notion enrichies avec section "AI Boardroom" apres le mini-deck
- Score dans le callout et la colonne DB toujours synchronises
- Rate limit : 3s entre chaque appel Gemini boardroom, resilient (le board fonctionne meme si un member echoue)
- **Workflow** : content ongoing → poll quotidien (analyse + board) → digest vendredi 12h → review vendredi 14h

---

## V1.0.1 — Code Review Cleanup (18 fevrier 2026)

- Email deporte dans `.env` : fusion de `GMAIL_USER` + `CHARLES_EMAIL` en une seule variable `USER_EMAIL` chargee depuis `.env`
- Plus aucun email hardcode dans le code Python ou les docstrings
- Scripts shell : `PROJECT_DIR` calcule dynamiquement via `dirname` au lieu d'un chemin absolu hardcode
- Documentation nettoyee : plus de references a des emails ou domaines personnels dans les fichiers publics (.md)
- `.env.example` mis a jour avec la nouvelle variable `USER_EMAIL`

---

## V1.0 — MVP Complet (17-18 fevrier 2026)

### Mardi 17 fevrier — Build Day

**Matin — Pipeline de base**
- Setup projet Python 3.11+ (virtualenv, requirements.txt, .env)
- Gmail OAuth : connexion au label "Newsletters-Digest"
- Email Reader : polling des emails non traites avec fenetre 14 jours
- Content Detection : identification automatique du type de contenu (newsletter HTML, YouTube, podcast Spotify/Apple)
- HTML Parser : extraction du texte avec BeautifulSoup + readability-lxml
- YouTube Extractor : transcription via youtube-transcript-api
- Podcast Extractor : download audio (yt-dlp) + transcription (Whisper API)
- Gemini Analyzer : analyse "partner VC senior" avec output JSON structure (takeaways, so what, ideas, signal strength)
- SQLite : stockage des contenus, analyses, et digests
- Notion Writer : creation des pages digest + idees en sous-pages dans "Request for Startups"
- Email Sender : envoi du digest HTML a USER_EMAIL
- Digest Compiler : compilation hebdomadaire cross-contenu avec Gemini
- Premier run complet : 27 emails ingeres, analyses, idees generees

**Apres-midi — Iterations sur feedback**
- Fix du cycle digest : passage de semaine calendaire a vendredi-a-vendredi (base sur `sent_at` du dernier digest)
- Anti-retraitement : les emails deja traites ne sont jamais reprocesses (tracking par message_id)
- Fenetre Gmail : limitation a 14 jours pour eviter de scanner tout l'historique
- Ajout du lundi de la semaine dans le sujet de l'email ("Semaine 7 — Lundi 10 fevrier 2026")
- Ajout callout jaune TLDR + score en haut de chaque page d'idee
- Scoring /10 par le "partner VC" pour chaque idee
- Tags automatiques (SaaS, Marketplace, AI Agency, B2B, etc.)
- Ton des mini-decks ajuste : "brilliant but lazy 15-year-old"
- Section "User Experience" ajoutee dans chaque mini-deck
- URLs des sources incluses dans chaque page d'idee

**Soir — Migration vers Notion Database**
- Creation de la database Notion "Request for Startups" (inline) avec proprietes : Name, Score, TLDR, Tags, Source, Semaine, Status, Cree le
- Migration des 56 pages d'idees existantes (actives + archivees) dans la database
- Script `classify_all_ideas.py` : classification automatique de toutes les idees avec Gemini (score, TLDR, tags, source)
- Refactoring du code pour creer les futures idees directement dans la database
- Nettoyage du code mort : suppression de `add_week_header_to_rfs()`, `get_week_analyses()`, `has_ideas_this_week()`
- Database passee en inline (visible directement dans la page parente)
- PRD.md reecrit pour la V1

### Mercredi 18 fevrier — Documentation & Automatisation

- Ajout colonne "Charles" dans la database (Love it / Meh / No go)
- PLAN.md reecrit : architecture V1, schema SQLite, database Notion, commandes CLI, roadmap V2
- CHANGELOG.md cree
- README.md cree pour GitHub
- Setup cron (launchd) : poll automatique quotidien + digest automatique vendredi
- Init git + push GitHub

---

## V0.5 — Notion Integration (semaine du 10 fevrier 2026)

- Setup Google Cloud Console (OAuth, Gmail API, Gemini API)
- Setup Notion Integration
- Setup OpenAI (Whisper)
- Configuration du filtre Gmail + alias newsletters
- Page "Build in Public" creee dans Notion avec premier article

