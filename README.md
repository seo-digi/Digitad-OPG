# Digitad OPG — Optimization Plan Generator

Outil interne Digitad pour generer automatiquement des plans d'optimisation SEO (Title, H1, Meta Description) pour les clients.

L'outil croise les donnees d'une etude de mots-cles avec les performances Google Search Console, propose un mapping mot-cle/URL via IA, et genere un fichier Excel avant/apres.

---

## Installation (une seule fois)

### 1. Prerequis

- **Python 3.9+** installe sur votre ordinateur
- **Un compte Anthropic** avec une cle API (demandez a votre responsable)


### 3. Installer les dependances

```bash
pip3 install -r requirements.txt
```

> La premiere execution telechargera aussi le modele d'embeddings (~470 MB). C'est normal, ca prend quelques minutes une seule fois.

### 4. Configurer votre cle API

```bash
cp .env.example .env
```

Ouvrez le fichier `.env` avec un editeur de texte et remplacez `sk-ant-api03-VOTRE-CLE-ICI` par votre vraie cle API LITE LLM:

```
LITELLM_API_KEY=sk-XXXXXXXXX-XXXXX
LITELLM_BASE_URL=https://litellm.XXXXX.ca/
```

> **IMPORTANT:** Ne partagez jamais votre cle API. Le fichier `.env` est ignore par Git et ne sera jamais committe.

---

## Utilisation

### Ce dont vous avez besoin avant de commencer

Pour chaque client, preparez ces 2 fichiers:

| Fichier | Format | Description |
|---------|--------|-------------|
| Etude de mots-cles | `.xlsx` (Excel) | L'etude de marche exportee de Google Sheets, avec les onglets FR et/ou EN |
| Donnees Search Console | `.csv` | Export CSV de SEO Gets (3 derniers mois, non-branded) | Pages

### Lancer l'outil

```
cd Digitad-OPG && python3 cli.py
```

### Le flow etape par etape

L'outil vous guide a chaque etape. Voici ce qui va se passer:

```
Etape 1 — Chargement des donnees
  → Le terminal vous demande le nom du client, la langue, et les chemins vers vos fichiers
  → L'outil charge et valide les donnees automatiquement

Etape 2 — Mapping des mots-cles
  → L'IA associe le meilleur mot-cle a chaque URL du site
  → Cela prend ~30 secondes (aucun cout API, tout se fait en local)

Etape 3 — Validation AI (optionnel)
  → L'outil vous demande si vous voulez une validation AI du mapping
  → Vous pouvez dire Non pour economiser des tokens

Etape 4 — Validation dans le navigateur
  → Votre navigateur s'ouvre automatiquement
  → Vous voyez un tableau avec toutes les pages et leurs mots-cles proposes
  → Modifiez les mots-cles si necessaire
  → Cliquez "Sauvegarder & Valider" quand vous etes satisfait

Etape 5 — Extraction des balises
  → L'outil scrape le Title, H1 et Meta Description actuels de chaque page
  → Suivez le progres en temps reel dans votre navigateur

Etape 6 — Reecriture IA
  → Claude genere de nouvelles balises optimisees pour chaque page
  → Le progres est visible dans votre navigateur

Etape 7 — Revision
  → Revenez au terminal pour revoir les reecritures une par une
  → Acceptez, modifiez, regenerez ou ignorez chaque page

Etape 8 — Export
  → Le fichier Excel final est genere dans le dossier du client
```

### Ou trouver le fichier final

Le fichier Excel est genere ici:

```
Digitad/
  {nom-du-client}/
    output/
      {client}_optimization_plan_{date}.xlsx
```

Exemple: `Digitad/Medicym/output/medicym_optimization_plan_2026-04-03.xlsx`

---

## Le fichier Excel

Le fichier contient 2 onglets (FR et EN) avec ces colonnes:

| Colonne | Description |
|---------|-------------|
| URL | L'adresse de la page |
| Mot-cle cible | Le mot-cle associe a la page |
| Volume mensuel | Le volume de recherche mensuel |
| Position actuelle | La position actuelle dans Google |
| Ancien Title | Le title tag actuel |
| **Nouveau Title** | Le title tag optimise |
| Ancien H1 | Le H1 actuel |
| **Nouveau H1** | Le H1 optimise |
| Ancienne Meta Desc | La meta description actuelle |
| **Nouvelle Meta Desc** | La meta description optimisee |

Les colonnes "Ancien" sont en gris, les colonnes "Nouveau" en vert.

---

## Reprendre un travail interrompu

Si l'outil est interrompu en cours de route (crash, fermeture accidentelle), relancez avec:

```bash
python3 cli.py --resume
```

L'outil reprendra automatiquement a la derniere etape completee (les donnees sont sauvegardees dans le dossier `.checkpoints` du client).

---

## Questions frequentes

### L'outil ne s'ouvre pas dans le navigateur

Si le navigateur ne s'ouvre pas automatiquement, le terminal affiche l'URL (ex: `http://localhost:50606`). Copiez-collez cette URL dans votre navigateur.

### Erreur "Cle API Anthropic manquante"

Verifiez que votre fichier `.env` existe et contient votre cle:
```bash
cat .env
```
Vous devriez voir: `ANTHROPIC_API_KEY=sk-ant-api03-...`

### Combien ca coute par client?

Environ **$0.30-0.50 USD** par execution (pour ~50 pages). Le cout vient uniquement des etapes 3 et 6 (appels Claude API). Tout le reste est gratuit (embeddings locaux).

### Je veux modifier le skill de redaction SEO

Les regles de redaction sont dans `config.py`, variable `SEO_SYSTEM_PROMPT`. Vous pouvez les modifier sans toucher au reste du code.

### Le modele d'embeddings prend beaucoup de place

Le modele `multilingual-e5-small` fait ~470 MB et est telecharge une seule fois dans le cache de votre machine. Il supporte le francais et l'anglais.

---

## Architecture technique

```
optimization-plan/
  cli.py          — Orchestrateur principal (point d'entree)
  config.py       — Configuration, regles SEO, constantes
  loader.py       — Chargement CSV + Excel
  mapper.py       — Mapping mot-cle/URL par embeddings
  scraper.py      — Extraction des balises HTML
  rewriter.py     — Reecriture via Claude API
  exporter.py     — Generation du fichier Excel
  server.py       — Serveur local pour l'interface web
  templates/      — Pages HTML (onboarding, mapping, progress)
  tests/          — Tests unitaires (36 tests)
```
