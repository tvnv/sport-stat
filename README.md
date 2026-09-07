# sport-stat

Application locale légère d’affichage des journées de championnats européens avec classement avant journée.

## V1

- 11 championnats obligatoires : Ligue 1, Ligue 2, Premier League, La Liga, Serie A, Serie B, Bundesliga, Primeira Liga, Super League Greece, Swiss Super League et Süper Lig.
- Trois vues : dernière journée (par défaut), aujourd’hui et prochaine journée.
- Chaque ligne de match affiche les équipes avec leur position **avant le début de la journée affichée**.
- Classement reconstruit uniquement avec les matchs terminés des journées strictement antérieures, scoring 3/1/0, tri points → différence de buts → buts marqués, avec tie-break spécialisé possible par compétition.
- Provider abstrait. Données réelles via API-Football si `API_FOOTBALL_KEY` est définie ; sinon provider de démonstration déterministe.
- Cache SQLite local avec fallback sur les dernières données connues si la source distante est indisponible.
- Interface responsive avec filtre pays.
- Docker/Compose sur le port 8080 et `GET /health` → `{"status":"ok"}`.

## Démarrage

```bash
docker compose up -d --build
# http://localhost:8080
```

Pour les données réelles, créer un `.env` à partir de `.env.example` et renseigner `API_FOOTBALL_KEY`. Sans clé, l’application démarre tout de même avec le provider local.

Démarrage local :

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## API

- `GET /health`
- `GET /api/dashboard?view=last`
- `GET /api/dashboard?view=today`
- `GET /api/dashboard?view=next`
- `GET /api/competitions`
- `GET /api/competitions/{competition}/last-matchday`
- `GET /api/competitions/{competition}/today`
- `GET /api/competitions/{competition}/next-matchday`

Les anciennes routes `/api/leagues` et `/api/competition/{id}` restent disponibles pour compatibilité.

## Première journée

Avant la J1, aucun classement sportif n’existe encore. L’application n’invente donc pas de rang : elle affiche `–` entre parenthèses jusqu’à ce qu’une journée antérieure terminée permette de calculer un classement.

## Tests

```bash
pytest -q
```
