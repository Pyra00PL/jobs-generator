# Restriction Generator 1.0.2

[Polska wersja](README_PL.md)

Desktop application for creating Jobs+ and Item Restrictions datapacks for
Minecraft 1.21.1. It scans NeoForge mod JAR files, reads recipes, detects
materials and item categories, and generates editable job and level
requirements.

## Features

- Polish and English interface
- Vanilla defaults and editable profiles
- independent job and level requirements for usage, crafting, enchanting and
  repairing
- compatible requirements with the same item, job and level are merged into a
  single generated restriction
- recipe scanning, including shaped, shapeless, smithing, tags and many custom
  result fields
- optional detection of weapons and armor without recipes, including boss loot,
  using item models, tags, language entries and loot tables
- items without recipes receive no automatic Smithing requirement
- material rules that can update hundreds of items at once
- item and ingredient icons read from local Minecraft and mod JAR files
- original fallback icons when local game assets are unavailable
- visual recipe preview
- filtering, sorting, multi-selection and bulk removal
- Enter-activated searches in both restriction and recipe lists
- adding selected detected items as neutral rows for manual configuration
- selecting all items visible under the current filter
- selectable Minecraft compatibility profile in the Export tab
- ZIP export ready for a world's `datapacks` directory

Default Vanilla progression:

| Equipment | Crafting | Usage |
| --- | --- | --- |
| Iron | Smith 1 | relevant job 1 |
| Diamond | Smith 20 | relevant job 20 |
| Netherite | Smith 40 | relevant job 40 |
| Elytra | unchanged | Hunter 1 |
| Mace and trident | unchanged | Hunter 20 |

Pickaxes use Miner, axes use Lumberjack, hoes use Farmer, while weapons and
armor use Hunter. Enchanting defaults to Enchanter and repairing defaults to
Smith. Every generated entry remains editable.

## Windows release

Download `RestrictionGenerator-1.0.2-Windows.exe` from the
[Releases](../../releases) page. The executable is portable and does not
require Python.

Windows may show a SmartScreen warning because the executable is not
code-signed. Verify its checksum from the release before running it.

## Run from source

Requirements:

- Python 3.13
- Windows 10 or 11 (other desktop systems may work but are not tested)

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

## Build the Windows executable

Run `Zbuduj_aplikacje.bat`, or install the build requirements and use the
included PyInstaller specification:

```powershell
python -m pip install -r requirements-build.txt
pyinstaller --noconfirm RestrictionGenerator.spec
```

The result is written to `dist/RestrictionGenerator.exe`.

## Local assets and privacy

The application reads only files selected or discovered on the local
computer. It does not download or upload Minecraft or mod assets. The
repository and release contain no copied Mojang or third-party mod textures.
See [ASSETS.md](ASSETS.md) for details.

## Related projects

- [Jobs+ Armor Restrictions](https://github.com/Pyra00PL/jobs-armor-restrictions)
- [Jobs+ Requirement Tooltips](https://github.com/Pyra00PL/jobs-requirement-tooltips)

## License

The application source and original fallback artwork are available under the
MIT License. Third-party names and trademarks belong to their respective
owners.

NOT AN OFFICIAL MINECRAFT PRODUCT. NOT APPROVED BY OR ASSOCIATED WITH MOJANG
OR MICROSOFT.
