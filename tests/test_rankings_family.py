"""Rankings/projections scoring math, tiering, scoring validation, and the
five projection-backed commands (rankings, projections, top200, flex, superflex)
via CliRunner with the network fetch patched out."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch

from typer.testing import CliRunner

from ffb.main import app
from ffb.commands.rankings import _calc_points, _assign_tiers, validate_scoring

runner = CliRunner()

# A WR line that's easy to verify by hand.
WR_STATS = {
    "passing_yards": 0, "passing_touchdowns": 0, "interceptions_thrown": 0,
    "rushing_yards": 0, "rushing_touchdowns": 0,
    "receptions": 100, "receiving_yards": 1300, "receiving_touchdowns": 10,
    "fumbles_lost": 0,
}


def _players():
    return [
        {"player_id": "1", "player_name": "QB A", "position": "QB", "team": "KC", "bye_week": "7", "points": 300.0, "tier": 1, "rank": 1},
        {"player_id": "2", "player_name": "RB B", "position": "RB", "team": "SF", "bye_week": "9", "points": 250.0, "tier": 1, "rank": 2},
        {"player_id": "3", "player_name": "WR C", "position": "WR", "team": "CIN", "bye_week": "10", "points": 240.0, "tier": 1, "rank": 3},
        {"player_id": "4", "player_name": "K D", "position": "K", "team": "BAL", "bye_week": "7", "points": 120.0, "tier": 2, "rank": 4},
    ]


class TestScoringMath(unittest.TestCase):
    def test_half_ppr(self):
        # 100*0.5 + 1300*0.1 + 10*6 = 50 + 130 + 60 = 240
        self.assertAlmostEqual(_calc_points(WR_STATS, "HALF"), 240.0)

    def test_full_ppr(self):
        # 100*1.0 + 130 + 60 = 290
        self.assertAlmostEqual(_calc_points(WR_STATS, "PPR"), 290.0)

    def test_standard(self):
        # 100*0 + 130 + 60 = 190
        self.assertAlmostEqual(_calc_points(WR_STATS, "STD"), 190.0)

    def test_negative_events(self):
        stats = dict(WR_STATS, interceptions_thrown=3, fumbles_lost=2)
        # 240 + 3*-2 + 2*-2 = 240 - 6 - 4 = 230
        self.assertAlmostEqual(_calc_points(stats, "HALF"), 230.0)


class TestTiers(unittest.TestCase):
    def test_breakpoints(self):
        players = [
            {"position": "WR", "points": 100.0},  # frac 1.0  -> tier 1
            {"position": "WR", "points": 70.0},   # frac 0.7  -> tier 2
            {"position": "WR", "points": 40.0},   # frac 0.4  -> tier 3
        ]
        _assign_tiers(players, {"WR.HALF": [1.0, 0.8, 0.5]}, "HALF")
        self.assertEqual([p["tier"] for p in players], [1, 2, 3])

    def test_no_breakpoints_defaults_tier1(self):
        players = [{"position": "TE", "points": 50.0}]
        _assign_tiers(players, {}, "HALF")
        self.assertEqual(players[0]["tier"], 1)


class TestValidateScoring(unittest.TestCase):
    def test_accepts_known(self):
        for s in ("half", "PPR", "Standard"):
            self.assertEqual(validate_scoring(s), s.lower())

    def test_rejects_unknown(self):
        with self.assertRaises(Exception), contextlib.redirect_stderr(io.StringIO()):
            validate_scoring("bogus")


class TestRankingsCommands(unittest.TestCase):
    def _run(self, module, args):
        with patch(f"ffb.commands.{module}._fetch_projections",
                   return_value=[dict(p) for p in _players()]):
            return runner.invoke(app, args)

    def test_rankings_position_filter_and_rerank(self):
        r = self._run("rankings", ["rankings", "WR", "--json"])
        self.assertEqual(r.exit_code, 0)
        d = json.loads(r.stdout)
        self.assertTrue(all(p["position"] == "WR" for p in d))
        self.assertEqual(d[0]["rank"], 1)

    def test_rankings_tier_filter(self):
        r = self._run("rankings", ["rankings", "--tier", "2", "--json"])
        d = json.loads(r.stdout)
        self.assertTrue(all(p["tier"] == 2 for p in d))

    def test_rankings_invalid_scoring_exits(self):
        r = runner.invoke(app, ["rankings", "QB", "-s", "bogus"])
        self.assertNotEqual(r.exit_code, 0)
        self.assertIn("Unknown scoring", r.stdout + str(r.stderr))

    def test_top200_sequential_ranks(self):
        r = self._run("top200", ["top200", "--json"])
        d = json.loads(r.stdout)
        self.assertEqual([p["rank"] for p in d], list(range(1, len(d) + 1)))

    def test_flex_excludes_qb_and_k(self):
        r = self._run("flex", ["flex", "--json"])
        d = json.loads(r.stdout)
        self.assertTrue(all(p["position"] in {"RB", "WR", "TE"} for p in d))

    def test_superflex_boosts_qb(self):
        r = self._run("superflex", ["superflex", "--qb-boost", "2.0", "--json"])
        d = json.loads(r.stdout)
        qb = next(p for p in d if p["position"] == "QB")
        self.assertAlmostEqual(qb["points"], 600.0)  # 300 * 2.0
        self.assertEqual(d[0]["rank"], 1)


if __name__ == "__main__":
    unittest.main()
