import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from core.generator import generate_pack
from core.models import RestrictionRow


class RestrictionSeparationTests(unittest.TestCase):
    def test_export_creates_four_independent_restrictions(self) -> None:
        row = RestrictionRow(
            item_id="minecraft:diamond_sword",
            use_job="hunter",
            use_level=20,
            smith_level=20,
            use_types="use_item,hurt_entity",
            smith_job="builder",
            enchant_job="enchanter",
            enchant_level=30,
            repair_job="smith",
            repair_level=25,
        )

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "restrictions.zip"
            count, warnings = generate_pack([row], output)
            self.assertEqual(count, 4)
            self.assertEqual(warnings, [])

            with zipfile.ZipFile(output) as archive:
                entries = {
                    name: json.loads(archive.read(name))
                    for name in archive.namelist()
                    if name.endswith(".json")
                }

        craft = self.find_entry(entries, "__craft_builder_20.json")
        usage = self.find_entry(entries, "__use_hunter_20.json")
        enchanting = self.find_entry(
            entries,
            "__enchant_enchanter_30.json",
        )
        repairing = self.find_entry(
            entries,
            "__repair_smith_25.json",
        )

        self.assertEqual(craft["types"], ["craft"])
        self.assertEqual(
            craft["conditions"][0]["job"],
            "jobsplus:builder",
        )
        self.assertEqual(
            usage["types"],
            ["use_item", "hurt_entity", "item_break_block"],
        )
        self.assertEqual(enchanting["types"], ["enchant"])
        self.assertEqual(repairing["types"], ["repair"])
        self.assertEqual(
            enchanting["conditions"][0]["job"],
            "jobsplus:enchanter",
        )
        self.assertEqual(
            repairing["conditions"][0]["job"],
            "jobsplus:smith",
        )
        self.assertTrue(
            all(
                entry["conditions"][0]["inverted"]
                for entry in entries.values()
            )
        )

    def test_old_profile_data_is_migrated(self) -> None:
        row = RestrictionRow.from_dict(
            {
                "item_id": "minecraft:diamond_pickaxe",
                "use_job": "miner",
                "use_level": 20,
                "smith_level": 20,
                "use_types": (
                    "use_item,item_break_block,hurt_entity,"
                    "repair,enchant"
                ),
            }
        )

        self.assertEqual(
            row.use_types,
            "use_item,item_break_block,hurt_entity",
        )
        self.assertEqual(row.enchant_job, "enchanter")
        self.assertEqual(row.enchant_level, 20)
        self.assertEqual(row.repair_job, "smith")
        self.assertEqual(row.repair_level, 20)
        self.assertEqual(row.smith_job, "smith")

    def test_use_job_cannot_take_enchant_or_repair_types(self) -> None:
        row = RestrictionRow(
            item_id="example:test_item",
            use_job="hunter",
            use_level=10,
            smith_level=0,
            use_types="use_item,enchant,repair",
            enchant_job="none",
            enchant_level=0,
            repair_job="none",
            repair_level=0,
        )

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "restrictions.zip"
            count, warnings = generate_pack([row], output)
            self.assertEqual(count, 1)
            self.assertEqual(len(warnings), 2)
            with zipfile.ZipFile(output) as archive:
                entry_name = next(
                    name
                    for name in archive.namelist()
                    if name.endswith(".json")
                )
                data = json.loads(archive.read(entry_name))

        self.assertEqual(data["types"], ["use_item"])

    def test_same_job_and_level_are_exported_as_one_restriction(self) -> None:
        row = RestrictionRow(
            item_id="example:steel_hammer",
            use_job="none",
            use_level=0,
            smith_job="smith",
            smith_level=20,
            use_types="",
            enchant_job="none",
            enchant_level=0,
            repair_job="smith",
            repair_level=20,
        )

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "restrictions.zip"
            count, warnings = generate_pack([row], output)
            self.assertEqual(count, 1)
            self.assertEqual(warnings, [])
            with zipfile.ZipFile(output) as archive:
                json_entries = [
                    name
                    for name in archive.namelist()
                    if name.endswith(".json")
                ]
                self.assertEqual(len(json_entries), 1)
                self.assertTrue(
                    json_entries[0].endswith(
                        "__combined_smith_20.json"
                    )
                )
                data = json.loads(archive.read(json_entries[0]))

        self.assertEqual(data["types"], ["craft", "repair"])
        self.assertEqual(
            data["conditions"][0]["job"],
            "jobsplus:smith",
        )

    def test_same_job_with_different_levels_stays_separate(self) -> None:
        row = RestrictionRow(
            item_id="example:steel_hammer",
            use_job="none",
            use_level=0,
            smith_job="smith",
            smith_level=20,
            use_types="",
            enchant_job="none",
            enchant_level=0,
            repair_job="smith",
            repair_level=30,
        )

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "restrictions.zip"
            count, warnings = generate_pack([row], output)

        self.assertEqual(count, 2)
        self.assertEqual(warnings, [])

    def test_empty_manual_usage_types_receive_safe_defaults(self) -> None:
        row = RestrictionRow(
            item_id="example:custom_lance",
            use_job="hunter",
            use_level=15,
            smith_level=0,
            use_types="",
            enchant_job="none",
            enchant_level=0,
            repair_job="none",
            repair_level=0,
        )

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "restrictions.zip"
            count, warnings = generate_pack([row], output)
            with zipfile.ZipFile(output) as archive:
                entry_name = next(
                    name
                    for name in archive.namelist()
                    if name.endswith(".json")
                )
                data = json.loads(archive.read(entry_name))

        self.assertEqual(count, 1)
        self.assertEqual(warnings, [])
        self.assertEqual(
            data["types"],
            ["use_item", "item_break_block", "hurt_entity"],
        )

    @staticmethod
    def find_entry(entries: dict[str, dict], suffix: str) -> dict:
        return next(
            value
            for name, value in entries.items()
            if name.endswith(suffix)
        )


if __name__ == "__main__":
    unittest.main()
