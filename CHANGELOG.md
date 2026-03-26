# Changelog

## Beta-1.0 (March 2026)
Features Added Since Alpha 1.0 (Mar 26, 2026)

### New Features

**Command Display Overhaul**

* Tree now shows the full simple command (`set /Game/Path/Object Property Value`) instead of just the object name
* Type column removed — single-column tree with hidden header for a cleaner look
* New `set\_mesh` command type for Type 6 mesh/level placement hotfixes
* `set\_dt` and `edit\_dt` recognized as valid commands (no longer flagged as errors)

**Per-Command Color Coding**

* Each command type has its own color: `set` = blue, `edit` = green, `early\_set` = cyan, `merge` = purple, `clone` = yellow/gold (#f8a715), `delete` = pink, `create` = teal, `news`/`rename` = orange, `exec` = maroon-pink, `set\_mesh` = soft yellow
* Colors customizable via Preferences → Command Color Coding (with color picker per command)
* Colors persist across sessions via QSettings

**Comment Display System**

* Comments show as separate bright yellow (#ffd700) italic rows above their entry
* No checkbox on comment rows — they're visual labels tied to the entry below
* Clicking a comment row shows the linked entry's details
* Comments survive file save/reload in both .bl3hotfix and .blmod formats

**Preferences Menu (New)**

* Moved Theme and Font \& Size Settings from View menu into new Preferences menu
* Show Detail Panel toggle (detail panel hidden by default, saves space)
* Keyboard Shortcuts editor with press-to-edit capture (supports keys, mouse buttons, scroll wheel)
* Command Color Coding editor with per-command color pickers
* All preferences persist across sessions

**Keyboard Shortcut Editor**

* Press-to-edit: click a shortcut field, then press any key combo, mouse button, or scroll wheel
* Supports Ctrl/Shift/Alt modifiers with mouse buttons (LeftClick, RightClick, MiddleClick, Mouse4, Mouse5)
* Supports mouse wheel bindings (WheelUp, WheelDown, WheelLeft, WheelRight)
* Per-shortcut reset button with refresh icon
* Reset All to Defaults button
* Custom wheel shortcuts work in main tree (e.g., Ctrl+WheelUp for zoom)

**Tutorial System**

* 6-page walkthrough: Welcome, Creating \& Opening Files, Categories \& Entries, Enable/Disable \& Color Coding, Object Explorer, Tips \& Shortcuts
* Shows automatically on first launch (can be dismissed with "Don't show on startup")
* Accessible anytime via Help → Tutorial
* Back/Next navigation with page indicator

**Independent Windows**

* All dialogs (entry edit, create, metadata, shortcuts, colors, font, tutorial) open as independent windows
* Dialogs don't force-overlap with the main window or Object Explorer
* Multiple entry editors can be open simultaneously (one per entry, prevents duplicates)
* Double-clicking or pressing Insert on an already-open entry focuses its existing editor

**Object Explorer Auto-Load Datapack**

* Object Explorer now auto-detects datapack files (.sqlite3, .sqlite, .db, .sql) in the AppData datapacks folder
* Just drop `data.sql` into `%LOCALAPPDATA%\\Programs\\OpenBL3CMM\\datapacks\\` and it loads automatically
* Falls back to last used database path if AppData scan finds nothing

**Object Explorer Preferences Menu**

* Added menu bar to Object Explorer with Preferences → Keyboard Shortcuts
* Removed Class column from tree — cleaner single-column layout with hidden header

### Improvements

**Insert Key Context-Sensitive**

* Insert key now edits the selected entry (if an entry is highlighted)
* Insert key adds a new entry (if a category is selected or nothing is selected)

**Entry Adding**

* `+ Entry` toolbar button adds to root level if no category was ever selected (instead of creating a "General" category)
* Contextual add captures target category before opening dialog (non-modal fix)
* Root-level entries render correctly in the tree

**Validation Relaxed**

* `set` with just object + attribute and no value is now valid (clears/sets to empty)
* Spark Type 6 and other unusual formats no longer flagged as errors
* Removed overly strict field count checks for Spark format
* Short-form paths (without `/`) no longer trigger warnings

**Parser Improvements**

* Disabled hotfix detection now only triggers for `#Spark...` or `#Inject...` lines (not `# Set the barrel mesh` which was being eaten as a disabled `set` command)
* Empty lines no longer clear pending comments — comments survive blank lines between them and the hotfix
* Spark format detection uses case-insensitive prefix matching (`spark` or `inject`)
* .blmod parser now correctly reads `'comment'` items and attaches them to the next entry (was silently discarding them)

**Command System**

* `\_original\_cmd` field on HotfixEntry preserves the original command type (clone, delete, etc.) through Spark round-trip
* Commands like `clone`, `delete`, `add`, `remove` no longer get changed to `set` after adding
* `simple\_type` extracts first word correctly for commands stored as raw lines (e.g., `clone Part\_PS\_JAK...`)

**AppData Path Updated**

* Changed from `AppData/Roaming/OpenBL3CMM` to `AppData/Local/Programs/OpenBL3CMM`
* Installer updated to create folders at the correct location
* Datapacks, backups, and mods folders created by both installer and app

### Bug Fixes

* Fixed `closeEvent` crash when window closes before UI initialization (`'MainWindow' object has no attribute 'tree'`)
* Fixed `DEFAULT\_SHORTCUTS` name collision between file dialog directory shortcuts and keyboard shortcuts (renamed to `DEFAULT\_KEY\_SHORTCUTS`)
* Fixed `QScrollArea` not imported (NameError in shortcut editor)
* Fixed dialogs losing theme styling when set to parentless (now uses `QApplication.instance()` stylesheet)
* Fixed `addChild` before `\_style\_entry\_item` — Qt needs the item in the tree before `setForeground` takes effect
* Fixed checkbox toggle losing entry color (now recovers command-type color)
* Fixed `\_sync\_children\_checkboxes` not passing color when toggling category checkbox
* Fixed scroll not working when hovering over shortcut fields (wheel events now pass through when not listening)

\---

## Alpha-1.0 (March 2026)

Features Added Since Alpha 0.1.0 (Mar 20, 2026)

Session 2 



BLIMP tag parser/serializer for mod metadata

.blmod YAML format support (read/write)

App icon (Vault symbol, multi-size .ico, 16-256px)

Windows taskbar icon fix via AppUserModelID

PyInstaller spec file + build.bat



Session 3 — Object Explorer



Full Object Explorer window (Tools → Object Explorer, Ctrl+E)

SQLite datapack loading with auto-detect (bl3refs)

Compressed SQLite datapac

Tree browser with lazy-loading, search by path/class/properties

References FROM/TO with double-click navigation

Tabbed properties panel — closeable, moveable, "+" for new tabs

Each tab has Save Current / Saved Items clipboard

Clickable links in properties (/Game/... paths, excludes /Script/)

Left-click → navigate in tab, Middle-click → new tab

Back/Forward buttons (◀ ▶) with full history

Alt+Left/Right, Mouse 4/5, Ctrl+Wheel zoom

Ctrl+F search dialog per active tab (regex, match case, wrap)

F1 shortcuts dialog — key capture with keyboard, mouse, scroll wheel, dual bindings



Session 3 — Syntax \& Editing



Syntax highlighter for edit dialogs (command/object/property coloring)

Validation on OK with problem list dialog

BLCMM-style auto-format for struct values with proper indentation

Auto-formats on load when entry has structs

Bracket matching (yellow highlight on matching ( ) pairs)

Struct spacing cleanup on save (( Key=Val ) → (Key=Val))



Session 3  — Commands



Type 2 DataTable hotfixes handled transparently (column name hidden)

Column auto-recovered from original raw\_line on edit

Fixed Type 1 field parsing (no more double-zero bug)

Clean round-trip for all command types

Removed overly strict / path validation



Session 3  — File \& Tree Fixes



Non-modal edit/new dialogs (Object Explorer accessible while editing)

Disabled entries exported as #SparkPatchEntry,...

Root category flattening on load (no more nested "root" accumulation)

Exporter skips redundant "root" wrappers

Drag-drop index fix after removal from same parent

Datapack generator (generate\_datapack.py) for creating bl3data.sqlite3

Updated PyInstaller spec with all files

