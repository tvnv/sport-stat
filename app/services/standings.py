"""Calcul du classement.

Invariant métier P0 : la position affichée est le classement AVANT le début de la
journée concernée. On ne prend en compte QUE les matchs terminés strictement avant
la journée (matchday) demandée. Aucun résultat de la journée courante n'influence
le classement.

Scoring déterministe 3/1/0 : victoire = 3 pts, nul = 1 pt, défaite = 0 pt.
Tri : points DESC, puis différence de buts DESC, puis buts marqués DESC.
"""
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from ..models import Match, StandingRow, Standings

# Tie-break isolable : chaque compétition peut fournir sa propre stratégie de tri.
# La stratégie par défaut implémente points -> différence de buts -> buts marqués.
def default_tiebreak_key(row: StandingRow) -> Tuple[int, int, int]:
    return (-row.points, -row.goal_diff, -row.goals_for)


Tiebreak = Callable[[StandingRow], Tuple]


def _is_before(m: Match, matchday: int) -> bool:
    # Strictement antérieur à la journée : matchday < journée demandée.
    return m.matchday < matchday


def _accumulate(matches: Iterable[Match]) -> Dict[str, Dict[str, int]]:
    acc: Dict[str, Dict[str, int]] = {}
    for m in matches:
        for side in ("home", "away"):
            t = getattr(m, f"{side}_team")
            score = getattr(m, f"{side}_score")
            key = t.id
            bucket = acc.setdefault(
                key,
                {
                    "name": t.name,
                    "points": 0,
                    "goal_diff": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "played": 0,
                    "won": 0,
                    "drawn": 0,
                    "lost": 0,
                },
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
    matches: Iterable[Match],
    league_id: str,
    matchday: int,
    tiebreak: Optional[Tiebreak] = None,
) -> Standings:
    """Calcule le classement AVANT la journée `matchday`.

    Seuls les matchs strictement antérieurs à `matchday` sont retenus.
    """
    tiebreak = tiebreak or default_tiebreak_key
    prior = [m for m in matches if m.finished() and _is_before(m, matchday)]
    acc = _accumulate(prior)

    rows: List[StandingRow] = []
    for key, b in acc.items():
        rows.append(
            StandingRow(
                position=0,
                team_id=key,
                team_name=b["name"],
                points=b["points"],
                goal_diff=b["goal_diff"],
                goals_for=b["goals_for"],
                played=b["played"],
                won=b["won"],
                drawn=b["drawn"],
                lost=b["lost"],
            )
        )
    rows.sort(key=tiebreak)
    for i, r in enumerate(rows, start=1):
        r.position = i
    return Standings(league_id=league_id, matchday=matchday, rows=rows)