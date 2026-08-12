import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from core.materials import MaterialRule, create_rows_from_material_rules
from core.recipe_scanner import (
    CraftableItem,
    merge_craftable_items,
    scan_jar_equipment_without_recipes,
    scan_jar_recipes,
)


class NonCraftableEquipmentScannerTests(unittest.TestCase):
    def test_scanner_finds_boss_loot_weapon_without_recipe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            jar_path = Path(temporary) / "bossmod.jar"
            self.write_test_jar(jar_path)

            items = scan_jar_equipment_without_recipes(jar_path)

        by_id = {item.item_id: item for item in items}
        weapon = by_id["bossmod:obsidian_lance"]
        self.assertEqual(weapon.category, "weapon")
        self.assertEqual(weapon.material, "obsidian")
        self.assertFalse(weapon.has_recipe)
        self.assertEqual(weapon.recipe_path, "")

    def test_scanner_uses_equipment_tags_for_custom_names(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            jar_path = Path(temporary) / "bossmod.jar"
            self.write_test_jar(jar_path)

            items = scan_jar_equipment_without_recipes(jar_path)

        by_id = {item.item_id: item for item in items}
        self.assertIn("bossmod:crown_of_ashes", by_id)
        self.assertEqual(
            by_id["bossmod:crown_of_ashes"].category,
            "armor",
        )
        self.assertNotIn("bossmod:decorative_statue", by_id)

    def test_existing_recipe_is_not_duplicated_by_fallback_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            jar_path = Path(temporary) / "bossmod.jar"
            self.write_test_jar(jar_path)

            recipes = scan_jar_recipes(jar_path)
            fallbacks = scan_jar_equipment_without_recipes(
                jar_path,
                {item.item_id for item in recipes},
            )
            merged = merge_craftable_items(recipes + fallbacks)

        matching = [
            item
            for item in merged
            if item.item_id == "bossmod:crafted_sword"
        ]
        self.assertEqual(len(matching), 1)
        self.assertTrue(matching[0].has_recipe)

    def test_material_rule_does_not_add_smithing_without_recipe(self) -> None:
        item = CraftableItem(
            item_id="bossmod:steel_boss_sword",
            material="steel",
            category="sword",
            source_mod="bossmod",
            recipe_path="",
            confidence="medium",
            material_source="item name",
            recipe_data={},
        )

        rows, skipped = create_rows_from_material_rules(
            [item],
            [MaterialRule("steel", 30)],
            set(),
        )

        self.assertEqual(skipped, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].use_level, 30)
        self.assertEqual(rows[0].smith_level, 0)
        self.assertEqual(rows[0].enchant_level, 30)
        self.assertEqual(rows[0].repair_level, 30)

    @staticmethod
    def write_test_jar(path: Path) -> None:
        recipe = {
            "type": "minecraft:crafting_shaped",
            "pattern": ["X", "S"],
            "key": {
                "X": {"item": "minecraft:iron_ingot"},
                "S": {"item": "minecraft:stick"},
            },
            "result": {"id": "bossmod:crafted_sword"},
        }
        loot_table = {
            "pools": [{
                "entries": [{
                    "type": "minecraft:item",
                    "name": "bossmod:obsidian_lance",
                }]
            }]
        }
        armor_tag = {
            "values": ["bossmod:crown_of_ashes"]
        }
        language = {
            "item.bossmod.obsidian_lance": "Obsidian Lance",
            "item.bossmod.crown_of_ashes": "Crown of Ashes",
            "item.bossmod.decorative_statue": "Decorative Statue",
            "item.bossmod.crafted_sword": "Crafted Sword",
        }

        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(
                "assets/bossmod/lang/en_us.json",
                json.dumps(language),
            )
            for item_path in language:
                item_name = item_path.split(".", 2)[-1]
                archive.writestr(
                    f"assets/bossmod/models/item/{item_name}.json",
                    json.dumps({"parent": "minecraft:item/generated"}),
                )
            archive.writestr(
                "data/bossmod/tags/items/armors.json",
                json.dumps(armor_tag),
            )
            archive.writestr(
                "data/bossmod/loot_tables/entities/boss.json",
                json.dumps(loot_table),
            )
            archive.writestr(
                "data/bossmod/recipes/crafted_sword.json",
                json.dumps(recipe),
            )


if __name__ == "__main__":
    unittest.main()
