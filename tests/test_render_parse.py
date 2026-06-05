"""Expert-list pick parsing (no browser needed; tests the pure parser)."""
import unittest

from ffb.api.render import _parse_pick


class TestParsePick(unittest.TestCase):
    def test_full_pick(self):
        raw = {
            "heading": "Malik Willis, (QB) MIA",
            "blurb": "Current ADP: 8.10 Rushing upside makes him an intriguing QB2.",
        }
        p = _parse_pick(raw)
        self.assertEqual(p["name"], "Malik Willis")
        self.assertEqual(p["position"], "QB")
        self.assertEqual(p["team"], "MIA")
        self.assertEqual(p["adp"], "8.10")
        self.assertNotIn("Current ADP", p["blurb"])
        self.assertTrue(p["blurb"].startswith("Rushing upside"))

    def test_space_before_comma(self):
        p = _parse_pick({"heading": "Jeremiyah Love , (RB) ARI", "blurb": "No ADP here."})
        self.assertEqual(p["name"], "Jeremiyah Love")
        self.assertEqual(p["position"], "RB")
        self.assertEqual(p["team"], "ARI")
        self.assertIsNone(p["adp"])

    def test_non_pick_heading_ignored(self):
        self.assertIsNone(_parse_pick({"heading": "Our Expert Sleeper Picks", "blurb": "x"}))


if __name__ == "__main__":
    unittest.main()
