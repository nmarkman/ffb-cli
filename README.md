# ffb-cli

CLI tool for [The Fantasy Footballers](https://www.thefantasyfootballers.com/) premium tools and public features.

Access rankings, projections, the trade analyzer, start/sit comparisons, the full UDK research suite (market share, target breakdown, value scout, consistency, expert lists, and more), the dynasty toolkit, player search, and news, all from your terminal. Crafted intentionally for both human and AI agent use (assuming your agent has access to your Fantasy Footballers user/pw)

## What's free vs. paywalled

The Footballers gate almost everything behind a purchase. Only **player search** and **news** work without an account. Everything else needs one of:

- **UDK** (Ultimate Draft Kit): the redraft draft-prep suite (rankings, projections, value scout, market share, target breakdown, consistency, expert lists, red zone, SoS, bye weeks, free agency, coaching changes, rookie report).
- **UDK+** (Dynasty Pass): the dynasty toolkit (`ffb dynasty ...`).
- **DFS Pass**: best ball.
- **FootClan**: in-season tools (trade analyzer, start/sit).

Run `ffb tools` for the full map of every tool, its tier, and the CLI command that covers it:

```bash
ffb tools                  # full catalog with coverage
ffb tools --tier free      # what works without an account
ffb tools --covered        # everything the CLI exposes
ffb tools --missing        # tools not (yet) wrapped
```

## Requirements

- Python 3.12+
- A Fantasy Footballers premium account (for rankings, projections, trade, start-sit)

## Installation

```bash
# Clone the repo
git clone https://github.com/nmarkman/ffb-cli.git
cd ffb-cli

# Create a virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Install Playwright's Chromium (needed for login only)
python -m playwright install chromium
```

Or install directly with pipx (no venv management needed):

```bash
pipx install git+https://github.com/nmarkman/ffb-cli.git
# Then install Playwright's Chromium
pipx runpip ffb-cli playwright install chromium
```

## Authentication

Most commands require a premium Fantasy Footballers account. Run `ffb login` to authenticate:

```bash
ffb login
```

This opens a Chromium browser window. Log in with your account, and the CLI captures your session automatically. Sessions last ~24 hours. When expired, just run `ffb login` again.

```bash
ffb login --status   # check if your session is valid
ffb login --logout   # clear your saved session
```

Session data is stored at `~/.config/ffb/session.json`.

### Headless Login (for AI Agents / CI)

If you're running in a headless environment (AI agents, SSH sessions, CI pipelines), use `--headless` to log in without a browser window:

```bash
# With flags
ffb login --headless -u me@email.com -p mypassword

# With environment variables
export FFB_USERNAME=me@email.com
export FFB_PASSWORD=mypassword
ffb login --headless
```

This performs the same browser-based authentication under the hood (headless Chromium), so it captures identical session cookies and API tokens. The session file is the same: once logged in, all commands work exactly the same way regardless of how you authenticated.

## Commands

### Player Search (no login required)

```bash
ffb players search "mahomes"              # fuzzy name search
ffb players search "jefferson" -p WR      # filter by position
ffb players search "smith" -t KC -n 5     # filter by team, limit results
```

After results appear, use arrow keys to select a player and view their info card with recent news.

### Rankings (login required)

```bash
ffb rankings                     # all positions, half-PPR
ffb rankings QB -s ppr -n 10     # top 10 QBs, PPR scoring
ffb rankings RB --tier 1         # tier 1 RBs only
```

Scoring formats: `half` (default), `ppr`, `standard`

### Projections (login required)

```bash
ffb projections QB               # QB stat projections
ffb projections RB -s ppr -n 15  # top 15 RB projections, PPR
```

### Trade Analyzer (login required)

```bash
ffb trade --give "Kelce, Lamb" --get "Chase"   # CLI mode
ffb trade                                       # interactive mode (prompts for players)
```

### Start/Sit (login required, in-season only)

```bash
ffb start-sit "Ja'Marr Chase" "CeeDee Lamb"
ffb start-sit "Josh Allen" "Jalen Hurts" "Lamar Jackson"
```

This tool is only available during the NFL season.

### News (no login required)

```bash
ffb news           # latest 10 articles
ffb news -n 5      # latest 5 articles
```

### Draft-board variants (login required)

```bash
ffb top200                       # overall top 200, half-PPR
ffb top200 -s ppr -n 100         # PPR, top 100
ffb superflex                    # 2QB / superflex board, 1.30x QB boost by default
ffb superflex --qb-boost 1.5     # heavier QB premium
ffb flex                         # RB/WR/TE only, top 50
```

### Research tools (login required)

```bash
ffb bye-weeks                    # all 32 teams, sorted by bye week
ffb bye-weeks -w 8               # only teams on bye in week 8
ffb bye-weeks -t KC              # one team

ffb sos                          # team SoS grid, all positions
ffb sos WR                       # sorted by easiest WR schedule
ffb sos QB --hard                # toughest QB schedules first
ffb sos -t KC                    # one team's full SoS row

ffb red-zone                     # top 25 by RZ touches (last season)
ffb red-zone RB -n 30            # top 30 RBs
ffb red-zone WR -s rec_targets   # WRs by RZ targets
ffb red-zone QB -s pass_tds      # QBs by RZ pass TDs
```

### UDK research suite (login required)

```bash
ffb value-scout                  # ADP across redraft / PPR / 2QB / dynasty
ffb value-scout QB -s 2qb        # QBs by SuperFlex ADP

ffb market-share WR              # WR share of team targets/yards/points
ffb market-share -t KC           # Chiefs usage shares
ffb market-share RB -s rush      # RBs by rushing-attempt share

ffb target-share -s te           # teams that funnel targets to TEs
ffb target-share KC              # one team's WR/RB/TE target split

ffb consistency RB -s boom       # RB boom-rate leaders
ffb consistency WR --ppr         # WRs, PPR start-worthy rates
ffb consistency -w "Josh Allen"  # one player's week-by-week game log

ffb free-agency                  # offseason signings + fantasy analysis
ffb coaching-changes             # fantasy impact of coaching moves
ffb rookie-report WR             # rookie scouting writeups

ffb experts sleepers             # the Footballers' sleeper picks
ffb experts breakouts RB         # RB breakouts
ffb experts busts                # players to avoid
```

The expert lists render in a headless browser (they have no inline data), so the
first run is a few seconds slower; results are then cached for an hour.

### Enriched rankings (login required)

`rankings`, `top200`, and `projections` accept `--enrich` to pull the richer UDK
global dataset, adding each player's analyst **risk** (1-10, lower is safer),
**upside** (1-10), projected **targets**, and (in `--json`) the player **blurb**:

```bash
ffb rankings WR --enrich         # adds Risk / Upside / Tgts columns
ffb top200 --enrich -n 50        # enriched overall board
ffb projections QB --enrich --json   # risk/upside/targets/blurb in JSON
```

### DFS Pass (login required)

```bash
ffb best-ball                    # top 50 by Underdog ADP
ffb best-ball WR -n 30           # top 30 WR best-ball values
ffb best-ball -t KC              # all KC players
```

### Dynasty (login required, UDK+)

The full dynasty toolkit lives under `ffb dynasty`. Run `ffb dynasty --help` for
everything (rankings, startup, rookies, production profiles, team opportunity,
trade analyzer/targets, scouting, free agents, injuries, draft results, tips,
lifecycles, FELIX, and the rookie class overview).

```bash
ffb dynasty felix                # top 30 overall FELIX scores
ffb dynasty felix WR -n 50       # top 50 WRs by FELIX
ffb dynasty rookie-overview      # narrative outlook on the rookie class
```

## JSON Output

Every command supports `--json` for machine-readable output (including error
states like the offseason start/sit tool, which returns `{"available": false}`).
This is the recommended surface for AI agents:

```bash
ffb rankings QB -n 5 --json
ffb players search "mahomes" --json
ffb consistency RB --json
ffb tools --json                 # the full tool/coverage map as data
```

Conventions an agent can rely on across commands:
- Position filter is a positional argument (`ffb rankings QB`); valid values are QB, RB, WR, TE (plus K, DST where applicable).
- `-n/--limit` caps results, `-s/--sort` picks a sort key, `-t/--team` filters by team, `-y/--season` picks a season.
- Invalid `--scoring` or `--sort` values exit non-zero with the list of valid values (no silent fallback).
- Commands that require login fail with a clear "Run `ffb login`" message, never a stack trace.

## Project Structure

```
src/ffb/
├── main.py              # CLI entry point + command registration
├── config.py            # Paths, constants, scoring formats
├── catalog.py           # Tool catalog (powers `ffb tools`): tiers + CLI coverage
├── auth/
│   ├── login.py         # Playwright browser login flow
│   └── session.py       # Session persistence (~/.config/ffb/)
├── api/
│   ├── client.py        # HTTP client with cookie/nonce auth
│   ├── endpoints.py     # API + page-path constants
│   ├── dynasty_scrape.py# Inline-JS / DOM extraction helpers
│   ├── udk_global.py    # window.udk.data loader + enrichment index
│   └── render.py        # Headless render (expert lists) via saved session
├── commands/            # One file per command (+ commands/dynasty/)
├── cache/
│   └── store.py         # File-based JSON cache with TTL
└── display/
    └── tables.py        # Rich table formatters
```

## Testing

The suite runs on the Python standard library (no pytest or other dev deps):

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

It covers the parse/transform logic of every command family (scoring math,
tiering, share aggregations, consistency rates, trade normalization, dynasty
averaging, player search, the catalog, and the scrapers) using fixtures, so it
runs offline with no login required.

`tests/live_validate.py` is a separate, login-required smoke harness that runs
every command against the live site and asserts data invariants (shares in
[0,1], sequential ranks, valid positions, well-formed JSON). It is not part of
the offline suite. Run it after logging in:

```bash
ffb login
python tests/live_validate.py "$(which ffb)"
```
