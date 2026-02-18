# Newsletter Digest Agent — Product Requirements Document (V1)

## 1. Product Vision

**One-liner :** Un agent IA qui digère mes newsletters, vidéos YouTube et podcasts, et me livre un brief hebdomadaire de partner VC — avec des idées de boîtes actionnables scorées et classifiées.

**Context :** Charles reçoit 15-25 newsletters/semaine de très haute qualité (tech, VC, startups, IA) + vidéos YouTube + podcasts. Pas le temps de tout consommer. Ce contenu est pourtant critique pour son rôle d'advisor et pour alimenter sa réflexion sur sa prochaine boîte.

**Target User :** Charles Thomas — advisor indépendant, futur fondateur.

## 2. Problem Statement

- **Problème :** 15-25 newsletters/semaine + YouTube + podcasts = trop de contenu, pas assez de temps. Le contenu est excellent mais reste non lu/non regardé.
- **Pourquoi c'est un vrai problème :** Ce contenu alimente directement la qualité de ses conseils aux fondateurs et sa capacité à identifier des opportunités de marché. Ne pas le consommer = perte de signal.
- **Aujourd'hui (pre-V1) :** Scroll rapide, lecture partielle, oubli. Aucune synthèse, aucune capitalisation systématique.

## 3. Expected Outcomes

| Outcome | Metric | Target | Statut V1 |
|---------|--------|--------|-----------|
| Gain de temps | Heures/semaine économisées sur la veille | 3-5h/semaine | OK |
| Couverture du contenu | % de newsletters/contenus analysés | 100% | OK |
| Génération d'idées | Nouvelles idées de boîtes/semaine dans Notion | 2-6/semaine | OK |
| Pertinence advisor | Insights actionnables pour ses clients | 5+/semaine | OK |
| Scoring des idées | Note /10 par le "partner VC" + TLDR | Chaque idée scorée | OK |

## 4. Requirements — V1 (Livré)

### Functional Requirements

1. **Ingestion de contenu** : Récupérer le contenu des newsletters (email forwarding), liens YouTube, Spotify, Apple Podcasts envoyés à l'alias newsletters
2. **Analyse VC-grade** : Analyser chaque contenu avec une lentille de partner VC senior (a16z, Sequoia, YC) — takeaways, so what advisor, signal strength
3. **Génération d'idées au fil de l'eau** : Identifier et formuler des idées de boîtes dès l'analyse de chaque email (pas d'attente du vendredi)
4. **Scoring & TLDR** : Chaque idée reçoit un score /10 et un TLDR de 50 mots par le "partner VC"
5. **Tags & Classification** : Chaque idée est taggée (SaaS, Marketplace, AI Agency, B2B, HealthTech, etc.)
6. **Database Notion "Request for Startups"** : Les idées sont stockées dans une database Notion inline avec propriétés (Name, Score, TLDR, Tags, Source, Semaine, Status, Créé le)
7. **Mini-deck JdLR** : Chaque idée a un mini-deck structuré (Context/Trend → Problem → Product → Market → User Experience → Execution → Vision)
8. **Callout TLDR** : Chaque page d'idée commence par un callout jaune avec le score et le TLDR
9. **Digest hebdomadaire** : Compilation cross-contenu le vendredi — top insights, thèmes récurrents, playbook advisor, top idées
10. **Push Notion** : Page digest dans "Newsletters Digests" (sous Dashboard Largo)
11. **Email récap** : Digest envoyé par email à l'utilisateur (USER_EMAIL dans `.env`) avec le lundi de la semaine dans le sujet
12. **Cycle vendredi→vendredi** : Le digest compile tout ce qui a été ingéré depuis le dernier digest (pas de contenu perdu entre deux cycles)
13. **Anti-retraitement** : Les emails déjà traités ne sont jamais reprocessés (tracking par message_id en SQLite)

### V2 — AI Boardroom (18 fevrier 2026) — LIVRE

1. **AI Boardroom inline** : 4 board members virtuels (Steve Jobs, Ann Miura-Ko, Ben Horowitz, JdLR) debattent chaque idee pendant le poll (pas de commande separee)
2. Chaque board member produit un verdict (invest/pass/dig_deeper), un score, et ses arguments
3. Une synthese automatique consolide les 4 verdicts en un score final pondere par conviction
4. **Workflow vendredi** : digest a 12h, review des idees (avec analyses du board) a 14h, Charles tague Love it / Meh / No go

