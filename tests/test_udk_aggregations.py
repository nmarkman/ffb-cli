"""Share and consistency aggregations (accuracy-critical math) for the UDK
research commands, driven through CliRunner with the page loaders patched."""
import json
import unittest
from unittest.mock import patch

from typer.testing import CliRunner

from ffb.main import app

runner = CliRunner()


def invoke(patch_target, fixture, args):
    with patch(patch_target, return_value=fixture):
        return runner.invoke(app, args)


class TestMarketShare(unittest.TestCase):
    def test_target_share_math(self):
        rows = []
        for wk in (1, 2):
            rows.append({
                "player_id": "9", "name": "WR X", "fantasy_position": "WR", "team": "KC",
                "season": "2025", "week": str(wk),
                "receiving_targets": "10.00", "total_receiving_targets": "40.00",
                "rushing_attempts": "0.00", "total_rushing_attempts": "0.00",
                "receiving_yards": "100.00", "total_receiving_yards": "400.00",
                "fantasy_points": "20.00", "total_fantasy_points": "100.00",
            })
        r = invoke("ffb.commands.market_share.load_const_data", rows,
                   ["market-share", "--min-games", "2", "--json"])
        self.assertEqual(r.exit_code, 0)
        d = json.loads(r.stdout)
        self.assertEqual(d[0]["games"], 2)
        # (10+10)/(40+40) = 0.25 ; points 40/200 = 0.20
        self.assertAlmostEqual(d[0]["target_share"], 0.25)
        self.assertAlmostEqual(d[0]["rec_yd_share"], 0.25)
        self.assertAlmostEqual(d[0]["points_share"], 0.20)


class TestTargetShare(unittest.TestCase):
    def test_team_split_sums_to_one(self):
        rows = []
        for wk in (1, 2):
            rows.append({
                "team_id": "1", "key": "ARI", "name": "Arizona Cardinals",
                "season": "2025", "week": str(wk),
                "wr_targets": "12.00", "rb_targets": "5.00", "te_targets": "12.00",
                "total_targets": "29.00",
            })
        r = invoke("ffb.commands.target_share.load_const_data", rows, ["target-share", "--json"])
        d = json.loads(r.stdout)
        row = d[0]
        self.assertEqual(row["wr_share"], round(24 / 58, 4))  # shares rounded to 4dp
        s = row["wr_share"] + row["rb_share"] + row["te_share"]
        self.assertAlmostEqual(s, 1.0, places=3)
        self.assertAlmostEqual(row["targets_per_game"], 29.0)


class TestValueScout(unittest.TestCase):
    def test_sorted_and_none_sinks(self):
        rows = [
            {"name": "Late", "fantasy_position": "RB", "team": "A", "bye_week": "5", "adp": "50.0"},
            {"name": "Early", "fantasy_position": "WR", "team": "B", "bye_week": "6", "adp": "2.0"},
            {"name": "NoAdp", "fantasy_position": "TE", "team": "C", "bye_week": "7", "adp": ""},
        ]
        r = invoke("ffb.commands.value_scout.load_const_data", rows, ["value-scout", "--json"])
        d = json.loads(r.stdout)
        self.assertEqual([p["name"] for p in d], ["Early", "Late", "NoAdp"])  # ascending, None last
        self.assertEqual([p["rank"] for p in d], [1, 2, 3])


class TestConsistency(unittest.TestCase):
    def _rb_row(self, ranks_points):
        row = {"name": "RB Y", "fantasy_position": "RB", "team_key": "SF",
               "season": "2025", "player_id": "5"}
        for i, (rank, pts) in enumerate(ranks_points, 1):
            row[f"week_{i}_played"] = "1"
            row[f"week_{i}_started"] = "1"
            row[f"week_{i}_opponent"] = "OPP"
            row[f"week_{i}_position_rank"] = str(rank)
            row[f"week_{i}_fantasy_points"] = str(pts)
            row[f"week_{i}_fantasy_points_ppr"] = str(pts)
        return row

    def test_boom_start_bust_rates(self):
        # 8 games, ranks: startable(<=24) = 1,3,10,20,5,15 -> 6/8 ; boom(<=5)=1,3,5 ->3/8 ; bust(>24)=30,40 ->2/8
        ranks_points = [(1, 30), (3, 25), (10, 18), (20, 12), (30, 6), (5, 22), (15, 14), (40, 3)]
        fixture = {"2025": [self._rb_row(ranks_points)]}
        r = invoke("ffb.commands.consistency.load_const_data_raw", fixture,
                   ["consistency", "RB", "--json"])
        self.assertEqual(r.exit_code, 0)
        d = json.loads(r.stdout)[0]
        self.assertEqual(d["games"], 8)
        self.assertAlmostEqual(d["start_pct"], 6 / 8)
        self.assertAlmostEqual(d["boom_pct"], 3 / 8)
        self.assertAlmostEqual(d["bust_pct"], 2 / 8)

    def test_weekly_game_log(self):
        fixture = {"2025": [self._rb_row([(1, 30), (5, 22), (10, 18)])]}
        r = invoke("ffb.commands.consistency.load_const_data_raw", fixture,
                   ["consistency", "-w", "RB Y", "--json"])
        d = json.loads(r.stdout)
        self.assertEqual(len(d["weeks"]), 3)
        self.assertEqual(d["weeks"][0]["points"], 30.0)
        self.assertEqual(d["player"]["team"], "SF")


if __name__ == "__main__":
    unittest.main()
