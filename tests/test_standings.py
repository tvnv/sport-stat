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
    matches = [mk("A", "B", 1, 2, 0), mk("B", "C", 1, 1, 1), mk("C", "A", 1, 3, 0)]
    s = compute_standings(matches, "TST", 2)
    by_team = {r.team_id: r for r in s.rows}
    assert by_team["A"].points == 3
    assert by_team["B"].points == 1
    assert by_team["C"].points == 4


def test_tiebreak_points_then_goal_diff_then_goals():
    matches = [mk("A", "X", 1, 3, 0), mk("B", "Y", 1, 2, 1)]
    s = compute_standings(matches, "TST", 2)
    assert [r.team_id for r in s.rows[:2]] == ["A", "B"]

    matches = [mk("C", "X", 1, 2, 0), mk("D", "Y", 1, 3, 1)]
    s = compute_standings(matches, "TST", 2)
    assert [r.team_id for r in s.rows[:2]] == ["D", "C"]


def test_exact_tie_has_stable_final_order():
    matches = [mk("B", "Y", 1, 1, 0), mk("A", "X", 1, 1, 0)]
    s = compute_standings(matches, "TST", 2)
    contenders = [r.team_id for r in s.rows if r.team_id in {"A", "B"}]
    assert contenders == ["A", "B"]


def test_custom_tiebreak_isolable():
    def by_goals(row):
        return (-row.goals_for, -row.points)

    matches = [mk("A", "X", 1, 1, 0), mk("B", "Y", 1, 0, 0)]
    custom = compute_standings(matches, "TST", 2, tiebreak=by_goals)
    assert custom.rows[0].team_id == "A"


def test_position_is_before_matchday_only():
    matches = [
        mk("A", "B", 1, 2, 0),
        mk("B", "A", 2, 0, 1),
    ]
    s = compute_standings(matches, "TST", 2)
    assert s.rows[0].team_id == "A"
    assert s.rows[0].points == 3
    assert s.rows[0].played == 1


def test_first_matchday_has_no_invented_ranking():
    matches = [mk("A", "B", 1, 2, 0)]
    s = compute_standings(matches, "TST", 1)
    assert s.rows == []


def test_all_prior_matchdays_are_used():
    matches = [mk("A", "B", 1, 2, 0), mk("A", "C", 2, 1, 0)]
    s = compute_standings(matches, "TST", 3)
    assert s.rows[0].team_id == "A"
    assert s.rows[0].played == 2


def test_draw_scores_one_point_each():
    matches = [mk("A", "B", 1, 1, 1)]
    s = compute_standings(matches, "TST", 2)
    by_team = {r.team_id: r for r in s.rows}
    assert by_team["A"].points == 1 and by_team["B"].points == 1


def test_partial_current_matchday_is_ignored_in_its_own_standings():
    matches = [
        mk("A", "B", 1, 2, 0),
        mk("C", "D", 2, 0, 0, status="SCHEDULED"),
    ]
    s = compute_standings(matches, "TST", 2)
    assert s.rows[0].played == 1
    assert all(r.team_id != "C" for r in s.rows)


def test_unknown_matchday_zero_is_excluded_from_standings():
    # Un match sans round exploitable (matchday=0) ne doit pas compter dans le
    # classement de n'importe quelle journée : les vues l'ignorent déjà.
    matches = [
        mk("A", "B", 0, 2, 0),
        mk("C", "D", 1, 1, 0),
    ]
    s = compute_standings(matches, "TST", 2)
    assert all(r.team_id != "A" for r in s.rows)
    assert all(r.team_id != "B" for r in s.rows)
    assert {r.team_id for r in s.rows} == {"C", "D"}
