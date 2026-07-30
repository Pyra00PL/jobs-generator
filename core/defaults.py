from core.models import RestrictionRow

USE_TOOL = "use_item,item_break_block,hurt_entity"
USE_WEAPON = "use_item,item_break_block,hurt_entity"
USE_ARMOR = "use_item"


def vanilla_rows() -> list[RestrictionRow]:
    rows: list[RestrictionRow] = []
    for material, level in (("diamond", 20), ("netherite", 40)):
        rows.extend([
            RestrictionRow(f"minecraft:{material}_pickaxe", "miner", level, level, USE_TOOL, enchant_level=level, repair_level=level),
            RestrictionRow(f"minecraft:{material}_axe", "lumberjack", level, level, USE_TOOL, enchant_level=level, repair_level=level),
            RestrictionRow(f"minecraft:{material}_hoe", "farmer", level, level, USE_TOOL, enchant_level=level, repair_level=level),
            RestrictionRow(f"minecraft:{material}_sword", "hunter", level, level, USE_WEAPON, enchant_level=level, repair_level=level),
        ])
        for armor in ("helmet", "chestplate", "leggings", "boots"):
            rows.append(RestrictionRow(f"minecraft:{material}_{armor}", "hunter", level, level, USE_ARMOR, enchant_level=level, repair_level=level))
    # Łopaty: tylko produkcja przez Smitha; brak klasy używania zgodnie z ustaleniami.
    rows.extend([
        RestrictionRow("minecraft:diamond_shovel", "none", 0, 20, ""),
        RestrictionRow("minecraft:netherite_shovel", "none", 0, 40, ""),
        RestrictionRow("minecraft:mace", "hunter", 20, 0, USE_WEAPON, enchant_level=20, repair_level=20),
        RestrictionRow("minecraft:trident", "hunter", 20, 0, USE_WEAPON, enchant_level=20, repair_level=20),
    ])
    return rows
