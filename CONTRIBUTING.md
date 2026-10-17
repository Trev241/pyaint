# Contributing to Pyaint

Pyaint is a Windows screen-automation app: a pure planner turns an image into
strokes, and a driver replays them in a painting app. Small, focused changes
with tests are much easier to review than broad rewrites.

Read the [README](README.md) first, especially **How it works**. The short
version: `pyaint/planner.py` is pure and has no screen access, `pyaint/bot.py`
executes a plan, and `pyaint/painter.py` is the only module that sends input.

## Set up

```bash
git clone https://github.com/Trev241/pyaint.git
cd pyaint
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev,build]"
```

Python 3.8+ on Windows 10/11. The GUI needs a display; the test suite does not.

## Tests

```bash
python -m pytest -q            # fast suite (no Qt)
python -m pytest -m ui         # Qt smoke tests, offscreen
```

The default run excludes the `ui` group because building widgets is slow. Run
both before opening a pull request, and add a regression test for every bug fix
in the suite that can exercise it. Tests must not capture the screen, move the
mouse, or depend on the developer's config: build a `Palette` from an explicit
colour map and fake screen actions.

## Building

Building is Windows-only and needs the optional `build` extra:

```bash
pip install -e ".[build]"
python scripts/build_exe.py    # wraps: pyinstaller --noconfirm --clean pyaint.spec
```

The result is a single `dist/pyaint.exe`. `pyaint.spec` is checked in, so the
local build and a release build agree. When frozen, `config.json`, `cache/` and
`targets/` are written next to the executable, so smoke-test it from a writable
folder. The test suite cannot test the frozen build: run it, find a canvas,
load an image, draw once, and check the console for missing-module errors.

## Releasing

1. Bump `version` in `pyproject.toml`.
2. Move the `[Unreleased]` entries in `CHANGELOG.md` under a new
   `## [x.y.z] - YYYY-MM-DD` heading (Keep a Changelog format).
3. Commit (`Release vX.Y.Z`), tag and push:

   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin <branch>
   git push origin vX.Y.Z
   ```

4. On GitHub, **Releases → Draft a new release**, choose the tag, use the
   changelog as the notes, attach `dist/pyaint.exe` (and its `.sha256` if you
   generate one), and publish. Do the same with `gh release create
   vX.Y.Z dist/pyaint.exe --title "vX.Y.Z" --notes-file CHANGELOG.md --latest`.
5. Verify the release page shows the asset and that
   `.../releases/latest/download/pyaint.exe` resolves.

### Updating the demo

GitHub does not play `.mp4` links. Drag the video into a GitHub text box (a new
issue is fine), copy the resulting
`https://github.com/user-attachments/assets/<uuid>` URL, and paste it on its own
line under `## Demo` in the README. Keep it short (10–20 s), mute it, and
prefer H.264 `.mp4` or `.webm`.

## Recipes

Support for another palette app is data, not code. Drop a JSON recipe in
`targets/` or `~/.pyaint/targets/`; the schema, locator types and inheritance
rules are in [`targets/README.md`](targets/README.md). Keep recipes declarative:
the planner must never branch on an app id.

## House style

- Keep the planner pure. Screen access, threads and Qt belong in the UI/executor
  layers.
- Match the surrounding spelling. The user-facing docs use British English
  (*colour*, *centre*).
- Comments explain *why*, not *what*. Prefer a small named constant over a
  magic number.
- Do not add anti-detection or input-spoofing code. Locating a target's UI is in
  scope; hiding automation is not.
- Keep documentation to `README.md`, this file, `targets/README.md`, and the
  changelog/licence. Do not reintroduce a `docs/` tree; if a section outgrows
  the README, it belongs in `CONTRIBUTING.md` or the recipe schema.
