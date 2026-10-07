from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import datetime as dt
import re

import requests
from dateutil import parser as dtparser

from core.config import (
    DEFAULT_MARKETS,
    DEFAULT_REGIONS,
    ESPN_NFL,
    ODDS_API_KEY,
    ODDS_BASE_URL,
    SPORT_KEY_NFL,
)
from core.http_cache import get_json_cached


@dataclass
class GameOdds:
    game_id: str
    commence_time_utc: str
    home_team: str
    away_team: str
    # spread from home team perspective: negative means home favored
    home_spread: Optional[float]
    # Which book/market used (debug/trace)
    spread_source: str


def _safe_float(x) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def _line_float(x) -> Optional[float]:
    """Parse ESPN line strings like '+3.5', '-7', 'PK', 'EVEN'."""
    if x is None:
        return None
    s = str(x).strip().upper()
    if s in {"PK", "PICK", "EVEN", "EV"}:
        return 0.0
    m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
    return float(m.group(0)) if m else None


def espn_home_spread(odds_list: Any, home_abbr: str | None = None, away_abbr: str | None = None) -> Optional[float]:
    """
    Home-perspective spread from an ESPN `competitions[0].odds` list (DraftKings).
    Prefers pointSpread.home.close.line, then `spread`, then parses `details` ("KC -3.5").
    """
    if not isinstance(odds_list, list):
        return None
    for o in odds_list:
        if not isinstance(o, dict):
            continue
        ps = o.get("pointSpread")
        if isinstance(ps, dict):
            home = ps.get("home") if isinstance(ps.get("home"), dict) else {}
            close = home.get("close") if isinstance(home.get("close"), dict) else {}
            v = _line_float(close.get("line"))
            if v is not None:
                return v
        v = _safe_float(o.get("spread"))
        if v is not None:
            return v
        details = str(o.get("details") or "").strip()
        if details.upper() in {"EVEN", "PK", "PICK"}:
            return 0.0
        m = re.match(r"^([A-Za-z]+)\s+([-+]?\d+(?:\.\d+)?)$", details)
        if m:
            abbr, line = m.group(1).upper(), float(m.group(2))
            if home_abbr and abbr == home_abbr.upper():
                return line
            if away_abbr and abbr == away_abbr.upper():
                return -line
    return None


def _fetch_espn_window(days_ahead: int, start_utc: dt.datetime, end_utc: dt.datetime) -> List[GameOdds]:
    """
    NFL games + DraftKings spreads from ESPN's scoreboard (no API key needed).
    ESPN only accepts single dates, so query each day in the window.
    """
    games: Dict[str, GameOdds] = {}
    day = (start_utc - dt.timedelta(days=1)).date()
    last = (end_utc + dt.timedelta(days=1)).date()
    while day <= last:
        ymd = day.strftime("%Y%m%d")
        try:
            resp = get_json_cached(
                f"{ESPN_NFL}/scoreboard",
                params={"dates": ymd},
                namespace="espn",
                cache_key=f"scoreboard:{ymd}",
                ttl_seconds=5 * 60,
                timeout_seconds=10,
            )
            data = resp.data or {}
        except Exception:
            data = {}
        for ev in data.get("events", []) or []:
            try:
                comp = ev["competitions"][0]
                home = next(t for t in comp["competitors"] if t.get("homeAway") == "home")
                away = next(t for t in comp["competitors"] if t.get("homeAway") == "away")
            except Exception:
                continue
            spread = espn_home_spread(
                comp.get("odds"),
                home.get("team", {}).get("abbreviation"),
                away.get("team", {}).get("abbreviation"),
            )
            gid = str(ev.get("id") or "")
            games[gid] = GameOdds(
                game_id=gid,
                commence_time_utc=str(comp.get("date") or ev.get("date") or ""),
                home_team=home.get("team", {}).get("displayName", ""),
                away_team=away.get("team", {}).get("displayName", ""),
                home_spread=spread,
                spread_source="espn_draftkings" if spread is not None else "no_spread_found",
            )
        day += dt.timedelta(days=1)
    return list(games.values())


