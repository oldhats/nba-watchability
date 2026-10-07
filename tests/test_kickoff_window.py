import datetime as dt

from dateutil import tz

from core.build_watchability_df import kickoff_window

ET = tz.gettz("America/New_York")


def _at(y, m, d, hh, mm):
    return dt.datetime(y, m, d, hh, mm, tzinfo=ET)


def test_kickoff_window():
    assert kickoff_window(_at(2026, 10, 11, 9, 30)) == "Sunday Morning"  # London
    assert kickoff_window(_at(2026, 10, 11, 13, 0)) == "Sunday Early"
    assert kickoff_window(_at(2026, 10, 11, 16, 5)) == "Sunday Late"
    assert kickoff_window(_at(2026, 10, 11, 16, 25)) == "Sunday Late"
    assert kickoff_window(_at(2026, 10, 11, 20, 20)) == "Sunday Night"
    assert kickoff_window(_at(2026, 10, 8, 20, 15)) == "Thursday Night"
    assert kickoff_window(_at(2026, 11, 26, 12, 30)) == "Thursday"  # Thanksgiving day game
    assert kickoff_window(_at(2026, 10, 12, 20, 15)) == "Monday Night"
    assert kickoff_window(None) == "TBD"


if __name__ == "__main__":
    test_kickoff_window()
    print("ok")
