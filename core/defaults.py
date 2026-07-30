from core.models import RestrictionRow

USE_TOOL = "use_item,item_break_block,hurt_entity,repair,enchant"
USE_WEAPON = "use_item,item_break_block,hurt_entity,repair,enchant"
USE_ARMOR = "use_item,repair,enchant"


def vanilla_rows() -> list[RestrictionRow]:
    rows: list[RestrictionRow] = []
    for material, level in (("diamond", 20), ("netherite", 40)):
        rows.extend([
            RestrictionRow(f"minecraft:{material}_pickaxe", "miner", level, level, USE_TOOL),
            RestrictionRow(f"minecraft:{material}_axe", "lumberjack", level, level, USE_TOOL),
            RestrictionRow(f"minecraft:{material}_hoe", "farmer", level, level, USE_TOOL),
            RestrictionRow(f"minecraft:{material}_sword", "hunter", level, level, USE_WEAPON),
        ])
        for armor in ("helmet", "chestplate", "leggings", "boots"):
            rows.append(RestrictionRow(f"minecraft:{material}_{armor}", "hunter", level, level, USE_ARMOR))
    # Łopaty: tylko produkcja przez Smitha; brak klasy używania zgodnie z ustaleniami.
    rows.extend([
        RestrictionRow("minecraft:diamond_shovel", "none", 0, 20, ""),
        RestrictionRow("minecraft:netherite_shovel", "none", 0, 40, ""),
        RestrictionRow("minecraft:mace", "hunter", 20, 0, USE_WEAPON),
        RestrictionRow("minecraft:trident", "hunter", 20, 0, USE_WEAPON),
    ])
    return rows
