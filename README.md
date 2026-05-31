# 3D Print Library

A Steam-style desktop library for managing your local 3D print files — `.3mf`, `.stl`, `.obj`, `.step`, `.gcode` and more. Browse your collection with thumbnail previews, filter by category, and send files directly to your slicer.

![3D Print Library screenshot](docs/screenshot.png)

---

## Features

- **Auto-scan folders** — point the app at any folder (or multiple folders) and it finds all your 3D print files recursively
- **Smart auto-categorization** — files are categorized automatically from filename keywords into 15 categories
- **Thumbnail previews** — extracts built-in thumbnails from `.3mf` files; searches online (DuckDuckGo) for STL previews; falls back to a live 3D matplotlib render
- **Smart 3MF import** — sends `.3mf` files to your slicer with printer/filament settings stripped, so your slicer setup is never overridden — but all painted colors, multi-material assignments, and modifier meshes are fully preserved
- **Auto-detect slicers** — finds your installed slicers via Windows Registry, Program Files, AppData, and drive roots — no manual .exe hunting
- **13 slicers supported** — OrcaSlicer, Bambu Studio, PrusaSlicer, UltiMaker Cura, Snapmaker Luban, Creality Print, Chitubox, Lychee Slicer, FlashPrint, Anycubic Photon Workshop, ideaMaker, Simplify3D, SuperSlicer
- **Right-click context menu** — rename, change category, edit notes, refresh thumbnail, open file location, remove from library
- **Search & filter** — live search bar + category sidebar filters
- **SQLite library database** — stored in `~/.3dprintlibrary/`, nothing is moved or modified on disk

---

## Requirements

