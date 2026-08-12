from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CraftableItem:
    item_id: str
    material: str
    category: str
    source_mod: str
    recipe_path: str
    confidence: str
    material_source: str
    recipe_data: dict[str, Any] = field(default_factory=dict)

    @property
    def has_recipe(self) -> bool:
        return bool(self.recipe_path)


CATEGORY_RULES: tuple[tuple[str, str], ...] = (
    ("weapons", "weapon"),
    ("weapon", "weapon"),
    ("armors", "armor"),
    ("armor", "armor"),
    ("pickaxe", "pickaxe"),
    ("battle_axe", "axe"),
    ("battleaxe", "axe"),
    ("axe", "axe"),
    ("hoe", "hoe"),
    ("sword", "sword"),
    ("longsword", "weapon"),
    ("greatsword", "weapon"),
    ("claymore", "weapon"),
    ("dagger", "weapon"),
    ("knife", "weapon"),
    ("katana", "weapon"),
    ("rapier", "weapon"),
    ("spear", "weapon"),
    ("lance", "weapon"),
    ("pike", "weapon"),
    ("halberd", "weapon"),
    ("glaive", "weapon"),
    ("polearm", "weapon"),
    ("scythe", "weapon"),
    ("hammer", "weapon"),
    ("warhammer", "weapon"),
    ("mace", "weapon"),
    ("morningstar", "weapon"),
    ("morning_star", "weapon"),
    ("flail", "weapon"),
    ("club", "weapon"),
    ("saber", "weapon"),
    ("sabre", "weapon"),
    ("cutlass", "weapon"),
    ("staff", "weapon"),
    ("wand", "weapon"),
    ("trident", "weapon"),
    ("bow", "weapon"),
    ("crossbow", "weapon"),
    ("helmet", "armor"),
    ("chestplate", "armor"),
    ("leggings", "armor"),
    ("boots", "armor"),
    ("shield", "armor"),
    ("buckler", "armor"),
    ("pavese", "armor"),
    ("pavise", "armor"),
    ("rondache", "armor"),
    ("tartsche", "armor"),
    ("scutum", "armor"),
    ("targe", "armor"),
    ("target", "armor"),
    ("shovel", "shovel"),
)

GENERIC_INGREDIENT_WORDS = {
    "stick", "sticks", "rod", "rods", "handle", "handles", "plank", "planks",
    "string", "leather", "wool", "nugget", "nuggets", "gem", "gems", "dust",
    "plate", "plates", "sheet", "sheets", "upgrade", "template", "smithing_template",
}

MATERIAL_CONTAINER_WORDS = {
    "ingot", "ingots", "gem", "gems", "ore", "ores", "block", "blocks", "plate",
    "plates", "sheet", "sheets", "nugget", "nuggets", "dust", "dusts", "storage_blocks",
}


def scan_craftable_items(jar_files: list[Path]) -> list[CraftableItem]:
    scanned: list[CraftableItem] = []
    for jar_file in jar_files:
        scanned.extend(scan_jar_recipes(jar_file))
    return merge_craftable_items(scanned)


def merge_craftable_items(items: list[CraftableItem]) -> list[CraftableItem]:
    results: dict[str, CraftableItem] = {}
    for item in items:
        previous = results.get(item.item_id)
        if previous is None or item_quality(item) > item_quality(previous):
            results[item.item_id] = item
    return sorted(results.values(), key=lambda value: value.item_id)


def scan_jar_recipes(jar_file: Path) -> list[CraftableItem]:
    found: list[CraftableItem] = []
    try:
        with zipfile.ZipFile(jar_file) as archive:
            tagged_categories = read_tagged_categories(archive)
            for recipe_path in archive.namelist():
                normalized = recipe_path.replace("\\", "/")
                if not normalized.endswith(".json"):
                    continue
                if not re.match(r"^data/[^/]+/recipes?/", normalized):
                    continue
                try:
                    payload = json.loads(archive.read(recipe_path).decode("utf-8-sig"))
                except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
                    continue
                if not isinstance(payload, dict):
                    continue
                output = extract_result_id(payload)
                if not output:
                    continue
                category = detect_category(output)
                if category == "other":
                    category = tagged_categories.get(output, "other")
                ingredients = extract_ingredients(payload)
                material, confidence, source = detect_material(output, ingredients)
                namespace = output.split(":", 1)[0]
                found.append(CraftableItem(
                    item_id=output,
                    material=material,
                    category=category,
                    source_mod=namespace,
                    recipe_path=recipe_path,
                    confidence=confidence,
                    material_source=source,
                    recipe_data=payload,
                ))
    except (OSError, zipfile.BadZipFile):
        return []
    return found


