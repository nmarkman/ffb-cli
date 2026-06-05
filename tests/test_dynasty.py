"""Dynasty numeric core (per-analyst averaging + scoring) shared by the dynasty
rankings/startup/rookies commands, plus the self-contained felix command path."""
import json
import unittest
from unittest.mock import patch

from typer.testing import CliRunner

from ffb.main import app
from ffb.commands.dynasty._common import project_average, calc_points

runner = CliRunner()


class TestCalcPoints(unittest.TestCase):
    def test_half_ppr(self):
        proj = {"receptions": 100, "receiving_yards": 1300, "receiving_touchdowns": 10}
        self.assertAlmostEqual(calc_points(proj, "HALF"), 240.0)

    def test_ppr(self):
        proj = {"receptions": 100, "receiving_yards": 1300, "receiving_touchdowns": 10}
        self.assertAlmostEqual(calc_points(proj, "PPR"), 290.0)


class TestProjectAverage(unittest.TestCase):
    def test_averages_across_analysts(self):
        projections = [
            {"player_id": "1", "analyst_id": "1", "name": "WR One", "fantasy_position": "WR",
             "team": "KC", "bye_week": "7", "receptions": "100", "receiving_yards": "1200"},
            {"player_id": "1", "analyst_id": "2", "name": "WR One", "fantasy_position": "WR",
             "team": "KC", "bye_week": "7", "receptions": "120", "receiving_yards": "1400"},
        ]
        out = project_average(projections)
        self.assertEqual(len(out), 1)
        row = out[0]
        self.assertEqual(row["analysts"], 2)
        self.assertEqual(row["player_name"], "WR One")
        self.assertAlmostEqual(row["receptions"], 110.0)       # (100+120)/2
        self.assertAlmostEqual(row["receiving_yards"], 1300.0)  # (1200+1400)/2

    def test_analyst_filter(self):
        projections = [
            {"player_id": "1", "analyst_id": "1", "name": "A", "fantasy_position": "RB", "receptions": "10"},
            {"player_id": "1", "analyst_id": "2", "name": "A", "fantasy_position": "RB", "receptions": "30"},
        ]
        out = project_average(projections, analyst_filter="andy")  # analyst_id 1
        self.assertEqual(out[0]["receptions"], 10.0)
        self.assertEqual(out[0]["analysts"], 1)


FELIX_HTML = """
<script>
const data = [
  {"name": "Rook A", "fantasy_position": "WR", "team": "KC", "experience": "1", "felix_score": "85.5", "felix_percentile": "0.9", "felix_peak": "95", "felix_reliability": "80"},
  {"name": "Rook B", "fantasy_position": "RB", "team": "SF", "experience": "2", "felix_score": "60.0", "felix_percentile": "0.6", "felix_peak": "70", "felix_reliability": "55"},
  {"name": "Rook C", "fantasy_position": "WR", "team": "CIN", "experience": "1", "felix_score": "72.0", "felix_percentile": "0.7", "felix_peak": "80", "felix_reliability": "65"}
];
</script>
"""


class TestFelixCommand(unittest.TestCase):
    def _run(self, args):
        with patch("ffb.commands.dynasty.felix.fetch_dynasty_page", return_value=FELIX_HTML):
            return runner.invoke(app, args)

    def test_sorted_by_score_desc(self):
        r = self._run(["dynasty", "felix", "--json"])
        self.assertEqual(r.exit_code, 0)
        d = json.loads(r.stdout)
        self.assertEqual([x["name"] for x in d], ["Rook A", "Rook C", "Rook B"])
        self.assertEqual([x["rank"] for x in d], [1, 2, 3])

    def test_position_filter(self):
        r = self._run(["dynasty", "felix", "WR", "--json"])
        d = json.loads(r.stdout)
        self.assertTrue(all(x["fantasy_position"] == "WR" for x in d))

    def test_min_score(self):
        r = self._run(["dynasty", "felix", "--min", "70", "--json"])
        d = json.loads(r.stdout)
        self.assertTrue(all(x["felix_score"] >= 70 for x in d))


if __name__ == "__main__":
    unittest.main()
