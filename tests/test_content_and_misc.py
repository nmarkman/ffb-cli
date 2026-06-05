"""Content parsers (free-agency snippets, rookie/article sections), the expert
list command (render patched), and the tools catalog command."""
import json
import unittest
from unittest.mock import patch

from typer.testing import CliRunner

from ffb.main import app
from ffb.api.dynasty_scrape import extract_ffb_snippets

runner = CliRunner()

SNIPPET_HTML = """
<div class="ffb-snippet">
  <div class="ffb-snippet--content">
    <h3>Daniel Jones</h3>
    <p>Daniel Jones Re-signed | 29 Years Old IND | 2 years, $88 million Danny Dimes returns to Indy and should provide late-round value.</p>
  </div>
</div>
<div class="ffb-snippet">
  <div class="ffb-snippet--content">
    <h3>Malik Willis</h3>
    <p>Malik Willis Signed | 27 Years Old MIA | 3 years, $67.5 million Rushing upside in Miami.</p>
  </div>
</div>
"""


class TestSnippets(unittest.TestCase):
    def test_extract(self):
        cards = extract_ffb_snippets(SNIPPET_HTML)
        names = [c["name"] for c in cards]
        self.assertIn("Daniel Jones", names)
        self.assertIn("Malik Willis", names)


# The real page yields snippets where name=player, meta=analysis blurb, and
# content opens with the move header then repeats the blurb. We patch
# extract_ffb_snippets to that shape so we test the command's header/blurb split.
REAL_SNIPPETS = [
    {"name": "Daniel Jones",
     "meta": "Danny Dimes returns to Indy and should provide late-round value.",
     "content": "Daniel Jones Re-signed | 29 Years Old IND | 2 years, $88 million "
                "Danny Dimes returns to Indy and should provide late-round value."},
    {"name": "Malik Willis",
     "meta": "Rushing upside in Miami.",
     "content": "Malik Willis Signed | 27 Years Old MIA | 3 years, $67.5 million Rushing upside in Miami."},
]


class TestFreeAgency(unittest.TestCase):
    def _invoke(self, args):
        with patch("ffb.commands.free_agency.fetch_page", return_value=""), \
             patch("ffb.commands.free_agency.extract_ffb_snippets", return_value=REAL_SNIPPETS):
            return runner.invoke(app, args)

    def test_move_and_blurb_split(self):
        r = self._invoke(["free-agency", "--json"])
        self.assertEqual(r.exit_code, 0)
        d = json.loads(r.stdout)
        jones = next(x for x in d if x["name"] == "Daniel Jones")
        self.assertIn("Re-signed", jones["move"])
        self.assertIn("IND", jones["move"])
        self.assertNotIn("Re-signed", jones["blurb"])  # move header stripped from blurb

    def test_name_filter(self):
        r = self._invoke(["free-agency", "willis", "--json"])
        d = json.loads(r.stdout)
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0]["name"], "Malik Willis")


ROOKIE_HTML = """
<main>
<h2>Fernando Mendoza , (QB) LV</h2><p>Strong arm and poise; a Day 2 dynasty stash with upside.</p>
<h2>Carnell Tate , (WR) TEN</h2><p>Polished route runner who should see early targets in Tennessee.</p>
<h2>Not A Player Heading</h2><p>This should be ignored because the heading is not a player line.</p>
</main>
"""


class TestRookieReport(unittest.TestCase):
    def test_player_sections_only(self):
        with patch("ffb.commands._scrape.fetch_page", return_value=ROOKIE_HTML):
            r = runner.invoke(app, ["rookie-report", "--json"])
        self.assertEqual(r.exit_code, 0)
        d = json.loads(r.stdout)
        names = [x["name"] for x in d]
        self.assertIn("Fernando Mendoza", names)
        self.assertNotIn("Not A Player Heading", names)
        self.assertTrue(all(x["position"] in {"QB", "WR"} for x in d))

    def test_position_filter(self):
        with patch("ffb.commands._scrape.fetch_page", return_value=ROOKIE_HTML):
            r = runner.invoke(app, ["rookie-report", "WR", "--json"])
        d = json.loads(r.stdout)
        self.assertEqual([x["name"] for x in d], ["Carnell Tate"])


COACHING_HTML = """
<main>
<p>Latest Episodes Subscribe DFS &amp; Betting</p>
<p>The younger LaFleur brother comes to the desert after years in the McVay and Shanahan systems, and should lift the Cardinals passing game in a meaningful way this season.</p>
<p>The former two-time Coach of the Year finds a new home in Atlanta and brings a defensive identity that could reshape the roster over the next two seasons of competition.</p>
</main>
"""


class TestCoachingChanges(unittest.TestCase):
    def test_drops_chrome_keeps_prose(self):
        with patch("ffb.commands._scrape.fetch_page", return_value=COACHING_HTML):
            r = runner.invoke(app, ["coaching-changes", "--json"])
        d = json.loads(r.stdout)
        self.assertEqual(len(d), 2)  # the chrome paragraph is dropped
        self.assertTrue(all("Episodes" not in p for p in d))


class TestExperts(unittest.TestCase):
    PICKS = [
        {"name": "Malik Willis", "position": "QB", "team": "MIA", "adp": "8.10", "blurb": "Upside."},
        {"name": "Rico Dowdle", "position": "RB", "team": "PIT", "adp": "9.10", "blurb": "Volume."},
    ]

    def test_position_filter(self):
        with patch("ffb.commands.experts.render_expert_picks", return_value=self.PICKS), \
             patch("ffb.commands.experts.get_cached", return_value=None), \
             patch("ffb.commands.experts.set_cached"):
            r = runner.invoke(app, ["experts", "sleepers", "RB", "--json"])
        self.assertEqual(r.exit_code, 0)
        d = json.loads(r.stdout)
        self.assertEqual([p["name"] for p in d], ["Rico Dowdle"])

    def test_unknown_list_rejected(self):
        r = runner.invoke(app, ["experts", "bogus"])
        self.assertNotEqual(r.exit_code, 0)


class TestToolsCommand(unittest.TestCase):
    def test_free_filter(self):
        r = runner.invoke(app, ["tools", "--tier", "free", "--json"])
        d = json.loads(r.stdout)
        self.assertTrue(all(x["tier"] == "free" for x in d))
        self.assertTrue(d)

    def test_covered_and_missing_disjoint(self):
        cov = json.loads(runner.invoke(app, ["tools", "--covered", "--json"]).stdout)
        mis = json.loads(runner.invoke(app, ["tools", "--missing", "--json"]).stdout)
        self.assertTrue(all(x["command"] for x in cov))
        self.assertTrue(all(not x["command"] for x in mis))


if __name__ == "__main__":
    unittest.main()