### V2.1 — A livrer

1. **Detection de patterns cross-newsletters** — themes recurrents = signaux forts (section dediee dans le digest ou les idees)
2. **Build in Public** — export automatique vers un blog/site (partie integrante de la V2.1)
3. **Migration google.generativeai → google.genai** — supprimer le deprecation warning, utiliser le SDK a jour
4. **Verifier launchd** — s'assurer que le poll (6h) et le digest (vendredi 12h) sont installes et tournent pour le workflow en continu

### V3 — A moyen terme

1. **Board members additionnels par sujet** — ex. Patrick Collison pour FinTech, Miyamoto pour Gaming (un ou deux membres selon les tags de l'idee)
2. **Plus de sources de contenu** — alimentation par d'autres newsletters et/ou flux RSS (la matiere premiere, c'est le content)
3. **Petit front / page web** — export "Idee de la semaine" : une page publique ou les gens peuvent voir "c'est quoi l'idee de la semaine"

### Nice-to-Have (au-dela de V3)

1. Digest quotidien en plus du hebdo
2. Integration Slack/Telegram/WhatsApp pour delivery
3. Vision (GPT-4V) pour newsletters tres visuelles

### Non-Functional Requirements

- **Performance :** Digest livré chaque vendredi à 12h (heure de Paris), polling quotidien à 6h
- **Rate limits :** Appels Gemini étalés (1 email à la fois, 3s entre les idées et board members) → zéro coût sur free tier
- **Security :** Credentials en `.env`, `credentials.json` et `token.json` en `.gitignore`
- **Scalability :** Supporte 25+ newsletters/semaine sans perte de qualité ni rate limit

## 5. User Stories

| # | En tant que... | Je veux... | Pour... | Statut |
|---|---------------|------------|---------|--------|
| 1 | Charles (advisor) | Recevoir un digest hebdo de toutes mes newsletters | Rester sharp sans y passer 5h | V1 |
| 2 | Charles (advisor) | Que chaque insight soit contextualisé pour mon rôle | Appliquer directement dans mes sessions | V1 |
| 3 | Charles (futur fondateur) | Que l'agent identifie et score des idées de boîtes | Alimenter ma Boîte à idées Notion | V1 |
| 4 | Charles (futur fondateur) | Que chaque idée ait un mini-deck structuré | Avoir un pitch prêt à approfondir | V1 |
| 5 | Charles | Forward facilement mes newsletters à l'agent | Que l'input soit simple, zéro friction | V1 |
| 6 | Charles | Filtrer et trier mes idées par score, tags, semaine | Prioriser mes explorations | V1 |

## 6. UX / User Flow

**Trigger :** Charles forward une newsletter, ou envoie un lien (YouTube, Spotify, Apple Podcasts) à l'alias newsletters.

**Flow principal :**
1. Email arrive sur l'alias newsletters → filtre Gmail → label "Newsletters-Digest"
2. Polling quotidien (6h) : l'agent détecte les nouveaux emails non traités
3. Pour chaque email, détection du type de contenu :
   - **Newsletter HTML** → parse HTML (BeautifulSoup + readability)
   - **Lien YouTube** → transcription via youtube-transcript-api
   - **Lien Spotify/Apple Podcasts** → download audio (yt-dlp) + transcription (Whisper)
4. Analyse avec Gemini 2.0 Flash (prompt "partner VC senior") → takeaways, ideas, score, tags
5. Chaque idée passe devant le AI Boardroom (4 board members) → score final, verdicts, arguments
6. Sauvegarde en SQLite + création immédiate des pages d'idées dans Notion (avec analyse du board)
7. Vendredi 12h : compilation digest hebdo (1 appel Gemini) + email
8. Vendredi 14h : Charles review les idées de la semaine et tague Love it / Meh / No go

**Output :**
- 1 page Notion "Digest Semaine XX" par semaine
- N entrées dans la database "Request for Startups" (avec score, TLDR, tags, mini-deck)
- 1 email récap hebdomadaire

## 7. Technical Architecture

**Stack :**
- **Email ingestion :** Gmail API (polling 1x/jour) — label "Newsletters-Digest"
- **Processing :** Python 3.11+
- **LLM :** Google Gemini 2.0 Flash — analyses individuelles + digest + mini-decks
- **Transcription podcasts :** OpenAI Whisper API
- **Orchestration :** launchd (1x/jour à 6h + vendredi 12h digest)
- **Output :** Notion API (database + pages) + Gmail API (envoi email)
- **Storage :** SQLite (fichier local)