def scan_jar_equipment_without_recipes(
    jar_file: Path,
    recipe_item_ids: set[str] | None = None,
) -> list[CraftableItem]:
    """Finds weapons and armor exposed by item models or item tags.

    Some equipment is obtained as boss loot and therefore has no recipe JSON.
    Item model paths provide a conservative list of possible registered items;
    item tags additionally recognize equipment whose ID has a custom name.
    """

    recipe_ids = {
        item_id.strip().lower()
        for item_id in (recipe_item_ids or set())
    }
    found: list[CraftableItem] = []
    try:
        with zipfile.ZipFile(jar_file) as archive:
            tagged_categories = read_tagged_categories(archive)
            item_definition_candidates: set[str] = set()
            model_candidates: set[str] = set()
            model_pattern = re.compile(
                r"^assets/([^/]+)/models/item/(.+)\.json$",
                re.IGNORECASE,
            )
            item_definition_pattern = re.compile(
                r"^assets/([^/]+)/items/(.+)\.json$",
                re.IGNORECASE,
            )
            for entry_name in archive.namelist():
                normalized_path = entry_name.replace("\\", "/")
                match = model_pattern.match(normalized_path)
                if match is not None:
                    item_id = normalize_item_id(
                        f"{match.group(1)}:{match.group(2)}"
                    )
                    if item_id:
                        model_candidates.add(item_id)
                    continue
                match = item_definition_pattern.match(normalized_path)
                if match is not None:
                    item_id = normalize_item_id(
                        f"{match.group(1)}:{match.group(2)}"
                    )
                    if item_id:
                        item_definition_candidates.add(item_id)

            language_candidates = read_item_ids_from_languages(archive)
            loot_candidates = read_item_ids_from_loot_tables(archive)
            owned_namespaces = {
                item_id.split(":", 1)[0]
                for item_id in (
                    model_candidates
                    | item_definition_candidates
                    | language_candidates
                )
            }
            candidates = (
                set(tagged_categories)
                | loot_candidates
                | item_definition_candidates
                | (model_candidates & language_candidates)
            )
            if not language_candidates:
                candidates.update(
                    item_id
                    for item_id in model_candidates
                    if is_likely_primary_item_model(item_id)
                )

            for item_id in sorted(candidates):
                if item_id in recipe_ids:
                    continue
                if item_id.startswith("minecraft:"):
                    continue
                item_namespace = item_id.split(":", 1)[0]
                if (
                    owned_namespaces
                    and item_namespace not in owned_namespaces
                ):
                    continue
                category = tagged_categories.get(
                    item_id,
                    detect_category(item_id),
                )
                if category not in {"weapon", "sword", "armor"}:
                    continue
                material, confidence, source = detect_material(
                    item_id,
                    [],
                )
                found.append(CraftableItem(
                    item_id=item_id,
                    material=material,
                    category=category,
                    source_mod=item_id.split(":", 1)[0],
                    recipe_path="",
                    confidence=confidence,
                    material_source=source,
                    recipe_data={},
                ))
    except (OSError, zipfile.BadZipFile):
        return []
    return found


def is_likely_primary_item_model(item_id: str) -> bool:
    """Rejects common model variants when a mod has no language registry."""

    path = item_id.split(":", 1)[-1]
    if "/" in path:
        return False
    variant_tokens = (
        "_3d",
        "_icon",
        "_broken",
        "_charged",
        "_open",
        "_pulling",
        "_blocking",
        "_trim",
    )
    return not any(token in path for token in variant_tokens)


