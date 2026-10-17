"""CLI-level tests for the in-season commands not covered in test_inseason.py
(ros, waivers, stream, dfs, player-news), the display formatters with real
logic, and the quiet failure path of the current-season merge. Page loaders
are patched at each command's module, so this runs offline."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch

from typer.testing import CliRunner

from ffb.api.client import AuthExpiredError
from ffb.commands import _scrape
from ffb.commands.player_news import news_rows
from ffb.commands.ros import ros_rows
from ffb.display.tables import _fmt_kickoff, _fmt_spread, _fmt_weather
from ffb.main import app

runner = CliRunner()


def line(pid, analyst, name, pos, team, games=10, **stats):
    row = {"player_id": pid, "analyst_id": analyst, "name": name, "fantasy_position": pos,
           "team": team, "week": "6", "remaining_games": games}
    for f in ("passing_yards", "passing_touchdowns", "interceptions_thrown", "rushing_yards",
              "rushing_touchdowns", "receptions", "receiving_yards", "receiving_touchdowns", "fumbles_lost"):
        row[f] = str(stats.get(f, 0))
    return row


ROS = [
    line("1", "1", "RB A", "RB", "ATL", games=12, rushing_yards=1000, rushing_touchdowns=8),
    line("1", "2", "RB A", "RB", "ATL", games=12, rushing_yards=900, rushing_touchdowns=6),
    line("2", "1", "WR B", "WR", "LAR", games=11, receptions=80, receiving_yards=1000, receiving_touchdowns=6),
    line("3", "1", "QB C", "QB", "BUF", games="", passing_yards=3000, passing_touchdowns=20),
]


class TestRos(unittest.TestCase):
    def test_rows_add_games_and_ppg(self):
        rows = ros_rows(ROS, "FLEX", "half")
        self.assertEqual([r["name"] for r in rows], ["WR B", "RB A"])
        rb = rows[1]
        self.assertEqual(rb["remaining_games"], 12)
        self.assertEqual(rb["points"], 137.0)  # mean(148, 126)
        self.assertEqual(rb["ppg"], round(137.0 / 12, 1))
        self.assertNotIn("injury_status", rb)
        self.assertNotIn("_avg", rb)

    def test_blank_remaining_games(self):
        qb = ros_rows(ROS, "QB", "half")[0]
        self.assertIsNone(qb["remaining_games"])
        self.assertIsNone(qb["ppg"])

    def test_cli_json_and_team_filter(self):
        with patch("ffb.commands.ros.load_tool_data", return_value=ROS):
            r = runner.invoke(app, ["ros", "RB", "-t", "ATL", "--json"])
        self.assertEqual(r.exit_code, 0, r.output)
        d = json.loads(r.stdout)
        self.assertEqual((d["week"], d["position"]), (6, "RB"))
        self.assertEqual([p["name"] for p in d["players"]], ["RB A"])

    def test_cli_table_renders(self):
        with patch("ffb.commands.ros.load_tool_data", return_value=ROS):
            r = runner.invoke(app, ["ros"])
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertIn("RB A", r.output)


WAIVERS = {
    "week": 6,
    "allGames": {"GB6": {"home_team": "GB", "away_team": "DAL"}},
    "rankings": [
        {"player_id": "1", "name": "RB X", "fantasy_position": "RB", "team": "GB", "consensus": 2,
         "andy": "2", "jason": "1", "mike": "3", "faab_low": "5", "faab_high": "15", "pickup_type": ""},
        {"player_id": "2", "name": "WR Y", "fantasy_position": "WR", "team": "PIT", "consensus": 1,
         "andy": "1", "jason": "2", "mike": "1", "faab_low": "0", "faab_high": "10", "pickup_type": "stash"},
    ],
    "defenseRankings": [
        {"player_id": "55", "name": "Chiefs", "fantasy_position": "D", "team": "KC", "consensus": 1,
         "andy": "1", "jason": "1", "mike": "1"},
    ],
}


class TestWaivers(unittest.TestCase):
    def invoke(self, *args):
        with patch("ffb.commands.waivers.load_tool_data", return_value=WAIVERS):
            return runner.invoke(app, ["waivers", *args])

    def test_all(self):
        d = json.loads(self.invoke("--json").stdout)
        self.assertEqual(d["position"], "ALL")
        self.assertEqual([p["name"] for p in d["players"]], ["WR Y", "RB X"])
        self.assertEqual(d["players"][1]["matchup"], "vs DAL")
        self.assertEqual(d["players"][1]["faab"], "5-15%")

    def test_position_filter_reranks(self):
        d = json.loads(self.invoke("RB", "--json").stdout)
        self.assertEqual([(p["name"], p["rank"]) for p in d["players"]], [("RB X", 1)])

    def test_dst_uses_defense_list(self):
        d = json.loads(self.invoke("DST", "--json").stdout)
        self.assertEqual(d["position"], "DST")
        self.assertEqual([(p["name"], p["position"]) for p in d["players"]], [("Chiefs", "DST")])

    def test_table_renders_stash(self):
        r = self.invoke()
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertIn("STASH", r.output)


def stream_row(team, weeks):
    row = {"team": team, "name": team}
    for w, (opp, pts) in weeks.items():
        row[f"week_{w}_opponent"] = opp
        row[f"week_{w}_fan_duel_quarterback_fantasy_points_allowed"] = str(pts)
    return row


# Through week 3: X faced strong offense A (30s everywhere), Y faced weak B.
STREAM_ROWS = [
    stream_row("X", {1: ("A", 30), 2: ("A", 30), 3: ("A", 30)}),
    stream_row("Y", {1: ("B", 20), 2: ("B", 20), 3: ("B", 20)}),
    stream_row("Z", {1: ("A", 30), 2: ("A", 30), 3: ("A", 30)}),
    stream_row("W", {1: ("B", 0), 2: ("B", 0), 3: ("B", 0)}),
]
STREAM_PAGE = ({"week": 4, "seasonWeeks": 5, "streamFinder": json.dumps(STREAM_ROWS),
                "allGames": {"Y4": {"home_team": "Y", "away_team": "Q"}}}, [])


class TestStream(unittest.TestCase):
    def invoke(self, *args, page=STREAM_PAGE):
        with patch("ffb.commands.stream.load_page_data", return_value=page):
            return runner.invoke(app, ["stream", *args])

    def test_decodes_string_payload_and_ranks_by_pae(self):
        d = json.loads(self.invoke("--json").stdout)
        self.assertEqual(d["ranked_by"], "pae")
        self.assertEqual(d["teams"][0]["team"], "Y")
        self.assertEqual(d["teams"][0]["upcoming"]["4"], "Q")

    def test_upcoming_weeks_clamped_to_season(self):
        d = json.loads(self.invoke("-w", "5", "--json").stdout)
        self.assertEqual(d["upcoming_weeks"], [4, 5])

    def test_raw_flag(self):
        d = json.loads(self.invoke("--raw", "--json").stdout)
        self.assertEqual(d["ranked_by"], "avg_allowed")
        self.assertIn(d["teams"][0]["team"], ("X", "Z"))

    def test_early_season_uses_raw(self):
        two_weeks = [{k: v for k, v in r.items() if not k.startswith("week_3")} for r in STREAM_ROWS]
        page = ({**STREAM_PAGE[0], "streamFinder": two_weeks}, [])
        d = json.loads(self.invoke("--json", page=page).stdout)
        self.assertEqual((d["through_week"], d["ranked_by"]), (2, "avg_allowed"))

    def test_no_data_yet(self):
        r = self.invoke("--json", page=({"week": 1, "streamFinder": []}, []))
        self.assertEqual(r.exit_code, 0)
        self.assertIn("No Stream Finder data", r.output)

    def test_table_renders(self):
        r = self.invoke()
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertIn("schedule-adjusted", r.output)


DFS_PLAYERS = [
    {"player_id": "1", "name": "WR Cheap", "fantasy_position": "WR", "team": "PIT",
     "upcoming_draft_kings_salary": "3000", "upcoming_fan_duel_salary": "5000"},
    {"player_id": "2", "name": "QB Pricey", "fantasy_position": "QB", "team": "BUF",
     "upcoming_draft_kings_salary": "8000", "upcoming_fan_duel_salary": "9000"},
]
DFS_PROJ = [
    line("1", "1", "WR Cheap", "WR", "PIT", receptions=5, receiving_yards=60),         # DK 11
    line("2", "1", "QB Pricey", "QB", "BUF", passing_yards=300, passing_touchdowns=2),  # DK 20
]
DFS_SIMPLE = ({"simpleProjections": [
    {"name": "Chiefs", "fantasy_position": "D", "team": "KC", "points": "8",
     "upcoming_draft_kings_salary": "4000", "upcoming_fan_duel_salary": "4500"}]}, [])


class TestDfs(unittest.TestCase):
    def invoke(self, *args, players=DFS_PLAYERS):
        with patch("ffb.commands.dfs._load_dfs_players", return_value=(players, DFS_PROJ)), \
             patch("ffb.commands.dfs.load_page_data", return_value=DFS_SIMPLE):
            return runner.invoke(app, ["dfs", *args])

    def names(self, *args):
        r = self.invoke(*args, "--json")
        self.assertEqual(r.exit_code, 0, r.output)
        return [p["name"] for p in json.loads(r.stdout)["players"]]

    def test_sorts(self):
        self.assertEqual(self.names(), ["WR Cheap", "QB Pricey", "Chiefs"])  # value
        self.assertEqual(self.names("-s", "points"), ["QB Pricey", "WR Cheap", "Chiefs"])
        self.assertEqual(self.names("-s", "salary"), ["QB Pricey", "Chiefs", "WR Cheap"])

    def test_filters(self):
        self.assertEqual(self.names("FLEX"), ["WR Cheap"])
        self.assertEqual(self.names("DST"), ["Chiefs"])
        self.assertEqual(self.names("--max-salary", "4000"), ["WR Cheap", "Chiefs"])

    def test_fanduel_salary(self):
        r = self.invoke("QB", "--site", "fd", "--json")
        p = json.loads(r.stdout)["players"][0]
        self.assertEqual((p["salary"], p["points"]), (9000, 20.0))

    def test_bad_site_and_sort(self):
        self.assertEqual(self.invoke("--site", "yahoo").exit_code, 1)
        self.assertEqual(self.invoke("-s", "ownership").exit_code, 1)

    def test_empty_page_points_at_login(self):
        r = self.invoke(players=[])
        self.assertEqual(r.exit_code, 1)
        self.assertIn("ffb login", r.output)


NEWS = [
    {"date_iso": "2026-10-16T10:00:00+00:00", "name": "Baker Mayfield", "fantasy_position": "QB",
     "team": "TB", "headline": "Ruled out", "injury_status": "OUT", "injury_side": "Right",
     "injury_location": "Hand", "injury_type": "Thumb"},
    {"date_iso": "2026-10-17T00:00:00+00:00", "name": "Evan Engram", "fantasy_position": "TE",
     "team": "DEN", "headline": "Two catches", "injury_status": None},
    {"date_iso": "2026-10-15T00:00:00+00:00", "name": "Chiefs", "fantasy_position": "D",
     "team": "KC", "headline": "Defense note", "injury_status": None},
]


class TestPlayerNews(unittest.TestCase):
    def names(self, *args):
        with patch("ffb.commands.player_news.load_tool_data", return_value={"news": NEWS}):
            r = runner.invoke(app, ["player-news", *args, "--json"])
        self.assertEqual(r.exit_code, 0, r.output)
        return [x["name"] for x in json.loads(r.stdout)]

    def test_rows_newest_first_with_injury_text(self):
        rows = news_rows(NEWS)
        self.assertEqual(rows[0]["name"], "Evan Engram")
        mayfield = next(r for r in rows if r["name"] == "Baker Mayfield")
        self.assertEqual(mayfield["injury"], "Right Hand Thumb")
        self.assertEqual(next(r for r in rows if r["name"] == "Chiefs")["position"], "DST")

    def test_filters(self):
        self.assertEqual(self.names("Mayfield"), ["Baker Mayfield"])
        self.assertEqual(self.names("--injuries"), ["Baker Mayfield"])
        self.assertEqual(self.names("-p", "dst"), ["Chiefs"])
        self.assertEqual(self.names("-t", "den"), ["Evan Engram"])

    def test_bad_position_rejected(self):
        with patch("ffb.commands.player_news.load_tool_data", return_value={"news": NEWS}):
            r = runner.invoke(app, ["player-news", "-p", "LB"])
        self.assertEqual(r.exit_code, 1)

    def test_full_panels_render(self):
        with patch("ffb.commands.player_news.load_tool_data", return_value={"news": NEWS}):
            r = runner.invoke(app, ["player-news", "Mayfield", "--full"])
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertIn("Ruled out", r.output)


class TestFormatters(unittest.TestCase):
    def test_spread(self):
        self.assertEqual(_fmt_spread(-7.5), "-7.5")
        self.assertEqual(_fmt_spread(3), "+3.0")
        self.assertEqual(_fmt_spread(0), "PK")
        self.assertEqual(_fmt_spread(None), "")

    def test_weather(self):
        self.assertEqual(_fmt_weather({"dome": True, "summary": "Rain"}), "Dome")
        self.assertEqual(
            _fmt_weather({"dome": False, "summary": "Rain", "temperature": 41.6, "wind_mph": 18.2, "precip_pct": 80}),
            "Rain, 42F, wind 18, 80% precip")
        self.assertEqual(_fmt_weather(None), "")

    def test_kickoff_is_local_and_unpadded(self):
        out = _fmt_kickoff("2026-10-18 17:00:00")
        self.assertRegex(out, r"^[A-Z][a-z]{2} [1-9]\d?:\d\d [AP]M$")
        self.assertEqual(_fmt_kickoff("not a date"), "not a date")
        self.assertEqual(_fmt_kickoff(None), "")


class TestCurrentSeasonFailurePath(unittest.TestCase):
    """The FootClan merge is optional: no session or an expired one must fall
    back to the UDK data silently, not print a login error mid-command."""

    def test_no_session(self):
        with patch.object(_scrape, "get_cached", return_value=None), \
             patch.object(_scrape, "load_session", return_value=None):
            self.assertIsNone(_scrape.load_current_season("/footclan/x/"))

    def test_expired_session_is_quiet(self):
        err = io.StringIO()
        with patch.object(_scrape, "get_cached", return_value=None), \
             patch.object(_scrape, "load_session", return_value=object()), \
             patch.object(_scrape, "FFBClient") as client, contextlib.redirect_stderr(err):
            client.return_value.get_page.side_effect = AuthExpiredError("expired")
            self.assertIsNone(_scrape.load_current_season("/footclan/x/"))
        self.assertEqual(err.getvalue(), "")

    def test_page_without_payload_not_cached(self):
        with patch.object(_scrape, "get_cached", return_value=None), \
             patch.object(_scrape, "load_session", return_value=object()), \
             patch.object(_scrape, "FFBClient") as client, \
             patch.object(_scrape, "set_cached") as cache:
            client.return_value.get_page.return_value = "<html>locked</html>"
            self.assertIsNone(_scrape.load_current_season("/footclan/x/"))
        cache.assert_not_called()


class TestFetchPageCacheGuard(unittest.TestCase):
    def test_shell_page_not_cached(self):
        with patch.object(_scrape, "get_cached", return_value=None), \
             patch.object(_scrape, "get_client") as gc, \
             patch.object(_scrape, "set_cached") as cache:
            gc.return_value.get_page.return_value = "<html>empty</html>"
            _scrape.fetch_page("/x/", require="const data")
            cache.assert_not_called()
            gc.return_value.get_page.return_value = "<script>const data = []</script>"
            _scrape.fetch_page("/x/", require="const data")
            cache.assert_called_once()


if __name__ == "__main__":
    unittest.main()
