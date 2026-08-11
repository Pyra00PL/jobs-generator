import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionSpinBox

from core.defaults import USE_TOOL, USE_WEAPON
from core.models import RestrictionRow
from core.recipe_scanner import CraftableItem
from ui.main_window import MainWindow, NoScrollComboBox, NoScrollSpinBox


class IgnoredEvent:
    def __init__(self) -> None:
        self.ignored = False

    def ignore(self) -> None:
        self.ignored = True


class RestrictionGeneratorUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = MainWindow()

    def tearDown(self) -> None:
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_application_uses_new_name_and_version(self) -> None:
        self.assertEqual(
            self.window.windowTitle(),
            "Restriction Generator v1.0.1",
        )
        self.assertEqual(
            self.window.minecraft_profile_combo.currentData(),
            "1.21.1",
        )

    def test_minecraft_version_can_be_selected_for_export(
        self,
    ) -> None:
        index = self.window.minecraft_profile_combo.findData(
            "1.21.4"
        )
        self.window.minecraft_profile_combo.setCurrentIndex(index)

        self.assertEqual(
            self.window.minecraft_profile_key,
            "1.21.4",
        )
        self.assertIn("Minecraft 1.21.4", self.window.subtitle.text())

    def test_material_filter_runs_only_after_enter(self) -> None:
        self.window.detected_items = [
            self.item("example:steel_sword", "steel", "sword"),
            self.item("example:bronze_axe", "bronze", "axe"),
        ]
        self.window.refresh_detected_items_table()
        self.assertEqual(self.window.detected_items_table.rowCount(), 2)

        self.window.item_filter.setText("steel")
        self.assertEqual(self.window.detected_items_table.rowCount(), 2)

        self.window.item_filter.returnPressed.emit()
        self.assertEqual(self.window.detected_items_table.rowCount(), 1)
        self.assertEqual(
            self.window.detected_items_table.item(0, 1).text(),
            "example:steel_sword",
        )

    def test_restrictions_filter_runs_only_after_enter(self) -> None:
        initial_visible = sum(
            not self.window.rules_table.isRowHidden(row)
            for row in range(self.window.rules_table.rowCount())
        )

        self.window.rules_filter.setText("netherite_pickaxe")
        visible_before_enter = sum(
            not self.window.rules_table.isRowHidden(row)
            for row in range(self.window.rules_table.rowCount())
        )
        self.assertEqual(visible_before_enter, initial_visible)

        self.window.rules_filter.returnPressed.emit()
        visible_after_enter = [
            row
            for row in range(self.window.rules_table.rowCount())
            if not self.window.rules_table.isRowHidden(row)
        ]
        self.assertEqual(len(visible_after_enter), 1)
        self.assertEqual(
            self.window.rules_table.item(
                visible_after_enter[0],
                2,
            ).text(),
            "minecraft:netherite_pickaxe",
        )

    def test_selected_detected_item_is_added_to_restrictions(self) -> None:
        selected = self.item(
            "example:steel_longsword",
            "steel",
            "weapon",
        )
        self.window.detected_items = [selected]
        self.window.refresh_detected_items_table()
        self.window.detected_items_table.cellWidget(0, 0).setChecked(True)

        with patch(
            "ui.main_window.QMessageBox.information",
        ):
            self.window.add_selected_detected_to_restrictions()

        self.assertIn(
            selected.item_id,
            {row.item_id for row in self.window.rows},
        )
        created = next(
            row
            for row in self.window.rows
            if row.item_id == selected.item_id
        )
        self.assertEqual(created.use_job, "none")
        self.assertEqual(created.use_level, 0)
        self.assertEqual(created.smith_job, "smith")
        self.assertEqual(created.smith_level, 0)
        self.assertEqual(created.use_types, USE_WEAPON)
        self.assertEqual(created.enchant_job, "enchanter")
        self.assertEqual(created.enchant_level, 0)
        self.assertEqual(created.repair_job, "smith")
        self.assertEqual(created.repair_level, 0)

    def test_vanilla_rows_have_separate_enchant_and_repair_editors(
        self,
    ) -> None:
        usage = self.window.rules_table.cellWidget(0, 3)
        smithing = self.window.rules_table.cellWidget(0, 4)
        enchant = self.window.rules_table.cellWidget(0, 5)
        repair = self.window.rules_table.cellWidget(0, 6)

        self.assertEqual(usage.job_id(), "miner")
        self.assertEqual(usage.level(), 1)
        self.assertEqual(smithing.job_id(), "smith")
        self.assertEqual(smithing.level(), 1)
        self.assertEqual(enchant.job_id(), "enchanter")
        self.assertEqual(enchant.level(), 1)
        self.assertEqual(repair.job_id(), "smith")
        self.assertEqual(repair.level(), 1)
        self.assertNotIn(
            "enchant",
            self.window.rules_table.item(0, 7).text().split(","),
        )
        self.assertNotIn(
            "repair",
            self.window.rules_table.item(0, 7).text().split(","),
        )

    def test_enchant_and_repair_jobs_are_collected_independently(
        self,
    ) -> None:
        smithing = self.window.rules_table.cellWidget(0, 4)
        enchant = self.window.rules_table.cellWidget(0, 5)
        repair = self.window.rules_table.cellWidget(0, 6)
        smithing.job_combo.setCurrentIndex(
            smithing.job_combo.findData("builder")
        )
        smithing.level_spin.setValue(27)
        enchant.job_combo.setCurrentIndex(
            enchant.job_combo.findData("alchemist")
        )
        enchant.level_spin.setValue(33)
        repair.job_combo.setCurrentIndex(
            repair.job_combo.findData("builder")
        )
        repair.level_spin.setValue(44)

        first_row = self.window.collect_rows()[0]

        self.assertEqual(first_row.use_job, "miner")
        self.assertEqual(first_row.smith_job, "builder")
        self.assertEqual(first_row.smith_level, 27)
        self.assertEqual(first_row.enchant_job, "alchemist")
        self.assertEqual(first_row.enchant_level, 33)
        self.assertEqual(first_row.repair_job, "builder")
        self.assertEqual(first_row.repair_level, 44)

    def test_description_updates_after_manual_editor_changes(
        self,
    ) -> None:
        usage = self.window.rules_table.cellWidget(0, 3)
        smithing = self.window.rules_table.cellWidget(0, 4)

        usage.job_combo.setCurrentIndex(
            usage.job_combo.findData("alchemist")
        )
        usage.level_spin.setValue(77)
        smithing.job_combo.setCurrentIndex(
            smithing.job_combo.findData("builder")
        )
        smithing.level_spin.setValue(66)
        self.app.processEvents()

        description = self.window.rules_table.item(
            0,
            8,
        ).text()
        self.assertIn("alchemik 77", description)
        self.assertIn("budowniczy 66", description)

    def test_manual_usage_fills_missing_use_types(self) -> None:
        self.window.rows = [
            RestrictionRow(
                item_id="example:custom_lance",
                use_job="none",
                use_level=0,
                smith_level=0,
                use_types="",
                enchant_job="none",
                enchant_level=0,
                repair_job="none",
                repair_level=0,
            )
        ]
        self.window.refresh_rules_table()
        usage = self.window.rules_table.cellWidget(0, 3)

        usage.job_combo.setCurrentIndex(
            usage.job_combo.findData("hunter")
        )
        usage.level_spin.setValue(12)
        self.app.processEvents()

        self.assertEqual(
            self.window.rules_table.item(0, 7).text(),
            USE_TOOL,
        )
        self.assertEqual(
            self.window.collect_rows()[0].use_types,
            USE_TOOL,
        )

    def test_composite_level_fields_are_wide_enough(
        self,
    ) -> None:
        for column in (3, 4, 5, 6):
            editor = self.window.rules_table.cellWidget(
                0,
                column,
            )
            self.assertGreaterEqual(
                editor.level_spin.width(),
                110,
            )

    def test_select_all_restrictions_selects_only_visible_rows(self) -> None:
        self.window.rules_filter.setText("diamond_pickaxe")
        self.window.rules_filter.returnPressed.emit()

        self.window.select_all_visible_rules()

        for row in range(self.window.rules_table.rowCount()):
            self.assertEqual(
                self.window.rules_table.cellWidget(
                    row,
                    0,
                ).isChecked(),
                not self.window.rules_table.isRowHidden(row),
            )

    def test_select_all_detected_items_uses_filtered_rows(self) -> None:
        self.window.detected_items = [
            self.item("example:copper_sword", "copper", "sword"),
            self.item("example:copper_axe", "copper", "axe"),
            self.item("example:steel_sword", "steel", "sword"),
        ]
        self.window.refresh_detected_items_table()
        self.window.item_filter.setText("copper")
        self.window.item_filter.returnPressed.emit()

        self.window.select_all_visible_detected_items()

        self.assertEqual(self.window.detected_items_table.rowCount(), 2)
        self.assertTrue(
            all(
                self.window.detected_items_table.cellWidget(
                    row,
                    0,
                ).isChecked()
                for row in range(
                    self.window.detected_items_table.rowCount()
                )
            )
        )

    def test_job_combo_ignores_mouse_wheel(self) -> None:
        combo = NoScrollComboBox()
        combo.addItems(["miner", "hunter"])
        combo.setCurrentIndex(0)
        event = IgnoredEvent()

        combo.wheelEvent(event)

        self.assertTrue(event.ignored)
        self.assertEqual(combo.currentIndex(), 0)

    def test_spinbox_arrows_have_equal_hitboxes(self) -> None:
        spin = NoScrollSpinBox()
        spin.resize(120, 36)
        option = QStyleOptionSpinBox()
        spin.initStyleOption(option)
        up_rect = spin.style().subControlRect(
            QStyle.ComplexControl.CC_SpinBox,
            option,
            QStyle.SubControl.SC_SpinBoxUp,
            spin,
        )
        down_rect = spin.style().subControlRect(
            QStyle.ComplexControl.CC_SpinBox,
            option,
            QStyle.SubControl.SC_SpinBoxDown,
            spin,
        )

        self.assertEqual(up_rect.width(), down_rect.width())
        self.assertEqual(up_rect.height(), down_rect.height())
        self.assertGreaterEqual(up_rect.width(), 28)
        self.assertGreaterEqual(up_rect.height(), 17)

    @staticmethod
    def item(
        item_id: str,
        material: str,
        category: str,
    ) -> CraftableItem:
        return CraftableItem(
            item_id=item_id,
            material=material,
            category=category,
            source_mod="example",
            recipe_path=f"data/example/recipe/{item_id.split(':')[1]}.json",
            confidence="high",
            material_source="recipe",
            recipe_data={},
        )


if __name__ == "__main__":
    unittest.main()
