"""Pure HTML/JSON parsing helpers used by the new UDK scrapers."""
import unittest

from ffb.api.dynasty_scrape import (
    extract_const_assignment,
    extract_headings_with_content,
    extract_player_cards,
    extract_post_grid,
    extract_dynasty_table,
    strip_html_tags,
)
from ffb.commands._scrape import to_float, to_int, _PLAYER_HEADING_RE, _ARTICLE_NOISE


class TestConstAssignment(unittest.TestCase):
    def test_list_payload(self):
        html = "<script>const data = [{\"a\": 1}, {\"a\": 2}];</script>"
        self.assertEqual(extract_const_assignment(html, "data"), [{"a": 1}, {"a": 2}])

    def test_season_keyed_dict_payload(self):
        html = 'const data = {"2025": [{"x": 1}], "2024": []};'
        out = extract_const_assignment(html, "data")
        self.assertEqual(set(out), {"2025", "2024"})
        self.assertEqual(out["2025"], [{"x": 1}])


class TestHeadings(unittest.TestCase):
    def test_extract_sections(self):
        html = "<h2>Fernando Mendoza , (QB) LV</h2><p>Strong arm.</p><h2>Next</h2><p>More.</p>"
        out = extract_headings_with_content(html, (2,))
        self.assertEqual(out[0]["heading"], "Fernando Mendoza , (QB) LV")
        self.assertIn("Strong arm", out[0]["body"])


class TestPlayerHeadingRegex(unittest.TestCase):
    def test_matches(self):
        m = _PLAYER_HEADING_RE.match("Carnell Tate , (WR) TEN")
        self.assertEqual(m.group(1).strip(), "Carnell Tate")
        self.assertEqual(m.group(2), "WR")
        self.assertEqual(m.group(3), "TEN")

    def test_non_match(self):
        self.assertIsNone(_PLAYER_HEADING_RE.match("Just A Heading"))


class TestNoiseFilter(unittest.TestCase):
    def test_drops_chrome(self):
        self.assertTrue(_ARTICLE_NOISE.search("Latest Episodes"))
        self.assertTrue(_ARTICLE_NOISE.search("Subscribe"))
        self.assertFalse(_ARTICLE_NOISE.search("Fernando Mendoza"))


class TestPlayerCards(unittest.TestCase):
    # Blurb uses the `player-blurb` alias so its class doesn't prefix-collide with
    # the card-start selector (which keys on `ffb-news--grid--player`).
    HTML = """
    <div class="ffb-news--grid--player">
      <h3 class="ffb-news--grid--player--name"><a href="/player/jamarr-chase/">Ja'Marr Chase</a></h3>
      <span class="ffb-news--grid--player--position">WR</span>
      <span class="ffb-news--grid--player--team">CIN</span>
      <div class="player-blurb">Elite target hog.</div>
    </div>
    <div class="ffb-news--grid--player">
      <h3 class="ffb-news--grid--player--name"><a href="/player/bijan-robinson/">Bijan Robinson</a></h3>
      <span class="ffb-news--grid--player--position">RB</span>
      <span class="ffb-news--grid--player--team">ATL</span>
      <div class="player-blurb">Workhorse back.</div>
    </div>
    """

    def test_extract(self):
        cards = extract_player_cards(self.HTML)
        self.assertEqual([c["name"] for c in cards], ["Ja'Marr Chase", "Bijan Robinson"])
        self.assertEqual(cards[0]["position"], "WR")
        self.assertEqual(cards[0]["team"], "CIN")
        self.assertEqual(cards[0]["link"], "/player/jamarr-chase/")
        self.assertIn("target", cards[0]["blurb"])


class TestPostGrid(unittest.TestCase):
    HTML = """
    <article class="ffb-post-grid--post">
      <h2><a href="/x/1/">Lifecycle of a WR</a></h2>
      <div class="excerpt">How receivers age.</div>
    </article>
    """

    def test_extract(self):
        cards = extract_post_grid(self.HTML)
        self.assertEqual(cards[0]["title"], "Lifecycle of a WR")
        self.assertEqual(cards[0]["link"], "/x/1/")
        self.assertIn("age", cards[0]["excerpt"])


class TestDynastyTable(unittest.TestCase):
    HTML = """
    <tr class="ffb-data--row"><td>1.01</td><td>Travis Hunter</td><td>WR</td></tr>
    <tr class="ffb-data--row"><td>1.02</td><td>Abdul Carter</td><td>EDGE</td></tr>
    """

    def test_extract_rows(self):
        rows = extract_dynasty_table(self.HTML)
        self.assertEqual(len(rows), 2)
        self.assertIn("Travis Hunter", rows[0]["cells"])


class TestCoercion(unittest.TestCase):
    def test_to_float(self):
        self.assertEqual(to_float("12.00"), 12.0)
        self.assertEqual(to_float(None), 0.0)
        self.assertEqual(to_float("", 1.0), 1.0)

    def test_to_int(self):
        self.assertEqual(to_int("17.0"), 17)
        self.assertEqual(to_int(""), 0)

    def test_strip_tags(self):
        self.assertEqual(strip_html_tags("<b>Hi</b> &amp; bye"), "Hi & bye")


if __name__ == "__main__":
    unittest.main()