- Windows 10 / 11
- Python 3.10 or newer ([python.org](https://python.org))

---

## Installation

### 1. Clone or download the repo

```bash
git clone https://github.com/drewbiehd/3DPrintLibrary.git
cd 3DPrintLibrary
```

Or download the ZIP from GitHub → **Code → Download ZIP**, then extract it.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

This installs: PySide6 (UI), Pillow (images), numpy-stl + matplotlib (3D render), duckduckgo-search (online thumbnails), and requests.

### 3. Run the app

```bash
python main.py
```

On first launch you will be prompted to add a folder. The app will also automatically detect any installed slicers.

---

## Quick Start

### Adding your files

1. Click **+ Add Folder** in the toolbar (or go to **⚙ Settings → Folders**)
2. Select the folder where your `.stl` / `.3mf` files live — subfolders are scanned automatically
3. Click **↻ Scan** — the library fills with cards

### Browsing

| Action | How |
|---|---|
| Filter by category | Click a category in the left sidebar |
| Search | Type in the search bar — filters live as you type |
| Sort | Use the **Sort** dropdown in the toolbar |
| View file details | Hover a card to see the full path in the tooltip |

### Opening files in your slicer

| File type | Button behaviour |
|---|---|
| **STL / OBJ** | **▶ Open in Slicer** — passes the file directly |
| **3MF** | **⬇ Import to Slicer** — strips printer/filament settings before sending, so your current slicer profile is untouched. Painted colors and multi-material structure are fully preserved. |

If you have multiple slicers configured, clicking the button shows a picker menu.

To load a `.3mf` as a full project (including its embedded settings), right-click the card → **📂 Open as Project**.

### Right-click menu (any card)

| Option | What it does |
|---|---|
| ⬇ Import to Slicer / ▶ Open in Slicer | Send to slicer (submenu if multiple slicers) |
| 📂 Open as Project | 3MF only — load with all embedded settings |
| 🏷 Change Category | Override the auto-detected category |
| ✏ Rename | Set a display name (original filename unchanged) |
| 📝 Edit Notes | Add personal notes to this file |
| 🔄 Refresh Thumbnail | Delete cached thumbnail and regenerate |
| 📂 Open File Location | Open the containing folder in Explorer |
| 🗑 Remove from Library | Remove from the library DB (file stays on disk) |

---

## Categories

Files are auto-categorized on scan. You can override any file's category via right-click → **Change Category**.

| Category | Typical contents |
|---|---|
| 🔧 Tools | Wrenches, jigs, clamps, calipers |
| 🖱 Clicker Toys | Fidgets, spinners, pop-its, sensory toys |
| 🚗 Toys | Cars, figures, play sets, pinwheels |
| 🎲 Gaming & Tabletop | D&D minis, terrain, dice towers, board game inserts |
| ⚔ Cosplay & Props | Armor, masks, weapons, movie/TV replicas |
| 🏠 Household | Kitchen, bathroom, garage organizers |
| 🎨 Art & Decor | Sculptures, wall art, vases, lithophanes |
| 💡 Gadgets & Electronics | Phone stands, Pi cases, cable management |
| 📦 Utility | Generic holders, mounts, brackets, storage |
| 🌿 Outdoors & Garden | Planters, bird feeders, bike parts |
| 💎 Fashion & Jewelry | Rings, earrings, bracelets, belt buckles |
| 🖨 3D Printer Parts | Printer upgrades, mods, replacement parts |
| 📚 Education | Science models, anatomy, geography |
| 🔩 Repairs | Replacement parts, spare hardware |
| 📁 Uncategorized | Anything that didn't match a keyword |

---

## Settings

Open **⚙ Settings** from the toolbar.

### Folders tab
Add or remove the watch folders that the library scans. Click **+ Add Folder** to browse to a directory. Hit **↻ Scan** in the toolbar to re-scan after adding folders.

### Slicers tab
- **🔍 Auto-Detect Slicers** — searches the Windows Registry, Program Files, AppData, and drive roots for any of the 13 supported slicers
- **+ Add Manually** — browse to any `.exe` if your slicer wasn't auto-detected
- **✕ Remove Selected** — remove a slicer from the list

Auto-detect runs automatically the first time you open this tab if no slicers are configured.

### Thumbnails tab
| Option | Default | Notes |
|---|---|---|
| Internet image search | ✅ On | DuckDuckGo — no API key needed |
| 3D render fallback | ✅ On | Uses matplotlib; disable if your PC is slow |
| Clear thumbnail cache | — | Deletes all cached PNGs and regenerates on next scan |

---

## How 3MF Import Works

Standard behavior when you pass a `.3mf` to a slicer on the command line is to open it as a full project — this overrides your printer profile, filament settings, and process settings with whatever was saved in the file.

3D Print Library solves this by creating a temporary stripped copy of the `.3mf` before sending it to your slicer:

**Stripped (printer/filament/process profiles):**
- `Metadata/project_settings.config`
- `Metadata/filament_settings_*.config`
- `Metadata/machine_settings_*.config`
- `Metadata/process_settings_*.config`
- Compiled G-code

**Kept (all model data):**
- `3D/3dmodel.model` — geometry **and** all `paint_color` triangle attributes (brush-painted color sections)
- `Metadata/model_settings.config` — per-object extruder slot assignments
- Plate layout and thumbnails

The result: your colors and multi-material structure import intact, your slicer settings are never touched.

---

## Supported File Formats

| Format | Thumbnails | Notes |
|---|---|---|
| `.3mf` | ✅ Extracted from file | Full color/multi-material import support |
| `.stl` | 🌐 Online search → 🎲 3D render | Most common format |
| `.obj` | 🌐 Online search | Wavefront OBJ |
| `.step` / `.stp` | 🌐 Online search | CAD format |
| `.gcode` | — | Sliced files, placeholder icon |

---

## Data & Privacy

- Your library database is stored at `~/.3dprintlibrary/library.db` (SQLite)
- Thumbnails are cached at `~/.3dprintlibrary/thumbnails/`
- No files are ever moved, renamed, or modified
- Internet image search uses DuckDuckGo — no account or API key required
- Nothing is sent anywhere except anonymous image searches when generating STL thumbnails (can be disabled in Settings → Thumbnails)

---

## License

MIT — do whatever you want with it.
