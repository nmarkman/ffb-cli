"""Public (no-login) commands: player search fuzzy matching and news."""
import json
import unittest
from unittest.mock import patch

from typer.testing import CliRunner

from ffb.main import app
from ffb.commands.players import _search_players

runner = CliRunner()

PLAYERS = [
    {"player_id": "1", "name": "Patrick Mahomes", "pos": "QB", "team": "KC", "status": None},
    {"player_id": "2", "name": "Justin Jefferson", "pos": "WR", "team": "MIN", "status": None},
    {"player_id": "3", "name": "Jefferson Smith", "pos": "WR", "team": "KC", "status": None},
    {"player_id": "4", "name": "Patrick Surtain", "pos": "CB", "team": "DEN", "status": None},
]


class TestSearchPlayers(unittest.TestCase):
    def test_fuzzy_match_ranks_best_first(self):
        out = _search_players("mahomes", PLAYERS, None, None, 10)
        self.assertEqual(out[0]["name"], "Patrick Mahomes")
        self.assertTrue(out[0]["score"] >= out[-1]["score"])  # sorted by score desc

    def test_position_filter(self):
        out = _search_players("jefferson", PLAYERS, "WR", None, 10)
        self.assertTrue(all(p["position"] == "WR" for p in out))

    def test_team_filter(self):
        out = _search_players("jefferson", PLAYERS, None, "KC", 10)
        self.assertTrue(all(p["team"] == "KC" for p in out))

    def test_limit(self):
        out = _search_players("e", PLAYERS, None, None, 1)
        self.assertLessEqual(len(out), 1)

    def test_no_match(self):
        self.assertEqual(_search_players("zzzznobody", PLAYERS, None, None, 10), [])


class TestNewsCommand(unittest.TestCase):
    ARTICLES = [
        {"title": "Article One", "date": "2026-05-26", "link": "https://x/1"},
        {"title": "Article Two", "date": "2026-05-25", "link": "https://x/2"},
        {"title": "Article Three", "date": "2026-05-24", "link": "https://x/3"},
    ]

    def test_cached_path_limit(self):
        # Patch the cache to return prebuilt articles -> no network.
        with patch("ffb.commands.news.get_cached", return_value=self.ARTICLES):
            r = runner.invoke(app, ["news", "-n", "3", "--json"])
        self.assertEqual(r.exit_code, 0)
        d = json.loads(r.stdout)
        self.assertEqual(len(d), 3)
        self.assertTrue(all(a.get("title") and a.get("link") for a in d))


if __name__ == "__main__":
    unittest.main()
