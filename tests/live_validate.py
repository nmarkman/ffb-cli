"""Live data-accuracy validation harness for the whole ffb CLI.

Runs every command via `ffb ... --json` and asserts data invariants. Dev tool
(needs auth + network), not part of the committed suite. Prints OK/SOFT/FAIL.
"""
import json
import subprocess
import sys

FFB = sys.argv[1] if len(sys.argv) > 1 else "ffb"
results = []


def run(args, timeout=120):
    p = subprocess.run([FFB, *args], capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


# ---- invariant helpers ----
def seq_ranks(rows, key="rank"):
    ranks = [r.get(key) for r in rows if r.get(key) is not None]
    assert ranks == list(range(1, len(ranks) + 1)), f"ranks not 1..n: {ranks[:5]}"


def all_pos(rows, pos, key="position"):
    bad = [r.get(key) for r in rows if (r.get(key) or "").upper() != pos]
    assert not bad, f"non-{pos}: {bad[:3]}"


def in_pos(rows, allowed, key="position"):
    bad = [r.get(key) for r in rows if (r.get(key) or "").upper() not in allowed]
    assert not bad, f"pos not in {allowed}: {bad[:3]}"


def has(rows, *keys):
    for k in keys:
        assert all(k in r for r in rows), f"missing key {k}"


def share_range(rows, keys):
    for r in rows:
        for k in keys:
            v = r.get(k)
            if v is None:
                continue
            assert 0 <= v <= 1.0001, f"{k}={v} out of [0,1]"


def check(name, args, validate, *, allow_empty=False, soft=False):
    try:
        rc, out, err = run(args)
    except subprocess.TimeoutExpired:
        results.append((name, "FAIL", "timeout")); return
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        status = "SOFT" if soft else "FAIL"
        results.append((name, status, f"non-JSON rc={rc}: {(err or out).strip()[:80]}")); return
    if not data and not allow_empty:
        results.append((name, "SOFT" if soft else "FAIL", "empty result")); return
    try:
        results.append((name, "OK", validate(data) or "ok"))
    except AssertionError as e:
        results.append((name, "FAIL", f"invariant: {e}"))
    except Exception as e:
        results.append((name, "FAIL", f"{type(e).__name__}: {e}"))


CHECKS = [
    # Public
    ("players search", ["players", "search", "mahomes", "--json"],
     lambda d: (has(d, "name"), f"{len(d)} results")[-1]),
    ("news", ["news", "-n", "3", "--json"],
     lambda d: (has(d, "title", "link"), f"{len(d)} articles")[-1]),
    # Rankings family
    ("rankings QB", ["rankings", "QB", "-n", "5", "--json"],
     lambda d: (seq_ranks(d), all_pos(d, "QB"), has(d, "points"), f"{len(d)} QBs")[-1]),
    ("rankings RB ppr", ["rankings", "RB", "-s", "ppr", "-n", "5", "--json"],
     lambda d: (all_pos(d, "RB"), "ppr")[-1]),
    ("rankings --enrich", ["rankings", "WR", "--enrich", "-n", "5", "--json"],
     lambda d: (has(d, "risk", "upside", "blurb"), "enriched")[-1]),
    ("rankings --tier 1", ["rankings", "RB", "--tier", "1", "--json"],
     lambda d: (all(r.get("tier") == 1 for r in d), "tier1")[-1]),
    ("projections RB", ["projections", "RB", "-n", "5", "--json"],
     lambda d: (all_pos(d, "RB"), has(d, "pass_yds", "rec_yds"), "stats")[-1]),
    ("top200", ["top200", "-n", "10", "--json"],
     lambda d: (seq_ranks(d), f"{len(d)} ranked")[-1]),
    ("superflex", ["superflex", "-n", "10", "--json"], lambda d: f"{len(d)} rows"),
    ("flex", ["flex", "-n", "10", "--json"],
     lambda d: (in_pos(d, {"RB", "WR", "TE"}), "flex pos")[-1]),
    # Trade / startsit (seasonal / fuzzy)
    ("trade", ["trade", "--give", "Travis Kelce", "--get", "Trey McBride", "--json"],
     lambda d: ("give_total" in d and "get_total" in d, "trade")[-1], ),
    ("start-sit", ["start-sit", "Ja'Marr Chase", "CeeDee Lamb", "--json"], lambda d: "ok"),
    # UDK research (existing)
    ("bye-weeks", ["bye-weeks", "--json"],
     lambda d: (len(d) >= 30 and all(r.get("bye_week") for r in d), f"{len(d)} teams")[-1]),
    ("bye-weeks -w 8", ["bye-weeks", "-w", "8", "--json"],
     lambda d: (all(str(r.get("bye_week")) == "8" for r in d), "wk8")[-1]),
    ("sos", ["sos", "--json"], lambda d: f"{len(d)} teams"),
    ("sos WR", ["sos", "WR", "--json"], lambda d: f"{len(d)} teams"),
    ("red-zone", ["red-zone", "-n", "10", "--json"], lambda d: (seq_ranks(d), "ranked")[-1]),
    ("best-ball", ["best-ball", "-n", "10", "--json"], lambda d: f"{len(d)} rows"),
    # New UDK tools
    ("value-scout", ["value-scout", "-n", "10", "--json"],
     lambda d: (seq_ranks(d), has(d, "adp"), "adp")[-1]),
    ("value-scout 2qb", ["value-scout", "QB", "-s", "2qb", "-n", "5", "--json"],
     lambda d: (all_pos(d, "QB", "fantasy_position"), "qb")[-1]),
    ("market-share WR", ["market-share", "WR", "-n", "10", "--json"],
     lambda d: (seq_ranks(d), share_range(d, ["target_share", "rush_share", "rec_yd_share", "points_share"]),
                all_pos(d, "WR", "fantasy_position"), "shares")[-1]),
    ("target-share", ["target-share", "--json"],
     lambda d: (seq_ranks(d), share_range(d, ["wr_share", "rb_share", "te_share"]), "splits")[-1]),
    ("consistency RB", ["consistency", "RB", "-n", "10", "--json"],
     lambda d: (seq_ranks(d), share_range(d, ["start_pct", "boom_pct", "bust_pct"]),
                all_pos(d, "RB", "fantasy_position"), "rates")[-1]),
    ("consistency weekly", ["consistency", "-w", "Josh Allen", "--json"],
     lambda d: (len(d["weeks"]) > 8, "log")[-1]),
    ("free-agency", ["free-agency", "-n", "5", "--json"],
     lambda d: (all(r.get("name") for r in d), f"{len(d)} moves")[-1]),
    ("coaching-changes", ["coaching-changes", "--json"],
     lambda d: (len(d) >= 5, f"{len(d)} paras")[-1]),
    ("rookie-report WR", ["rookie-report", "WR", "-n", "5", "--json"],
     lambda d: (all_pos(d, "WR"), f"{len(d)} rookies")[-1]),
    ("experts sleepers", ["experts", "sleepers", "--json"],
     lambda d: (all(r.get("name") and r.get("position") for r in d), f"{len(d)} picks")[-1]),
    ("tools", ["tools", "--json"], lambda d: (len(d) >= 40, f"{len(d)} tools")[-1]),
    # Dynasty
    ("dyn rankings", ["dynasty", "rankings", "-n", "5", "--json"], lambda d: f"{len(d)} rows"),
    ("dyn startup", ["dynasty", "startup", "-n", "5", "--json"], lambda d: f"{len(d)} rows"),
    ("dyn rookies", ["dynasty", "rookies", "-n", "5", "--json"], lambda d: f"{len(d)} rows"),
    ("dyn rookie-overview", ["dynasty", "rookie-overview", "--json"], lambda d: f"{len(d)} sections"),
    ("dyn production", ["dynasty", "production", "Bijan", "--json"], lambda d: "ok"),
    ("dyn trade", ["dynasty", "trade", "--give", "Mahomes", "--get", "Daniels", "--json"], lambda d: "ok"),
    ("dyn trade-targets", ["dynasty", "trade-targets", "--json"], lambda d: f"{len(d)} items"),
    ("dyn team-opportunity", ["dynasty", "team-opportunity", "--json"], lambda d: f"{len(d)} rows"),
    ("dyn movers", ["dynasty", "movers", "--json"], lambda d: f"{len(d)} items"),
    ("dyn mock", ["dynasty", "mock", "--json"], lambda d: f"{len(d)} items"),
    ("dyn scouting", ["dynasty", "scouting", "--json"], lambda d: f"{len(d)} items"),
    ("dyn free-agents", ["dynasty", "free-agents", "--json"], lambda d: f"{len(d)} items"),
    ("dyn injuries", ["dynasty", "injuries", "--json"], lambda d: f"{len(d)} items"),
    ("dyn draft-results", ["dynasty", "draft-results", "--json"], lambda d: f"{len(d)} items"),
    ("dyn tips", ["dynasty", "tips", "--json"], lambda d: f"{len(d)} items"),
    ("dyn lifecycles", ["dynasty", "lifecycles", "--json"], lambda d: f"{len(d)} items"),
    ("dyn felix", ["dynasty", "felix", "-n", "5", "--json"], lambda d: f"{len(d)} rows"),
]

# Commands that may legitimately be empty/seasonal -> soft-fail
SOFT = {"trade", "start-sit", "dyn production", "dyn trade", "dyn scouting", "bye-weeks -w 8"}

for name, args, validate in CHECKS:
    check(name, args, validate, soft=(name in SOFT), allow_empty=(name in SOFT))

width = max(len(n) for n, _, _ in results)
ok = sum(1 for _, s, _ in results if s == "OK")
soft = sum(1 for _, s, _ in results if s == "SOFT")
fail = sum(1 for _, s, _ in results if s == "FAIL")
for name, status, msg in results:
    mark = {"OK": "OK  ", "SOFT": "soft", "FAIL": "FAIL"}[status]
    print(f"[{mark}] {name.ljust(width)}  {msg}")
print(f"\n{ok} OK, {soft} soft, {fail} FAIL  (of {len(results)})")
sys.exit(1 if fail else 0)
