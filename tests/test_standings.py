from app.models import Match, Team
from app.services.standings import compute_standings


def mk(h, a, md, hs, as_, status="FINISHED"):
    return Match(
        id=f"{h}{a}{md}",
        league_id="TST",
        matchday=md,
        date="2024-01-01T12:00:00Z",
        home_team=Team(id=h, name=h),
        away_team=Team(id=a, name=a),
        home_score=hs,
        away_score=as_,
        status=status,
    )


def test_simple_points_3_1_0():
    matches = [
        mk("A", "B", 1, 2, 0),  # A gagne -> +3, B perd
        mk("B", "C", 1, 1, 1),  # B nul -> +1, C nul -> +1
        mk("C", "A", 1, 3, 0),  # C gagne -> +3, A perd
    ]
    s = compute_standings(matches, "TST", 2)
    by_team = {r.team_id: r for r in s.rows}
    assert by_team["A"].points == 3  # victoire (j1) + défaite (j1 vs C)
    assert by_team["B"].points == 1  # défaite + nul
    assert by_team["C"].points == 4  # nul + victoire
    assert by_team["A"].won == 1 and by_team["A"].lost == 1
    assert by_team["B"].drawn == 1


def test_tiebreak_points_then_goal_diff_then_goals():
    # A et B ont le même nombre de points (3), A meilleure diff de buts.
    matches = [
        mk("A", "X", 1, 3, 0),   # A +3, diff +3
        mk("B", "Y", 1, 2, 1),   # B +3, diff +1
    ]
    s = compute_standings(matches, "TST", 2)
    assert [r.team_id for r in s.rows[:2]] == ["A", "B"]

    # Même points et même diff -> buts marqués départage.
    matches = [
        mk("C", "X", 1, 2, 0),  # C +3 diff +2
        mk("D", "Y", 1, 3, 1),  # D +3 diff +2, plus de buts
    ]
    s = compute_standings(matches, "TST", 2)
    assert [r.team_id for r in s.rows[:2]] == ["D", "C"]


def test_custom_tiebreak_isolable():
    # Une compétition peut fournir sa propre stratégie de tri (par buts marqués d'abord).
    def by_goals(row):
        return (-row.goals_for, -row.points)

    matches = [
        mk("A", "X", 1, 1, 0),  # A 3pts 1 but
        mk("B", "Y", 1, 0, 0),  # B 3pts 0 but
    ]
    default = compute_standings(matches, "TST", 2)
    custom = compute_standings(matches, "TST", 2, tiebreak=by_goals)
    assert default.rows[0].team_id == "A" and custom.rows[0].team_id == "A"
    assert custom.rows[1].team_id == "B"


def test_position_is_before_matchday_only():
    # Position calculée UNIQUEMENT avec les matchs strictement antérieurs à la journée.
    # La journée 2 (courante) ne doit PAS influencer le classement de la journée 2.
    matches = [
        mk("A", "B", 1, 2, 0),  # journée 1 : A +3
        mk("B", "A", 2, 0, 1),  # journée 2 : A +3 (serait ajouté si bug)
    ]
    s = compute_standings(matches, "TST", 2)
    assert s.rows[0].team_id == "A"
    assert s.rows[0].points == 3  # 1 seule victoire, journée 1 seulement
    assert s.rows[0].played == 1


def test_last_matchday_uses_all_prior():
    matches = [
        mk("A", "B", 1, 2, 0),
        mk("A", "C", 2, 1, 0),
    ]
    # Classement avant la journée 3 -> tient compte des journées 1 et 2.
    s = compute_standings(matches, "TST", 3)
    assert s.rows[0].team_id == "A"
    assert s.rows[0].played == 2


def test_draw_scores_one_point_each():
    matches = [mk("A", "B", 1, 1, 1)]
    s = compute_standings(matches, "TST", 2)
    by_team = {r.team_id: r for r in s.rows}
    assert by_team["A"].points == 1 and by_team["B"].points == 1


def test_partial_matchday_ignored_in_standings():
    # Journée partielle : seul le match terminé compte pour le classement de la journée suivante.
    matches = [
        mk("A", "B", 1, 2, 0),
        mk("C", "D", 2, 0, 0, status="SCHEDULED"),  # non terminé, journée 2
    ]
    s = compute_standings(matches, "TST", 2)
    assert s.rows[0].played == 1
    assert all(r.team_id != "C" for r in s.rows)