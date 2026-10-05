# Releasing

How to ship a standalone `pyaint.exe` and publish it on GitHub, plus how to
embed the demo video in the README.

## 1. Build the `.exe`

On a Windows machine, from the repo root:

```bash
pip install -e ".[build]"      # PyInstaller
python scripts/build_exe.py    # wraps: pyinstaller --noconfirm --clean pyaint.spec
```

The result is a single file: `dist/pyaint.exe`. The spec (`pyaint.spec`) is
one-file, `console=True` (the app logs there so bugs are reportable), and
collects `pynput`'s lazy platform backends.

**Runtime paths.** When frozen, `pyaint/paths.py` writes `config.json`,
`cache/`, and `targets/` next to the executable (not inside it). So the folder
you ship in must be writable; a user with the `.exe` on a read-only share will
fail to save settings.

**Smoke-test before publishing** (the test suite cannot test the frozen build):

1. Run `dist/pyaint.exe` from a writable folder.
2. Auto-detect on a blank canvas, load an image, draw once.
3. Confirm `config.json` appears next to the `.exe` and `cache/` is cleared on exit.
4. Check the console for missing-module errors (usually a PyInstaller
   `hiddenimports` gap).

## 2. Version and changelog

1. Bump `version` in `pyproject.toml`.
2. In `CHANGELOG.md`, move the `[Unreleased]` entries under a new
   `## [x.y.z] - YYYY-MM-DD` heading (Keep a Changelog format).
3. Commit:

   ```bash
   git add -A
   git commit -m "Release vX.Y.Z"
   ```

## 3. Tag and push

```bash
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin <branch>       # e.g. main or rework
git push origin vX.Y.Z
```

## 4. Publish the GitHub release

The old tag-triggered `release.yml` workflow was removed, so attach the `.exe`
by hand (or restore that workflow if you want CI to build it).

**Web UI**

1. On GitHub: **Releases → Draft a new release**.
2. **Choose a tag** → the `vX.Y.Z` tag you pushed (or create it here).
3. Title `vX.Y.Z`; use **Generate release notes**, or paste the changelog.
4. Drag `dist/pyaint.exe` into the **Attach binaries** box (add the `.sha256`
   too if you generate one).
5. Tick **Set as the latest release**, then **Publish release**.

**GitHub CLI** (equivalent)

```bash
gh release create vX.Y.Z dist/pyaint.exe \
  --title "vX.Y.Z" \
  --notes-file CHANGELOG.md \
  --latest
```

Verify the release page shows the asset and that `.../releases/latest/download/pyaint.exe`
resolves.

## 5. Embed the demo video in the README

GitHub does **not** play `.mp4` via `![](link.mp4)`; it only renders an image
link. The supported path is a **user attachment**:

1. Open any GitHub text box — a new **issue**, a PR description, or a comment.
2. **Drag the video file in.** GitHub uploads it and inserts a URL such as
   `https://github.com/user-attachments/assets/<uuid>`.
3. Copy that URL. (You can cancel the issue/comment afterwards — the asset
   persists.)
4. Paste it on its own line in `README.md`; GitHub renders an inline player:

   ```markdown
   ## Demo

   https://github.com/user-attachments/assets/<uuid>

   <sub>A one-line caption.</sub>
   ```

   The repository README already uses exactly this pattern.

Notes:

- Prefer **`.mp4`** (H.264) or `.webm`, keep it **short** (10–20 s) and small;
  strip audio (`ffmpeg -i in.mp4 -an -vf scale=1280:-2 out.mp4`). Images/GIFs
  are heavier, so a video is usually better.
- For a clickable poster instead, upload a still to the issue, then
  `[![poster](image-url)](video-url)`.
- The asset is tied to your account/repo; deleting it from the attachments UI
  breaks the README.
