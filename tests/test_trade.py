"""Trade value normalization (both page shapes) and fuzzy player matching."""
import unittest

from ffb.commands.trade import _values_from_global_blob, _values_from_list, _find_player


def _analyst_row(pid, name, pos, **stats):
    base = {"player_id": pid, "name": name, "fantasy_position": pos, "team": "XX"}
    base.update(stats)
    return base


class TestGlobalBlob(unittest.TestCase):
    def test_average_points_sort_rank(self):
        blob = {"projections": [
            # WR: avg rec 110, recyd 1300, rectd 10 -> HALF 55+130+60 = 245
            _analyst_row("1", "WR One", "WR", receptions=100, receiving_yards=1300, receiving_touchdowns=10),
            _analyst_row("1", "WR One", "WR", receptions=120, receiving_yards=1300, receiving_touchdowns=10),
            # RB: rush 1000yd/8td, rec 40/300 -> HALF 100+48+20+30 = 198
            _analyst_row("2", "RB Two", "RB", rushing_yards=1000, rushing_touchdowns=8, receptions=40, receiving_yards=300),
            _analyst_row("2", "RB Two", "RB", rushing_yards=1000, rushing_touchdowns=8, receptions=40, receiving_yards=300),
        ]}
        out = _values_from_global_blob(blob)
        self.assertEqual([p["player_name"] for p in out], ["WR One", "RB Two"])
        self.assertEqual([p["rank"] for p in out], [1, 2])
        self.assertAlmostEqual(out[0]["value"], 245.0, places=1)
        self.assertAlmostEqual(out[1]["value"], 198.0, places=1)


class TestListShape(unittest.TestCase):
    def test_uses_fantasy_points(self):
        out = _values_from_list([
            {"name": "A", "fantasy_position": "QB", "team": "KC", "rank": 1, "fantasy_points": "300.5"},
            {"name": "B", "fantasy_position": "RB", "team": "SF", "rank": 2, "fantasy_points": 250},
        ])
        self.assertEqual(out[0]["value"], 300.5)
        self.assertEqual(out[1]["value"], 250.0)


class TestFindPlayer(unittest.TestCase):
    VALUES = [
        {"player_name": "Travis Kelce"},
        {"player_name": "Ja'Marr Chase"},
        {"player_name": "Trey McBride"},
    ]

    def test_partial_match(self):
        self.assertEqual(_find_player("kelce", self.VALUES)["player_name"], "Travis Kelce")

    def test_apostrophe_name(self):
        self.assertEqual(_find_player("jamarr chase", self.VALUES)["player_name"], "Ja'Marr Chase")

    def test_no_match_returns_none(self):
        self.assertIsNone(_find_player("zzzznobody", self.VALUES))


if __name__ == "__main__":
    unittest.main()
