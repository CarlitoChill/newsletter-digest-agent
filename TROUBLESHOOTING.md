# Dépannage — Newsletter Digest Agent

## Je n'ai pas reçu le digest le vendredi à 12h (ou pas de nouvelles idées RFS)

### 1. Vérifier si launchd est installé et chargé

Les jobs doivent être dans `~/Library/LaunchAgents/` et chargés par `launchctl`.

```bash
# Lister les jobs du projet
launchctl list | grep newsletter-digest
```

Tu dois voir au moins :
- `cool.largo.newsletter-digest.poll`
- `cool.largo.newsletter-digest.digest`

Si tu ne vois rien, les plists ne sont pas installés ou pas chargés.

### 2. Vérifier les logs du jour

Les scripts écrivent dans `data/` à la racine du projet :

```bash
cd projects/01-newsletter-digest   # ou ton chemin projet

# Dernières lignes du digest (vendredi 12h)
tail -100 data/digest.log

# Dernières lignes du poll (tous les jours 6h)
tail -100 data/poll.log
```

- Si **digest.log** n'a pas d'entrée "Digest started" ce vendredi vers 12h → le job digest n'a pas été lancé (launchd pas installé, Mac éteint/veille, ou plist incorrect).
- Si **poll.log** n'a pas d'entrée "Poll started" cette semaine → pas de nouveaux emails traités donc pas de nouvelles idées RFS.

### 3. Lancer le digest à la main (récupérer le digest de la semaine)

Pour recevoir tout de suite le digest sans attendre le prochain vendredi :

```bash
cd projects/01-newsletter-digest
source .venv/bin/activate
python -m src.main digest
```

Option pour forcer la génération même si un digest existe déjà pour la période :

```bash
python -m src.main digest --force
```

Tu devrais recevoir l'email et voir la page Notion du digest se créer.

### 4. Installer ou réinstaller launchd (si les plists manquent)

Les plists sont dans `scripts/launchd/`. Il faut les copier dans `~/Library/LaunchAgents/` en **remplaçant le chemin du projet** par le tien.

```bash
cd projects/01-newsletter-digest
PROJECT_PATH="$(pwd)"

# Remplacer le placeholder dans les plists et copier
sed "s|PROJECT_PATH_PLACEHOLDER|$PROJECT_PATH|g" scripts/launchd/cool.largo.newsletter-digest.poll.plist > ~/Library/LaunchAgents/cool.largo.newsletter-digest.poll.plist
sed "s|PROJECT_PATH_PLACEHOLDER|$PROJECT_PATH|g" scripts/launchd/cool.largo.newsletter-digest.digest.plist > ~/Library/LaunchAgents/cool.largo.newsletter-digest.digest.plist

# Charger les jobs
launchctl load ~/Library/LaunchAgents/cool.largo.newsletter-digest.poll.plist
launchctl load ~/Library/LaunchAgents/cool.largo.newsletter-digest.digest.plist

# Vérifier
launchctl list | grep newsletter-digest
```

**Important :** Si tu déplaces le projet ailleurs, refais cette procédure avec le nouveau chemin (ou édite les plists dans `~/Library/LaunchAgents/` à la main).

### 5. Rappel des horaires

- **Poll** : tous les jours à **6h** (heure locale) → lit les nouveaux emails, analyse, crée les idées dans Request for Startups.
- **Digest** : **vendredi à 12h** (heure locale) → compile le digest de la semaine, crée la page Notion, envoie l'email.

Si le Mac était en veille ou éteint à 6h ou à 12h vendredi, le job ne tourne pas (launchd ne rattrape pas les exécutions manquées).

### 6. Désinstaller les jobs (pour debug ou arrêt)

```bash
launchctl unload ~/Library/LaunchAgents/cool.largo.newsletter-digest.poll.plist
launchctl unload ~/Library/LaunchAgents/cool.largo.newsletter-digest.digest.plist
```

Tu peux ensuite relancer poll et digest à la main quand tu veux.
