# OpenBL3CMM

A visual hotfix mod editor for Borderlands 3, inspired by [OpenBLCMM](https://github.com/BLCM/OpenBLCMM) (Borderlands Community Mod Manager).

Made by Ty-Gone.

## What is this?

OpenBL3CMM lets you create, edit, and manage BL3 hotfix mods with a visual interface — no more hand-editing giant text files. It's designed to work with [OpenHotfixLoader](https://github.com/apple1417/OpenHotfixLoader) (OHL) and [B3HM](https://borderlandsmodding.com/bl3-running-mods/).

Think of it as BLCMM, but for Borderlands 3.

## Features

### Mod Editing
- **Visual category tree** with checkboxes to enable/disable individual entries or entire categories
- **Simple command syntax** — write `set`, `edit`, `merge`, `early_set` instead of raw `SparkPatchEntry` lines
- **Three entry modes** — Raw Text, Simple Command (guided), or Spark Format (individual fields)
- **BLCMM-style auto-format** — struct values like `(Key=Val,...)` display with proper indentation
- **Bracket matching** — highlights matching `(` `)` pairs in the editor
- **Syntax highlighting** — commands, object paths, and properties colored in real-time
- **Validation on save** — warns about potential problems before saving
- **Drag and drop** reordering of entries and categories
- **Copy / Cut / Paste** entries and categories
- **Search** across all entries
- **Non-modal editing** — edit entries while browsing the Object Explorer

### Object Explorer
- **Built-in data browser** — browse all BL3 game objects (Tools → Object Explorer, Ctrl+E)
- **Tabbed properties** — open multiple objects in separate tabs, closeable and moveable
- **Clickable links** — object paths in JSON become clickable, navigate with left-click or middle-click to open in new tab
- **Save/bookmark objects** — each tab has a clipboard of saved object paths
- **Back/Forward navigation** — full history with ◀ ▶ buttons, Alt+Left/Right, Mouse 4/5
- **Search in properties** — Ctrl+F with regex, match case, wrap around (per active tab)
- **Zoom** — Ctrl+Wheel, Ctrl+=/-, Ctrl+0 to reset
- **Customizable shortcuts** — F1 to open shortcuts dialog, key capture supports keyboard, mouse buttons, and scroll wheel with dual bindings
- **References** — browse references FROM and TO any object, double-click to navigate
- **Search by path, class, or properties** with "Search Properties" checkbox
- **Datapack support** — loads SQLite datapacks (apocalyptech's bl3refs format, Grimm's JSON data, ZIP, 7z)

### DataTable Hotfixes (Type 2)
- **Transparent handling** — Type 2 DataTable hotfixes display as clean `set TABLE ROW VALUE` without showing the ugly column hash
- **Column auto-recovery** — the column name is preserved internally and recovered automatically on save

### File Formats
- **`.bl3hotfix`** — standard OHL/B3HM text format
- **`.blmod`** — YAML-based format (requires PyYAML)
- **BLIMP tags** — reads and writes `@title`, `@author`, `@version`, `@description` metadata
- **Disabled entries** — saved as `#SparkPatchEntry,...` (game skips `#` lines)
- **Import / Export** — import mods as categories, export individual categories or enabled-only

### UI
- **6 themes** — Midnight, Obsidian, BL3 Orange, Soft Dark, Soft Purple, Catppuccin Mocha
- **Customizable fonts** — change UI font, monospace font, and size
- **Session persistence** — remembers last file, expanded categories, theme, and font settings

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

## Example: Modding the Maggie

**Change damage** (Type 2 DataTable hotfix):
```
SparkPatchEntry,(1,2,0,),/Game/Gear/Weapons/_Shared/_Design/GameplayAttributes/_Unique/DataTable_WeaponBalance_Unique_JAK.DataTable_WeaponBalance_Unique_JAK,PS_Maggie,DamageScale_2_4F6EF14648BA8F2AE9217DAFEA60EE53,0,,500.0
```

**Add projectiles** (set InventoryAttributeEffects with all original entries + new one):
```
set Part_PS_JAK_Barrel_Maggie.Part_PS_JAK_Barrel_Maggie InventoryAttributeEffects
(
    (
        AttributeToModify=/Game/GameData/Weapons/Att_Weapon_Damage.Att_Weapon_Damage,
        ModifierType=ScaleSimple,
        ModifierValue=
        (
            BaseValueConstant=0.0,
            DataTableValue=
            (
                DataTable=/Game/Gear/Weapons/_Shared/_Design/GameplayAttributes/_Unique/DataTable_WeaponBalance_Unique_JAK.DataTable_WeaponBalance_Unique_JAK,
                RowName=PS_Maggie,
                ValueName=DamageScale_2_4F6EF14648BA8F2AE9217DAFEA60EE53
            ),
            BaseValueScale=1.0
        )
    ),
    (
        AttributeToModify=/Game/GameData/Weapons/Att_Weapon_Spread.Att_Weapon_Spread,
        ModifierType=ScaleSimple,
        ModifierValue=(BaseValueConstant=3.5,BaseValueScale=1.0)
    ),
    (
        AttributeToModify=/Game/GameData/Weapons/Att_Weapon_MaxLoadedAmmo.Att_Weapon_MaxLoadedAmmo,
        ModifierType=PreAdd,
        ModifierValue=(BaseValueConstant=4.0,BaseValueScale=1.0)
    ),
    (
        AttributeToModify=/Game/GameData/Weapons/Att_Weapon_CustomSightColorScheme.Att_Weapon_CustomSightColorScheme,
        ModifierType=OverrideBaseValue,
        ModifierValue=(BaseValueConstant=1.0,BaseValueScale=1.0)
    ),
    (
        AttributeToModify=/Game/GameData/Weapons/Att_Weapon_ProjectilesPerShot.Att_Weapon_ProjectilesPerShot,
        ModifierType=PreAdd,
        ModifierValue=(BaseValueConstant=44.0,BaseValueScale=1.0)
    )
)
```

> **Important:** When setting `InventoryAttributeEffects`, include ALL original entries plus your additions — it replaces the entire array.

## Generating a Datapack

The Object Explorer needs a datapack to browse game data:

```bash
# From Grimm's extracted JSON + bl3refs
python generate_datapack.py --from-json "C:\path\to\extracted\" --merge-refs bl3refs.sqlite3 -o bl3data.sqlite3

# From 7z archive
python generate_datapack.py --from-7z "Final version.7z" --merge-refs bl3refs.sqlite3 -o bl3data.sqlite3
```

Get `bl3refs.sqlite3` from [apocalyptech's BL3 Object Refs](https://apocalyptech.com/games/bl3-refs/).

## Installation

### Pre-built EXE (Windows)

Download `OpenBL3CMM.exe` from the [releases page](https://github.com/mantorofficial/OpenBL3CMM/releases) and run it.

### From Source

Requires Python 3.10+.

```bash
pip install PySide6
pip install pyyaml    # optional, for .blmod support
python main.py
```

## Building the EXE

```bash
pip install pyinstaller
python -m PyInstaller --clean OpenBL3CMM.spec
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New mod |
| Ctrl+O | Open file |
| Ctrl+S | Save |
| Ctrl+Shift+S | Save As |
| Ctrl+E | Object Explorer |
| Insert | Add entry |
| Ctrl+H | Add category |
| Ctrl+B / Ctrl+D | Enable / Disable selected |
| Ctrl+C / X / V | Copy / Cut / Paste |
| Delete | Delete selected |
| Ctrl+= / Ctrl+- | Zoom |
| Ctrl+0 | Reset zoom |

### Object Explorer

| Shortcut | Action |
|----------|--------|
| Ctrl+F | Search in properties |
| Alt+Left / Right | Back / Forward |
| Mouse 4 / 5 | Back / Forward |
| Ctrl+Wheel | Zoom |
| Ctrl+0 | Reset Zoom |
| F1 | Show / edit shortcuts |

## Project Structure

```
main.py                — GUI, dialogs, tree, themes
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
build.bat              — Windows build script
```

## Modding Resources

- [BL3 Hotfix Modding Guide](https://github.com/BLCM/BLCMods/wiki/Borderlands-3-Hotfix-Modding)
- [BL3 Hotfix Format](https://github.com/BLCM/BLCMods/wiki/Borderlands-3-Hotfixes)
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
