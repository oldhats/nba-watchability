from __future__ import annotations

from typing import Dict, Optional, Tuple
import re

def _normalize_team_name(name: str) -> str:
    # Lightweight normalization to improve matching across data sources.
    n = name.lower().strip()
    n = re.sub(r"[^a-z0-9\s]", "", n)
    n = re.sub(r"\s+", " ", n)
    # common aliases
    n = n.replace("la chargers", "los angeles chargers")
    n = n.replace("la rams", "los angeles rams")
    n = n.replace("ny giants", "new york giants")
    n = n.replace("ny jets", "new york jets")
    return n

def fetch_team_win_pct_map() -> Dict[str, float]:
    """
    Returns dict mapping normalized team name -> win_pct (0..1), from ESPN NFL standings.
    """
    try:
        from core.standings_espn import fetch_team_win_pct_map as _espn

        return _espn()
    except Exception:
        # Fallback to neutral priors.
        return {}


def get_win_pct(team_name: str, winpct_map: Dict[str, float], default: float = 0.5) -> float:
    key = _normalize_team_name(team_name)
    return float(winpct_map.get(key, default))


def get_record(
    team_name: str,
    record_map: Dict[str, Tuple[int, int]],
    default: Tuple[Optional[int], Optional[int]] = (None, None),
) -> Tuple[Optional[int], Optional[int]]:
    key = _normalize_team_name(team_name)
    return record_map.get(key, default)  # type: ignore[return-value]
