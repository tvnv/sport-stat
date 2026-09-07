# sport-stat

Application personnelle de statistiques et d'affichage des championnats de football européens.

## Fonctionnalités (V1)

- **Source de données** : API-Football (plan Free) via `httpx`.
- **Technologies** : FastAPI + httpx + SQLite + HTML/CSS générés côté serveur + JS minimal + Docker.
- **Port HTTP** : `8080` (service).
- **Championnats supportés (11)** : Ligue 1, Ligue 2, Premier League, La Liga, Serie A, Serie B, Bundesliga, Primeira Liga, Super League Greece, Swiss Super League, Süper Lig.
- **Vues** : `Dernière journée` (défaut) | `Aujourd'hui` | `Prochaine journée`.
- **Positions avant journée** : chaque position affichée entre parenthèses est le classement **avant** le début de la journée concernée (reconstruit déterministiquement à partir des matchs précédents ; règles de départage isolées par compétition dans `config/competitions.yaml`). Avant la première journée, toutes les équipes de la compétition sont présentes avec 0 match / 0 point, ordonnées par identifiant d'équipe croissant (ordre documenté).
- **Dernière journée** : sélectionne la dernière journée entièrement terminée ; une journée partiellement jouée n'est jamais choisie.
- **Endpoint** : `GET /health` retourne `{"status": "ok"}`.

## Configuration

Configuration des championnats : `config/competitions.yaml`. Chaque compétition définit son identifiant API-Football (`api_football_id`), son pays et ses règles de départage (`tie_break_rules`) :

```yaml
  - name: "Ligue 1"
    api_football_id: 61
    country: "France"
    tie_break_rules:
      - goal_difference
      - goals_scored
      - head_to_head_points
      - head_to_head_goal_difference
      - head_to_head_goals_scored
```

Les règles de départage réellement supportées sont : `goal_difference`, `goals_scored`, `head_to_head_points`, `head_to_head_goal_difference`, `head_to_head_goals_scored`. Le `fair_play` n'est pas supporté faute de données réelles et ne doit pas être configuré.

Variables d'environnement (copier `.env.example` vers `.env`) :

| Variable | Description |
| --- | --- |
| `API_FOOTBALL_KEY` | Clé API-Football (https://www.api-football.com/) |
| `API_CACHE_TTL_SECONDS` | Durée de validité du cache SQLite (défaut `3600`) |
| `DATABASE_PATH` | Chemin du fichier SQLite (défaut `data/sport_stat.db`) |

## Lancer en local

```bash
pip install -r requirements.txt
export API_FOOTBALL_KEY=xxxxxxxxxxxxxxxx
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Ouvrir http://localhost:8080

## Lancer avec Docker

```bash
cp .env.example .env   # puis renseigner API_FOOTBALL_KEY
docker compose up --build
```

Ouvrir http://localhost:8080

## Tests

```bash
python -m pytest tests/ -q
```

## Structure

```
config/competitions.yaml   # 11 championnats + règles de départage
app/
  main.py                  # création de l'application FastAPI
  routes.py                # routes / et /health
  api_client.py            # client API-Football + persistance SQLite
  standings.py             # reconstruction déterministe des classements
  database.py              # schéma SQLite
  templates/               # HTML côté serveur
  static/                  # CSS
tests/
  test_health.py
  test_standings.py
```