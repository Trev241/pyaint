# Contributing to Pyaint

Thanks for helping. The most valuable contributions are **target recipes**
(so Pyaint drives more apps) and **bug reports from real runs**.

## Ways to help

- **Share a target recipe** — the easiest contribution. See
  [`targets/README.md`](targets/README.md); drop a `.json` file in `targets/`
  or post it in Discussions.
- **Report a bug** — use the [bug report](.github/ISSUE_TEMPLATE/bug_report.yml)
  template and include the console output.
- **Improve docs** — `Docs/` and `README.md` are the front door for both users
  and search engines. Corrections are welcome.
- **Code** — see below.

## Development setup

```bash
git clone https://github.com/Trev241/pyaint.git
cd pyaint
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev,build]"
python -m pytest -q             # headless, no display required
python main.py                  # GUI (Windows desktop only)
```

## Project layout

User-facing code lives in the `pyaint/` package:

| Area | Files |
|------|-------|
| Drawing engine | `pyaint/bot.py`, `pyaint/painter.py`, `pyaint/palette.py` |
| Environment state | `pyaint/profile.py`, `pyaint/config.py` |
| Targets & detection | `pyaint/targets.py`, `pyaint/locators.py`, `pyaint/validation.py` |
| Colour calibration / cache | `pyaint/calibration.py`, `pyaint/cache.py` |
| UI | `pyaint/ui/window.py`, `pyaint/ui/setup.py` |

## Ground rules

- **Keep the drawing engine app-agnostic.** App differences belong in a
  target recipe or the `ScreenPainter` seam, never in `bot.py` conditionals.
- **Tests are headless.** Anything that touches `pyautogui`/`tkinter` at import
  or call time needs a fake (see `tests/test_draw.py`, `tests/test_painter.py`).
- **Add a test** for behaviour changes; run `python -m pytest -q` before opening
  a PR.
- **Update `CHANGELOG.md`** under `[Unreleased]`.
- **Never commit runtime state:** `config.json`, `color_calibration.json`,
  `cache/`, or preview PNGs (all gitignored).

## Adding a target recipe

1. Copy the closest built-in from `pyaint/targets.py` into a new JSON file in
   `targets/`.
2. Tune `detection` against a screenshot (the dev helper
   `AGENTS/tools/detect_screenshot.py` can test detection offline).
3. Validate: recipes are self-checked on load; failures are printed to the
   console.
4. Open a PR with the recipe and, ideally, a screenshot of it working.

## Scope

Pyaint automates a user's own screen. Contributions that hide automation from
the host app (anti-cheat / detection evasion, input spoofing, "humanization")
are **out of scope** and will be declined.
