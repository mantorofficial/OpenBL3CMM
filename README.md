# OpenBL3CMM

A visual hotfix mod editor for Borderlands 3, inspired by [OpenBLCMM](https://github.com/BLCM/OpenBLCMM) (Borderlands Community Mod Manager).

Made by Ty-Gone.

## What is this?

OpenBL3CMM lets you create, edit, and manage BL3 hotfix mods with a visual interface — no more hand-editing giant text files. It's designed to work with [OpenHotfixLoader](https://github.com/apple1417/OpenHotfixLoader) (OHL) and [B3HM](https://borderlandsmodding.com/bl3-running-mods/).

Think of it as BLCMM, but for Borderlands 3.

[

![OpenBL3CMM Demo](https://img.youtube.com/vi/wVtU341Y2wE/maxresdefault.jpg)

]
(https://youtu.be/wVtU341Y2wE)

## Features

- **Visual category tree** with checkboxes to enable/disable individual entries or entire categories
- **Simple command syntax** — write `set`, `edit`, `merge`, `early_set`, `news` instead of raw `SparkPatchEntry` lines
- **Three entry modes** — Raw Text (just type), Simple Command (guided), or Spark Format (individual fields)
- **Drag and drop** reordering of entries and categories
- **Copy / Cut / Paste** entries and categories
- **Search** across all entries
- **6 themes** — Midnight, Obsidian, BL3 Orange, Soft Dark, Soft Purple, Catppuccin Mocha
- **Customizable fonts** — change UI font, monospace font, and size (Ctrl+=/- to zoom)
- **BLIMP tag support** — reads and writes `@title`, `@author`, `@version`, `@description` metadata
- **`.blmod` format support** — read/write the proposed YAML-based mod format
- **Session persistence** — remembers your last file, expanded categories, theme, and font settings
- **Import / Export** — import mods as categories, export individual categories as standalone mods

## Simple Commands

Instead of writing raw Spark format, you can use friendly commands:

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

All commands support optional params override: `set (1,2,0,MatchAll) /Game/Path Prop Value`

The app displays entries in simple command form but saves them as Spark format for OHL compatibility.

## Example

What you see in the editor:
```
edit /Game/GameData/Balance/HealthAndDamage/DamageBalanceScalers/DataTable_Damage_GlobalBase.DataTable_Damage_GlobalBase PlayerGroundSlamDamage Base_2_5C32556442B4DA4D7EAE1A8610E0A950 0 200000
```

What gets saved to the file:
```
SparkLevelPatchEntry,(1,2,0,MatchAll),/Game/GameData/Balance/HealthAndDamage/DamageBalanceScalers/DataTable_Damage_GlobalBase.DataTable_Damage_GlobalBase,PlayerGroundSlamDamage,Base_2_5C32556442B4DA4D7EAE1A8610E0A950,0,,200000
```

## Installation

### Pre-built EXE (Windows)

Download `OpenBL3CMM.exe` from the releases page and run it. No installation needed.

### From source

Requires Python 3.10+.

```bash
pip install PySide6
pip install pyyaml    # optional, for .blmod support
```

Then run:
```bash
python main.py
```

## Building the EXE

```bash
pip install pyinstaller
python -m PyInstaller --clean OpenBL3CMM.spec
```

The exe will be at `dist/OpenBL3CMM.exe`.

## File Format

OpenBL3CMM works with standard `.bl3hotfix` text files that OHL and B3HM understand. The file format uses `###` headers for metadata and `######` section headers for categories:

```
###
### Name: My Mod
### Version: 1.0
### Author: MyName
###

# @title My Mod
# @author MyName
# @version 1.0
# @game BL3

##############################
###### Category Name #########
##############################

# Entry description
SparkPatchEntry,(1,1,0,),/Game/Path/Object,Property,0,,Value
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New mod |
| Ctrl+O | Open file |
| Ctrl+S | Save |
| Ctrl+Shift+S | Save As |
| Insert | Add entry (to selected category) |
| Ctrl+H | Add category (at root) |
| Ctrl+B | Enable selected |
| Ctrl+D | Disable selected |
| Ctrl+C / X / V | Copy / Cut / Paste |
| Ctrl+R | Rename category |
| Delete | Delete selected |
| Ctrl+= / Ctrl+- | Zoom in / out |
| Ctrl+0 | Reset zoom |

## Project Structure

```
main.py       — PySide6 GUI (main window, dialogs, tree, themes)
models.py     — Data model (ModFile, Category, HotfixEntry)
parser.py     — Parses .bl3hotfix and .blmod files into ModFile
exporter.py   — Exports ModFile back to .bl3hotfix or .blmod
commands.py   — Simple command syntax ↔ Spark format conversion
blimp.py      — BLIMP metadata tag parser/generator
blmod.py      — .blmod YAML format parser/serializer
```

## Credits

- **Ty-Gone** — OpenBL3CMM development
- **[apple1417](https://github.com/apple1417)** — OpenHotfixLoader, BLIMP spec, .blmod format spec
- **[LightChaosman](https://github.com/BLCM/OpenBLCMM)** — Original BLCMM (inspiration)
- **[Apocalyptech](https://github.com/apocalyptech)** — BL3 modding resources and OpenBLCMM
- **BLCM Community** — Borderlands modding community

## License

OpenBL3CMM is licensed under the [GNU General Public License v3](https://www.gnu.org/licenses/gpl-3.0.en.html).
A copy can be found at [License.txt](License.txt).
