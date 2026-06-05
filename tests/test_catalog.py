"""Catalog integrity: every entry is well-formed and coverage counts agree."""
import unittest

from ffb.catalog import CATALOG, covered, uncovered, coverage_summary

VALID_TIERS = {"free", "UDK", "UDK+", "DFS Pass", "FootClan"}
REQUIRED_KEYS = {"category", "tool", "tier", "command", "summary"}


class TestCatalog(unittest.TestCase):
    def test_entries_well_formed(self):
        for e in CATALOG:
            self.assertEqual(REQUIRED_KEYS, set(e), f"bad keys in {e}")
            self.assertIn(e["tier"], VALID_TIERS, f"bad tier in {e}")
            self.assertTrue(e["tool"] and e["summary"], f"empty field in {e}")

    def test_covered_uncovered_partition(self):
        self.assertEqual(len(covered()) + len(uncovered()), len(CATALOG))
        self.assertTrue(all(e["command"] for e in covered()))
        self.assertTrue(all(not e["command"] for e in uncovered()))

    def test_coverage_summary(self):
        n_cov, n_total = coverage_summary()
        self.assertEqual(n_total, len(CATALOG))
        self.assertEqual(n_cov, len(covered()))
        self.assertGreater(n_cov, 0)

    def test_free_tier_present(self):
        free = [e for e in CATALOG if e["tier"] == "free"]
        self.assertTrue(any("players" in (e["command"] or "") for e in free))
        self.assertTrue(any("news" in (e["command"] or "") for e in free))

    def test_commands_start_with_ffb(self):
        for e in covered():
            self.assertTrue(e["command"].startswith("ffb "), e["command"])


if __name__ == "__main__":
    unittest.main()
