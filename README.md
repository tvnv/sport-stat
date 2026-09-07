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

## Notes de campagne (stabilisation 2026-09-07)

Défauts corrigés lors de la campagne, chacun couvert par un test déterministe :

- **Contamination du cache SQLite** : un rafraîchissement partiel (ex. réponse API réduite) ne réintroduit plus d'anciens matchs dans le fallback. La dernière réponse réussie est la seule référence (`tests/test_cache.py::test_cache_partial_refresh_does_not_contaminate_fallback`).
- **Erreurs API-Football en HTTP 200** : un corps d'erreur (quota, clé invalide) lève désormais une exception pour que le cache serve le fallback au lieu d'une réponse vide trompeuse (`tests/test_cache.py::test_http_provider_raises_on_api_error_body`).
- **Vue « prochaine » sur journée étalée** : une journée qui s'étend sur plusieurs jours (vendredi → lundi) faisait afficher le même matchday pour « aujourd'hui » et « prochaine ». La vue « prochaine » est désormais strictement après la journée en cours (`tests/test_service.py::test_next_is_strictly_after_current_spanning_matchday`).
- **Matchs sans round exploitable** : un match avec `matchday = 0` ne peut plus entrer dans le classement de n'importe quelle journée (`tests/test_standings.py::test_unknown_matchday_zero_is_excluded_from_standings`).
- **Paramètre `view` invalide** : `/api/dashboard?view=invalide` retombe proprement sur `last` au lieu d'être renvoyé tel quel (`tests/test_endpoints.py::test_dashboard_invalid_view_falls_back_to_last`).
