from app.standings import (
    compute_standings_for_round,
    get_team_position,
    _validate_rules,
)


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


def test_standings_before_first_matchday_include_all_teams():
    # All teams of the competition/saison are known through their fixtures.
    # Before matchday 1, every team must appear with played=0 and points=0.
    matches = [
        _match(1, "Regular Season - 1", (101, "Alpha"), (102, "Beta"), 2, 0),
        _match(2, "Regular Season - 1", (103, "Gamma"), (104, "Delta"), 1, 0),
        _match(3, "Regular Season - 2", (101, "Alpha"), (103, "Gamma"), 0, 0, status="NS"),
        _match(4, "Regular Season - 2", (102, "Beta"), (104, "Delta"), 0, 0, status="NS"),
    ]
    # Note: even when target_round is matchday 1 (before any match of the
    # competition is "played"/finished), all four teams must be present.
    standings = compute_standings_for_round(matches, 61, 2026, "Regular Season - 1", ["goal_difference", "goals_scored"])
    assert len(standings) == 4
    for s in standings:
        assert s["played"] == 0
        assert s["points"] == 0
    # Deterministic order before any match: ascending team_id as documented.
    assert [s["team_id"] for s in standings] == [101, 102, 103, 104]


def test_standings_before_matchday_include_all_teams_after_some_rounds():
    # Even for a later matchday, a team that has not yet "played" a finished
    # match (but is scheduled) must still be present with played=0.
    matches = [
        _match(1, "Regular Season - 1", (101, "Alpha"), (102, "Beta"), 2, 0),
        _match(2, "Regular Season - 1", (103, "Gamma"), (104, "Delta"), 1, 0, status="NS"),
        _match(3, "Regular Season - 2", (101, "Alpha"), (103, "Gamma"), 0, 0, status="NS"),
        _match(4, "Regular Season - 2", (102, "Beta"), (104, "Delta"), 0, 0, status="NS"),
    ]
    standings = compute_standings_for_round(matches, 61, 2026, "Regular Season - 2", ["goal_difference", "goals_scored"])
    # Delta's match was not finished in round 1 -> 0 played, but still listed.
    delta = [s for s in standings if s["team_id"] == 104][0]
    assert delta["played"] == 0
    assert delta["points"] == 0
    assert len(standings) == 4


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


def test_standings_exclude_target_round_and_incomplete():
    # A team that only "played" (finished) a match of the target round must NOT
    # have it counted; teams that played a partial target round must remain at
    # the pre-round state.
    matches = [
        _match(1, "Regular Season - 1", (101, "Alpha"), (102, "Beta"), 2, 0),
        _match(2, "Regular Season - 1", (103, "Gamma"), (104, "Delta"), 1, 0),
        # Target round 2: one match finished, one still scheduled.
        _match(3, "Regular Season - 2", (103, "Gamma"), (101, "Alpha"), 9, 0, status="FT"),
        _match(4, "Regular Season - 2", (102, "Beta"), (104, "Delta"), 5, 5, status="NS"),
    ]
    standings = compute_standings_for_round(matches, 61, 2026, "Regular Season - 2", ["goal_difference", "goals_scored"])
    for s in standings:
        assert s["played"] == 1
        assert s["goal_difference"] not in (9, -9, 5, -5)


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


def test_tiebreak_rules_validated_and_points_always_first():
    # points is always prepended if missing.
    rules = _validate_rules(["goal_difference", "goals_scored"])
    assert rules == ["points", "goal_difference", "goals_scored"]
    # fair_play is filtered out as an unsupported rule (no silent constant 0).
    rules = _validate_rules(["goal_difference", "fair_play"])
    assert "fair_play" not in rules
    assert rules == ["points", "goal_difference"]
    # Unknown rules are filtered out.
    rules = _validate_rules(["bogus"])
    assert rules == ["goal_difference", "goals_scored"]


def test_tiebreak_rules_consistency_documented():
    # The rules used by the configs must be a strict subset of what the
    # implementation actually supports. fair_play must NOT be simulated by a
    # silent constant (config no longer includes it).
    import yaml
    from pathlib import Path
    from app.config import COMPETITIONS_CONFIG
    with open(COMPETITIONS_CONFIG) as f:
        data = yaml.safe_load(f)
    supported = {
        "points", "goal_difference", "goals_scored",
        "head_to_head_points", "head_to_head_goal_difference",
        "head_to_head_goals_scored",
    }
    for comp in data["competitions"]:
        for rule in comp.get("tie_break_rules", []):
            assert rule in supported, f"{comp['name']} uses unsupported rule {rule}"
            assert rule != "fair_play", f"{comp['name']} still advertises fair_play"


def test_position_lookup():
    standings = [
        {"team_id": 101, "team_name": "Alpha", "rank": 1},
        {"team_id": 102, "team_name": "Beta", "rank": 2},
    ]
    assert get_team_position(102, standings) == 2
    assert get_team_position(999, standings) is None