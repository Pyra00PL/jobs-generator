from __future__ import annotations

from dataclasses import dataclass

from core.defaults import USE_ARMOR, USE_TOOL, USE_WEAPON
from core.models import RestrictionRow
from core.recipe_scanner import CraftableItem


@dataclass
class MaterialRule:
    material: str
    level: int
    enabled: bool = True


DEFAULT_MATERIAL_RULES = [
    MaterialRule("iron", 10),
    MaterialRule("diamond", 20),
    MaterialRule("steel", 30),
    MaterialRule("netherite", 40),
]


def job_and_types(category: str) -> tuple[str, str]:
    if category == "pickaxe":
        return "miner", USE_TOOL
    if category == "axe":
        return "lumberjack", USE_TOOL
    if category == "hoe":
        return "farmer", USE_TOOL
    if category in {"sword", "weapon"}:
        return "hunter", USE_WEAPON
    if category == "armor":
        return "hunter", USE_ARMOR
    if category == "shovel":
        return "none", ""
    return "none", ""


def create_rows_from_material_rules(
    items: list[CraftableItem],
    rules: list[MaterialRule],
    existing_item_ids: set[str],
) -> tuple[list[RestrictionRow], list[str]]:
    level_by_material = {
        rule.material.strip().lower(): rule.level
        for rule in rules
        if rule.enabled and rule.material.strip() and rule.level > 0
    }
    created: list[RestrictionRow] = []
    skipped: list[str] = []

    for item in items:
        material = item.material.strip().lower()
        level = level_by_material.get(material)
        if level is None:
            continue
        if item.item_id in existing_item_ids:
            skipped.append(item.item_id)
            continue
        job, use_types = job_and_types(item.category)
        created.append(RestrictionRow(
            item_id=item.item_id,
            use_job=job,
            use_level=level if job != "none" else 0,
            smith_level=level,
            use_types=use_types,
            enabled=True,
        ))
        existing_item_ids.add(item.item_id)

    return created, skipped
