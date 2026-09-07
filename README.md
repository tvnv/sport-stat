# sport-stat

Application personnelle de statistiques et d’affichage des championnats de football européens — V1 tableau des journées.

## Fonctionnalités

- **11 championnats** configurables (`config/leagues.yaml`) : Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Primeira Liga, Eredivisie, Brasileirão, Jupiler Pro League, Champions League, Europa League.
- **Vues** : dernière journée (défaut), aujourd'hui, prochaine journée.
- **Classement avant journée (P0)** : la position entre parenthèses de chaque équipe est calculée **exclusivement** avec les matchs strictement antérieurs à la journée affichée. Aucun résultat de la journée courante n'influence le classement.
- **Scoring déterministe 3/1/0** (victoire/nul/défaite), tri points → différence de buts → buts marqués. Tie-break isolable par compétition (`COMPETITION_TIEBREAKS`).
- **FootballProvider** : abstraction du provider externe (football-data.org). Cache SQLite local (TTL 6h) évitant un appel externe à chaque page, avec **fallback** sur les dernières données connues si le provider est indisponible.
- **UI compacte responsive** : pays, ligue, journée, date, matchs, score ou heure, statut.
- **Docker + docker compose** sur le port **8080**, `.env.example` sans secret.

## Démarrage

```bash
# Docker
cp .env.example .env
docker compose up --build     # http://localhost:8080

# Local
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Sans `FOOTBALL_API_TOKEN`, un provider de démonstration déterministe est utilisé (aucune clé requise). Configurez `FOOTBALL_API_TOKEN` dans `.env` pour les données réelles.

## Endpoints

- `GET /health` → `{"status":"ok"}`
- `GET /` — dashboard
- `GET /api/dashboard?label=last|today|next`
- `GET /competition/{league_id}`
- `GET /api/competition/{league_id}?label=last|today|next`
- `GET /api/leagues`

## Tests

```bash
pytest -q
```

Couvrent : classement 3/1/0, tie-break (défaut + isolable), position avant-journée, dernière journée, nul, journée partielle, cache/fallback, endpoints et pages.