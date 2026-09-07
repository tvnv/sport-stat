from collections import defaultdict


def _make_team_entry(team_id: int, team_name: str) -> dict:
    return {
        "team_id": team_id,
        "team_name": team_name,
        "played": 0, "win": 0, "draw": 0, "loss": 0,
        "goals_for": 0, "goals_against": 0,
        "goal_difference": 0, "points": 0,
        "h2h": defaultdict(lambda: {"pts": 0, "gf": 0, "ga": 0}),
    }


def _collect_all_teams(matches: list[dict], league_id: int, season: int) -> dict[int, dict]:
    teams: dict[int, dict] = {}
    for m in matches:
        if m["league_id"] == league_id and m["season"] == season:
            hid, aid = m["home_team_id"], m["away_team_id"]
            if hid not in teams:
                teams[hid] = _make_team_entry(hid, m["home_team_name"])
            if aid not in teams:
                teams[aid] = _make_team_entry(aid, m["away_team_name"])
    return teams


def compute_standings_for_round(
    matches: list[dict],
    league_id: int,
    season: int,
    target_round: str,
    tie_break_rules: list[str] | None = None,
) -> list[dict]:
    team_stats = _collect_all_teams(matches, league_id, season)

    matches_before = [
        m for m in matches
        if m["league_id"] == league_id
        and m["season"] == season
        and _round_is_before(m["round"], target_round)
        and m["status_short"] in ("FT", "P", "AET", "PEN")
    ]

    for m in matches_before:
        hid, aid = m["home_team_id"], m["away_team_id"]
        hg, ag = m["home_goals"], m["away_goals"]
        if hg is None or ag is None:
            continue
        hg, ag = int(hg), int(ag)

        team_stats[hid]["played"] += 1
        team_stats[aid]["played"] += 1
        team_stats[hid]["goals_for"] += hg
        team_stats[hid]["goals_against"] += ag
        team_stats[aid]["goals_for"] += ag
        team_stats[aid]["goals_against"] += hg
        team_stats[hid]["goal_difference"] = team_stats[hid]["goals_for"] - team_stats[hid]["goals_against"]
        team_stats[aid]["goal_difference"] = team_stats[aid]["goals_for"] - team_stats[aid]["goals_against"]

        team_stats[hid]["h2h"][aid]["gf"] += hg
        team_stats[hid]["h2h"][aid]["ga"] += ag
        team_stats[aid]["h2h"][hid]["gf"] += ag
        team_stats[aid]["h2h"][hid]["ga"] += hg

        if hg > ag:
            team_stats[hid]["win"] += 1
            team_stats[hid]["points"] += 3
            team_stats[aid]["loss"] += 1
            team_stats[hid]["h2h"][aid]["pts"] += 3
        elif hg < ag:
            team_stats[aid]["win"] += 1
            team_stats[aid]["points"] += 3
            team_stats[hid]["loss"] += 1
            team_stats[aid]["h2h"][hid]["pts"] += 3
        else:
            team_stats[hid]["draw"] += 1
            team_stats[aid]["draw"] += 1
            team_stats[hid]["points"] += 1
            team_stats[aid]["points"] += 1
            team_stats[hid]["h2h"][aid]["pts"] += 1
            team_stats[aid]["h2h"][hid]["pts"] += 1

    teams = list(team_stats.values())
    if not teams:
        return []

    teams.sort(key=lambda t: t["team_id"])
    _sort_with_tiebreak(teams, tie_break_rules or ["goal_difference", "goals_scored"])

    result = []
    for rank, t in enumerate(teams, 1):
        result.append({
            "team_id": t["team_id"],
            "team_name": t["team_name"],
            "played": t["played"],
            "win": t["win"],
            "draw": t["draw"],
            "loss": t["loss"],
            "goals_for": t["goals_for"],
            "goals_against": t["goals_against"],
            "goal_difference": t["goal_difference"],
            "points": t["points"],
            "rank": rank,
        })
    return result


def _round_is_before(r1: str, r2: str) -> bool:
    def extract_num(r: str) -> int:
        import re
        m = re.search(r"(\d+)", r)
        return int(m.group(1)) if m else 0
    return extract_num(r1) < extract_num(r2)


def _sort_with_tiebreak(teams: list[dict], rules: list[str]) -> None:
    rules = _validate_rules(rules)

    def criterion_value(rule: str, group: list[dict], team: dict):
        if rule == "points":
            return team["points"]
        if rule == "goal_difference":
            return team["goal_difference"]
        if rule == "goals_scored":
            return team["goals_for"]
        if rule.startswith("head_to_head"):
            gids = {t["team_id"] for t in group}
            total_pts = 0
            total_gd = 0
            total_gf = 0
            for opp_id, h2h in team.get("h2h", {}).items():
                if opp_id in gids:
                    total_pts += h2h["pts"]
                    total_gd += h2h["gf"] - h2h["ga"]
                    total_gf += h2h["gf"]
            if rule == "head_to_head_points":
                return total_pts
            if rule == "head_to_head_goal_difference":
                return total_gd
            if rule == "head_to_head_goals_scored":
                return total_gf
        return 0

    groups: list[list[dict]] = [teams]
    for rule in rules:
        next_groups: list[list[dict]] = []
        for group in groups:
            if len(group) <= 1:
                next_groups.append(group)
                continue
            scored = [(criterion_value(rule, group, t), t) for t in group]
            scored.sort(key=lambda x: (-x[0], x[1]["team_id"]))
            subgroup: list[dict] = []
            prev_val = None
            for val, team in scored:
                if prev_val is None or val == prev_val:
                    subgroup.append(team)
                else:
                    next_groups.append(subgroup)
                    subgroup = [team]
                prev_val = val
            next_groups.append(subgroup)
        groups = next_groups

    flat: list[dict] = []
    for group in groups:
        group.sort(key=lambda t: (-t["points"], -t["goal_difference"], -t["goals_for"], t["team_id"]))
        flat.extend(group)
    teams[:] = flat


def _validate_rules(rules: list[str]) -> list[str]:
    known = {
        "points", "goal_difference", "goals_scored",
        "head_to_head_points", "head_to_head_goal_difference",
        "head_to_head_goals_scored",
    }
    filtered = [r for r in rules if r in known]
    if not filtered:
        return ["goal_difference", "goals_scored"]
    if "points" not in filtered:
        filtered = ["points"] + filtered
    return filtered


def get_team_position(team_id: int, standings: list[dict]) -> int | None:
    for s in standings:
        if s["team_id"] == team_id:
            return s["rank"]
    return None
