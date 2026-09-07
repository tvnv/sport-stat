"""Calcul déterministe du classement avant une journée.

Invariant P0 : seuls les matchs terminés de journées strictement antérieures à la
journée demandée sont intégrés. Aucun résultat de la journée affichée ne compte.
"""
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from ..models import Match, StandingRow, Standings


def default_tiebreak_key(row: StandingRow) -> Tuple:
    # Les trois règles métier minimales, puis un dernier critère stable uniquement
    # pour rendre l'ordre reproductible quand elles sont strictement égales.
    return (-row.points, -row.goal_diff, -row.goals_for, row.team_name.casefold(), row.team_id)


Tiebreak = Callable[[StandingRow], Tuple]


def _is_before(m: Match, matchday: int) -> bool:
    # Une journée inconnue (round absent, 0) ne peut pas nourrir le classement :
    # elle serait comptée pour chaque journée affichée.
    return 0 < m.matchday < matchday


def _accumulate(matches: Iterable[Match]) -> Dict[str, Dict[str, int]]:
    acc: Dict[str, Dict[str, int]] = {}
    for m in matches:
        for side in ("home", "away"):
            t = getattr(m, f"{side}_team")
            score = getattr(m, f"{side}_score")
            key = t.id
            bucket = acc.setdefault(
                key,
                {"name": t.name, "points": 0, "goal_diff": 0, "goals_for": 0,
                 "goals_against": 0, "played": 0, "won": 0, "drawn": 0, "lost": 0},
            )
            bucket["played"] += 1
            bucket["goals_for"] += score
            bucket["goals_against"] += m.home_score + m.away_score - score
            bucket["goal_diff"] += score - (m.home_score + m.away_score - score)
            other = m.home_score if side == "away" else m.away_score
            if score > other:
                bucket["won"] += 1
                bucket["points"] += 3
            elif score == other:
                bucket["drawn"] += 1
                bucket["points"] += 1
            else:
                bucket["lost"] += 1
    return acc


def compute_standings(
    matches: Iterable[Match], league_id: str, matchday: int, tiebreak: Optional[Tiebreak] = None,
) -> Standings:
    """Calcule le classement immédiatement avant `matchday`.

    Pour la première journée, aucun match antérieur n'existe : `rows` est vide.
    L'UI affiche alors « – » plutôt qu'inventer une position inexistante.
    """
    key = tiebreak or default_tiebreak_key
    prior = [m for m in matches if m.finished() and _is_before(m, matchday)]
    acc = _accumulate(prior)
    rows: List[StandingRow] = [
        StandingRow(
            position=0, team_id=team_id, team_name=b["name"], points=b["points"],
            goal_diff=b["goal_diff"], goals_for=b["goals_for"], played=b["played"],
            won=b["won"], drawn=b["drawn"], lost=b["lost"],
        )
        for team_id, b in acc.items()
    ]
    rows.sort(key=key)
    for i, row in enumerate(rows, start=1):
        row.position = i
    return Standings(league_id=league_id, matchday=matchday, rows=rows)