def read_item_ids_from_languages(
    archive: zipfile.ZipFile,
) -> set[str]:
    """Reads registered-looking item IDs from Minecraft language keys."""

    item_ids: set[str] = set()
    language_pattern = re.compile(
        r"^assets/([^/]+)/lang/(?:en_us|en_gb)\.json$",
        re.IGNORECASE,
    )
    for entry_name in archive.namelist():
        normalized_path = entry_name.replace("\\", "/")
        language_match = language_pattern.match(normalized_path)
        if language_match is None:
            continue
        asset_namespace = language_match.group(1).lower()
        item_prefix = f"item.{asset_namespace}."
        try:
            payload = json.loads(
                archive.read(entry_name).decode("utf-8-sig")
            )
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        for translation_key in payload:
            if not isinstance(translation_key, str):
                continue
            normalized_key = translation_key.lower()
            if not normalized_key.startswith(item_prefix):
                continue
            item_id = normalize_item_id(
                f"{asset_namespace}:{normalized_key[len(item_prefix):]}"
            )
            if item_id:
                item_ids.add(item_id)
    return item_ids


def read_item_ids_from_loot_tables(
    archive: zipfile.ZipFile,
) -> set[str]:
    """Finds concrete item entries used by loot tables, including boss loot."""

    item_ids: set[str] = set()
    loot_pattern = re.compile(
        r"^data/[^/]+/loot_tables?/.+\.json$",
        re.IGNORECASE,
    )
    for entry_name in archive.namelist():
        normalized_path = entry_name.replace("\\", "/")
        if loot_pattern.match(normalized_path) is None:
            continue
        try:
            payload = json.loads(
                archive.read(entry_name).decode("utf-8-sig")
            )
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        collect_loot_item_ids(payload, item_ids)
    return item_ids


def collect_loot_item_ids(value: Any, output: set[str]) -> None:
    if isinstance(value, list):
        for element in value:
            collect_loot_item_ids(element, output)
        return
    if not isinstance(value, dict):
        return

    entry_type = value.get("type")
    item_name = value.get("name")
    if (
        entry_type in {"item", "minecraft:item"}
        and isinstance(item_name, str)
    ):
        normalized = normalize_item_id(item_name)
        if normalized:
            output.add(normalized)

    for nested in value.values():
        collect_loot_item_ids(nested, output)


def read_tagged_categories(archive: zipfile.ZipFile) -> dict[str, str]:
    """Rozpoznaje wyposażenie z tagów itemów, także gdy nazwa jest nietypowa."""

    categories: dict[str, str] = {}
    for tag_path in archive.namelist():
        normalized = tag_path.replace("\\", "/").lower()
        if not normalized.endswith(".json"):
            continue
        if not re.match(r"^data/[^/]+/tags/items?/", normalized):
            continue
        category = detect_category(normalized)
        if category == "other":
            continue
        try:
            payload = json.loads(archive.read(tag_path).decode("utf-8-sig"))
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        values = payload.get("values", []) if isinstance(payload, dict) else []
        if not isinstance(values, list):
            continue
        for value in values:
            item_id = value if isinstance(value, str) else value.get("id") if isinstance(value, dict) else None
            if isinstance(item_id, str) and not item_id.startswith("#"):
                normalized_id = normalize_item_id(item_id)
                if normalized_id:
                    categories[normalized_id] = category
    return categories


def extract_result_id(payload: dict[str, Any]) -> str | None:
    """Odczytuje wynik receptury także z popularnych niestandardowych pól."""

    result_keys = (
        "result",
        "output",
        "results",
        "outputs",
        "product",
        "result_item",
        "output_item",
        "primary_output",
        "assembled",
    )
    for key in result_keys:
        if key not in payload:
            continue
        result_id = extract_item_id(payload[key])
        if result_id:
            return result_id
    return None


def extract_item_id(value: Any) -> str | None:
    if isinstance(value, str):
        return normalize_item_id(value)
    if isinstance(value, list):
        for element in value:
            result_id = extract_item_id(element)
            if result_id:
                return result_id
        return None
    if not isinstance(value, dict):
        return None

    for key in ("id", "item"):
        item_id = value.get(key)
        if isinstance(item_id, str):
            normalized = normalize_item_id(item_id)
            if normalized:
                return normalized

    for key in ("result", "output", "stack", "value"):
        if key in value:
            result_id = extract_item_id(value[key])
            if result_id:
                return result_id
    return None


def normalize_item_id(value: str) -> str | None:
    value = value.strip().lower()
    if re.fullmatch(r"[a-z0-9_.-]+:[a-z0-9_./-]+", value):
        return value
    return None


