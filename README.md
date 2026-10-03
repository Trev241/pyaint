<div align="center">

# Pyaint

**Transform any image into automated brush strokes.**

Pyaint recreates a picture by driving the mouse in a painting app — MS Paint,
GIMP, skribbl.io, and anything else you can teach it.

[![license](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE.md)
[![platform](https://img.shields.io/badge/platform-Windows-0078d4)](#requirements)

[Quick start](#quick-start) • [Supported apps](#supported-apps) • [FAQ](#faq) • [Documentation](#documentation)

</div>

---

## Demo

https://github.com/user-attachments/assets/965556a4-f72b-4e24-a9ea-160732c6be51

<sub>GIMP — custom colour calibration and automatic layers.</sub>

https://github.com/user-attachments/assets/50f2f344-8ca9-439b-8722-0175356ad59e

<sub>MS Paint — sampled palette and double-click colour mode.</sub>

![A picture drawn by Pyaint](assets/sample.png)

## Supported apps

Pyaint finds the canvas and palette on screen, then replays the image as
horizontal brush strokes. Support level depends on how much of the app can be
auto-detected.

| App | Support | Setup |
|-----|---------|-------|
| **skribbl.io** | Canvas + fixed 2×13 palette auto-detected | `Auto-detect` — no manual teaching |
| **MS Paint** (Windows 11) | Canvas + palette auto-detected when maximized at 1920×1080 | `Auto-detect`, or teach manually |
| **GIMP** | Layer workflow + colour-dialog calibration | Manual teach (recommended) |
| **Clip Studio Paint** | Generic palette / colour-dialog path | Manual teach |
| **Krita / Photoshop** | Generic path | Manual teach |
| **Anything else** | Full manual setup | Manual teach |

Recipes for more apps are data, not code — see
[target recipes](#target-recipes).

## Requirements

- **Windows 10/11** (screen capture + synthetic input are Windows-oriented).
- **Python 3.8+**. You can also build a standalone `.exe` that bundles Python
  (see the install options below).

> **Display scaling / multi-monitor:** `pyautogui` captures the primary monitor
> at physical pixels. Set Windows scaling to 100% on the target monitor, or
> expect screenshot↔click coordinates to drift.

## Quick start

### 1. Install

**Option A — pip / pipx:**

```bash
pipx install git+https://github.com/Trev241/pyaint.git
pyaint
```

**Option B — from source:**

```bash
git clone https://github.com/Trev241/pyaint.git
cd pyaint
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**Want a standalone `.exe`?** Install the build extra and run
`python scripts/build_exe.py`; the result lands in `dist/pyaint.exe`.

### 2. Draw

1. Pick your app in the **Target App** dropdown.
2. Click **Auto-detect** (minimize Pyaint, let the target show, confirm the
   preview) — or click **Setup** and teach the Palette and Canvas by clicking
   their corners.
3. Load an image from a file or URL.
4. Click **Start**. Press `ESC` to stop, `P` to pause/resume.

That's it. For skribbl.io the first draw should take about a minute.

> **Honest note:** auto-detection is tuned against specific window layouts and
> resolutions. If it can't find a region it falls back to manual teaching — it
> will never silently draw in the wrong place.

## How it works

```
image  →  fit + downscale to the canvas (nearest-neighbour)
       →  map each pixel to the nearest palette / custom colour
       →  run-length encode each row into horizontal strokes
       →  replay strokes with pyautogui, selecting colours as it goes
```

Two processing modes:

- **Layered** (default) — sorts colours by frequency and repaints lower layers,
  producing fewer, cleaner colour switches.
- **Slotted** — a direct colour→lines mapping; faster to process.

Processing can be **pre-computed** into `cache/` so repeat draws start
instantly, and any draw can be **paused/resumed** from the exact stroke.

## Configuration

Settings live in `config.json` next to the executable (or the repo root for a
source checkout) and are written whenever you change something in the UI.

| Setting | Range | Meaning |
|---------|-------|---------|
| **Delay** | 0.0–1.0 s | Time between strokes |
| **Pixel Size** | 3–50 px | Detail level (lower = more detail, slower) |
| **Precision** | 0.0–1.0 | Colour accuracy |
| **Jump Delay** | 0.0–2.0 s | Pause inserted after large cursor jumps |

Options include **Ignore White Pixels**, **Use Custom Colors**, **New Layer**,
**Skip First Color**, and **MSPaint Mode** (double-click swatches).

For a full reference see [`Docs/configuration.md`](Docs/configuration.md).

## Target recipes

A recipe tells Pyaint which tools an app needs, how to pick colours, and how to
auto-detect the canvas/palette. Drop a JSON file in `targets/` (or
`~/.pyaint/targets/`) and it appears in the dropdown after a restart.

```json
{
  "id": "my-paint",
  "name": "My Paint",
  "extends": "desktop-base",
  "drawing_settings": { "pixel_size": 6 }
}
```

The schema (locators, inheritance, validation) is documented in
[`targets/README.md`](targets/README.md).

## FAQ

**Does it work on macOS or Linux?**
No. Pyaint relies on Windows screen capture and `pyautogui` input, and the
detection is tuned for Windows apps.

**Colors are wrong.**
Make sure the target palette was sampled correctly (re-run **Setup**), lower
**Pixel Size**, or use **Use Custom Colors** with calibration for a
colour-dialog app. See [`Docs/troubleshooting.md`](Docs/troubleshooting.md).

**Drawing is too slow / too fast.**
Adjust **Delay** and **Pixel Size**. **Pre-compute** makes repeated runs start
instantly but does not change drawing speed.

**Auto-detect found nothing.**
The window may be resized, on a non-primary monitor, or under display scaling.
Maximize the app on the primary monitor at 100% scaling and retry, or teach the
tools manually with **Setup**.

**Where does it save data?**
`config.json`, `color_calibration.json`, `cache/`, and `targets/` sit next to
the executable (the repo root for a source checkout). Nothing is uploaded; the
only network request is downloading an image you give it by URL.

**Can I use this on skribbl.io?**
Locating the app's UI to draw your own image is allowed here, but using it to
deceive other players is not the intended use. See [Intended use](#intended-use).

## Intended use

Pyaint is for drawing your own images in applications you control: art,
accessibility, offline demos, and testing. It is **not** a tool for deceiving
people or defeating anti-cheat systems, and contributions that hide automation
(input spoofing, anti-detection "humanization") are out of scope. You are
responsible for complying with the terms of service of any app you use it with.

## Documentation

- [Usage guide](Docs/usage-guide.md)
- [Configuration](Docs/configuration.md)
- [Architecture](Docs/architecture.md)
- [Troubleshooting](Docs/troubleshooting.md)
- [API reference](Docs/api.md)
- [Changelog](CHANGELOG.md)

## Development

```bash
pip install -e ".[dev,build]"
python -m pytest -q          # headless, no display needed
python main.py               # GUI (Windows)
python scripts/build_exe.py  # build dist/pyaint.exe
```

The test suite is fully headless (118 tests); the GUI and screen input are
verified manually on Windows.

## License

GNU General Public License v3.0 or later — see [`LICENSE.md`](LICENSE.md).
