from __future__ import annotations

import html as py_html
import datetime as dt
import textwrap

import altair as alt
import pandas as pd
import streamlit as st
from dateutil import tz

from core.build_watchability_df import _parse_time_remaining, build_watchability_df
from core.config import LOCAL_TZ_NAME
from core.team_meta import get_team_abbr, get_team_mascot

import core.watchability as watch

LOCAL_TZ = tz.gettz(LOCAL_TZ_NAME)

# Must Watch -> Hard Skip: one red, fading out. A fade recedes toward the background in both
# light and dark themes, so "more red = more watchable" holds either way.
REGION_ORDER = ["Must Watch", "Strong Watch", "Watchable", "Skippable", "Hard Skip"]
REGION_COLORS = {
    "Must Watch": "rgba(224,64,59,1.0)",
    "Strong Watch": "rgba(224,64,59,0.72)",
    "Watchable": "rgba(224,64,59,0.48)",
    "Skippable": "rgba(224,64,59,0.28)",
    "Hard Skip": "rgba(224,64,59,0.12)",
}
# Chart text that must read on white and on the dark background (~3.3:1 and ~5.7:1).
CHART_INK = "#8a8f98"


def _normalize_dashboard_df_types(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    d = df.copy()
    for c in ["Kickoff dt (ET)", "Kickoff dt (UTC)"]:
        if c in d.columns:
            d[c] = pd.to_datetime(d[c], errors="coerce")
    d["Team Quality"] = d["Team quality"]
    d["Competitiveness"] = d["Closeness"]
    return d


@st.cache_data(ttl=60 * 5)
def load_watchability_df(days_ahead: int = 7) -> pd.DataFrame:
    return _normalize_dashboard_df_types(build_watchability_df(days_ahead=days_ahead))


def inject_base_css() -> None:
    st.markdown(
        """
<style>
/* Hide Streamlit multipage/sidebar nav (cleaner + more professional). */
section[data-testid="stSidebar"] {display: none;}
div[data-testid="stSidebarNav"] {display: none;}
div[data-testid="collapsedControl"] {display: none;}

.block-container {padding-top: 1rem; padding-bottom: 1rem;}
.menu-row {display:flex; align-items:center; gap:12px;}
.menu-awi {width:110px;}
.menu-awi .score {font-size: 14px; font-weight: 650; line-height: 1.15; word-break: break-word;}
.menu-awi .subscores {margin-top: 2px; font-size: 12px; color: color-mix(in srgb, currentColor 75%, transparent); line-height: 1.15;}
.menu-awi .subscore {display:block;}
.menu-awi .label {font-size: 18px; font-weight: 800; color: color-mix(in srgb, currentColor 90%, transparent); line-height: 1.15;}
.live-badge {color: #e0403b; font-weight: 700; font-size: 13px; margin-top: 2px;}
.live-time {color: #e0403b; font-size: 13px; line-height: 1.1; margin-top: 2px;}
.menu-teams {flex: 1; display:flex; align-items:center; gap:10px; min-width: 240px;}
.menu-teams .team {display:flex; align-items:center; gap:8px; min-width: 0;}
.menu-teams img {width: 28px; height: 28px;}
.menu-teams .name {font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
.menu-teams .at {opacity: 0.6; padding: 0 2px;}
.menu-matchup {flex: 1; min-width: 0; display:flex; flex-direction: column; gap: 2px;}
.menu-matchup .teamline {display:flex; align-items:center; gap:8px; min-width: 0; flex-wrap: wrap; row-gap: 2px;}
.menu-matchup img {width: 34px; height: 34px;}
.menu-matchup .name {flex: 1 1 auto; min-width: 0; font-size: 16px; font-weight: 800; color: color-mix(in srgb, currentColor 90%, transparent); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
.menu-matchup .name-full {display: inline;}
.menu-matchup .name-short {display: none;}
.menu-matchup .record {flex: 0 0 auto; font-size: 11px; font-weight: 400; color: color-mix(in srgb, currentColor 65%, transparent); white-space: nowrap;}
.menu-matchup .record-inline {font-size: 11px; font-weight: 400; color: color-mix(in srgb, currentColor 65%, transparent); white-space: nowrap; margin-left: 6px;}
.menu-matchup .sep {font-size: 11px; font-weight: 400; color: color-mix(in srgb, currentColor 35%, transparent); white-space: nowrap;}
.menu-matchup .health {font-size: 11px; font-weight: 600; color: color-mix(in srgb, currentColor 65%, transparent); white-space: nowrap;}
.menu-matchup .health[data-tooltip] {cursor: pointer; text-decoration: underline dotted color-mix(in srgb, currentColor 35%, transparent); position: relative;}
.menu-matchup .health[data-tooltip]:hover::after {
  content: attr(data-tooltip);
  position: absolute;
  left: 0;
  top: 125%;
  z-index: 9999;
  max-width: 320px;
  white-space: normal;
  background: #262730;
  color: #fafafa;
  border: 1px solid rgba(250,250,250,0.20);
  box-shadow: 0 8px 24px rgba(0,0,0,0.25);
  padding: 8px 10px;
  border-radius: 8px;
  font-weight: 500;
  line-height: 1.25;
}
.menu-matchup .health[data-tooltip]:hover::before {
  content: "";
  position: absolute;
  left: 12px;
  top: 110%;
  border-width: 6px;
  border-style: solid;
  border-color: transparent transparent color-mix(in srgb, currentColor 20%, transparent) transparent;
}
.menu-meta {width: 240px; font-size: 13px; color: color-mix(in srgb, currentColor 75%, transparent); line-height: 1.3;}
.menu-meta div {margin: 1px 0;}

/* Matchup badges (key injuries) */
.matchup-badges {display:flex; flex-wrap: wrap; gap: 6px; margin-left: 42px; margin-top: 2px;}
.badge {display:inline-flex; align-items:center; border: 1px solid color-mix(in srgb, currentColor 20%, transparent); border-radius: 999px; padding: 3px 8px; font-size: 11px; font-weight: 750; color: color-mix(in srgb, currentColor 75%, transparent); background: color-mix(in srgb, currentColor 4%, transparent);}
.badge[data-tooltip] {cursor: pointer; text-decoration: underline dotted color-mix(in srgb, currentColor 35%, transparent); position: relative;}
.badge[data-tooltip]:hover::after {
  content: attr(data-tooltip);
  position: absolute;
  left: 0;
  top: 125%;
  z-index: 9999;
  max-width: 340px;
  white-space: pre-line;
  background: #262730;
  color: #fafafa;
  border: 1px solid rgba(250,250,250,0.20);
  box-shadow: 0 8px 24px rgba(0,0,0,0.25);
  padding: 8px 10px;
  border-radius: 8px;
  font-weight: 500;
  line-height: 1.25;
}
.badge[data-tooltip]:hover::before {
  content: "";
  position: absolute;
  left: 12px;
  top: 110%;
  border-width: 6px;
  border-style: solid;
  border-color: transparent transparent color-mix(in srgb, currentColor 20%, transparent) transparent;
}

/* Recommendations module */
.rec-wrap {margin-bottom: 10px;}
.rec-head {font-size: 22px; font-weight: 1000; color: color-mix(in srgb, currentColor 92%, transparent); letter-spacing: 0.2px; margin-bottom: 8px; margin-top: 68px;}
.rec-card {border: 1px solid color-mix(in srgb, currentColor 15%, transparent); border-left: 3px solid #e0403b; border-radius: 14px; padding: 12px 12px; background: color-mix(in srgb, currentColor 4%, transparent); box-shadow: 0 6px 18px rgba(0,0,0,0.12); margin-bottom: 10px;}
.rec-title {font-size: 20px; font-weight: 900; color: color-mix(in srgb, currentColor 90%, transparent); line-height: 1.1;}
.rec-title.now {color: #e0403b;}
.rec-title.upcoming {color: #e0403b;}
.rec-sub {margin-top: 2px; font-size: 18px; font-weight: 900; color: color-mix(in srgb, currentColor 92%, transparent); line-height: 1.1;}
.rec-row {margin-top: 8px; display:flex; align-items:center; gap:10px;}
.rec-teams {flex:1; display:flex; flex-direction: column; gap:6px; min-width: 0;}
.rec-teamline {display:flex; align-items:center; gap:8px; min-width: 0; flex-wrap: wrap; row-gap: 2px;}
.rec-teamline img {width: 34px; height: 34px;}
.rec-teamline .name {flex: 1 1 auto; min-width: 0; font-size: 16px; font-weight: 800; color: color-mix(in srgb, currentColor 90%, transparent); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
.rec-teamline .name-full {display: inline;}
.rec-teamline .name-short {display: none;}
.rec-teamline .record {flex: 0 0 auto; font-size: 11px; font-weight: 400; color: color-mix(in srgb, currentColor 65%, transparent); white-space: nowrap;}
.rec-teamline .record-inline {font-size: 11px; font-weight: 400; color: color-mix(in srgb, currentColor 65%, transparent); white-space: nowrap; margin-left: 6px;}
.rec-teamline .sep {font-size: 11px; font-weight: 400; color: color-mix(in srgb, currentColor 35%, transparent); white-space: nowrap;}
.rec-teamline .health {font-size: 11px; font-weight: 600; color: color-mix(in srgb, currentColor 65%, transparent); white-space: nowrap;}
.rec-teamline .health[data-tooltip] {cursor: pointer; text-decoration: underline dotted color-mix(in srgb, currentColor 35%, transparent); position: relative;}
.rec-teamline .health[data-tooltip]:hover::after {
  content: attr(data-tooltip);
  position: absolute;
  left: 0;
  top: 125%;
  z-index: 9999;
  max-width: 320px;
  white-space: normal;
  background: #262730;
  color: #fafafa;
  border: 1px solid rgba(250,250,250,0.20);
  box-shadow: 0 8px 24px rgba(0,0,0,0.25);
  padding: 8px 10px;
  border-radius: 8px;
  font-weight: 500;
  line-height: 1.25;
}
.rec-teamline .health[data-tooltip]:hover::before {
  content: "";
  position: absolute;
  left: 12px;
  top: 110%;
  border-width: 6px;
  border-style: solid;
  border-color: transparent transparent color-mix(in srgb, currentColor 20%, transparent) transparent;
}
.rec-meta {display:flex; flex-direction: column; align-items: flex-end; gap:6px;}
.chip {display:inline-flex; align-items:center; justify-content:center; border: 1px solid color-mix(in srgb, currentColor 20%, transparent); border-radius: 999px; padding: 6px 10px; font-size: 12px; font-weight: 700; color: color-mix(in srgb, currentColor 80%, transparent); background: color-mix(in srgb, currentColor 4%, transparent);}
.chip a {color: inherit; text-decoration: none;}
.rec-live {font-size: 12px; font-weight: 900; color: #e0403b;}
.rec-score {font-size: 12px; font-weight: 900; color: #e0403b; margin-top: -2px;}
.rec-wi {font-size: 12px; font-weight: 800; color: color-mix(in srgb, currentColor 78%, transparent);}
.rec-tip {font-weight: 850; color: color-mix(in srgb, currentColor 82%, transparent);}
.rec-menu-row {padding-top: 10px; padding-bottom: 10px;}
.rec-menu-row + .rec-menu-row {border-top: 1px solid color-mix(in srgb, currentColor 12%, transparent);}
.day-rank-row {padding: 10px 0;}
.day-rank-row + .day-rank-row {border-top: 1px solid color-mix(in srgb, currentColor 12%, transparent);}
.day-rank-day {line-height: 1.2;}
.day-rank-chip {
  display: inline-flex;
  align-items: center;
  border: 1px solid rgba(224,64,59,0.30);
  border-radius: 999px;
  padding: 5px 12px;
  font-size: 14px;
  font-weight: 850;
  color: rgba(224,64,59,0.95);
  background: rgba(224,64,59,0.08);
  text-decoration: none;
}
.rec-card a.day-rank-chip, .rec-card a.day-rank-chip:visited {color: #e0403b; text-decoration: none;}
.day-rank-chip:hover {
  background: rgba(224,64,59,0.14);
  border-color: rgba(224,64,59,0.45);
}
.day-rank-count {margin-top: 2px; font-size: 13px; font-weight: 700; color: color-mix(in srgb, currentColor 72%, transparent); line-height: 1.2;}
/* Small "info" hover icon next to the dashboard caption. */
.info-icon {display:inline-flex; align-items:center; justify-content:center; width: 22px; height: 22px; border-radius: 999px; border: 1px solid color-mix(in srgb, currentColor 25%, transparent); color: color-mix(in srgb, currentColor 80%, transparent); font-size: 13px; font-weight: 700;}
.info-icon[data-tooltip] {cursor: pointer; position: relative;}
.caption-row {display: inline-flex; align-items: center; gap: 10px;}
.caption-text {color: color-mix(in srgb, currentColor 60%, transparent); font-size: 0.9rem; line-height: 1.25;}
.caption-spacer {height: 14px;}
.info-icon[data-tooltip]:hover::after {
  content: attr(data-tooltip);
  position: absolute;
  left: 0;
  top: 130%;
  z-index: 9999;
  width: 340px;
  white-space: pre-line;
  background: #262730;
  color: #fafafa;
  border: 1px solid rgba(250,250,250,0.20);
  box-shadow: 0 8px 24px rgba(0,0,0,0.25);
  padding: 10px 12px;
  border-radius: 10px;
  font-weight: 500;
  line-height: 1.3;
}
.info-icon[data-tooltip]:hover::before {
  content: "";
  position: absolute;
  left: 10px;
  top: 115%;
  border-width: 6px;
  border-style: solid;
  border-color: transparent transparent color-mix(in srgb, currentColor 20%, transparent) transparent;
}

/* Sunday window headers in the game list */
.window-head {display:flex; align-items:baseline; gap:10px; margin: 18px 0 8px; padding-bottom: 4px; border-bottom: 2px solid #e0403b;}
.window-name {font-size: 17px; font-weight: 900; color: color-mix(in srgb, currentColor 95%, transparent);}
.window-meta {font-size: 13px; font-weight: 600; color: color-mix(in srgb, currentColor 60%, transparent);}

/* Mobile layout: prevent overlap by stacking meta below matchup. */
@media (max-width: 640px) {
  .menu-row {flex-wrap: wrap; align-items: flex-start; gap: 8px 10px;}
  .menu-awi {width: 92px;}
  .menu-matchup {min-width: 0; flex: 1 1 calc(100% - 102px);}
  .menu-meta {width: 100%; padding-left: 92px; font-size: 14px; line-height: 1.35;}
  .menu-matchup .record {font-size: 11px;}
  .matchup-badges {margin-left: 42px;}
  .menu-matchup .name-full {display: none;}
  .menu-matchup .name-short {display: inline;}
  .rec-teamline .name-full {display: none;}
  .rec-teamline .name-short {display: inline;}
  .day-rank-chip {font-size: 13px; padding: 4px 10px;}
  .day-rank-count {font-size: 12px;}
}

/* On mobile, show Recommendations above the All Games menu. */
.recs-mobile {display: none;}
.recs-desktop {display: block;}

/* Day selector chips */
[data-testid="stSegmentedControl"] > label {margin-bottom: 0.25rem;}
[data-testid="stSegmentedControl"] [role="radiogroup"] {
  gap: 0;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, currentColor 18%, transparent);
  width: fit-content;
  background: color-mix(in srgb, currentColor 4%, transparent);
}
[data-testid="stSegmentedControl"] [role="radiogroup"] label {
  min-height: 36px;
  padding: 0 18px;
  border: 0;
  border-right: 1px solid color-mix(in srgb, currentColor 18%, transparent);
  border-radius: 0;
  background: transparent;
}
[data-testid="stSegmentedControl"] [role="radiogroup"] label:last-child {
  border-right: 0;
}
[data-testid="stSegmentedControl"] [role="radiogroup"] label p {
  font-size: 12px;
  font-weight: 500;
  line-height: 1.1;
}
[data-testid="stSegmentedControl"] [role="radiogroup"] label:has(input:checked) {
  background: rgba(224, 64, 59, 0.08);
}
[data-testid="stSegmentedControl"] [role="radiogroup"] label:has(input:checked) p {
  color: rgba(224, 64, 59, 0.96);
}

@media (max-width: 640px) {
  [data-testid="stSegmentedControl"] [role="radiogroup"] label {
    min-height: 34px;
    padding: 0 14px;
  }
  [data-testid="stSegmentedControl"] [role="radiogroup"] label p {
    font-size: 11px;
  }
}

@media (max-width: 640px) {
  .recs-mobile {display: block;}
  .recs-desktop {display: none;}
}
</style>
""",
        unsafe_allow_html=True,
    )


def _parse_score(x):
    try:
        if x is None:
            return None
        return int(float(x))
    except Exception:
        return None


def _round_spread_display_value(spread) -> float | None:
    try:
        if spread is None:
            return None
        if pd.isna(spread):
            return None
        return round(float(spread) * 2.0) / 2.0
    except Exception:
        return None


def _spread_display_parts(row) -> tuple[str, str]:
    spread = _round_spread_display_value(row.get("Home spread"))
    home = str(row.get("Home team", "") or "")
    home_abbr = get_team_abbr(home) or home[:3].upper()
    label = "Spread"
    if spread is None:
        return label, "?"
    s = f"{spread:+.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    return label, f"{home_abbr} {s}"


def _to_valid_datetime(x) -> dt.datetime | None:
    """
    Normalize pandas/stdlib datetime-like values and guard against NaT.
    """
    if x is None:
        return None
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    if isinstance(x, dt.datetime):
        return x
    try:
        t = pd.to_datetime(x, errors="coerce")
        if pd.isna(t):
            return None
        return t.to_pydatetime() if hasattr(t, "to_pydatetime") else t
    except Exception:
        return None


def _kickoff_text(row) -> str:
    """e.g. 'Sun 1:00pm ET'."""
    t = _to_valid_datetime(row.get("Kickoff dt (ET)"))
    if t is None:
        return str(row.get("Kickoff (ET)") or "TBD")
    t = t.astimezone(LOCAL_TZ)
    return f"{t.strftime('%a')} {t.strftime('%I:%M%p').lstrip('0').lower()} ET"


def _espn_gamecast_url(game_id) -> str:
    gid = str(game_id or "").strip()
    if not gid:
        return ""
    if not gid.isdigit():
        return ""
    return f"https://www.espn.com/nfl/game/_/gameId/{gid}"


def _watch_chip_html(where_url: str, provider: str) -> str:
    url = str(where_url or "").strip()
    if not url:
        return ""
    provider_label = str(provider or "").strip() or "Local TV"
    return (
        f"<span class='chip'><a href='{py_html.escape(url)}' target='_blank' rel='noopener noreferrer'>"
        f"Where to watch: {py_html.escape(provider_label)}</a></span>"
    )


def _follow_chip_html(game_id) -> str:
    follow_url = _espn_gamecast_url(game_id)
    if not follow_url:
        return ""
    return (
        f"<span class='chip'><a href='{py_html.escape(follow_url)}' target='_blank' rel='noopener noreferrer'>"
        "Where to follow: ESPN</a></span>"
    )


def _chips_for_row_html(row, *, wrap_in_divs: bool) -> str:
    chips: list[str] = []
    watch_chip = _watch_chip_html(
        str(row.get("Where to watch URL") or ""),
        str(row.get("Where to watch provider") or "") or "Local TV",
    )
    follow_chip = _follow_chip_html(row.get("ESPN game id"))
    if watch_chip:
        chips.append(watch_chip)
    if follow_chip:
        chips.append(follow_chip)
    if wrap_in_divs:
        return "".join(f"<div>{c}</div>" for c in chips)
    return "\n".join(chips)


def _w2wn_live_boost(time_remaining: str | None, away_score: int | None, home_score: int | None) -> float:
    """
    W2WN live boost (NFL: "one-score game" = within 8):
      - +3 in Q3 if score diff <= 8
      - +5 in Q4/OT if score diff <= 8
    """
    q, _sec = _parse_time_remaining(time_remaining)
    if q is None:
        return 0.0
    if away_score is None or home_score is None:
        return 0.0
    try:
        diff = abs(int(away_score) - int(home_score))
    except Exception:
        return 0.0
    if diff > 8:
        return 0.0
    if q == 3:
        return 3.0
    if q >= 4:
        return 5.0
    return 0.0


def _pick_slate_df(df: pd.DataFrame, slate_day: str | None) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if slate_day and "Local date" in df.columns:
        out = df[df["Local date"].astype(str) == str(slate_day)].copy()
        if not out.empty:
            return out
    # Fallback: earliest date in the window.
    if "Local date" in df.columns:
        dates = sorted({str(x) for x in df["Local date"].dropna().tolist() if str(x).strip()})
        if dates:
            return df[df["Local date"].astype(str) == dates[0]].copy()
    return df.copy()


def render_recommendations_module(df: pd.DataFrame, *, slate_day: str | None, wrapper_class: str = "") -> None:
    """
    Recommendations:
      - What to watch now (W2WN)
      - Best upcoming game today
      - Best games / best day over the next 7 days
    """
    if df is None or df.empty:
        return

    now = dt.datetime.now(tz=LOCAL_TZ)
    d = _pick_slate_df(df, slate_day)
    if d is None or d.empty:
        return

    selected_slate_date: dt.date | None = None
    try:
        if slate_day and len(str(slate_day)) == 10:
            y, m, dd = (int(x) for x in str(slate_day).split("-"))
            selected_slate_date = dt.date(y, m, dd)
        elif "Local date" in d.columns and not d["Local date"].dropna().empty:
            v = d["Local date"].dropna().iloc[0]
            if isinstance(v, dt.date):
                selected_slate_date = v
    except Exception:
        selected_slate_date = None

    is_same_day_slate = bool(selected_slate_date) and selected_slate_date == now.date()
    is_future_slate = bool(selected_slate_date) and selected_slate_date > now.date()

    d["_is_live"] = d.get("Is live", False)
    d["_status"] = d.get("Status", "pre").astype(str) if "Status" in d.columns else "pre"

    def _minutes_to_kickoff_row(r) -> float | None:
        t = _to_valid_datetime(r.get("Kickoff dt (ET)"))
        if t is not None:
            return (t - now).total_seconds() / 60.0
        return None

    d["_minutes_to_kickoff"] = d.apply(_minutes_to_kickoff_row, axis=1)

    def _w2wn_score_row(r) -> float:
        wi = float(r.get("aWI") or 0.0)
        # Treat ESPN 'in' as live even if boolean flag is missing.
        if bool(r.get("_is_live", False)) or str(r.get("_status") or "").lower() == "in":
            away_s = _parse_score(r.get("Away score"))
            home_s = _parse_score(r.get("Home score"))
            return wi + float(_w2wn_live_boost(r.get("Time remaining"), away_s, home_s))
        if str(r.get("_status") or "").lower() == "pre":
            m = r.get("_minutes_to_kickoff")
            if m is None:
                # Unknown kickoff time: strongly de-prioritize.
                return wi - 1_000_000.0
            m = max(0.0, float(m))
            return wi - (m / 2.0)
        return wi

    d["_w2wn_score"] = d.apply(_w2wn_score_row, axis=1)

    def _subscores_row(r) -> tuple[str, str]:
        q = r.get("Team quality")
        c = r.get("Closeness")
        q_score = None if q is None else 100.0 * float(q)
        c_score = None if c is None else 100.0 * float(c)
        q_str = "—" if q_score is None else str(int(round(q_score)))
        c_str = "—" if c_score is None else str(int(round(c_score)))
        return c_str, q_str

    def _spread_str(r) -> tuple[str, str]:
        return _spread_display_parts(r)

    def _menu_like_row(row) -> str:
        awi_score = int(round(float(row.get("aWI") or 0.0)))
        label = py_html.escape(str(row.get("Region") or ""))

        c_str, q_str = _subscores_row(row)

        live_badge = ""
        is_live = bool(row.get("_is_live", False)) or str(row.get("_status") or "").lower() == "in"
        if is_live:
            away_s = _parse_score(row.get("Away score"))
            home_s = _parse_score(row.get("Home score"))
            tr = str(row.get("Time remaining") or "").strip()
            tr_line = f"<div class='live-time'>🚨 LIVE {py_html.escape(tr)}</div>" if tr else "<div class='live-time'>🚨 LIVE</div>"
            if away_s is not None and home_s is not None:
                live_badge = f"{tr_line}<div class='live-badge'>{int(away_s)} - {int(home_s)}</div>"
            else:
                live_badge = tr_line

        away_full = str(row.get("Away team") or "")
        home_full = str(row.get("Home team") or "")
        away_mascot = get_team_mascot(away_full) or away_full
        home_mascot = get_team_mascot(home_full) or home_full
        away = py_html.escape(away_full)
        home = py_html.escape(home_full)
        away_short = py_html.escape(str(away_mascot))
        home_short = py_html.escape(str(home_mascot))

        tip_line = py_html.escape(f"Kickoff {_kickoff_text(row)}")

        spread_label, spread_value = _spread_str(row)
        spread_str = py_html.escape(spread_value)
        spread_label = py_html.escape(spread_label)

        where_html = _chips_for_row_html(row, wrap_in_divs=True)

        record_away = py_html.escape(str(row.get("Record (away)", "—")))
        record_home = py_html.escape(str(row.get("Record (home)", "—")))

        away_inj = str(row.get("Away Key Injuries", "") or "").strip()
        home_inj = str(row.get("Home Key Injuries", "") or "").strip()

        inj_lines: list[str] = []
        if away_inj:
            inj_lines.append(f"{away_mascot}: {away_inj}")
        if home_inj:
            inj_lines.append(f"{home_mascot}: {home_inj}")
        inj_tooltip = py_html.escape("\n".join(inj_lines)) if inj_lines else ""

        badges_html = ""
        if inj_tooltip:
            badges_html = f"<div class='matchup-badges'><span class='badge' data-tooltip=\"{inj_tooltip}\">❗ Key Injuries</span></div>"

        away_logo = py_html.escape(str(row.get("Away logo") or ""))
        home_logo = py_html.escape(str(row.get("Home logo") or ""))
        away_img = f"<img src='{away_logo}'/>" if away_logo else ""
        home_img = f"<img src='{home_logo}'/>" if home_logo else ""

        return (
            f"<div class='menu-row rec-menu-row'>"
            f"<div class='menu-awi'>"
            f"<div class='label'>{label}</div>"
            f"<div class='score'>Watchability {awi_score}</div>"
            f"<div class='subscores'>"
            f"<span class='subscore'>Competitiveness {py_html.escape(c_str)}</span>"
            f"<span class='subscore'>Team Quality {py_html.escape(q_str)}</span>"
            f"</div>"
            f"{live_badge}"
            f"</div>"
            f"<div class='menu-matchup'>"
            f"<div class='teamline'>"
            f"{away_img}"
            f"<div class='name'><span class='name-full'>{away}</span><span class='name-short'>{away_short}</span><span class='record-inline'>{record_away}</span></div>"
            f"</div>"
            f"<div class='teamline'>"
            f"{home_img}"
            f"<div class='name'><span class='name-full'>{home}</span><span class='name-short'>{home_short}</span><span class='record-inline'>{record_home}</span></div>"
            f"</div>"
            f"{badges_html}"
            f"</div>"
            f"<div class='menu-meta'>"
            f"<div class='rec-tip'>{tip_line}</div>"
            f"<div>{spread_label}: {spread_str}</div>"
            f"{where_html}"
            f"</div>"
            f"</div>"
        )

    def _rec_card_multi(*, title: str, title_class: str, subtitle: str, rows: list) -> str:
        # rows: list of dataframe rows (Series-like)
        inner_rows = "\n".join([_menu_like_row(r) for r in rows])
        return textwrap.dedent(
            f"""
            <div class="rec-card">
              <div class="rec-title {py_html.escape(title_class)}">{py_html.escape(title)}</div>
              <div class="rec-sub">{py_html.escape(subtitle)}</div>
              {inner_rows}
            </div>
            """
        ).strip()

    def _day_rank_card(*, title: str, subtitle: str, day_rows: list[dict[str, str]]) -> str:
        inner_rows = []
        for row in day_rows:
            day_text = py_html.escape(str(row.get("day") or ""))
            href = str(row.get("href") or "").strip()
            if href:
                day_html = f"<a class='day-rank-chip' href='{py_html.escape(href)}'>{day_text}</a>"
            else:
                day_html = f"<span class='day-rank-chip'>{day_text}</span>"
            inner_rows.append(
                textwrap.dedent(
                    f"""
                    <div class="day-rank-row">
                      <div class="day-rank-day">{day_html}</div>
                      <div class="day-rank-count">{py_html.escape(str(row.get("count") or ""))}</div>
                    </div>
                    """
                ).strip()
            )
        return textwrap.dedent(
            f"""
            <div class="rec-card">
              <div class="rec-title upcoming">{py_html.escape(title)}</div>
              <div class="rec-sub">{py_html.escape(subtitle)}</div>
              {' '.join(inner_rows)}
            </div>
            """
        ).strip()

    cards: list[str] = []

    # 1) What to watch now
    show_w2wn = False
    try:
        if is_same_day_slate:
            # Only show when there is a live game.
            any_live = bool(
                (d.get("_is_live", False) == True).any()  # noqa: E712
                or (d.get("_status", "").astype(str).str.lower() == "in").any()
            )
            show_w2wn = any_live
    except Exception:
        show_w2wn = False

    if show_w2wn:
        live_df = d[
            (d.get("_is_live", False) == True)  # noqa: E712
            | (d.get("_status", "").astype(str).str.lower() == "in")
        ].copy()
        if not live_df.empty:
            live_sorted = live_df.sort_values(["_w2wn_score", "aWI"], ascending=False).reset_index(drop=True)
            rows = [live_sorted.iloc[0]]
            if len(live_sorted) > 1:
                r2 = live_sorted.iloc[1]
                if float(r2.get("aWI") or 0.0) > 50.0:
                    rows.append(r2)
            cards.append(_rec_card_multi(title="What to watch now", title_class="now", subtitle="Watch LIVE:", rows=rows))

    # 2) Best upcoming game today
    if is_future_slate:
        upcoming = d[
            (d["_status"].astype(str).str.lower() == "pre")
            & (d.get("_is_live", False) == False)  # noqa: E712
        ].copy()
    else:
        upcoming = d[
            (d["_status"].astype(str).str.lower() == "pre")
            & (d.get("_is_live", False) == False)  # noqa: E712
            & (d["_minutes_to_kickoff"].notna())
            & (d["_minutes_to_kickoff"].astype(float) > 0)
        ].copy()
    if not upcoming.empty:
        upcoming_sorted = upcoming.sort_values(["aWI", "_minutes_to_kickoff"], ascending=[False, True]).reset_index(drop=True)
        rows = [upcoming_sorted.iloc[0]]
        if len(upcoming_sorted) > 1:
            r2 = upcoming_sorted.iloc[1]
            if float(r2.get("aWI") or 0.0) > 50.0:
                rows.append(r2)
        if len(upcoming_sorted) > 2:
            r3 = upcoming_sorted.iloc[2]
            if float(r3.get("aWI") or 0.0) > 50.0:
                rows.append(r3)
        upcoming_title = (
            f"Best of {selected_slate_date.strftime('%A')}"
            if is_future_slate and selected_slate_date
            else "Best upcoming today"
        )
        cards.append(_rec_card_multi(title=upcoming_title, title_class="upcoming", subtitle="", rows=rows))

    # 2b) Best games upcoming next 7 days (always use full df, not just selected slate).
    full_upcoming = df.copy()
    if full_upcoming is not None and not full_upcoming.empty:
        if "Status" in full_upcoming.columns:
            status_series = full_upcoming["Status"].astype(str).str.lower()
        else:
            status_series = pd.Series(["pre"] * len(full_upcoming), index=full_upcoming.index)
        full_upcoming = full_upcoming[status_series == "pre"].copy()
        if "Kickoff dt (ET)" in full_upcoming.columns:
            full_upcoming = full_upcoming.sort_values(["aWI", "Kickoff dt (ET)"], ascending=[False, True])
        else:
            full_upcoming = full_upcoming.sort_values("aWI", ascending=False)
        if not full_upcoming.empty:
            top_rows = [full_upcoming.iloc[i] for i in range(min(3, len(full_upcoming)))]
            cards.append(
                _rec_card_multi(
                    title="Best games upcoming next 7 days",
                    title_class="upcoming",
                    subtitle="",
                    rows=top_rows,
                )
            )

    # 2c) Best day of games upcoming next 7 days (rank all available days).
    if df is not None and not df.empty and "Local date" in df.columns:
        day_df = df.copy()
        if "Status" in day_df.columns:
            day_df = day_df[day_df["Status"].astype(str).str.lower() == "pre"].copy()
        day_rank_rows: list[dict[str, str]] = []
        if not day_df.empty:
            # If the first game of the current day has already started, exclude that day
            # entirely from the "best upcoming days" ranking to avoid mixing "today" with
            # still-upcoming future slates.
            try:
                if "Kickoff dt (ET)" in df.columns:
                    today_rows = df[df["Local date"] == now.date()].copy()
                    today_kickoffs = today_rows["Kickoff dt (ET)"].apply(_to_valid_datetime).dropna()
                    if not today_kickoffs.empty:
                        earliest_today_kickoff = min(today_kickoffs.tolist())
                        if earliest_today_kickoff <= now:
                            day_df = day_df[day_df["Local date"] != now.date()].copy()
            except Exception:
                pass

            grouped = (
                day_df.dropna(subset=["Local date"])
                .groupby("Local date", dropna=True)
                .apply(
                    lambda g: pd.Series(
                        {
                            "strong_count": int(g["Region"].isin(["Must Watch", "Strong Watch"]).sum()),
                            "game_count": int(len(g)),
                            "avg_awi": (
                                float(pd.to_numeric(g["aWI"], errors="coerce").mean())
                                if "aWI" in g.columns
                                else 0.0
                            ),
                        }
                    )
                )
                .reset_index()
            )
            if not grouped.empty:
                grouped = grouped.sort_values(
                    ["strong_count", "game_count", "Local date"],
                    ascending=[False, False, True],
                )
                for _, gr in grouped.head(3).iterrows():
                    d_local = gr.get("Local date")
                    if isinstance(d_local, dt.date):
                        day_label = f"{d_local.strftime('%a')} {d_local.month}/{d_local.day}"
                    else:
                        day_label = str(d_local)
                    strong_count = int(gr.get("strong_count") or 0)
                    game_count = int(gr.get("game_count") or 0)
                    avg_awi_raw = gr.get("avg_awi")
                    avg_awi = 0 if pd.isna(avg_awi_raw) else int(round(float(avg_awi_raw)))
                    noun = "game" if strong_count == 1 else "games"
                    day_rank_rows.append(
                        {
                            "label": "",
                            "day": day_label,
                            "href": f"?day={d_local.isoformat()}#top" if isinstance(d_local, dt.date) else "",
                            "count": f"{strong_count} Strong+ {noun}, Avg watchability {avg_awi}, {game_count} total games",
                        }
                    )
        if day_rank_rows:
            cards.append(
                _day_rank_card(
                    title="Best day of games upcoming next 7 days",
                    subtitle="",
                    day_rows=day_rank_rows,
                )
            )

    if not cards:
        cards.append(
            textwrap.dedent(
                """
                <div class="rec-card">
                  <div class="rec-sub" style="font-size:16px; font-weight:700; color: rgba(49,51,63,0.72);">
                    No live or upcoming recommendation for this slate yet.
                  </div>
                </div>
                """
            ).strip()
        )

    header_html = "<div class='rec-wrap'><div class='rec-head'>What to Watch Recommendations</div></div>"
    inner = "\n".join([header_html] + cards)
    if wrapper_class:
        inner = f"<div class='{py_html.escape(wrapper_class)}'>{inner}</div>"
    st.markdown(inner, unsafe_allow_html=True)


def _fmt_m_d(d: dt.date) -> str:
    return f"{d.month}/{d.day}"


def build_dashboard_frames() -> tuple[pd.DataFrame, pd.DataFrame, list[str], dict[str, str]]:
    df = load_watchability_df(days_ahead=7)
    if df.empty:
        return df, pd.DataFrame(columns=["Local date", "Day"]), [], {}

    df_dates = (
        df.dropna(subset=["Local date"])
        .sort_values("Local date")
        .loc[:, ["Local date", "Day"]]
        .drop_duplicates()
    )
    date_options = [d.isoformat() for d in df_dates["Local date"].tolist()]
    date_to_label = {
        d.isoformat(): f"{d.strftime('%a')} {_fmt_m_d(d)}"
        for d, _day in df_dates.itertuples(index=False, name=None)
    }

    return df, df_dates, date_options, date_to_label


def render_chart(
    df: pd.DataFrame,
    date_options: list[str],
    date_to_label: dict[str, str],
    default_day: str | None = None,
) -> str | None:
    def _fmt_m_d_yy_from_iso(iso: str | None) -> str | None:
        if not iso:
            return None
        try:
            y, m, d = (int(x) for x in iso.split("-"))
            return f"{m}/{d}/{str(y)[2:]}"
        except Exception:
            return None

    QUALITY_FLOOR = getattr(watch, "QUALITY_FLOOR", 0.1)
    CLOSENESS_FLOOR = getattr(watch, "CLOSENESS_FLOOR", 0.1)

    df_plot = df.copy()
    selected: str | None = None
    if date_options:
        default_value = default_day if (default_day in date_options) else date_options[0]
        # Clicking the active day deselects it; fall back to the default instead of an empty slate.
        selected = st.segmented_control(
            "Day",
            options=date_options,
            format_func=lambda x: date_to_label.get(x, x),
            default=default_value,
        ) or default_value
        df_plot = df[df["Local date"].astype(str) == selected].copy()
    df_plot["Away Key Injuries"] = df_plot["Away Key Injuries"].fillna("")
    df_plot["Home Key Injuries"] = df_plot["Home Key Injuries"].fillna("")

    chart_date_str = _fmt_m_d_yy_from_iso(selected)

    # Responsive sizing: keep mobile optimized, slightly larger on desktop web.
    # Vega-Lite exposes a `width` signal we can use to scale mark sizes.
    logo_size = alt.ExprRef(expr="clamp(width*0.06, 40, 50)")  # 40px on mobile, up to ~+24% on desktop
    tip_font_size = alt.ExprRef(expr="clamp(width*0.018, 11, 14)")
    region_label_font_size = alt.ExprRef(expr="clamp(width*0.040, 24, 30)")
    legend_font_size = alt.ExprRef(expr="clamp(width*0.020, 13, 16)")
    circle_size = alt.ExprRef(expr="clamp(width*1.2, 800, 992)")
    hit_target_size = alt.ExprRef(expr="clamp(width*6.3, 4200, 5208)")
    tips_dy = alt.ExprRef(expr="clamp(width*0.050, 32, 40)")
    axis_label_font_size = alt.ExprRef(expr="clamp(width*0.030, 20, 25)")
    axis_sublabel_font_size = alt.ExprRef(expr="clamp(width*0.020, 13, 16)")
    axis_label_dx = alt.ExprRef(expr="clamp(width*-0.110, -74, -90)")
    x_axis_title_dy = alt.ExprRef(expr="clamp(width*0.110, 72, 90)")
    x_axis_subtitle_dy = alt.ExprRef(expr="clamp(width*0.140, 92, 115)")
    chart_title_font_size = alt.ExprRef(expr="clamp(width*0.033, 21, 26)")

    region_order = REGION_ORDER
    region_colors = REGION_COLORS

    step = 0.02
    q_vals = [QUALITY_FLOOR + i * step for i in range(int((1.0 - QUALITY_FLOOR) / step) + 1)]
    c_vals = [CLOSENESS_FLOOR + i * step for i in range(int((1.0 - CLOSENESS_FLOOR) / step) + 1)]
    cells = []
    for q in q_vals[:-1]:
        for c in c_vals[:-1]:
            q_mid = q + step / 2
            c_mid = c + step / 2
            a = watch.awi(q_mid, c_mid)
            cells.append(
                {
                    "q": q,
                    "q2": min(1.0, q + step),
                    "c": c,
                    "c2": min(1.0, c + step),
                    "Region": watch.awi_label(a),
                }
            )
    regions_df = pd.DataFrame(cells)

    regions = (
        alt.Chart(regions_df)
        .mark_rect(opacity=0.45)
        .encode(
            x=alt.X("q:Q", scale=alt.Scale(domain=[QUALITY_FLOOR, 1.0]), axis=None),
            x2="q2:Q",
            y=alt.Y("c:Q", scale=alt.Scale(domain=[CLOSENESS_FLOOR, 1.0]), axis=None),
            y2="c2:Q",
            color=alt.Color(
                "Region:N",
                sort=region_order,
                scale=alt.Scale(domain=region_order, range=[region_colors[r] for r in region_order]),
                legend=None,
            ),
            tooltip=[],
        )
    )

    axes = alt.Chart(df_plot).mark_point(opacity=0).encode(
        x=alt.X(
            "Team Quality:Q",
            scale=alt.Scale(domain=[QUALITY_FLOOR, 1.0]),
            axis=alt.Axis(
                title="Team Quality",
                format=".2f",
                titleFontSize=18,
                titleFontWeight="bold",
                titlePadding=28,
                labelFontSize=12,
            ),
        ),
        y=alt.Y(
            "Competitiveness:Q",
            scale=alt.Scale(domain=[CLOSENESS_FLOOR, 1.0]),
            axis=alt.Axis(
                title="Competitiveness",
                format=".2f",
                titleFontSize=18,
                titleFontWeight="bold",
                titlePadding=34,
                labelFontSize=12,
            ),
        ),
        tooltip=[],
    )

    region_labels_df = pd.DataFrame(
        [
            {"label": "Must Watch", "x": 0.93, "y": 0.93},
            {"label": "Strong", "x": 0.83, "y": 0.82},
            {"label": "Watchable", "x": 0.64, "y": 0.60},
            {"label": "Skippable", "x": 0.40, "y": 0.40},
            {"label": "Hard Skip", "x": 0.20, "y": 0.20},
        ]
    )
    region_text = alt.Chart(region_labels_df).mark_text(
        fontSize=region_label_font_size,
        fontWeight=700,
        opacity=0.2,
        color=CHART_INK,
    ).encode(
        x=alt.X("x:Q", scale=alt.Scale(domain=[QUALITY_FLOOR, 1.0]), axis=None),
        y=alt.Y("y:Q", scale=alt.Scale(domain=[CLOSENESS_FLOOR, 1.0]), axis=None),
        text=alt.Text("label:N"),
        tooltip=[],
    )

    # X-axis overlay label: render as two separate text marks (more reliable than newline rendering).
    x_axis_label_df_top = pd.DataFrame(
        [{"text": "Quality of Teams", "x": 0.55, "y": CLOSENESS_FLOOR + 0.035}]
    )
    x_axis_label_top = alt.Chart(x_axis_label_df_top).mark_text(
        dy=x_axis_title_dy,
        fontSize=axis_label_font_size,
        fontWeight=800,
        opacity=0.95,
        color=CHART_INK,
    ).encode(
        x=alt.X("x:Q", scale=alt.Scale(domain=[QUALITY_FLOOR, 1.0]), axis=None),
        y=alt.Y("y:Q", scale=alt.Scale(domain=[CLOSENESS_FLOOR, 1.0]), axis=None),
        text=alt.Text("text:N"),
        tooltip=[],
    )

    x_axis_label_df_bottom = pd.DataFrame(
        [{"text": "(Avg Injury-Adjusted Winning Percentages)", "x": 0.55, "y": CLOSENESS_FLOOR + 0.035}]
    )
    x_axis_label_bottom = alt.Chart(x_axis_label_df_bottom).mark_text(
        dy=x_axis_subtitle_dy,
        fontSize=axis_sublabel_font_size,
        fontWeight=500,
        opacity=0.95,
        color=CHART_INK,
    ).encode(
        x=alt.X("x:Q", scale=alt.Scale(domain=[QUALITY_FLOOR, 1.0]), axis=None),
        y=alt.Y("y:Q", scale=alt.Scale(domain=[CLOSENESS_FLOOR, 1.0]), axis=None),
        text=alt.Text("text:N"),
        tooltip=[],
    )

    x_axis_label_text = x_axis_label_top + x_axis_label_bottom

    y_axis_label_df_top = pd.DataFrame(
        [{"text": "Competitiveness", "x": QUALITY_FLOOR - 0.07, "y": 0.605}]
    )

    y_axis_label_text_top = alt.Chart(y_axis_label_df_top).mark_text(
        dx=axis_label_dx,
        fontSize=axis_label_font_size,
        fontWeight=800,
        opacity=0.95,
        color=CHART_INK,
        angle=270,
    ).encode(
        x=alt.X("x:Q", scale=alt.Scale(domain=[QUALITY_FLOOR, 1.0]), axis=None),
        y=alt.Y("y:Q", scale=alt.Scale(domain=[CLOSENESS_FLOOR, 1.0]), axis=None),
        text=alt.Text("text:N"),
        tooltip=[],
    )

    y_axis_label_df_bottom = pd.DataFrame(
        [{"text": "(Absolute Spread)", "x": QUALITY_FLOOR - 0.07, "y": 0.93}]
    )

    y_axis_label_text_bottom = alt.Chart(y_axis_label_df_bottom).mark_text(
        dx=axis_label_dx,
        fontSize=axis_sublabel_font_size,
        fontWeight=500,
        opacity=0.95,
        color=CHART_INK,
        angle=270,
    ).encode(
        x=alt.X("x:Q", scale=alt.Scale(domain=[QUALITY_FLOOR, 1.0]), axis=None),
        y=alt.Y("y:Q", scale=alt.Scale(domain=[CLOSENESS_FLOOR, 1.0]), axis=None),
        text=alt.Text("text:N"),
        tooltip=[],
    )

    y_axis_label_text = y_axis_label_text_top + y_axis_label_text_bottom

    df_plot = df_plot.copy()
    def _spread_display_text_row(r) -> str:
        lbl, val = _spread_display_parts(r)
        return f"{lbl}: {val}"

    df_plot["Spread display"] = df_plot.apply(_spread_display_text_row, axis=1)

    game_tooltip = [
        alt.Tooltip("Matchup:N"),
        alt.Tooltip("aWI:Q", title="Watchability", format=".1f"),
        alt.Tooltip("Region:N"),
        alt.Tooltip("Kickoff (ET):N", title="Kickoff"),
        alt.Tooltip("Window:N"),
        alt.Tooltip("Spread display:N", title="Spread"),
        alt.Tooltip("Health (away):Q", title="Away health", format=".2f"),
        alt.Tooltip("Health (home):Q", title="Home health", format=".2f"),
        alt.Tooltip("Away Key Injuries:N"),
        alt.Tooltip("Home Key Injuries:N"),
        alt.Tooltip("Record (away):N"),
        alt.Tooltip("Record (home):N"),
    ]

    circles = alt.Chart(df_plot).mark_circle(size=circle_size, opacity=0.10).encode(
        x=alt.X("Team Quality:Q", scale=alt.Scale(domain=[QUALITY_FLOOR, 1.0]), axis=None),
        y=alt.Y("Competitiveness:Q", scale=alt.Scale(domain=[CLOSENESS_FLOOR, 1.0]), axis=None),
        color=alt.Color(
            "Region:N",
            sort=region_order,
            scale=alt.Scale(domain=region_order, range=[region_colors[r] for r in region_order]),
            legend=alt.Legend(title=None),
        ),
        tooltip=game_tooltip,
    )

    hit_targets = alt.Chart(df_plot).mark_circle(size=hit_target_size, opacity=0.001).encode(
        x=alt.X("Team Quality:Q", scale=alt.Scale(domain=[QUALITY_FLOOR, 1.0]), axis=None),
        y=alt.Y("Competitiveness:Q", scale=alt.Scale(domain=[CLOSENESS_FLOOR, 1.0]), axis=None),
        tooltip=game_tooltip,
    )

    dx = 0.03
    away_points = df_plot.assign(_x=(df_plot["Team quality"] - dx).clip(0, 1), _logo=df_plot["Away logo"])
    home_points = df_plot.assign(_x=(df_plot["Team quality"] + dx).clip(0, 1), _logo=df_plot["Home logo"])
    tooltip_cols = [
        "Matchup",
        "Kickoff short",
        "Kickoff (ET)",
        "Window",
        "Spread display",
        "Home spread",
        "Record (away)",
        "Record (home)",
        "aWI",
        "Region",
        "Team quality",
        "Closeness",
        "Importance",
        "Health (away)",
        "Health (home)",
        "Away Key Injuries",
        "Home Key Injuries",
        "Importance (away)",
        "Importance (home)",
        "Seed radius (away)",
        "Seed radius (home)",
        "Playoff radius (away)",
        "Playoff radius (home)",
        "_x",
        "_logo",
    ]
    tooltip_cols = list(dict.fromkeys([c for c in tooltip_cols if c in df_plot.columns] + ["_x", "_logo"]))

    images_df = pd.concat(
        [
            away_points[tooltip_cols].assign(_side="away"),
            home_points[tooltip_cols].assign(_side="home"),
        ],
        ignore_index=True,
    )
    images_df = images_df[images_df["_logo"].astype(bool)]

    images = alt.Chart(images_df).mark_image(width=logo_size, height=logo_size).encode(
        x=alt.X("_x:Q", axis=None),
        y=alt.Y("Closeness:Q", axis=None),
        url=alt.Url("_logo:N"),
        tooltip=game_tooltip,
    )

    tips = alt.Chart(df_plot).mark_text(
        dy=tips_dy,
        fontSize=tip_font_size,
        color=CHART_INK,
    ).encode(
        x=alt.X("Team quality:Q", axis=None),
        y=alt.Y("Closeness:Q", axis=None),
        text=alt.Text("Kickoff display:N"),
        tooltip=game_tooltip,
    )

    chart_legend_df = pd.DataFrame(
        [
            {"text": "↗ More watchable", "x": QUALITY_FLOOR + 0.01, "y": CLOSENESS_FLOOR + 0.04},
            #{"text": "↙ Less watchable", "x": QUALITY_FLOOR + 0.01, "y": CLOSENESS_FLOOR + 0.03},
        ]
    )
    chart_legend = alt.Chart(chart_legend_df).mark_text(
        align="left",
        baseline="top",
        fontSize=legend_font_size,
        fontWeight=700,
        color=CHART_INK,
        opacity=0.95,
    ).encode(
        x=alt.X("x:Q", scale=alt.Scale(domain=[QUALITY_FLOOR, 1.0]), axis=None),
        y=alt.Y("y:Q", scale=alt.Scale(domain=[CLOSENESS_FLOOR, 1.0]), axis=None),
        text=alt.Text("text:N"),
        tooltip=[],
    )

    chart = (
        axes
        + regions
        + region_text
        + x_axis_label_text
        + y_axis_label_text
        + circles
        + hit_targets
        + images
        + tips
        + chart_legend
    ).resolve_scale(x="shared", y="shared").properties(
        height=560,
        title=alt.TitleParams(
            text=["Watchability Landscape" + " " + chart_date_str] if chart_date_str else ["Watchability Landscape Today"],
            anchor="middle",
            fontSize=chart_title_font_size,
            fontWeight=800,
            color=CHART_INK,
            dy=4,
        ),
    )
    st.altair_chart(chart, width="stretch")
    return selected


def _render_menu_row(r) -> str:
    awi_score = int(round(float(r["aWI"])))
    label = py_html.escape(str(r["Region"]))

    q = r.get("Team quality")
    c = r.get("Closeness")
    q_score = None if q is None else 100.0 * float(q)
    c_score = None if c is None else 100.0 * float(c)
    q_str = "—" if q_score is None else str(int(round(q_score)))
    c_str = "—" if c_score is None else str(int(round(c_score)))

    live_badge = ""
    if bool(r.get("Is live", False)):
        away_s = r.get("Away score")
        home_s = r.get("Home score")
        tr = r.get("Time remaining")
        tr_line = (
            f"<div class='live-time'>🚨 LIVE {py_html.escape(str(tr))}</div>"
            if tr
            else "<div class='live-time'>🚨 LIVE</div>"
        )
        if away_s is not None and home_s is not None:
            live_badge = f"{tr_line}<div class='live-badge'>{int(away_s)} - {int(home_s)}</div>"
        else:
            live_badge = f"{tr_line}"

    away_full = str(r["Away team"])
    home_full = str(r["Home team"])
    away_mascot = get_team_mascot(away_full) or away_full
    home_mascot = get_team_mascot(home_full) or home_full
    away = py_html.escape(away_full)
    home = py_html.escape(home_full)
    away_short = py_html.escape(str(away_mascot))
    home_short = py_html.escape(str(home_mascot))
    tip_line = py_html.escape(f"Kickoff {_kickoff_text(r)}")
    where_html = _chips_for_row_html(r, wrap_in_divs=True)
    spread_label, spread_value = _spread_display_parts(r)
    spread_str = py_html.escape(spread_value)
    spread_label = py_html.escape(spread_label)
    record_away = py_html.escape(str(r.get("Record (away)", "—")))
    record_home = py_html.escape(str(r.get("Record (home)", "—")))

    away_inj = str(r.get("Away Key Injuries", "") or "").strip()
    home_inj = str(r.get("Home Key Injuries", "") or "").strip()

    inj_lines: list[str] = []
    if away_inj:
        inj_lines.append(f"{away_mascot}: {away_inj}")
    if home_inj:
        inj_lines.append(f"{home_mascot}: {home_inj}")
    inj_tooltip = py_html.escape("\n".join(inj_lines)) if inj_lines else ""

    badges_html = ""
    if inj_tooltip:
        badges_html = f"<div class='matchup-badges'><span class='badge' data-tooltip=\"{inj_tooltip}\">❗ Key Injuries</span></div>"
    away_logo = py_html.escape(str(r["Away logo"]))
    home_logo = py_html.escape(str(r["Home logo"]))
    away_img = f"<img src='{away_logo}'/>" if away_logo else ""
    home_img = f"<img src='{home_logo}'/>" if home_logo else ""

    # Avoid leading indentation/newlines: Streamlit Markdown can render it as a code block.
    return f"""<div class="rec-card menu-row">
<div class="menu-awi">
<div class="label">{label}</div>
<div class="score">Watchability {awi_score}</div>
<div class="subscores">
<span class="subscore">Competitiveness {c_str}</span>
<span class="subscore">Team Quality {q_str}</span>
</div>
{live_badge}
</div>
<div class="menu-matchup">
<div class="teamline">
{away_img}
<div class="name"><span class="name-full">{away}</span><span class="name-short">{away_short}</span><span class="record-inline">{record_away}</span></div>
</div>
<div class="teamline">
{home_img}
<div class="name"><span class="name-full">{home}</span><span class="name-short">{home_short}</span><span class="record-inline">{record_home}</span></div>
</div>
{badges_html}
</div>
<div class="menu-meta">
<div>{tip_line}</div>
<div>{spread_label}: {spread_str}</div>
{where_html}
</div>
</div>"""


def _sort_games(day_df: pd.DataFrame, sort_mode: str) -> pd.DataFrame:
    if sort_mode == "Kickoff time":
        return day_df.sort_values(["Kickoff dt (ET)", "aWI"], ascending=[True, False], na_position="last")
    return day_df.sort_values("aWI", ascending=False)


def _window_header_html(window: str, games: pd.DataFrame) -> str:
    """e.g. 'Sunday Late   4:05 / 4:25pm ET · 5 games'."""
    clocks: list[str] = []
    for t in games["Kickoff dt (ET)"].dropna().sort_values():
        c = t.astimezone(LOCAL_TZ).strftime("%I:%M%p").lstrip("0").lower()
        if c not in clocks:
            clocks.append(c)
    n = len(games)
    meta = f"{' / '.join(clocks)} ET · {n} game{'s' if n != 1 else ''}" if clocks else f"{n} games"
    return (
        f"<div class='window-head'><span class='window-name'>{py_html.escape(window)}</span>"
        f"<span class='window-meta'>{py_html.escape(meta)}</span></div>"
    )


def render_table(df: pd.DataFrame, *, selected_day: str) -> None:
    day_df = df[df["Local date"].astype(str) == str(selected_day)].copy()
    if day_df.empty:
        return
    multi_window = day_df["Window"].nunique() > 1
    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    with c1:
        sort_mode = st.segmented_control("Sort ↓", options=["Watchability", "Kickoff time"], default="Watchability")
        sort_mode = sort_mode or "Watchability"
    with c2:
        group = st.toggle("Group by window", value=True, disabled=not multi_window)

    if not (multi_window and group):
        for _, row in _sort_games(day_df, sort_mode).iterrows():
            st.markdown(_render_menu_row(row), unsafe_allow_html=True)
        return

    # Windows in kickoff order (Morning -> Early -> Late -> Night).
    first_kickoff = day_df.groupby("Window")["Kickoff dt (ET)"].min().sort_values()
    for window in first_kickoff.index:
        games = day_df[day_df["Window"] == window]
        st.markdown(_window_header_html(window, games), unsafe_allow_html=True)
        for _, row in _sort_games(games, sort_mode).iterrows():
            st.markdown(_render_menu_row(row), unsafe_allow_html=True)


def render_full_dashboard(title: str, caption: str) -> None:
    inject_base_css()

    st.markdown("<div id='top'></div>", unsafe_allow_html=True)
    st.title(title)
    info_text = (
        "How it works\n"
        "• Input 1 - Competitiveness: based on the spread (smaller spread = more competitive game).\n"
        "• Input 2 - Team quality: average of team winning percentages adjusted for injured starters (QB matters most).\n"
        "• Output: a single Watchability score + simple labels (Must Watch → Hard Skip).\n"
        "• Updates live: watchability changes as the score changes (page refreshes every 10 minutes).\n"
        "• Times are Eastern. Sunday games are grouped by window: morning, early, late and night."
    )
    info_attr = py_html.escape(info_text).replace("\n", "&#10;")
    cap_text = py_html.escape(caption)
    st.markdown(
        f"<div class='caption-row'><span class='caption-text'>{cap_text}</span>"
        f"<span class='info-icon' data-tooltip=\"{info_attr}\">i</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='caption-spacer'></div>", unsafe_allow_html=True)
    _render_dashboard_body()


@st.fragment(run_every=600)  # re-render every 10 minutes; data cache TTL (5 min) keeps it fresh
def _render_dashboard_body() -> None:
    df, _df_dates, date_options, date_to_label = build_dashboard_frames()
    if df.empty:
        st.warning("No NFL games found in the next week. Enjoy the break!")
        return

    default_day = st.query_params.get("day")

    left, right = st.columns([1.05, 1.0], gap="large")
    with left:
        selected = render_chart(
            df=df,
            date_options=date_options,
            date_to_label=date_to_label,
            default_day=default_day,
        )
        render_recommendations_module(df, slate_day=selected, wrapper_class="recs-mobile")
        st.markdown("<div style='font-size:22px; font-weight:950; margin-top:10px;'>All Games</div>", unsafe_allow_html=True)
        render_table(df=df, selected_day=selected)
    with right:
        render_recommendations_module(df, slate_day=selected, wrapper_class="recs-desktop")
