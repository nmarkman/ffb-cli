# ffb-cli

CLI tool for [The Fantasy Footballers](https://www.thefantasyfootballers.com/) premium tools and public features.

Access rankings, projections, the trade analyzer, start/sit comparisons, player search, and news — all from your terminal. Crafted intentionally for both human and AI agent use (assuming your agent has access to your Fantasy Footballers user/pw)

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

This performs the same browser-based authentication under the hood (headless Chromium), so it captures identical session cookies and API tokens. The session file is the same — once logged in, all commands work exactly the same way regardless of how you authenticated.

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

## JSON Output

All commands support `--json` for machine-readable output:

```bash
ffb rankings QB -n 5 --json
ffb players search "mahomes" --json
```

## Project Structure

```
src/ffb/
├── main.py              # CLI entry point
├── config.py            # Paths, constants, scoring formats
├── auth/
│   ├── login.py         # Playwright browser login flow
│   └── session.py       # Session persistence (~/.config/ffb/)
├── api/
│   ├── client.py        # HTTP client with cookie/nonce auth
│   └── endpoints.py     # API endpoint constants
├── commands/            # One file per command
├── cache/
│   └── store.py         # File-based JSON cache with TTL
└── display/
    └── tables.py        # Rich table formatters
```
