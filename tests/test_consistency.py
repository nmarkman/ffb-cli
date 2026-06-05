"""Consistency engine: season selection and weekly game-log extraction."""
import unittest

from ffb.commands.consistency import _season_rows, _player_weeks


def _row(**weeks):
    """Build a player row from {week_num: (played, points, ppr, rank, started, opp)}."""
    r = {"name": "Test Player", "fantasy_position": "RB", "team_key": "KC"}
    for wk, (played, pts, ppr, rank, started, opp) in weeks.items():
        r[f"week_{wk}_played"] = played
        r[f"week_{wk}_fantasy_points"] = pts
        r[f"week_{wk}_fantasy_points_ppr"] = ppr
        r[f"week_{wk}_position_rank"] = rank
        r[f"week_{wk}_started"] = started
        r[f"week_{wk}_opponent"] = opp
    return r


class TestSeasonRows(unittest.TestCase):
    def test_picks_most_recent_by_default(self):
        data = {"2023": [{"a": 1}], "2025": [{"a": 3}], "2024": [{"a": 2}]}
        season, rows = _season_rows(data, None)
        self.assertEqual(season, 2025)
        self.assertEqual(rows, [{"a": 3}])

    def test_picks_requested_season(self):
        data = {"2023": [{"a": 1}], "2025": [{"a": 3}]}
        season, rows = _season_rows(data, 2023)
        self.assertEqual(season, 2023)
        self.assertEqual(rows, [{"a": 1}])

    def test_unknown_season_falls_back_to_recent(self):
        data = {"2024": [{"a": 2}], "2025": [{"a": 3}]}
        season, rows = _season_rows(data, 1999)
        self.assertEqual(season, 2025)

    def test_list_passthrough(self):
        season, rows = _season_rows([{"a": 1}], 2025)
        self.assertEqual(rows, [{"a": 1}])


class TestPlayerWeeks(unittest.TestCase):
    def test_only_played_weeks(self):
        row = _row(
            **{
                "1": ("1", "20.0", "25.0", "3", "1", "BAL"),
                "2": ("0", "0.0", "0.0", "", "0", ""),    # bye / inactive
                "3": ("1", "10.0", "12.0", "18", "1", "NO"),
            }
        )
        weeks = _player_weeks(row, ppr=False)
        self.assertEqual([w["week"] for w in weeks], [1, 3])
        self.assertEqual(weeks[0]["points"], 20.0)
        self.assertEqual(weeks[0]["position_rank"], 3)
        self.assertTrue(weeks[0]["started"])

    def test_ppr_scoring(self):
        row = _row(**{"1": ("1", "20.0", "25.5", "3", "1", "BAL")})
        weeks = _player_weeks(row, ppr=True)
        self.assertEqual(weeks[0]["points"], 25.5)


if __name__ == "__main__":
    unittest.main()
