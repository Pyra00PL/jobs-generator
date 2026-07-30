from __future__ import annotations

import sys
from pathlib import Path


BUILTIN_ICON_FILES = {
    "minecraft:stick": "stick.png",
    "minecraft:iron_ingot": "iron_ingot.png",
    "minecraft:copper_ingot": "copper_ingot.png",
    "minecraft:gold_ingot": "gold_ingot.png",
    "minecraft:netherite_ingot": "netherite_ingot.png",
    "minecraft:diamond": "diamond.png",
    "minecraft:emerald": "emerald.png",
    "minecraft:string": "string.png",
    "minecraft:nether_star": "nether_star.png",
    "minecraft:white_wool": "white_wool.png",
    "minecraft:leather": "leather.png",
    "minecraft:feather": "feather.png",
    "minecraft:flint": "flint.png",
    "minecraft:diamond_sword": "diamond_sword.png",
    "minecraft:diamond_pickaxe": "diamond_pickaxe.png",
    "minecraft:diamond_axe": "diamond_axe.png",
    "minecraft:diamond_hoe": "diamond_hoe.png",
    "minecraft:diamond_shovel": "diamond_shovel.png",
    "minecraft:diamond_helmet": "diamond_helmet.png",
    "minecraft:diamond_chestplate": "diamond_chestplate.png",
    "minecraft:diamond_leggings": "diamond_leggings.png",
    "minecraft:diamond_boots": "diamond_boots.png",
    "minecraft:netherite_sword": "netherite_sword.png",
    "minecraft:netherite_pickaxe": "netherite_pickaxe.png",
    "minecraft:netherite_axe": "netherite_axe.png",
    "minecraft:netherite_hoe": "netherite_hoe.png",
    "minecraft:netherite_shovel": "netherite_shovel.png",
    "minecraft:netherite_helmet": "netherite_helmet.png",
    "minecraft:netherite_chestplate": "netherite_chestplate.png",
    "minecraft:netherite_leggings": "netherite_leggings.png",
    "minecraft:netherite_boots": "netherite_boots.png",
    "minecraft:mace": "mace.png",
    "minecraft:trident": "trident.png",
}

WOOL_COLORS = (
    "white",
    "orange",
    "magenta",
    "light_blue",
    "yellow",
    "lime",
    "pink",
    "gray",
    "light_gray",
    "cyan",
    "purple",
    "blue",
    "brown",
    "green",
    "red",
    "black",
)


def resource_directory() -> Path:
    """Zwraca folder własnych ikon zastępczych programu."""

    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        return Path(bundled_root) / "assets" / "fallback_items"
    return (
        Path(__file__).resolve().parent.parent
        / "assets"
        / "fallback_items"
    )


def read_builtin_item_icons() -> dict[str, bytes]:
    """Wczytuje oryginalne ikony zastępcze dostarczane z programem."""

    icon_directory = resource_directory()
    icons: dict[str, bytes] = {}
    for item_id, file_name in BUILTIN_ICON_FILES.items():
        icon_path = icon_directory / file_name
        try:
            icons[item_id] = icon_path.read_bytes()
        except OSError:
            continue

    white_wool = icons.get("minecraft:white_wool")
    if white_wool:
        icons["minecraft:wool"] = white_wool
        for color in WOOL_COLORS:
            icons[f"minecraft:{color}_wool"] = white_wool
    return icons


def builtin_item_ids() -> set[str]:
    """Zwraca ID, dla których program ma ikonę zastępczą."""

    return set(BUILTIN_ICON_FILES)


def builtin_icon_id_for_tag(tag: str) -> str | None:
    """Dobiera czytelną ikonę Vanilla dla popularnego tagu składnika."""

    normalized = tag.strip().lower().lstrip("#")
    path = normalized.split(":", 1)[-1]
    tokens = {
        token
        for token in path.replace("\\", "/").replace("-", "_").split("/")
        if token
    }

    if "wool" in tokens or "wools" in tokens:
        return "minecraft:white_wool"

    direct_tokens = (
        ("netherite", "minecraft:netherite_ingot"),
        ("copper", "minecraft:copper_ingot"),
        ("iron", "minecraft:iron_ingot"),
        ("gold", "minecraft:gold_ingot"),
        ("diamond", "minecraft:diamond"),
        ("emerald", "minecraft:emerald"),
        ("stick", "minecraft:stick"),
        ("sticks", "minecraft:stick"),
        ("string", "minecraft:string"),
        ("strings", "minecraft:string"),
        ("nether_star", "minecraft:nether_star"),
        ("leather", "minecraft:leather"),
        ("feather", "minecraft:feather"),
        ("feathers", "minecraft:feather"),
        ("flint", "minecraft:flint"),
    )
    joined_path = "_".join(tokens)
    for token, item_id in direct_tokens:
        if token in tokens or token in joined_path:
            return item_id
    return None
