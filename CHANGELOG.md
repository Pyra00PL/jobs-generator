# Changelog

## 1.0.2

- added an enabled-by-default scanner option for weapons and armor without
  crafting recipes, such as boss loot
- detects non-craftable equipment from item definitions, models, language
  entries, item tags and loot tables
- marks these items as having no recipe and disables their recipe-preview
  button
- material rules no longer create a Smithing restriction for an item without
  a crafting recipe
- avoids common model variants and foreign Vanilla tag entries during fallback
  scanning

## 1.0.1

- merged restrictions that target the same item, job and level into one JSON
  containing all matching restriction types
- fixed manually added items so selecting Usage automatically supplies safe
  use restriction types
- added Iron Vanilla equipment with level 1 defaults
- added Elytra with Hunter, Enchanter and Smith level 1 defaults

## 1.0.0

- renamed the application to Restriction Generator
- added an Enter-activated search field to the Restrictions tab
- changed Materials and recipes filtering so it runs only after pressing Enter
- added an action for inserting only selected detected items as neutral,
  manually editable restriction rows
- added **Select all visible** to the filtered Restrictions and detected-items
  lists
- disabled mouse-wheel changes in the Use job fields
- enlarged and equalized the up/down arrow hitboxes in numeric fields
- separated enchanting and repairing from the Use job restriction
- added independent job and level editors for Enchanting (default Enchanter)
  and Repairing (default Smith)
- combined Usage and Smithing into consistent job/level editors
- made the Smithing job configurable while keeping Smith as the default
- widened every numeric level field and its composite table column
- made the Description column update immediately after manual changes
- restored the Minecraft version selector in the Export tab and version-aware
  datapack metadata
- added automatic migration of legacy profiles that stored `enchant` and
  `repair` inside use restriction types

## 0.14.0

- added 33 original fallback icons for common ingredients and Vanilla equipment
- added local discovery of the Minecraft 1.21.1 client JAR for accurate
  inventory icons
- retained local model and texture loading for modded items
- ensured distributed files contain no copied Minecraft or third-party mod
  textures

Earlier development changes are documented in the repository history.
