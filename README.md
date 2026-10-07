# NFL Watchability

An NFL fork of [NBA Watchability](https://github.com/cameronntaylor/nba-watchability) ([live NBA app](https://nba-watchability.streamlit.app/)). It uses the same model and dashboard, rewired for football.

## Run it

```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

You don't need an API key. Games, DraftKings spreads, standings, injuries and depth charts all come from ESPN's public endpoints. If you set `ODDS_API_KEY`, spreads come from [The Odds API](https://the-odds-api.com) instead (median across books, sport `americanfootball_nfl`).

## What changed from the NBA version

| Piece | NBA | NFL |
|---|---|---|
| Games + spreads | The Odds API (key required) | ESPN scoreboard + DraftKings line, with The Odds API optional |
| Team quality | Win % × injury health + star bump | Win % × injury health (no star bump) |
| Player impact | PTS+REB+AST share of team | Depth-chart starters weighted by position (a QB is ~37% of a team) |
| Injury statuses | Out / GTD with text parsing | Official Out / Doubtful / Questionable / IR report |
| Importance | Seed + play-in radius over 10 games | Seed + playoff-bubble radius (7th/8th seed) over 3 games |
| Blowout spread | 15 pts | 14 pts |
| Live games | Live Odds API line | Live line if available, otherwise implied from score + time left |
| Clock | 12-min quarters | 15-min quarters |
| Forecast / X bot | 7-day model forecast, tweet bot | Removed (ESPN already lists the full week with lines) |
| Times | Pacific | Eastern; Sunday games grouped by window (morning / early / late / night) |
| Theme | Light | Light + dark with red accents; follows the system setting, switchable in ⋮ → Settings (`.streamlit/config.toml`) |

The CES formula in `core/watchability.py` (70% quality, 30% closeness) is unchanged.

## Deploy

1. Push this repo to GitHub.
2. Create an app at share.streamlit.io.
3. Set the main file to `app/streamlit_app.py`.
