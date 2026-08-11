import unittest

from core.defaults import USE_ARMOR, USE_TOOL, vanilla_rows


class VanillaDefaultsTests(unittest.TestCase):
    def test_iron_equipment_uses_level_one_defaults(self) -> None:
        rows = {row.item_id: row for row in vanilla_rows()}

        pickaxe = rows["minecraft:iron_pickaxe"]
        self.assertEqual(pickaxe.use_job, "miner")
        self.assertEqual(pickaxe.use_level, 1)
        self.assertEqual(pickaxe.smith_job, "smith")
        self.assertEqual(pickaxe.smith_level, 1)
        self.assertEqual(pickaxe.use_types, USE_TOOL)
        self.assertEqual(pickaxe.enchant_level, 1)
        self.assertEqual(pickaxe.repair_level, 1)

        armor = rows["minecraft:iron_chestplate"]
        self.assertEqual(armor.use_job, "hunter")
        self.assertEqual(armor.use_level, 1)
        self.assertEqual(armor.smith_level, 1)
        self.assertEqual(armor.use_types, USE_ARMOR)

        shovel = rows["minecraft:iron_shovel"]
        self.assertEqual(shovel.use_job, "none")
        self.assertEqual(shovel.use_level, 0)
        self.assertEqual(shovel.smith_level, 1)

    def test_elytra_uses_level_one_without_crafting(self) -> None:
        rows = {row.item_id: row for row in vanilla_rows()}
        elytra = rows["minecraft:elytra"]

        self.assertEqual(elytra.use_job, "hunter")
        self.assertEqual(elytra.use_level, 1)
        self.assertEqual(elytra.use_types, USE_ARMOR)
        self.assertEqual(elytra.smith_level, 0)
        self.assertEqual(elytra.enchant_job, "enchanter")
        self.assertEqual(elytra.enchant_level, 1)
        self.assertEqual(elytra.repair_job, "smith")
        self.assertEqual(elytra.repair_level, 1)


if __name__ == "__main__":
    unittest.main()
