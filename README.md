# OpenBL3CMM

A visual hotfix mod editor for Borderlands 3, inspired by [OpenBLCMM](https://github.com/BLCM/OpenBLCMM) (Borderlands Community Mod Manager).

Made by Ty-Gone.

## What is this?

OpenBL3CMM lets you create, edit, and manage BL3 hotfix mods with a visual interface — no more hand-editing giant text files. It's designed to work with [OpenHotfixLoader](https://github.com/apple1417/OpenHotfixLoader) (OHL) and [B3HM](https://borderlandsmodding.com/bl3-running-mods/).

Think of it as BLCMM, but for Borderlands 3.

## Quick Start

### 1. Install
Download `OpenBL3CMM_Setup.exe` from the [releases page](https://github.com/mantorofficial/OpenBL3CMM/releases) and run the installer.

### 2. Set Up the Object Explorer (Optional but Recommended)
The Object Explorer lets you browse all BL3 game objects. To use it:

1. Download `bl3data.sqlite3` from the repo: **[bl3data.sqlite3](https://github.com/mantorofficial/OpenBL3CMM/releases/tag/Sql-datapack)**
2. Place it in: `%LOCALAPPDATA%\Programs\OpenBL3CMM\datapacks\`
3. Open the Object Explorer (Ctrl+E) — it auto-detects the datapack

> **Tip:** The datapacks folder is created automatically by the installer. You can also load datapacks manually via the "Load Datapack..." button.

### 3. Start Modding
- Use **File → New** to create a blank mod, or download the **[Template Mod](Template_Mod.blmod)** as a starting point
- Add categories and entries using the toolbar or keyboard shortcuts
- Save as `.bl3hotfix` or `.blmod`
- Place your mod file where OHL/B3HM can find it

## Downloads

| File | Description |
|------|-------------|
| [OpenBL3CMM_Setup.exe](https://github.com/mantorofficial/OpenBL3CMM/releases) | Windows installer (from Releases) |
| [Template_Mod.blmod](Template_Mod.blmod) | Template mod file to get started |
| [bl3data.sqlite3](https://github.com/mantorofficial/OpenBL3CMM/releases/tag/Sql-datapack) | BL3 Object Explorer datapack — place in `%LOCALAPPDATA%\Programs\OpenBL3CMM\datapacks\` |

## Features

### Mod Editing
- **Visual category tree** with checkboxes to enable/disable individual entries or entire categories
- **Full command display** — tree shows the complete simple command (`set /Game/Path/Object Property Value`)
- **Per-command color coding** — `set` = blue, `edit` = green, `clone` = gold, `delete` = pink, etc. (customizable)
- **Comment display** — comments show as bright yellow labels above their entry
- **Simple command syntax** — write `set`, `edit`, `merge`, `early_set` instead of raw `SparkPatchEntry` lines
- **Three entry modes** — Raw Text, Simple Command (guided), or Spark Format (individual fields)
- **BLCMM-style auto-format** — struct values like `(Key=Val,...)` display with proper indentation
- **Bracket matching** — highlights matching `(` `)` pairs in the editor
- **Syntax highlighting** — commands, object paths, and properties colored in real-time
- **Validation on save** — warns about potential problems before saving
- **Drag and drop** reordering of entries and categories
- **Copy / Cut / Paste** entries and categories
- **Search** across all entries
- **Independent windows** — edit multiple entries simultaneously without overlap

### Object Explorer
- **Auto-load datapack** — drop `data.sql` in the datapacks folder and it's detected automatically
- **Built-in data browser** — browse all BL3 game objects (Tools → Object Explorer, Ctrl+E)
- **Tabbed properties** — open multiple objects in separate tabs, closeable and moveable
- **Clickable links** — object paths in JSON become clickable, navigate with left-click or middle-click to open in new tab
- **Save/bookmark objects** — each tab has a clipboard of saved object paths
- **Back/Forward navigation** — full history with ◀ ▶ buttons, Alt+Left/Right, Mouse 4/5
- **Search in properties** — Ctrl+F with regex, match case, wrap around (per active tab)
- **Zoom** — Ctrl+Wheel, Ctrl+=/-, Ctrl+0 to reset
- **Preferences menu** — Keyboard Shortcuts editor accessible from menu bar
- **References** — browse references FROM and TO any object, double-click to navigate
- **Search by path, class, or properties** with "Search Properties" checkbox
- **Datapack support** — loads SQLite datapacks (apocalyptech's bl3refs format, Grimm's JSON data, ZIP, 7z)

### Preferences
- **Keyboard Shortcuts** — press-to-edit capture supporting keys, mouse buttons, and scroll wheel
- **Command Color Coding** — customize colors per command type with color picker
- **Theme selector** — 6 themes: Midnight, Obsidian, BL3 Orange, Soft Dark, Soft Purple, Catppuccin Mocha
- **Font & Size settings** — change UI font, monospace font, and size
- **Detail Panel toggle** — show/hide the right-side detail panel

### Tutorial
- Built-in 6-page walkthrough for new users
- Shows on first launch, accessible anytime via Help → Tutorial

### DataTable Hotfixes (Type 2)
- **Transparent handling** — Type 2 DataTable hotfixes display as clean `set TABLE ROW VALUE` without showing the ugly column hash
- **Column auto-recovery** — the column name is preserved internally and recovered automatically on save

### File Formats
- **`.bl3hotfix`** — standard OHL/B3HM text format
- **`.blmod`** — YAML-based format (requires PyYAML)
- **BLIMP tags** — reads and writes `@title`, `@author`, `@version`, `@description` metadata
- **Disabled entries** — saved as `#SparkPatchEntry,...` (game skips `#` lines)
- **Import / Export** — import mods as categories, export individual categories or enabled-only

## Simple Commands

| Command | Description | Spark Type |
|---------|-------------|------------|
| `set` | Set a property | SparkPatchEntry |
| `edit` | Level-specific set (MatchAll) | SparkLevelPatchEntry |
| `merge` | Character-loaded patch | SparkCharacterLoadedEntry |
| `early_set` | Early level patch | SparkEarlyLevelPatchEntry |
| `news` | Inject news item | InjectNewsItem |
| `set_cmp` | Compare-and-set | SparkPatchEntry |
| `set_array` | Set entire array | SparkPatchEntry |
| `set_struct` | Set struct field | SparkPatchEntry |
| `add` | Add to array | SparkPatchEntry |
| `remove` | Remove from array | SparkPatchEntry |
| `clone` | Clone an object | SparkPatchEntry |
| `delete` | Delete an object | SparkPatchEntry |
| `create` | Create a new object | SparkPatchEntry |
| `rename` | Rename an object | SparkPatchEntry |
| `exec` | Include another mod file | exec |
| `set_mesh` | Type 6 mesh placement | SparkLevelPatchEntry |

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New mod |
| Ctrl+O | Open file |
| Ctrl+S | Save |
| Ctrl+Shift+S | Save As |
| Ctrl+E | Object Explorer |
| Insert | Edit selected entry / Add new entry |
| Ctrl+H | Add category |
| Ctrl+B / Ctrl+D | Enable / Disable selected |
| Ctrl+C / X / V | Copy / Cut / Paste |
| Delete | Delete selected |
| Ctrl+= / Ctrl+- | Zoom In / Out |
| Ctrl+0 | Reset zoom |

All shortcuts are customizable via Preferences → Keyboard Shortcuts.

### Object Explorer

| Shortcut | Action |
|----------|--------|
| Ctrl+F | Search in properties |
| Alt+Left / Right | Back / Forward |
| Mouse 4 / 5 | Back / Forward |
| Ctrl+Wheel | Zoom |

## Installation

### Pre-built Installer (Windows)

Download `OpenBL3CMM_Setup.exe` from the [releases page](https://github.com/mantorofficial/OpenBL3CMM/releases) and run it. The installer creates:

```
%LOCALAPPDATA%\Programs\OpenBL3CMM\
├── backups\       — auto-backups before each save
├── datapacks\     — place data.sql here for Object Explorer
└── mods\          — default mod directory
```

### From Source

Requires Python 3.10+.

```bash
pip install PySide6
pip install pyyaml    # optional, for .blmod support
python main.py
```

## Generating a Datapack

If you want to generate your own datapack instead of using the provided `data.sql`:

```bash
# From Grimm's extracted JSON + bl3refs
python generate_datapack.py --from-json "C:\path\to\extracted\" --merge-refs bl3refs.sqlite3 -o bl3data.sqlite3

# From 7z archive
python generate_datapack.py --from-7z "Final version.7z" --merge-refs bl3refs.sqlite3 -o bl3data.sqlite3
```

Get `bl3refs.sqlite3` from [apocalyptech's BL3 Object Refs](https://apocalyptech.com/games/bl3-refs/).

## Project Structure

```
main.py                — GUI, dialogs, tree, themes, preferences
models.py              — Data model (ModFile, Category, HotfixEntry)
parser.py              — File parser (.bl3hotfix, .blmod)
exporter.py            — File exporter
commands.py            — Simple command ↔ Spark format conversion
blimp.py               — BLIMP metadata tags
blmod.py               — .blmod YAML format
object_explorer.py     — Object Explorer window
hotfix_highlighter.py  — Syntax highlighting + validation
generate_datapack.py   — SQLite datapack generator
openbl3cmm.ico         — App icon
OpenBL3CMM.spec        — PyInstaller spec
installer.iss          — Inno Setup installer script
build.bat              — Windows build script
CHANGELOG.md           — Version history
Template_Mod.blmod     — Template mod file
```

## Modding Resources

- [BL3 Hotfix Modding Guide](https://github.com/BLCM/BLCMods/wiki/Borderlands-3-Hotfix-Modding)
- [BL3 Hotfix Format](https://github.com/BLCM/BLCMods/wiki/Borderlands-3-Hotfixes)
- [BL3 Item and Weapon Parts](https://github.com/BLCM/BLCMods/wiki/Borderlands-3-Item-and-Weapon-Parts)
- [Make Every Gun an Alien Barrel](https://github.com/BLCM/BLCMods/wiki/Make-every-gun-an-Alien-barrel)
- [BL3 Mod Authors Guide](https://github.com/BLCM/bl3mods/blob/master/README-authors.md)
- [Community Mods](https://github.com/BLCM/bl3mods)
- [OpenHotfixLoader](https://github.com/apple1417/OpenHotfixLoader)

## Credits

- **Ty-Gone** — OpenBL3CMM development
- **[apple1417](https://github.com/apple1417)** — OpenHotfixLoader, BLIMP spec, .blmod format
- **[LightChaosman](https://github.com/BLCM/OpenBLCMM)** — Original BLCMM (inspiration)
- **[Apocalyptech](https://github.com/apocalyptech)** — BL3 modding resources, Object Refs, OpenBLCMM
- **BLCM Community** — Borderlands modding community

## License

OpenBL3CMM is licensed under the [GNU General Public License v3](https://www.gnu.org/licenses/gpl-3.0.en.html).
A copy can be found at [License.txt](License.txt).