def _fetch_odds_api_window(start_utc: dt.datetime, end_utc: dt.datetime, days_ahead: int) -> List[GameOdds]:
    url = f"{ODDS_BASE_URL}/sports/{SPORT_KEY_NFL}/odds"
    base_params = {
        "apiKey": ODDS_API_KEY,
        "regions": DEFAULT_REGIONS,
        "markets": DEFAULT_MARKETS,
        "oddsFormat": "american",
        "dateFormat": "iso",
    }
    params_with_window = dict(base_params)
    params_with_window["commenceTimeFrom"] = start_utc.isoformat().replace("+00:00", "Z")
    params_with_window["commenceTimeTo"] = end_utc.isoformat().replace("+00:00", "Z")

    data: List[Dict[str, Any]]
    try:
        resp = get_json_cached(
            url,
            params=params_with_window,
            namespace="odds_api",
            cache_key=f"nfl_odds_window:{days_ahead}:{start_utc.isoformat()}:{end_utc.isoformat()}",
            ttl_seconds=5 * 60,
            timeout_seconds=20,
        )
        data = resp.data
    except requests.HTTPError as e:
        if getattr(e.response, "status_code", None) != 422:
            raise
        resp = get_json_cached(
            url,
            params=base_params,
            namespace="odds_api",
            cache_key="nfl_odds_unfiltered",
            ttl_seconds=5 * 60,
            timeout_seconds=20,
        )
        data = resp.data

    games: List[GameOdds] = []
    for ev in data:
        home = ev.get("home_team")
        home_spreads = []
        for book in ev.get("bookmakers", []) or []:
            for mkt in book.get("markets", []) or []:
                if mkt.get("key") != "spreads":
                    continue
                for outcome in mkt.get("outcomes", []) or []:
                    if outcome.get("name") == home:
                        pt = _safe_float(outcome.get("point"))
                        if pt is not None:
                            home_spreads.append(pt)
        if home_spreads:
            s = sorted(home_spreads)
            mid = len(s) // 2
            consensus = s[mid] if len(s) % 2 == 1 else 0.5 * (s[mid - 1] + s[mid])
            src = "median_across_books"
        else:
            consensus, src = None, "no_spread_found"
        games.append(
            GameOdds(
                game_id=ev.get("id", ""),
                commence_time_utc=ev.get("commence_time"),
                home_team=home,
                away_team=ev.get("away_team"),
                home_spread=consensus,
                spread_source=src,
            )
        )
    return games


def fetch_nfl_spreads_window(days_ahead: int = 7) -> List[GameOdds]:
    """
    NFL games with home spreads for a window starting a few hours ago (so live games stay
    visible) through `days_ahead` days out.

    Uses ESPN's scoreboard (DraftKings line) by default. If ODDS_API_KEY is set, spreads
    from The Odds API (median across books) override ESPN's where the teams match.
    """
    days_ahead = max(0, int(days_ahead))
    now_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    # NFL games run ~3.5h; keep them visible while live.
    start_utc = now_utc - dt.timedelta(hours=5)
    end_utc = now_utc + dt.timedelta(days=days_ahead, hours=23, minutes=59)

    games = _fetch_espn_window(days_ahead, start_utc, end_utc)

    if ODDS_API_KEY:
        try:
            from core.standings import _normalize_team_name as norm

            oa = _fetch_odds_api_window(start_utc, end_utc, days_ahead)
            by_teams = {(norm(g.home_team or ""), norm(g.away_team or "")): g for g in oa}
            for g in games:
                hit = by_teams.get((norm(g.home_team), norm(g.away_team)))
                if hit and hit.home_spread is not None:
                    g.home_spread = hit.home_spread
                    g.spread_source = hit.spread_source
        except Exception:
            pass

    filtered: List[GameOdds] = []
    for g in games:
        if not g.commence_time_utc:
            continue
        try:
            t = dtparser.isoparse(g.commence_time_utc)
        except Exception:
            continue
        if start_utc <= t <= end_utc:
            filtered.append(g)
    filtered.sort(key=lambda g: dtparser.isoparse(g.commence_time_utc))
    return filtered

