import datetime as dt
import os
import tempfile
from unittest import mock

import core.odds_api as odds


def test_odds_api_called_once_per_ttl():
    # Two page loads a minute apart (different window timestamps) must share one metered call.
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(url)
        r = mock.Mock()
        r.raise_for_status.return_value = None
        r.json.return_value = []
        return r

    with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"NFL_WATCH_CACHE_DIR": d}), \
            mock.patch("core.http_cache.requests.get", side_effect=fake_get):
        t0 = dt.datetime(2026, 10, 11, 17, 0, tzinfo=dt.timezone.utc)
        for minutes in (0, 1, 29):
            start = t0 + dt.timedelta(minutes=minutes)
            odds._fetch_odds_api_window(start, start + dt.timedelta(days=7), 7)
    assert len(calls) == 1, calls


if __name__ == "__main__":
    test_odds_api_called_once_per_ttl()
    print("ok")
