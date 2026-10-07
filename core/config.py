import os

# Optional. When set, spreads come from The Odds API (median across books).
# Without it, the app uses the DraftKings line that ESPN's scoreboard carries.
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
ODDS_BASE_URL = "https://api.the-odds-api.com/v4"
SPORT_KEY_NFL = "americanfootball_nfl"
DEFAULT_REGIONS = "us"
DEFAULT_MARKETS = "spreads"

ESPN_NFL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
