"""In-season FootClan tools: consensus ranking math, waiver re-ranking, Vegas
implied totals, Stream Finder, start/sit name resolution, DFS values, the
current-season merge for the research commands, and the auth-error handler.
Fixtures stand in for the scraped pages, so this runs offline."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch

from typer.testing import CliRunner

from ffb.api.client import AuthExpiredError
from ffb.commands import _inseason as ins
from ffb.commands._scrape import merge_current_season, resolve_min_games
from ffb.commands.consistency import _with_current_season
from ffb.commands.dfs import dfs_points, dfs_rows
from ffb.commands.startsit import compare, directory_match, is_exact, resolve, unavailable
from ffb.main import app

runner = CliRunner()


def proj(pid, analyst, name, pos, team, **stats):
    row = {"player_id": pid, "analyst_id": analyst, "name": name,
           "fantasy_position": pos, "team": team, "injury_status": None}
    row.update({f: "0.00" for f in ins.STAT_FIELDS})
    row.update({k: str(v) for k, v in stats.items()})
    return row


# Two WRs, three analysts. WR A: 10 rec / 100 yd / 1 TD for Andy + Jason,
# Mike has him lower. WR B: flat 6 rec / 60 yd / 0 TD for everyone.
WEEKLY = [
    proj("1", "1", "WR A", "WR", "KC", receptions=10, receiving_yards=100, receiving_touchdowns=1),
    proj("1", "2", "WR A", "WR", "KC", receptions=10, receiving_yards=100, receiving_touchdowns=1),
    proj("1", "3", "WR A", "WR", "KC", receptions=4, receiving_yards=40, receiving_touchdowns=0),
    proj("2", "1", "WR B", "WR", "BUF", receptions=6, receiving_yards=60),
    proj("2", "2", "WR B", "WR", "BUF", receptions=6, receiving_yards=60),
    proj("2", "3", "WR B", "WR", "BUF", receptions=6, receiving_yards=60),
    proj("3", "1", "QB C", "QB", "KC", passing_yards=250, passing_touchdowns=2),
    proj("4", "1", "Empty", "WR", "NE"),  # all-zero line still counts, like the site
]

GAMES = {
    "KC6": {"home_team": "KC", "away_team": "LAC", "week": "6"},
    "LAC6": {"home_team": "KC", "away_team": "LAC", "week": "6"},
    "BUF6": {"home_team": "LV", "away_team": "BUF", "week": "6"},
    "LV6": {"home_team": "LV", "away_team": "BUF", "week": "6"},
}


class TestConsensusRankings(unittest.TestCase):
    def test_average_then_score(self):
        rows = ins.consensus_rankings(WEEKLY, "HALF", ("WR",))
        a = next(r for r in rows if r["name"] == "WR A")
        # avg line: 8 rec, 80 yd, 0.667 TD -> 4 + 8 + 4 = 16.0 half-PPR
        self.assertAlmostEqual(a["points"], 16.0, places=1)
        self.assertEqual(a["andy_points"], 21.0)  # 5 + 10 + 6
        self.assertEqual(a["mike_points"], 6.0)   # 2 + 4

    def test_consensus_and_analyst_ranks(self):
        rows = ins.consensus_rankings(WEEKLY, "HALF", ("WR",))
        self.assertEqual([r["name"] for r in rows], ["WR A", "WR B", "Empty"])
        a, b, _ = rows
        self.assertEqual((a["rank"], a["andy_rank"], a["mike_rank"]), (1, 1, 2))
        self.assertEqual((b["rank"], b["andy_rank"], b["mike_rank"]), (2, 2, 1))

    def test_position_filter_and_empty_rows(self):
        rows = ins.consensus_rankings(WEEKLY, "HALF", ins.FLEX_POSITIONS)
        self.assertNotIn("QB C", [r["name"] for r in rows])
        # An all-zero projection is still ranked (last, at 0 points), as on the site.
        self.assertEqual((rows[-1]["name"], rows[-1]["points"]), ("Empty", 0.0))

    def test_missing_analyst_scores_zero_but_is_ranked(self):
        rows = ins.consensus_rankings(WEEKLY, "HALF", ("WR",))
        empty = next(r for r in rows if r["name"] == "Empty")
        # Only Andy projected him: the mean uses Andy alone, Jason/Mike rank him last.
        self.assertIsNone(empty["jason_points"])
        self.assertEqual(empty["jason_rank"], 3)
        qb = ins.consensus_rankings(WEEKLY, "HALF", ("QB",))[0]
        self.assertEqual(qb["points"], 18.0)  # Andy's line alone, not diluted by zeros

    def test_six_point_passing_tds(self):
        four = ins.consensus_rankings(WEEKLY, "HALF", ("QB",))[0]["points"]
        six = ins.consensus_rankings(WEEKLY, "HALF", ("QB",), pass_td=6)[0]["points"]
        self.assertAlmostEqual(six - four, 4.0)  # 2 TDs * 2 extra points

    def test_scoring_format_changes_points(self):
        half = ins.consensus_rankings(WEEKLY, "HALF", ("WR",))[1]["points"]
        ppr = ins.consensus_rankings(WEEKLY, "PPR", ("WR",))[1]["points"]
        self.assertAlmostEqual(ppr - half, 3.0)  # 6 receptions * 0.5


class TestSimpleAndWaivers(unittest.TestCase):
    def test_simple_rankings_join_points(self):
        ranks = [
            {"player_id": "55", "name": "Chiefs", "fantasy_position": "D", "team": "KC",
             "consensus": 2, "andy": "1", "jason": "3", "mike": "2"},
            {"player_id": "21", "name": "Bills", "fantasy_position": "D", "team": "BUF",
             "consensus": 1, "andy": "2", "jason": "1", "mike": "1"},
        ]
        projs = [{"player_id": "55", "points": "10.70", "upcoming_game_opponent": "LAC"}]
        rows = ins.simple_rankings(ranks, projs)
        self.assertEqual([r["team"] for r in rows], ["BUF", "KC"])
        self.assertEqual(rows[1]["points"], 10.7)
        self.assertEqual(rows[1]["opponent"], "LAC")
        self.assertEqual(rows[0]["points"], 0.0)

    def test_waiver_rerank_and_faab(self):
        rows = [
            {"player_id": "1", "name": "A", "fantasy_position": "RB", "team": "GB",
             "consensus": 3, "andy": "5", "jason": "2", "mike": "9",
             "faab_low": "5", "faab_high": "15", "pickup_type": ""},
            {"player_id": "2", "name": "B", "fantasy_position": "WR", "team": "PIT",
             "consensus": 7, "andy": "1", "jason": "", "mike": "4",
             "faab_low": "3", "faab_high": "0", "pickup_type": "stash"},
        ]
        out = ins.waiver_rankings(rows)
        self.assertEqual([r["name"] for r in out], ["A", "B"])
        self.assertEqual((out[0]["rank"], out[0]["andy_rank"]), (1, 2))
        self.assertEqual((out[1]["andy_rank"], out[1]["jason_rank"]), (1, None))
        self.assertEqual(out[0]["faab"], "5-15%")
        self.assertEqual(out[1]["faab"], "3%")
        self.assertTrue(out[1]["stash"])
        self.assertEqual(ins.faab_range(None, None), "-")


class TestScheduleAndVegas(unittest.TestCase):
    def test_matchup(self):
        self.assertEqual(ins.matchup("KC", 6, GAMES), "vs LAC")
        self.assertEqual(ins.matchup("BUF", 6, GAMES), "@ LV")
        self.assertEqual(ins.matchup("CIN", 6, GAMES), "BYE")

    def test_implied_totals(self):
        odds = [{"away_team_key": "LAC", "home_team_key": "KC", "over_under": "41.50",
                 "home_point_spread": "-7.50", "date": "2026-10-18 20:25:00", "status": "Scheduled"}]
        g = ins.vegas_games(odds, {"KC": {"summary": "Clear", "temperature": "62", "wind_speed": "10",
                                          "precip_probability": "0.2", "stadium_type": "Outdoor"}})[0]
        self.assertEqual(g["home_implied"], 24.5)  # 41.5/2 + 7.5/2
        self.assertEqual(g["away_implied"], 17.0)
        self.assertEqual(g["weather"]["precip_pct"], 20)
        self.assertFalse(g["weather"]["dome"])
        kc, lac = ins.team_vegas("KC", [g]), ins.team_vegas("LAC", [g])
        self.assertEqual((kc["spread"], kc["implied_total"]), (-7.5, 24.5))
        self.assertEqual((lac["spread"], lac["implied_total"]), (7.5, 17.0))
        self.assertIsNone(ins.team_vegas("CIN", [g])["spread"])


class TestStreamFinder(unittest.TestCase):
    ROWS = [
        {"team": "KC", "name": "Chiefs", "week_1_opponent": "DEN", "week_2_opponent": "IND",
         "week_1_fan_duel_quarterback_fantasy_points_allowed": "10.00",
         "week_2_fan_duel_quarterback_fantasy_points_allowed": "20.00"},
        {"team": "LAC", "name": "Chargers", "week_1_opponent": "ARI", "week_2_opponent": None,
         "week_1_fan_duel_quarterback_fantasy_points_allowed": "30.00"},
    ]

    def test_ranked_most_generous_first(self):
        out = ins.defense_vs_position(self.ROWS, "QB", through_week=2, upcoming=[6], games=GAMES, adjusted=False)
        self.assertEqual([r["team"] for r in out], ["LAC", "KC"])
        self.assertEqual(out[1]["avg_allowed"], 15.0)
        self.assertEqual(out[0]["games"], 1)  # the bye week doesn't count
        self.assertEqual(out[0]["upcoming"]["6"], "@KC")
        self.assertEqual(out[1]["upcoming"]["6"], "LAC")

    def test_schedule_adjusted_pae(self):
        # Defense X allowed 30 to offense A, which scores 30 against everyone
        # (PAE 0). Defense Y allowed 20 to offense B, which usually scores 10
        # (PAE +10). Raw FPA ranks X softer; PAE correctly ranks Y softer.
        rows = [
            {"team": "X", "week_1_opponent": "A", "week_1_fan_duel_quarterback_fantasy_points_allowed": "30"},
            {"team": "Y", "week_1_opponent": "B", "week_1_fan_duel_quarterback_fantasy_points_allowed": "20"},
            {"team": "Z", "week_1_opponent": "A", "week_1_fan_duel_quarterback_fantasy_points_allowed": "30"},
            {"team": "W", "week_1_opponent": "B", "week_1_fan_duel_quarterback_fantasy_points_allowed": "0"},
        ]
        raw = ins.defense_vs_position(rows, "QB", through_week=1, upcoming=[], games={}, adjusted=False)
        adj = ins.defense_vs_position(rows, "QB", through_week=1, upcoming=[], games={})
        self.assertIn(raw[0]["team"], ("X", "Z"))
        self.assertEqual(adj[0]["team"], "Y")
        self.assertEqual(adj[0]["pae"], 10.0)
        self.assertEqual(next(r for r in adj if r["team"] == "X")["pae"], 0.0)

    def test_completed_through(self):
        self.assertEqual(ins.completed_through(self.ROWS), 2)


class TestPositions(unittest.TestCase):
    def test_aliases(self):
        self.assertEqual(ins.normalize_position("dst", ("QB", "D")), "D")
        self.assertEqual(ins.normalize_position("DEF", ("QB", "D")), "D")
        self.assertIsNone(ins.normalize_position(None, ("QB",)))

    def test_invalid_exits(self):
        r = runner.invoke(app, ["weekly", "LB"])
        self.assertEqual(r.exit_code, 1)
        self.assertIn("Unknown position", r.output)


POOL = [
    {"name": "Ja'Marr Smith", "position": "WR", "team": "CIN", "points": 14.0, "rank": 8},
    {"name": "Puka Nacua", "position": "WR", "team": "LAR", "points": 17.6, "rank": 1},
    {"name": "Seattle Seahawks", "position": "DST", "team": "SEA", "points": 8.0, "rank": 6},
    {"name": "Kansas City Chiefs", "position": "DST", "team": "KC", "points": 10.7, "rank": 1},
]


class TestStartSitResolve(unittest.TestCase):
    def test_fuzzy_player(self):
        self.assertEqual(resolve("puka", POOL)[0]["name"], "Puka Nacua")

    def test_defense_by_team_code_nickname_city(self):
        for q in ("KC", "Chiefs", "chiefs dst", "Kansas City DST", "Kansas City Chiefs"):
            self.assertEqual(resolve(q, POOL)[0]["team"], "KC", q)

    def test_unrelated_name_never_lands_on_a_defense(self):
        # Regression: a player on bye used to fuzzy-match "Seattle Seahawks".
        self.assertEqual(resolve("Ja'Marr Chase", [p for p in POOL if p["position"] == "DST"]), (None, 0))

    def test_directory_finds_player_not_in_pool(self):
        directory = [{"name": "Ja'Marr Chase", "pos": "WR", "team": "CIN"},
                     {"name": "Puka Nacua", "pos": "WR", "team": "LAR"},
                     {"name": "Free Agent", "pos": "WR", "team": None}]
        other, score = directory_match("Ja'Marr Chase", directory, POOL)
        self.assertEqual(other["name"], "Ja'Marr Chase")
        self.assertGreater(score, resolve("Ja'Marr Chase", POOL)[1])
        # In-pool players and free agents are never directory matches.
        self.assertEqual(directory_match("Puka Nacua", directory, POOL), (None, 0))
        self.assertEqual(directory_match("Free Agent", directory, POOL), (None, 0))

    def test_unavailable_bye_vs_no_projection(self):
        self.assertEqual(unavailable({"name": "X", "pos": "WR", "team": "CIN"}, 6, GAMES)["verdict"], "BYE")
        self.assertEqual(unavailable({"name": "Y", "pos": "RB", "team": "KC"}, 6, GAMES)["verdict"], "NO PROJ")

    def test_is_exact(self):
        self.assertTrue(is_exact("puka nacua", POOL[1]))
        self.assertFalse(is_exact("puka", POOL[1]))

    def test_compare_orders_by_points(self):
        out = compare([POOL[0], POOL[1]], [])
        self.assertEqual([r["verdict"] for r in out], ["START", "SIT"])
        self.assertEqual(out[0]["name"], "Puka Nacua")


class TestDfs(unittest.TestCase):
    def test_site_scoring(self):
        line = {"receptions": 6, "receiving_yards": 80, "receiving_touchdowns": 1, "fumbles_lost": 1}
        self.assertAlmostEqual(dfs_points(line, "dk"), 6 + 8 + 6 - 1)
        self.assertAlmostEqual(dfs_points(line, "fd"), 3 + 8 + 6 - 2)

    def test_rows_join_salary_and_value(self):
        players = [{"player_id": "2", "name": "WR B", "fantasy_position": "WR", "team": "BUF",
                    "upcoming_draft_kings_salary": "4000", "upcoming_fan_duel_salary": "5500",
                    "upcoming_game_opponent": "LV", "upcoming_opponent_position_rank": "27"},
                   {"player_id": "9", "name": "No Proj", "fantasy_position": "WR",
                    "upcoming_draft_kings_salary": "3000"}]
        simple = [{"name": "Chiefs", "fantasy_position": "D", "team": "KC", "points": "10.0",
                   "upcoming_draft_kings_salary": "3600", "upcoming_game_opponent": "LAC"}]
        rows = dfs_rows(players, WEEKLY, simple, "dk")
        self.assertEqual([r["name"] for r in rows], ["WR B", "Chiefs"])
        wr = rows[0]
        self.assertEqual((wr["salary"], wr["points"], wr["opp_pos_rank"]), (4000, 12.0, 27))
        self.assertEqual(wr["value"], 3.0)
        self.assertEqual(rows[1]["position"], "DST")


class TestCurrentSeasonMerge(unittest.TestCase):
    def test_list_merge_replaces_same_season(self):
        udk = [{"season": "2025", "id": "old"}, {"season": "2026", "id": "stale"}]
        cur = [{"season": "2026", "id": "new"}]
        self.assertEqual([r["id"] for r in merge_current_season(udk, cur)], ["new", "old"])
        self.assertEqual(merge_current_season(udk, None), udk)

    def test_consistency_dict_merge(self):
        merged = _with_current_season({"2025": [1]}, [{"season": "2026"}])
        self.assertEqual(sorted(merged), ["2025", "2026"])
        self.assertEqual(_with_current_season({"2025": [1]}, None), {"2025": [1]})

    def test_min_games_scales_early_season(self):
        self.assertEqual(resolve_min_games(None, 6, 5), 3)
        self.assertEqual(resolve_min_games(None, 6, 17), 6)
        self.assertEqual(resolve_min_games(None, 4, 1), 1)
        self.assertEqual(resolve_min_games(2, 6, 17), 2)  # explicit flag wins


START_SIT_PAGE = ({
    "week": 6, "allGames": GAMES, "teams": {"KC": {}, "LAC": {}, "BUF": {}, "LV": {}, "CIN": {}},
    "vegas": [{"away_team_key": "BUF", "home_team_key": "LV", "over_under": "53.5",
               "home_point_spread": "4.5", "date": "2026-10-18 20:25:00", "status": "Scheduled"},
              {"away_team_key": "LAC", "home_team_key": "KC", "over_under": "41.5",
               "home_point_spread": "-7.5", "date": "2026-10-18 20:25:00", "status": "Scheduled"}],
    "weather": {}, "defenseRanks": [], "kickerRanks": [], "simpleProjections": [],
}, WEEKLY)


class TestInSeasonCommands(unittest.TestCase):
    def test_weekly_json(self):
        with patch("ffb.commands.weekly.load_page_data", return_value=START_SIT_PAGE):
            r = runner.invoke(app, ["weekly", "WR", "--json"])
        self.assertEqual(r.exit_code, 0, r.output)
        d = json.loads(r.stdout)
        self.assertEqual(d["week"], 6)
        self.assertEqual([p["name"] for p in d["players"]], ["WR A", "WR B", "Empty"])
        self.assertEqual(d["players"][0]["matchup"], "vs LAC")
        self.assertNotIn("_avg", d["players"][0])

    def test_start_sit_json(self):
        with patch("ffb.commands.startsit.load_page_data", return_value=START_SIT_PAGE):
            r = runner.invoke(app, ["start-sit", "WR A", "WR B", "--json"])
        self.assertEqual(r.exit_code, 0, r.output)
        d = json.loads(r.stdout)
        self.assertEqual(d["start"], "WR A")
        self.assertEqual(d["players"][0]["implied_total"], 24.5)
        self.assertEqual(d["players"][1]["spread"], -4.5)

    def test_start_sit_ambiguous_last_name(self):
        # Regression: "Jefferson" silently resolved to the in-pool Van Jefferson
        # while Justin Jefferson was on bye. A tie like that must ask.
        pool = POOL + [{"name": "Van Jefferson", "position": "WR", "team": "WAS", "points": 2.8, "rank": 152}]
        directory = [{"name": "Justin Jefferson", "pos": "WR", "team": "MIN"}]
        with patch("ffb.commands.startsit.build_pool", return_value=(6, pool, START_SIT_PAGE[0])), \
             patch("ffb.commands.startsit._fetch_player_data", return_value=directory):
            r = runner.invoke(app, ["start-sit", "Jefferson", "Puka Nacua"])
        self.assertEqual(r.exit_code, 1)
        self.assertIn("Justin Jefferson", r.output)

    def test_start_sit_offseason(self):
        empty = ({"week": 0}, [])
        with patch("ffb.commands.startsit.load_page_data", return_value=empty):
            r = runner.invoke(app, ["start-sit", "A", "B", "--json"])
        self.assertEqual(r.exit_code, 0)
        self.assertFalse(json.loads(r.stdout)["available"])

    def test_games_byes_from_schedule(self):
        with patch("ffb.commands.games.load_page_data", return_value=START_SIT_PAGE):
            r = runner.invoke(app, ["games", "-s", "total", "--json"])
        self.assertEqual(r.exit_code, 0, r.output)
        d = json.loads(r.stdout)
        self.assertEqual(d["byes"], ["CIN"])
        self.assertEqual(d["games"][0]["home"], "LV")  # higher total first


class TestAuthHandler(unittest.TestCase):
    def test_expired_session_is_one_line_not_a_traceback(self):
        def boom(*a, **k):
            raise AuthExpiredError("expired")
        err = io.StringIO()
        with patch("ffb.commands.weekly.load_page_data", side_effect=boom), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                app(["weekly"], standalone_mode=True)
        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(err.getvalue().strip(), "Session expired. Run `ffb login` to re-authenticate.")


if __name__ == "__main__":
    unittest.main()
