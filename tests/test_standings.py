from app.standings import compute_standings_for_round, get_team_position


def _match(mid, round_str, home, away, hg, ag, status="FT", league=61, season=2026):
    return {
        "id": mid,
        "league_id": league,
        "season": season,
        "round": round_str,
        "date": f"2026-01-01T00:00:00Z",
        "home_team_id": home[0],
        "home_team_name": home[1],
        "away_team_id": away[0],
        "away_team_name": away[1],
        "home_goals": hg,
        "away_goals": ag,
        "status_short": status,
        "elapsed": None,
    }


def test_standings_before_matchday():
    # Round 1: after it, A wins, B wins, C loses, D loses
    matches = [
        _match(1, "Regular Season - 1", (101, "Alpha"), (102, "Beta"), 2, 0),
        _match(2, "Regular Season - 1", (103, "Gamma"), (104, "Delta"), 1, 0),
    ]
    standings_before_r2 = compute_standings_for_round(matches, 61, 2026, "Regular Season - 2", ["goal_difference", "goals_scored"])
    assert standings_before_r2[0]["team_name"] == "Alpha"
    assert standings_before_r2[0]["rank"] == 1
    assert standings_before_r2[1]["team_name"] == "Gamma"
    assert standings_before_r2[1]["rank"] == 2
    assert len(standings_before_r2) == 4

    # The two losers of round 1 (Beta, Delta) are ranked 3/4 (0 pts).
    # Teams that have not yet played the target matchday must still appear.
    names_after = [s["team_name"] for s in standings_before_r2]
    assert "Delta" in names_after


def test_standings_ignore_target_round_results():
    matches = [
        _match(1, "Regular Season - 1", (101, "Alpha"), (102, "Beta"), 2, 0),
        _match(2, "Regular Season - 1", (103, "Gamma"), (104, "Delta"), 1, 0),
        # Round 2 already played: Gamma AND Delta both have results. If the
        # matchday in question is Round 2, these results must NOT be included.
        _match(3, "Regular Season - 2", (103, "Gamma"), (101, "Alpha"), 9, 0),
        _match(4, "Regular Season - 2", (102, "Beta"), (104, "Delta"), 9, 0),
    ]
    standings_before_r2 = compute_standings_for_round(matches, 61, 2026, "Regular Season - 2", ["goal_difference", "goals_scored"])
    for s in standings_before_r2:
        assert s["played"] == 1, f"{s['team_name']} played {s['played']} but should have played only round-1 matches"
        # Goal difference must not include the 9-goal games of round 2.
        assert s["goal_difference"] not in (9, -9), f"{s['team_name']} leak of round-2 result"


def test_tiebreak_goal_difference():
    matches = [
        _match(1, "Regular Season - 1", (101, "Alpha"), (102, "Beta"), 1, 0),
        _match(2, "Regular Season - 1", (103, "Gamma"), (104, "Delta"), 5, 0),
        _match(3, "Regular Season - 1", (101, "Alpha"), (103, "Gamma"), 0, 0),
        _match(4, "Regular Season - 1", (102, "Beta"), (104, "Delta"), 0, 0),
    ]
    # Alpha: 1W 1D = 4pts, GD +1. Gamma: 1W 1D = 4pts, GD +5.
    standings = compute_standings_for_round(matches, 61, 2026, "Regular Season - 2", ["goal_difference", "goals_scored"])
    assert standings[0]["team_name"] == "Gamma"
    assert standings[1]["team_name"] == "Alpha"


def test_tiebreak_head_to_head():
    # La Liga rules: head_to_head before goal difference.
    # After 3 matchdays Alpha and Gamma are tied on 6 points, but Gamma has the
    # better overall goal difference (+4 vs +2). Alpha won the head-to-head
    # (1-0), so the h2h-first rules must rank Alpha above Gamma.
    matches = [
        _match(11, "Regular Season - 1", (101, "Alpha"), (103, "Gamma"), 1, 0),
        _match(12, "Regular Season - 1", (102, "Beta"), (104, "Delta"), 0, 0),
        _match(13, "Regular Season - 2", (101, "Alpha"), (104, "Delta"), 2, 0),
        _match(14, "Regular Season - 2", (103, "Gamma"), (102, "Beta"), 1, 0),
        _match(15, "Regular Season - 3", (103, "Gamma"), (104, "Delta"), 3, 0),
        _match(16, "Regular Season - 3", (101, "Alpha"), (102, "Beta"), 0, 1),
    ]
    standings = compute_standings_for_round(matches, 61, 2026, "Regular Season - 4",
                                            ["head_to_head_points",
                                             "head_to_head_goal_difference",
                                             "head_to_head_goals_scored",
                                             "goal_difference",
                                             "goals_scored"])
    assert standings[0]["team_name"] == "Alpha"
    assert standings[1]["team_name"] == "Gamma"

    # The same data with GD-first rules (English style) ranks Gamma above Alpha.
    epl_style = compute_standings_for_round(matches, 61, 2026, "Regular Season - 4",
                                            ["goal_difference", "goals_scored"])
    assert epl_style[0]["team_name"] == "Gamma"
    assert epl_style[1]["team_name"] == "Alpha"


def test_position_lookup():
    standings = [
        {"team_id": 101, "team_name": "Alpha", "rank": 1},
        {"team_id": 102, "team_name": "Beta", "rank": 2},
    ]
    assert get_team_position(102, standings) == 2
    assert get_team_position(999, standings) is None