def extract_ingredients(payload: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("key", "ingredients", "base", "addition", "template", "ingredient", "input"):
        if key in payload:
            collect_ingredient_values(payload[key], values)
    return values


def extract_direct_ingredient_ids(
    payload: dict[str, Any],
) -> set[str]:
    item_ids: set[str] = set()
    for key in (
        "key",
        "ingredients",
        "base",
        "addition",
        "template",
        "ingredient",
        "input",
    ):
        if key in payload:
            collect_direct_item_ids(payload[key], item_ids)
    return item_ids


def collect_direct_item_ids(value: Any, output: set[str]) -> None:
    if isinstance(value, str):
        if value.startswith("#"):
            return
        normalized = normalize_item_id(value)
        if normalized:
            output.add(normalized)
        return
    if isinstance(value, list):
        for element in value:
            collect_direct_item_ids(element, output)
        return
    if not isinstance(value, dict):
        return

    for key in ("item", "id"):
        item_id = value.get(key)
        if isinstance(item_id, str):
            normalized = normalize_item_id(item_id)
            if normalized:
                output.add(normalized)
    for key, nested in value.items():
        if key not in {"item", "id", "tag", "count"}:
            collect_direct_item_ids(nested, output)


def extract_ingredient_tag_ids(
    payload: dict[str, Any],
) -> set[str]:
    """Zwraca tagi użyte w polach składników receptury."""

    tag_ids: set[str] = set()
    for key in (
        "key",
        "ingredients",
        "base",
        "addition",
        "template",
        "ingredient",
        "input",
    ):
        if key in payload:
            collect_ingredient_tag_ids(payload[key], tag_ids)
    return tag_ids


def collect_ingredient_tag_ids(
    value: Any,
    output: set[str],
) -> None:
    if isinstance(value, str):
        if value.startswith("#"):
            normalized = normalize_tag_id(value)
            if normalized:
                output.add(normalized)
        return
    if isinstance(value, list):
        for element in value:
            collect_ingredient_tag_ids(element, output)
        return
    if not isinstance(value, dict):
        return

    tag = value.get("tag")
    if isinstance(tag, str):
        normalized = normalize_tag_id(tag)
        if normalized:
            output.add(normalized)
    for key, nested in value.items():
        if key not in {"item", "id", "tag", "count"}:
            collect_ingredient_tag_ids(nested, output)


def read_item_tag_registry(
    jar_files: list[Path],
) -> dict[str, list[str]]:
    """Łączy definicje tagów przedmiotów ze wskazanych archiwów JAR."""

    registry: dict[str, list[str]] = {}
    tag_pattern = re.compile(
        r"^data/([^/]+)/tags/items?/(.+)\.json$",
        re.IGNORECASE,
    )
    for jar_file in jar_files:
        try:
            with zipfile.ZipFile(jar_file) as archive:
                for entry_name in archive.namelist():
                    normalized_path = entry_name.replace("\\", "/")
                    match = tag_pattern.match(normalized_path)
                    if not match:
                        continue
                    tag_id = (
                        f"{match.group(1).lower()}:"
                        f"{match.group(2).lower()}"
                    )
                    try:
                        payload = json.loads(
                            archive.read(entry_name).decode("utf-8-sig")
                        )
                    except (
                        KeyError,
                        UnicodeDecodeError,
                        json.JSONDecodeError,
                    ):
                        continue
                    if not isinstance(payload, dict):
                        continue
                    values = payload.get("values", [])
                    if not isinstance(values, list):
                        continue
                    if payload.get("replace") is True:
                        registry[tag_id] = []
                    tag_values = registry.setdefault(tag_id, [])
                    for value in values:
                        raw_id = (
                            value
                            if isinstance(value, str)
                            else value.get("id")
                            if isinstance(value, dict)
                            else None
                        )
                        if not isinstance(raw_id, str):
                            continue
                        normalized_value = normalize_tag_value(raw_id)
                        if (
                            normalized_value
                            and normalized_value not in tag_values
                        ):
                            tag_values.append(normalized_value)
        except (OSError, zipfile.BadZipFile):
            continue
    return registry


def resolve_item_tag(
    tag_id: str,
    registry: dict[str, list[str]],
    maximum_depth: int = 16,
) -> list[str]:
    """Rozwija tag i jego tagi zagnieżdżone do konkretnych Item ID."""

    normalized = normalize_tag_id(tag_id)
    if not normalized:
        return []

    resolved: list[str] = []
    visited: set[str] = set()

    def visit(current_tag: str, depth: int) -> None:
        if depth > maximum_depth or current_tag in visited:
            return
        visited.add(current_tag)
        for value in registry.get(current_tag, []):
            if value.startswith("#"):
                nested = normalize_tag_id(value)
                if nested:
                    visit(nested, depth + 1)
                continue
            item_id = normalize_item_id(value)
            if item_id and item_id not in resolved:
                resolved.append(item_id)

    visit(normalized, 0)
    return resolved


def normalize_tag_id(value: str) -> str | None:
    normalized = value.strip().lower().lstrip("#")
    return normalize_item_id(normalized)


def normalize_tag_value(value: str) -> str | None:
    normalized = value.strip().lower()
    if normalized.startswith("#"):
        tag_id = normalize_tag_id(normalized)
        return f"#{tag_id}" if tag_id else None
    return normalize_item_id(normalized)


def collect_ingredient_values(value: Any, output: list[str]) -> None:
    if isinstance(value, str):
        output.append(value.lower())
    elif isinstance(value, list):
        for element in value:
            collect_ingredient_values(element, output)
    elif isinstance(value, dict):
        for key in ("item", "tag", "id"):
            item = value.get(key)
            if isinstance(item, str):
                output.append(item.lower())
        for key, nested in value.items():
            if key not in {"item", "tag", "id", "count"}:
                collect_ingredient_values(nested, output)


def detect_category(item_id: str) -> str:
    # Obsługuje zarówno ID przedmiotu (mod:item), jak i ścieżkę tagu
    # (data/mod/tags/item/weapons/lances.json).
    path = item_id.split(":", 1)[-1].lower()
    for token, category in CATEGORY_RULES:
        if token in path:
            return category
    return "other"


def detect_material(item_id: str, ingredients: list[str]) -> tuple[str, str, str]:
    output_path = item_id.split(":", 1)[1]
    output_tokens = tokenize(output_path)
    category_tokens = {token for token, _ in CATEGORY_RULES}
    name_candidates = [
        token for token in output_tokens
        if token not in category_tokens and token not in {"reinforced", "heavy", "light", "long", "short", "great", "war"}
    ]

    ingredient_candidates: list[tuple[str, str]] = []
    for ingredient in ingredients:
        path = ingredient.split(":", 1)[-1]
        tokens = tokenize(path)
        filtered = [t for t in tokens if t not in MATERIAL_CONTAINER_WORDS and t not in GENERIC_INGREDIENT_WORDS]
        for token in filtered:
            if len(token) >= 3:
                ingredient_candidates.append((token, ingredient))

    # Najpewniejsze: materiał występuje jednocześnie w nazwie produktu i składniku/tagu.
    for token in name_candidates:
        for ingredient_token, ingredient in ingredient_candidates:
            if token == ingredient_token:
                return token, "wysoka", f"receptura: {ingredient}"

    # Tagi typu c:ingots/steel albo forge:ingots/steel.
    for ingredient in ingredients:
        path = ingredient.split(":", 1)[-1]
        tokens = tokenize(path)
        if any(container in tokens for container in MATERIAL_CONTAINER_WORDS):
            candidates = [t for t in tokens if t not in MATERIAL_CONTAINER_WORDS and t not in GENERIC_INGREDIENT_WORDS]
            if candidates:
                return candidates[-1], "wysoka", f"tag/składnik: {ingredient}"

    # Konkretne składniki kończące się np. steel_ingot.
    for token, ingredient in ingredient_candidates:
        if token not in GENERIC_INGREDIENT_WORDS:
            return token, "średnia", f"składnik: {ingredient}"

    if name_candidates:
        return name_candidates[0], "średnia", "nazwa przedmiotu"

    return "unknown", "niska", "nie wykryto"


def tokenize(value: str) -> list[str]:
    return [token for token in re.split(r"[/_.-]+", value.lower()) if token]


def item_quality(item: CraftableItem) -> tuple[int, int, int]:
    """Preferuje wpis z rozpoznaną kategorią i pewniejszym materiałem."""

    return (
        1 if item.has_recipe else 0,
        1 if item.category != "other" else 0,
        confidence_rank(item.confidence),
    )


def confidence_rank(value: str) -> int:
    return {"niska": 1, "średnia": 2, "wysoka": 3}.get(value, 0)
