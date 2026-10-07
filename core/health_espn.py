"""
NFL player impact + injury weights.

The NBA version measured each player's impact as PTS+REB+AST per game. Football
stats don't compare across positions, so the NFL version uses ESPN depth charts:
only listed starters count, and each starter's impact comes from a position weight
(a QB is worth far more than a guard). A team's `impact_share` values sum to 1, so
the rest of the pipeline (health = 1 - 0.6 * sum(injury_weight * share)) is unchanged.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.config import ESPN_NFL
from core.http_cache import get_json_cached
from core.standings import _normalize_team_name
from core.watchability_v2_params import (
    INJURY_WEIGHT_AVAILABLE,
    INJURY_WEIGHT_DOUBTFUL,
    INJURY_WEIGHT_OUT,
    INJURY_WEIGHT_PROBABLE,
    INJURY_WEIGHT_QUESTIONABLE,
)

ESPN_TEAMS_URL = f"{ESPN_NFL}/teams"
ESPN_DEPTH_URL = f"{ESPN_NFL}/teams/{{team_id}}/depthcharts"

# Relative value of a starter at each depth-chart slot. Matched against the slot key
# ESPN uses (qb, wr1, lt, lde, rolb, nt, fs, pk, ...). First matching rule wins.
POSITION_WEIGHTS: list[tuple[str, float]] = [
    (r"^qb$", 12.0),
    (r"^wr1$", 1.8),
    (r"^wr2$", 1.4),
    (r"^wr\d*$", 1.0),
    (r"^rb$", 1.2),
    (r"^te\d*$", 1.0),
    (r"^lt$", 1.0),
    (r"^(lg|c|rg|rt)$", 0.8),
    (r"^(lde|rde|lolb|rolb|de|edge)$", 1.1),
    (r"^(ldt|rdt|nt|dt)$", 0.8),
    (r"^(wlb|mlb|slb|lilb|rilb|ilb|lb)$", 0.7),
    (r"^(lcb|rcb|cb)$", 1.0),
    (r"^(ss|fs|s)$", 0.7),
    (r"^nb$", 0.5),
    (r"^pk$", 0.4),
]


def position_weight(slot: str) -> float:
    s = (slot or "").strip().lower()
    for pat, w in POSITION_WEIGHTS:
        if re.match(pat, s):
            return w
    return 0.0


def _injury_weight(status: str) -> float:
    s = (status or "").strip().lower()
    if not s:
        return INJURY_WEIGHT_AVAILABLE
    if s in {"o", "ir", "ir-r", "inactive", "susp", "suspension"} or s.startswith(("pup", "nfi")):
        return INJURY_WEIGHT_OUT
    if "injured reserve" in s or "out" in s or "suspen" in s or "physically unable" in s:
        return INJURY_WEIGHT_OUT
    if "doubt" in s or s == "d":
        return INJURY_WEIGHT_DOUBTFUL
    if "question" in s or s == "q":
        return INJURY_WEIGHT_QUESTIONABLE
    if "prob" in s or s == "p":
        return INJURY_WEIGHT_PROBABLE
    return INJURY_WEIGHT_AVAILABLE


def injury_weight(status: str) -> float:
    """Convert an ESPN NFL injury status (Out, Doubtful, Questionable, IR, ...) into a 0..1 weight."""
    return _injury_weight(status)


@dataclass
class PlayerImpact:
    athlete_id: str
    name: str
    position: str
    # Kept for compatibility with the NBA pipeline's star formula (always 0 for NFL).
    points_per_game: float
    assists_per_game: float
    rebounds_per_game: float
    steals_per_game: float
    blocks_per_game: float
    raw_impact: float
    impact_share: float
    relative_raw_impact: float
    injury_status: str = ""
    injury_weight: float = 0.0


def fetch_team_id_map(*, ttl_seconds: int = 7 * 24 * 60 * 60) -> Dict[str, str]:
    """normalized team name -> ESPN team id"""
    resp = get_json_cached(
        ESPN_TEAMS_URL,
        namespace="espn",
        cache_key="teams",
        ttl_seconds=ttl_seconds,
        timeout_seconds=15,
    )
    out: Dict[str, str] = {}

    def walk(o: Any) -> None:
        if isinstance(o, dict):
            t = o.get("team")
            if isinstance(t, dict) and t.get("id") and t.get("displayName"):
                out[_normalize_team_name(str(t["displayName"]))] = str(t["id"])
                return
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(resp.data)
    return out


def fetch_team_starters(team_id: str, *, ttl_seconds: int = 6 * 60 * 60) -> List[tuple[str, str, str]]:
    """
    Returns [(athlete_id, name, slot)] for the first player at each depth-chart slot,
    across offense, defense and kicker. A player listed in two slots keeps the higher-weight one.
    """
    resp = get_json_cached(
        ESPN_DEPTH_URL.format(team_id=team_id),
        namespace="espn",
        cache_key=f"depthchart:{team_id}",
        ttl_seconds=ttl_seconds,
        timeout_seconds=15,
    )
    data = resp.data or {}
    best: Dict[str, tuple[str, str, float]] = {}
    for formation in data.get("depthchart", []) or []:
        positions = formation.get("positions") if isinstance(formation, dict) else None
        if not isinstance(positions, dict):
            continue
        for slot, p in positions.items():
            w = position_weight(slot)
            if w <= 0 or not isinstance(p, dict):
                continue
            athletes = p.get("athletes") or []
            if not athletes or not isinstance(athletes[0], dict):
                continue
            a = athletes[0]
            aid = str(a.get("id") or "").strip()
            if not aid:
                continue
            name = str(a.get("displayName") or a.get("fullName") or "")
            if aid not in best or w > best[aid][2]:
                best[aid] = (name, slot.upper(), w)
    return [(aid, name, slot) for aid, (name, slot, _) in best.items()]


def compute_team_player_impacts(team_name: str, *, season_year: Optional[int] = None) -> List[PlayerImpact]:
    """
    Per-starter impact for one team. impact_share sums to 1 across starters.
    """
    team_id = fetch_team_id_map().get(_normalize_team_name(team_name))
    if not team_id:
        return []
    starters = fetch_team_starters(team_id)
    raws = [(aid, name, slot, position_weight(slot)) for aid, name, slot in starters]
    total = sum(r[3] for r in raws) or 1.0
    top = max((r[3] for r in raws), default=1.0) or 1.0
    players = [
        PlayerImpact(
            athlete_id=aid,
            name=name,
            position=slot,
            points_per_game=0.0,
            assists_per_game=0.0,
            rebounds_per_game=0.0,
            steals_per_game=0.0,
            blocks_per_game=0.0,
            raw_impact=float(w),
            impact_share=float(w) / total,
            relative_raw_impact=float(w) / top,
        )
        for aid, name, slot, w in raws
    ]
    players.sort(key=lambda p: p.raw_impact, reverse=True)
    return players