**Schéma :**
```
[newsletters alias → Gmail]
        │
        ▼ (1x/jour, 6h)
[Gmail API] → [Détection type] → [Extraction contenu] → [Gemini Flash]
                                                              │
                                                    ┌─────────┴─────────┐
                                                    ▼                   ▼
                                                [Analyse]         [AI Boardroom]
                                                (partner VC)      (4 members)
                                                    │                   │
                                              ┌─────┴─────┐            │
                                              ▼           ▼            ▼
                                          [SQLite]    [Notion Database + Pages]
                                          (analyses)  (idées + board analysis)
                                              │
                                              ▼  (Vendredi 12h)
                                      [Digest Compiler]
                                           │
                                           ├──→ Notion (page digest)
                                           └──→ Email (USER_EMAIL)
                                                    │
                                              (Vendredi 14h)
                                        Charles review : Love it / Meh / No go
```

## 8. Risks & Mitigations

| Risk | Impact | Probabilité | Mitigation |
|------|--------|-------------|------------|
| Newsletters en HTML complexe | Perte de contenu lors du parsing | Moyen | Parser HTML robuste + fallback texte brut |
| Qualité variable de l'analyse LLM | Insights superficiels | Moyen | Prompt engineering solide + itération |
| Rate limits Gemini free tier | Échec temporaire d'analyse | Faible | Retry avec backoff exponentiel + étalement des appels |
| Rate limits Notion API | Échec de création de pages | Faible | Retry logic |
| Podcasts Spotify sans audio direct | Pas de transcription | Moyen | Fallback sur flux RSS ou show notes |

## 9. Milestones

| Phase | Description | Statut |
|-------|-------------|--------|
| V0 — POC | Script Python : forward 1 newsletter → analyse LLM → output texte | FAIT |
| V0.5 — Notion | Push Notion (digest + idées en sous-pages) | FAIT |
| V1 — MVP | Pipeline complet : ingestion → analyse → idées scorées dans database Notion → digest hebdo → email | FAIT |
| V1.1 — Automatisation | Scheduling automatique (launchd), zero intervention | FAIT |
| V2 — AI Boardroom | 4 board members (Jobs/Miura-Ko/Horowitz/JdLR) debattent chaque idee | FAIT |
| V2.1 — Patterns + Build in Public + GenAI + launchd | Patterns cross-newsletters, Build in Public, migration google.genai, verif launchd | TODO |
| V3 — Board par sujet + sources + front | Board members par sujet, plus de sources (RSS, newsletters), page "Idee de la semaine" | TODO |

## 10. Décisions prises

- [x] **Notion "Request for Startups"** : Database inline (pas des sous-pages flottantes) avec propriétés Name, Score, TLDR, Tags, Source, Semaine, Status, Créé le
- [x] **Ingestion email** : alias `newsletters@...` sur le compte principal, filtre Gmail + label "Newsletters-Digest"
- [x] **Cycle digest** : Vendredi→vendredi (basé sur `sent_at` du dernier digest), pas sur les semaines calendaires
- [x] **Idées au fil de l'eau** : Créées dans Notion dès le polling (pas d'attente du vendredi)
- [x] **LLM** : Google Gemini 2.0 Flash — free tier suffisant pour 25+ newsletters/semaine
- [x] **Scoring** : Note /10 attribuée par le persona "partner VC senior", stricte (8+ = très prometteur)
- [x] **Tags** : Classification automatique parmi 14 catégories (SaaS, Marketplace, AI Agency, B2B, FinTech, etc.)
- [x] **Ton des mini-decks** : "Brilliant but lazy 15-year-old" — simple, direct, engageant
- [x] **Email** : Sujet inclut le lundi de la semaine (ex: "Newsletter Digest — Semaine 7 — Lundi 10 février 2026")
- [x] **Anti-retraitement** : Tracking par message_id en SQLite, fenêtre de 14 jours sur Gmail API

## 11. Open Questions (V3+)

- [ ] Mini-digest quotidien en plus du hebdo ?
- [ ] Integration Slack/Telegram/WhatsApp pour delivery ?
- [ ] Vision (GPT-4V) pour newsletters tres visuelles ?
