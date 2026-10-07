from __future__ import annotations

from typing import Any


def _parse_line_float(x: Any) -> float | None:
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    try:
        if s.upper() in {"PK", "PICK", "EVEN", "EV"}:
            return 0.0
        return float(s.replace("+", ""))
    except Exception:
        return None


def extract_closing_spreads(summary: dict[str, Any]) -> dict[str, Any]:
    """
    Attempts to extract a *closing* point spread from ESPN summary JSON.

    Prefer `pickcenter[*].pointSpread.home/away.close.line` (DraftKings widget style).
    Fallback to `odds[*].spread.home/away.close.line` (older format).

    Returns keys:
      - home_spread_close (float|None)  # negative => home favored
      - away_spread_close (float|None)
      - spread_provider (str|None)
    """
    home_close = None
    away_close = None
    provider = None

    pickcenter = summary.get("pickcenter")
    if isinstance(pickcenter, list) and pickcenter:
        # Choose the first record that has a pointSpread dict.
        for rec in pickcenter:
            if not isinstance(rec, dict):
                continue
            ps = rec.get("pointSpread")
            if not isinstance(ps, dict):
                continue
            h = ps.get("home") if isinstance(ps.get("home"), dict) else None
            a = ps.get("away") if isinstance(ps.get("away"), dict) else None
            h_close = (h.get("close") if isinstance(h, dict) else None) if h else None
            a_close = (a.get("close") if isinstance(a, dict) else None) if a else None
            if isinstance(h_close, dict):
                home_close = _parse_line_float(h_close.get("line"))
            if isinstance(a_close, dict):
                away_close = _parse_line_float(a_close.get("line"))
            prov = rec.get("provider")
            if isinstance(prov, dict):
                provider = prov.get("name") or prov.get("displayName") or prov.get("id")
            if home_close is not None or away_close is not None:
                break

    if home_close is None and away_close is None:
        odds = summary.get("odds")
        if isinstance(odds, list) and odds:
            for rec in odds:
                if not isinstance(rec, dict):
                    continue
                sp = rec.get("spread")
                if not isinstance(sp, dict):
                    continue
                h = sp.get("home") if isinstance(sp.get("home"), dict) else None
                a = sp.get("away") if isinstance(sp.get("away"), dict) else None
                h_close = (h.get("close") if isinstance(h, dict) else None) if h else None
                a_close = (a.get("close") if isinstance(a, dict) else None) if a else None
                if isinstance(h_close, dict):
                    home_close = _parse_line_float(h_close.get("line"))
                if isinstance(a_close, dict):
                    away_close = _parse_line_float(a_close.get("line"))
                prov = rec.get("provider")
                if isinstance(prov, dict):
                    provider = prov.get("name") or prov.get("displayName") or prov.get("id")
                if home_close is not None or away_close is not None:
                    break

    # If only one side exists, infer the other.
    if home_close is None and away_close is not None:
        home_close = -float(away_close)
    if away_close is None and home_close is not None:
        away_close = -float(home_close)

    return {
        "home_spread_close": home_close,
        "away_spread_close": away_close,
        "spread_provider": provider,
    }
