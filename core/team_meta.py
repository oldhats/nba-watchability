from __future__ import annotations

import re
from typing import Optional

# Canonical mapping: normalized team name -> ESPN abbreviation

TEAM_ABBR = {
    "arizona cardinals": "ARI",
    "atlanta falcons": "ATL",
    "baltimore ravens": "BAL",
    "buffalo bills": "BUF",
    "carolina panthers": "CAR",
    "chicago bears": "CHI",
    "cincinnati bengals": "CIN",
    "cleveland browns": "CLE",
    "dallas cowboys": "DAL",
    "denver broncos": "DEN",
    "detroit lions": "DET",
    "green bay packers": "GB",
    "houston texans": "HOU",
    "indianapolis colts": "IND",
    "jacksonville jaguars": "JAX",
    "kansas city chiefs": "KC",
    "las vegas raiders": "LV",
    "los angeles chargers": "LAC",
    "los angeles rams": "LAR",
    "miami dolphins": "MIA",
    "minnesota vikings": "MIN",
    "new england patriots": "NE",
    "new orleans saints": "NO",
    "new york giants": "NYG",
    "new york jets": "NYJ",
    "philadelphia eagles": "PHI",
    "pittsburgh steelers": "PIT",
    "san francisco 49ers": "SF",
    "seattle seahawks": "SEA",
    "tampa bay buccaneers": "TB",
    "tennessee titans": "TEN",
    "washington commanders": "WSH",
}

TEAM_MASCOT = {
    "arizona cardinals": "Cardinals",
    "atlanta falcons": "Falcons",
    "baltimore ravens": "Ravens",
    "buffalo bills": "Bills",
    "carolina panthers": "Panthers",
    "chicago bears": "Bears",
    "cincinnati bengals": "Bengals",
    "cleveland browns": "Browns",
    "dallas cowboys": "Cowboys",
    "denver broncos": "Broncos",
    "detroit lions": "Lions",
    "green bay packers": "Packers",
    "houston texans": "Texans",
    "indianapolis colts": "Colts",
    "jacksonville jaguars": "Jaguars",
    "kansas city chiefs": "Chiefs",
    "las vegas raiders": "Raiders",
    "los angeles chargers": "Chargers",
    "los angeles rams": "Rams",
    "miami dolphins": "Dolphins",
    "minnesota vikings": "Vikings",
    "new england patriots": "Patriots",
    "new orleans saints": "Saints",
    "new york giants": "Giants",
    "new york jets": "Jets",
    "philadelphia eagles": "Eagles",
    "pittsburgh steelers": "Steelers",
    "san francisco 49ers": "49ers",
    "seattle seahawks": "Seahawks",
    "tampa bay buccaneers": "Buccaneers",
    "tennessee titans": "Titans",
    "washington commanders": "Commanders",
}


def normalize_team_name(name: str) -> str:
    # Keep in sync with `core.standings._normalize_team_name` behavior (but avoid importing it here).
    n = name.lower().strip()
    n = re.sub(r"[^a-z0-9\s]", "", n)
    n = re.sub(r"\s+", " ", n)
    # common aliases
    n = n.replace("la chargers", "los angeles chargers")
    n = n.replace("la rams", "los angeles rams")
    n = n.replace("ny giants", "new york giants")
    n = n.replace("ny jets", "new york jets")
    return n


def get_team_abbr(team_name: str) -> Optional[str]:
    return TEAM_ABBR.get(normalize_team_name(team_name))


def get_team_mascot(team_name: str) -> Optional[str]:
    """
    Returns the mascot/nickname (e.g. 'Chiefs') for display in compact/mobile layouts.
    """
    n = normalize_team_name(team_name)
    mascot = TEAM_MASCOT.get(n)
    if mascot:
        return mascot
    parts = [p for p in n.split(" ") if p]
    if not parts:
        return None
    return parts[-1].title()


def get_logo_url(team_name: str, size: int = 500) -> Optional[str]:
    abbr = get_team_abbr(team_name)
    if not abbr:
        return None
    size_i = int(size) if size is not None else 500
    if size_i not in {500, 200}:
        size_i = 500
    return f"https://a.espncdn.com/i/teamlogos/nfl/{size_i}/{abbr.lower()}.png"
