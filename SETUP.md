# Newsletter Digest Agent — Guide de Setup

Ce guide t'accompagne pas-a-pas pour configurer tous les services necessaires avant de lancer le build. Chaque etape explique **pourquoi** on fait ca, **comment** le faire, et **comment verifier** que ca a marche.

---

## Prerequis 1 : Google Workspace (FAIT)

### Pourquoi

Notre agent doit lire les newsletters que tu recois. Plutot que de connecter directement ta boite principale, on cree un alias (ex: `newsletters@tondomaine.com`) avec un filtre Gmail qui etiquette automatiquement ces emails. Comme ca, ton inbox reste propre et notre script sait exactement ou aller chercher.

### Ce qui a ete fait

- [x] Alias newsletters cree sur le compte principal (Admin Console)
- [x] Filtre Gmail : les emails envoyes a l'alias newsletters sont archives automatiquement et etiquetes "Newsletters-Digest"

### Verification

Envoie un email de test a ton alias newsletters depuis une autre adresse. Il ne doit pas apparaitre dans ton inbox, mais tu dois le retrouver dans Gmail en cliquant sur le label "Newsletters-Digest" dans la sidebar gauche.

---

## Prerequis 2 : Google Cloud Console

### Pourquoi

Google Cloud Console, c'est le "tableau de bord" de Google pour les developpeurs. Pense a ca comme un standard telephonique : quand tu utilises Gmail dans ton navigateur, tu passes par la porte d'entree normale. Mais quand un programme informatique (notre script Python) veut lire tes emails ou utiliser Gemini (l'IA de Google), il doit passer par une porte speciale : l'API (Application Programming Interface).

Pour utiliser cette porte speciale, il faut :
1. Un **projet** Google Cloud (un dossier qui regroupe tout)
2. **Activer les API** qu'on veut utiliser (Gmail + Gemini)
3. Des **credentials** (des cles d'acces) pour prouver que notre script a le droit d'entrer

C'est exactement comme un badge d'acces a un immeuble de bureaux : tu crees ton compte (le projet), tu demandes l'acces aux etages dont tu as besoin (les API), et on te donne un badge (les credentials).

### Step by step

#### Etape 2.1 — Accepter les free credits

Tu es sur la page d'accueil de Google Cloud Console (console.cloud.google.com). Tu vois le message "Try Google Cloud with $300 in free credits".

1. Clique sur **"Start Free"** ou **"Try for Free"**
2. Suis les etapes (il te demandera peut-etre une carte bancaire, mais c'est juste pour la verification — tu ne seras pas debite tant que tu ne passes pas en compte payant, et notre usage ne depassera jamais les credits gratuits)
3. Une fois fait, tu reviens sur le dashboard Google Cloud

> **Pourquoi $300 ?** Google offre ces credits pour que les developpeurs puissent tester. Notre projet consomme environ $0.20/mois en Gemini API. Les $300 te couvrent pour... 125 ans. Tu ne les depenseras jamais.

#### Etape 2.2 — Creer un projet

Un projet Google Cloud, c'est un dossier qui regroupe toutes les API, cles, et configs liees a une meme application. On en cree un pour notre Newsletter Digest.

1. En haut de la page, tu vois un selecteur de projet (ca peut afficher "Select a project" ou "My First Project")
2. Clique dessus
3. Dans la fenetre qui s'ouvre, clique sur **"New Project"** (en haut a droite)
4. Nom du projet : **`Newsletter Digest`**
5. Organisation : laisse tel quel (largo.cool ou "No organization")
6. Location : laisse tel quel
7. Clique sur **"Create"**
8. Attends quelques secondes, puis clique sur la notification **"Select Project"** qui apparait, ou retourne dans le selecteur de projet en haut et selectionne "Newsletter Digest"

**Verification :** En haut de la page, tu dois voir "Newsletter Digest" affiche comme projet actif.

#### Etape 2.3 — Activer Gmail API

Activer une API, c'est dire a Google : "je veux que mon projet ait le droit d'utiliser ce service". Tant que l'API n'est pas activee, notre script ne peut pas lire les emails.

1. Dans le menu de gauche (ou via la barre de recherche en haut), cherche **"APIs & Services"** (ou "API et services")
2. Clique sur **"Library"** (Bibliotheque)
3. Dans la barre de recherche, tape **"Gmail API"**
4. Clique sur **"Gmail API"** dans les resultats
5. Clique sur le gros bouton bleu **"Enable"** (Activer)
6. Attends quelques secondes — tu es redirige vers la page de l'API

**Verification :** Tu vois la page "Gmail API" avec le statut "Enabled" et des graphiques (vides pour l'instant, c'est normal).

#### Etape 2.4 — Activer Gemini API

Meme logique : on active l'acces a Gemini (l'IA de Google qui va analyser nos newsletters).

1. Retourne dans **"APIs & Services" > "Library"**
2. Cherche **"Generative Language API"** (c'est le nom technique de l'API Gemini)
3. Clique dessus
4. Clique sur **"Enable"**

> **Note :** Si tu ne trouves pas "Generative Language API", cherche "Gemini API" — Google change parfois les noms. L'important c'est d'activer l'API qui donne acces aux modeles Gemini.

**Verification :** Meme chose — statut "Enabled" sur la page de l'API.

#### Etape 2.5 — Configurer l'ecran de consentement OAuth

OAuth, c'est le systeme qui permet a notre script de se connecter a ton compte Gmail de facon securisee. Quand tu utilises "Se connecter avec Google" sur un site web, c'est OAuth. Ici, c'est la meme chose mais pour notre script Python.

Avant de creer les cles d'acces, Google exige qu'on configure un "ecran de consentement" — c'est la page qui s'affichera quand tu autoriseras le script a acceder a ton Gmail.

L'interface s'appelle desormais **"Google Auth Platform"** (et non plus "OAuth consent screen" dans APIs & Services). Tu la trouves dans le menu de gauche de la console Google Cloud.

1. Va dans **"Google Auth Platform" > "Branding"**
   - **App name** : `Newsletter Digest`
   - **User support email** : selectionne ton email principal
   - **Developer contact email** : ton email principal
   - Le reste : laisse vide
   - Clique sur **"Save"**
2. Va dans **"Google Auth Platform" > "Audience"**
   - Choisis **"Internal"** (disponible parce que tu es sur un Google Workspace largo.cool — ca limite l'acces aux comptes @largo.cool, pas besoin d'ajouter des test users ni de passer par la verification Google)
   - Clique sur **"Save"**

> **Pourquoi "Internal" ?** Comme tu as un Google Workspace (largo.cool), le mode Internal est plus simple et plus securise : seuls les comptes @largo.cool peuvent utiliser l'app, pas d'ecran d'avertissement "This app isn't verified", pas de test users a configurer. Si tu n'avais pas de Workspace (compte Gmail classique), il faudrait choisir "External" et s'ajouter en test user.

#### Etape 2.6 — Creer les credentials OAuth 2.0

Maintenant on cree le fameux "badge d'acces" — le fichier que notre script utilisera pour s'authentifier.

1. Va dans **"APIs & Services" > "Credentials"**
2. En haut, clique sur **"+ Create Credentials"**
3. Choisis **"OAuth client ID"**
4. Application type : **"Desktop app"**
5. Name : **`Newsletter Digest Desktop`** (ou ce que tu veux)
6. Clique sur **"Create"**
7. Une fenetre apparait avec ton "Client ID" et "Client Secret" — **ne les copie pas manuellement**
8. Clique sur **"Download JSON"** (icone de telechargement)
9. Un fichier `client_secret_XXXXX.json` est telecharge
10. **Renomme-le** en `credentials.json`
11. **Garde-le precieusement** — on le mettra dans le dossier du projet pendant le build

> **IMPORTANT : ne partage JAMAIS ce fichier.** C'est comme un mot de passe. Il donne acces a ton Gmail. On le mettra dans le `.env` ou a la racine du projet, et il sera exclu du versionning (`.gitignore`).

**Verification :** Tu as un fichier `credentials.json` sur ton Mac (probablement dans ~/Downloads). Ouvre-le avec un editeur de texte — tu dois voir un JSON avec "client_id", "client_secret", "redirect_uris", etc.

#### Etape 2.7 — Creer une API key pour Gemini

En plus d'OAuth (pour Gmail), on a besoin d'une API key simple pour Gemini. C'est un autre type de cle, plus simple : juste une chaine de caracteres.

1. Toujours dans **"APIs & Services" > "Credentials"**
2. Clique sur **"+ Create Credentials"**
3. Choisis **"API key"**
4. Une cle apparait (une longue chaine de caracteres genre `AIzaSy...`)
5. **Copie-la** et garde-la quelque part (un fichier texte temporaire, ou ton gestionnaire de mots de passe)
6. Optionnel mais recommande : clique sur **"Restrict Key"**, puis dans "API restrictions", selectionne **"Generative Language API"** uniquement. Comme ca, meme si la cle fuitait, elle ne pourrait etre utilisee que pour Gemini.
7. Clique sur **"Save"**

**Verification :** Tu as une API key Gemini (commence par `AIzaSy...`). Note-la quelque part de sur.

---

## Prerequis 3 : OpenAI (Whisper)

### Pourquoi

Whisper, c'est le modele d'OpenAI specialise dans la transcription audio-vers-texte. Il ecoute un fichier audio (un podcast, par exemple) et le transforme en texte ecrit.

On en a besoin **uniquement pour les podcasts**. Les videos YouTube ont deja des sous-titres generes automatiquement par YouTube qu'on recupere gratuitement. Mais les podcasts (Spotify, Apple Podcasts) n'ont pas de transcription — il faut donc telecharger l'audio et le transcrire.

Cout : $0.006 par minute, soit ~$0.36 pour un podcast d'1 heure. Avec 2-5 podcasts par mois, ca fait $1-2/mois.

### Step by step

#### Etape 3.1 — Creer un compte OpenAI

1. Va sur **platform.openai.com** (attention, pas chatgpt.com — c'est le site pour les developpeurs)
2. Clique sur **"Sign Up"** ou **"Log In"** si tu as deja un compte ChatGPT (c'est le meme compte)
3. Tu arrives sur le dashboard de l'API

#### Etape 3.2 — Ajouter du credit

OpenAI fonctionne en pre-paye : tu charges du credit, et chaque appel a l'API debite ton solde.

1. Va dans **"Settings" > "Billing"** (dans le menu de gauche)
2. Clique sur **"Add payment method"** et ajoute ta CB
3. Clique sur **"Add credit"** et ajoute **$5** (ca te couvre pour 2-3 mois de podcasts)

#### Etape 3.3 — Generer une API key

1. Va dans **"API Keys"** (dans le menu de gauche, ou via dashboard > API keys)
2. Clique sur **"Create new secret key"**
3. Nom : **`Newsletter Digest`**
4. Clique sur **"Create secret key"**
5. **Copie la cle immediatement** — elle ne sera plus affichee apres. Garde-la dans ton gestionnaire de mots de passe ou un fichier texte temporaire.

> La cle ressemble a `sk-proj-...` — c'est une longue chaine de caracteres.

**Verification :** Tu as une API key OpenAI (commence par `sk-proj-...`). Note-la quelque part de sur.

---

## Prerequis 4 : Notion Integration

### Pourquoi

Notre script doit ecrire dans ton Notion : creer des pages de digest, creer des sous-pages d'idees dans "Request for Startups". Pour ca, Notion exige un "token d'integration" — c'est un mot de passe special que Notion genere pour les applications externes.

En plus du token, il faut **partager** les pages Notion avec l'integration. C'est comme inviter quelqu'un dans un document Google Docs : tant que tu ne l'as pas invite, il ne peut pas y acceder, meme s'il a le lien.

### Step by step

#### Etape 4.1 — Creer une integration Notion

1. Va sur **notion.so/profile/integrations** (ou tape "Notion integrations" dans Google)
2. Clique sur **"New integration"** (ou "+ Create new integration")
3. Remplis :
   - **Name** : `Newsletter Digest`
   - **Associated workspace** : selectionne ton workspace (celui ou tu as "Dashboard Largo")
   - **Type** : "Internal" (c'est juste pour toi)
4. Clique sur **"Save"** / **"Submit"**
5. Tu arrives sur la page de l'integration. Tu vois un **"Internal Integration Secret"** (commence par `ntn_...` ou `secret_...`)
6. **Copie ce token** et garde-le precieusement

> **Ne partage jamais ce token.** Il donne acces en ecriture a ton Notion.

#### Etape 4.2 — Donner acces aux pages

Meme avec le token, l'integration ne peut acceder qu'aux pages que tu lui partages explicitement.

1. Ouvre ton Notion dans le navigateur
2. Va sur la page **"Dashboard Largo"**
3. En haut a droite, clique sur **"..."** (les trois points) > **"Connections"** > **"Connect to"** > cherche **"Newsletter Digest"** > clique dessus
4. Confirme quand Notion te demande si tu veux inclure les sous-pages (dis **oui** — ca donnera acces a "Request for Startups" et toutes les sous-pages d'idees)

**Verification :** L'integration "Newsletter Digest" apparait dans les connections de la page "Dashboard Largo". Tu peux verifier aussi sur "Request for Startups" — elle devrait y etre aussi (heritee de la page parente).

---

## Recapitulatif : ce que tu dois avoir a la fin

| Element | Ou le trouver | Format |
|---------|--------------|--------|
| Fichier `credentials.json` (OAuth Gmail) | Telecharge depuis Google Cloud Console | Fichier JSON |
| API key Gemini | Creee dans Google Cloud Console > Credentials | Chaine `AIzaSy...` |
| API key OpenAI (Whisper) | Creee dans platform.openai.com > API Keys | Chaine `sk-proj-...` |
| Token Notion | Cree dans notion.so/profile/integrations | Chaine `ntn_...` ou `secret_...` |

Quand tu as ces 4 elements, tu es pret pour le build. Ouvre un nouveau thread Cursor et dis : **"On lance le build du Newsletter Digest Agent"** en taguant `@PRD.md` et `@PLAN.md`.
