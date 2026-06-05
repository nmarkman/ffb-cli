"""Existing UDK table commands: bye-weeks, sos, red-zone, best-ball."""
import json
import unittest
from unittest.mock import patch

from typer.testing import CliRunner

from ffb.main import app

runner = CliRunner()


def invoke(target, fixture, args):
    with patch(target, return_value=fixture):
        return runner.invoke(app, args)


class TestByeWeeks(unittest.TestCase):
    FIX = [
        {"bye_week": "10", "name": "Team B", "key": "TB"},
        {"bye_week": "5", "name": "Team A", "key": "TA"},
        {"bye_week": "8", "name": "Team C", "key": "TC"},
    ]

    def test_sorted_by_week(self):
        r = invoke("ffb.commands.bye_weeks.load_const_data", self.FIX, ["bye-weeks", "--json"])
        d = json.loads(r.stdout)
        self.assertEqual([x["bye_week"] for x in d], [5, 8, 10])

    def test_week_filter(self):
        r = invoke("ffb.commands.bye_weeks.load_const_data", self.FIX, ["bye-weeks", "-w", "8", "--json"])
        d = json.loads(r.stdout)
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0]["key"], "TC")


class TestSos(unittest.TestCase):
    FIX = [
        {"name": "Team A", "team": "TA", "bye_week": "5", "qb_total": "200", "rb_total": "180",
         "wr_total": "260", "te_total": "120", "k_total": "150", "d_total": "140"},
        {"name": "Team B", "team": "TB", "bye_week": "9", "qb_total": "210", "rb_total": "190",
         "wr_total": "300", "te_total": "110", "k_total": "160", "d_total": "130"},
    ]

    def test_wr_sort_easiest_first(self):
        r = invoke("ffb.commands.sos.load_const_data", self.FIX, ["sos", "WR", "--json"])
        d = json.loads(r.stdout)
        # easiest (most WR points allowed) first
        self.assertEqual(d[0]["team"], "TB")
        self.assertGreaterEqual(d[0]["wr_total"], d[1]["wr_total"])

    def test_hard_flips_order(self):
        r = invoke("ffb.commands.sos.load_const_data", self.FIX, ["sos", "WR", "--hard", "--json"])
        d = json.loads(r.stdout)
        self.assertEqual(d[0]["team"], "TA")


class TestRedZone(unittest.TestCase):
    FIX = [
        {"name": "RB Old", "fantasy_position": "RB", "team": "TA", "season": "2024",
         "red_zone_rushing_attempts": "50", "red_zone_rushing_touchdowns": "10",
         "red_zone_receiving_targets": "5", "red_zone_passing_attempts": "0"},
        {"name": "RB New", "fantasy_position": "RB", "team": "TB", "season": "2025",
         "red_zone_rushing_attempts": "40", "red_zone_rushing_touchdowns": "8",
         "red_zone_receiving_targets": "20", "red_zone_passing_attempts": "0"},
        {"name": "WR New", "fantasy_position": "WR", "team": "TC", "season": "2025",
         "red_zone_receiving_targets": "30", "red_zone_rushing_attempts": "0",
         "red_zone_passing_attempts": "0", "red_zone_receiving_touchdowns": "6"},
    ]

    def test_defaults_to_latest_season_and_touches(self):
        r = invoke("ffb.commands.red_zone.load_const_data", self.FIX, ["red-zone", "--json"])
        d = json.loads(r.stdout)
        # only 2025 rows, sorted by touches (rec tgts + rush att + pass att) desc.
        # RB New touches = 20 + 40 = 60 ; WR New = 30 -> RB New ranks first.
        self.assertTrue(all(x["season"] == 2025 for x in d))
        self.assertEqual(d[0]["name"], "RB New")

    def test_position_filter(self):
        r = invoke("ffb.commands.red_zone.load_const_data", self.FIX, ["red-zone", "WR", "--json"])
        d = json.loads(r.stdout)
        self.assertTrue(all(x["fantasy_position"] == "WR" for x in d))


class TestBestBall(unittest.TestCase):
    FIX = [
        {"name": "P Late", "fantasy_position": "RB", "team": "TA", "bye_week": "5", "adp": "40.0", "betz": "1", "borg": "2"},
        {"name": "P Early", "fantasy_position": "WR", "team": "TB", "bye_week": "6", "adp": "3.0", "betz": "3", "borg": "4"},
    ]

    def test_sorted_by_adp(self):
        r = invoke("ffb.commands.best_ball.load_const_data", self.FIX, ["best-ball", "--json"])
        d = json.loads(r.stdout)
        self.assertEqual([x["name"] for x in d], ["P Early", "P Late"])


if __name__ == "__main__":
    unittest.main()
