from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.defaults import vanilla_rows
from core.builtin_icons import (
    builtin_icon_id_for_tag,
    builtin_item_ids,
    read_builtin_item_icons,
)
from core.generator import generate_pack
from core.icon_scanner import find_minecraft_client_jar, read_item_icons
from core.i18n import translate
from core.materials import DEFAULT_MATERIAL_RULES, MaterialRule, create_rows_from_material_rules
from core.models import RestrictionRow
from core.profile import load_profile, save_profile
from core.recipe_scanner import (
    CraftableItem,
    extract_direct_ingredient_ids,
    extract_ingredient_tag_ids,
    extract_ingredients,
    merge_craftable_items,
    read_item_tag_registry,
    resolve_item_tag,
    scan_jar_recipes,
)
from core.scanner import ModFile, scan_mods_folder

JOBS = ["none", "miner", "lumberjack", "farmer", "hunter", "smith", "digger", "builder", "fisherman", "alchemist", "enchanter"]


class NoScrollSpinBox(QSpinBox):
    """Pole liczbowe, którego wartości nie zmienia kółko myszy."""

    def wheelEvent(self, event) -> None:
        event.ignore()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.language = "pl"
        self.mods_folder: Path | None = None
        self.detected_mods: list[ModFile] = []
        self.detected_items: list[CraftableItem] = []
        self.mod_item_cache: dict[Path, list[CraftableItem]] = {}
        self.item_icons: dict[str, bytes] = read_builtin_item_icons()
        self.item_tag_registry: dict[str, list[str]] = {}
        self.recipe_by_item: dict[str, CraftableItem] = {}
        self.rows = vanilla_rows()
        self.material_rules = [MaterialRule(r.material, r.level, r.enabled) for r in DEFAULT_MATERIAL_RULES]
        self.setWindowTitle("Jobs Generator v0.14")
        self.resize(1400, 820)
        self.setMinimumSize(1050, 650)
        self.build_ui()
        self.refresh_rules_table()
        self.refresh_material_rules_table()

    def tr(self, key: str, **values) -> str:
        return translate(self.language, key, **values)

    def build_ui(self) -> None:
        title = QLabel("Jobs Generator")
        title.setObjectName("titleLabel")
        subtitle = QLabel("Jobs+ 9.0.0 + Item Restrictions 9.0.0 • Minecraft 1.21.1")
        subtitle.setObjectName("mutedLabel")

        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        header = QHBoxLayout()
        header.addLayout(title_column)
        header.addStretch()
        self.language_button = QPushButton(self.tr("language_button"))
        self.language_button.setFixedWidth(54)
        self.language_button.setToolTip("English / Polski")
        self.language_button.clicked.connect(self.toggle_language)
        header.addWidget(self.language_button)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_rules_tab(), self.tr("tab_restrictions"))
        self.tabs.addTab(self.build_mods_tab(), self.tr("tab_mod_scanner"))
        self.tabs.addTab(self.build_materials_tab(), self.tr("tab_materials"))
        self.tabs.addTab(self.build_export_tab(), self.tr("tab_export"))
        layout = QVBoxLayout()
        layout.setContentsMargins(22, 18, 22, 18)
        layout.addLayout(header)
        layout.addWidget(self.tabs)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)
        self.statusBar().showMessage(self.tr("ready"))

    def toggle_language(self) -> None:
        tab_index = self.tabs.currentIndex()
        self.collect_rows()
        self.collect_material_rules()
        checked_paths = set(self.selected_mod_paths())
        rules_sort = self.rules_sort_combo.currentData()
        rules_descending = self.rules_sort_direction.currentData()
        detected_sort = self.detected_sort_combo.currentData()
        detected_descending = self.detected_sort_direction.currentData()
        filter_text = self.item_filter.text()
        export_path = self.export_path.text()

        previous_central = self.takeCentralWidget()
        self.language = "en" if self.language == "pl" else "pl"
        self.build_ui()

        self.set_combo_value(self.rules_sort_combo, rules_sort)
        self.set_combo_value(
            self.rules_sort_direction,
            rules_descending,
        )
        self.set_combo_value(self.detected_sort_combo, detected_sort)
        self.set_combo_value(
            self.detected_sort_direction,
            detected_descending,
        )
        self.item_filter.setText(filter_text)
        self.export_path.setText(export_path)
        self.refresh_rules_table()
        self.refresh_material_rules_table()
        self.refresh_detected_items_table()
        self.refresh_mods_table(checked_paths)
        self.tabs.setCurrentIndex(tab_index)
        self.statusBar().showMessage(self.tr("ready"))

        if previous_central is not None:
            previous_central.deleteLater()

    @staticmethod
    def set_combo_value(combo: QComboBox, value) -> None:
        index = combo.findData(value)
        if index >= 0:
            previous = combo.blockSignals(True)
            combo.setCurrentIndex(index)
            combo.blockSignals(previous)

    def build_rules_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        info = QLabel(self.tr("rules_info"))
        info.setWordWrap(True)
        info.setObjectName("mutedLabel")
        layout.addWidget(info)
        buttons = QHBoxLayout()
        for text, slot in (
            (self.tr("restore_vanilla"), self.reset_vanilla),
            (self.tr("add_item"), self.add_row),
            (self.tr("delete_selected"), self.delete_selected),
            (self.tr("save_profile"), self.save_profile_dialog),
            (self.tr("load_profile"), self.load_profile_dialog),
        ):
            button = QPushButton(text)
            button.clicked.connect(slot)
            buttons.addWidget(button)
        layout.addLayout(buttons)

        sort_controls = QHBoxLayout()
        sort_controls.addWidget(QLabel(self.tr("sort_items")))
        self.rules_sort_combo = QComboBox()
        self.rules_sort_combo.addItem(self.tr("sort_alphabetical"), "item")
        self.rules_sort_combo.addItem(self.tr("sort_mod"), "mod")
        self.rules_sort_combo.addItem(self.tr("sort_job"), "job")
        self.rules_sort_combo.addItem(self.tr("sort_use_level"), "use_level")
        self.rules_sort_combo.addItem(self.tr("sort_smith_level"), "smith_level")
        self.rules_sort_combo.currentIndexChanged.connect(self.sort_rules)
        sort_controls.addWidget(self.rules_sort_combo)
        self.rules_sort_direction = QComboBox()
        self.rules_sort_direction.addItem(self.tr("ascending"), False)
        self.rules_sort_direction.addItem(self.tr("descending"), True)
        self.rules_sort_direction.currentIndexChanged.connect(self.sort_rules)
        sort_controls.addWidget(self.rules_sort_direction)
        sort_controls.addStretch()
        layout.addLayout(sort_controls)

        self.rules_table = QTableWidget(0, 8)
        self.rules_table.setHorizontalHeaderLabels([
            self.tr("select"),
            self.tr("enabled"),
            self.tr("item_id"),
            self.tr("use_job"),
            self.tr("use_level"),
            self.tr("smith_crafting"),
            self.tr("use_types"),
            self.tr("description"),
        ])
        self.rules_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.rules_table.setIconSize(QSize(32, 32))
        self.rules_table.verticalHeader().setDefaultSectionSize(38)
        self.rules_table.setColumnWidth(0, 60)
        self.rules_table.setColumnWidth(1, 60)
        self.rules_table.setColumnWidth(2, 280)
        self.rules_table.setColumnWidth(3, 140)
        self.rules_table.setColumnWidth(4, 110)
        self.rules_table.setColumnWidth(5, 110)
        self.rules_table.setColumnWidth(6, 330)
        self.rules_table.horizontalHeader().setSectionResizeMode(
            7,
            QHeaderView.ResizeMode.Stretch,
        )
        layout.addWidget(self.rules_table)
        return page

    def build_mods_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.folder_label = QLabel(
            str(self.mods_folder)
            if self.mods_folder
            else self.tr("no_mods_folder")
        )
        self.folder_label.setWordWrap(True)

        buttons = QHBoxLayout()
        choose = QPushButton(self.tr("choose_mods_folder"))
        choose.clicked.connect(self.choose_mods_folder)
        scan = QPushButton(self.tr("scan_mods"))
        scan.clicked.connect(self.scan_mods)
        self.load_mods_button = QPushButton(self.tr("load_selected_mods"))
        self.load_mods_button.clicked.connect(self.load_selected_mods)
        self.load_mods_button.setEnabled(bool(self.detected_mods))
        buttons.addWidget(choose)
        buttons.addWidget(scan)
        buttons.addWidget(self.load_mods_button)

        selection_buttons = QHBoxLayout()
        select_all = QPushButton(self.tr("select_all"))
        select_all.clicked.connect(lambda: self.set_all_mod_checkboxes(True))
        select_none = QPushButton(self.tr("deselect_all"))
        select_none.clicked.connect(lambda: self.set_all_mod_checkboxes(False))
        selection_buttons.addWidget(select_all)
        selection_buttons.addWidget(select_none)
        selection_buttons.addStretch()

        self.mods_table = QTableWidget(0, 8)
        self.mods_table.setHorizontalHeaderLabels([
            self.tr("load"),
            self.tr("name"),
            self.tr("mod_id"),
            self.tr("items"),
            self.tr("version"),
            self.tr("author"),
            self.tr("loader"),
            self.tr("file"),
        ])
        self.mods_table.setColumnWidth(0, 70)
        self.mods_table.setColumnWidth(1, 200)
        self.mods_table.setColumnWidth(2, 150)
        self.mods_table.setColumnWidth(3, 100)
        self.mods_table.setColumnWidth(4, 100)
        self.mods_table.setColumnWidth(5, 170)
        self.mods_table.setColumnWidth(6, 90)
        self.mods_table.horizontalHeader().setStretchLastSection(True)
        self.mods_table.setSortingEnabled(True)

        layout.addWidget(self.folder_label)
        layout.addLayout(buttons)
        layout.addLayout(selection_buttons)
        layout.addWidget(self.mods_table)
        note = QLabel(self.tr("scanner_note"))
        note.setWordWrap(True)
        note.setObjectName("mutedLabel")
        layout.addWidget(note)
        return page

    def build_materials_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        info = QLabel(self.tr("materials_info"))
        info.setWordWrap(True)
        info.setObjectName("mutedLabel")
        layout.addWidget(info)

        material_buttons = QHBoxLayout()
        add_rule = QPushButton(self.tr("add_material"))
        add_rule.clicked.connect(self.add_material_rule)
        delete_rule = QPushButton(self.tr("delete_materials"))
        delete_rule.clicked.connect(self.delete_material_rule)
        apply_rules = QPushButton(self.tr("apply_materials"))
        apply_rules.clicked.connect(self.apply_material_rules)
        material_buttons.addWidget(add_rule)
        material_buttons.addWidget(delete_rule)
        material_buttons.addWidget(apply_rules)
        layout.addLayout(material_buttons)

        self.material_rules_table = QTableWidget(0, 4)
        self.material_rules_table.setHorizontalHeaderLabels([
            self.tr("select"),
            self.tr("enabled"),
            self.tr("material"),
            self.tr("material_level"),
        ])
        self.material_rules_table.setMaximumHeight(210)
        self.material_rules_table.setColumnWidth(0, 70)
        self.material_rules_table.setColumnWidth(1, 70)
        self.material_rules_table.setColumnWidth(2, 260)
        self.material_rules_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.material_rules_table)

        filters = QHBoxLayout()
        filters.addWidget(QLabel(self.tr("filter")))
        self.item_filter = QLineEdit()
        self.item_filter.setPlaceholderText(self.tr("filter_placeholder"))
        self.item_filter.textChanged.connect(self.refresh_detected_items_table)
        filters.addWidget(self.item_filter)
        filters.addWidget(QLabel(self.tr("sort")))
        self.detected_sort_combo = QComboBox()
        self.detected_sort_combo.addItem(self.tr("sort_alphabetical"), "item")
        self.detected_sort_combo.addItem(self.tr("sort_mod"), "mod")
        self.detected_sort_combo.addItem(self.tr("sort_material"), "material")
        self.detected_sort_combo.addItem(self.tr("sort_category"), "category")
        self.detected_sort_combo.addItem(self.tr("sort_recipe"), "recipe")
        self.detected_sort_combo.currentIndexChanged.connect(self.refresh_detected_items_table)
        filters.addWidget(self.detected_sort_combo)
        self.detected_sort_direction = QComboBox()
        self.detected_sort_direction.addItem(self.tr("ascending"), False)
        self.detected_sort_direction.addItem(self.tr("descending"), True)
        self.detected_sort_direction.currentIndexChanged.connect(self.refresh_detected_items_table)
        filters.addWidget(self.detected_sort_direction)
        self.detected_summary = QLabel(self.tr("not_scanned"))
        filters.addWidget(self.detected_summary)
        layout.addLayout(filters)

        detected_buttons = QHBoxLayout()
        delete_detected = QPushButton(self.tr("delete_detected"))
        delete_detected.clicked.connect(self.delete_selected_detected_items)
        detected_buttons.addWidget(delete_detected)
        detected_buttons.addStretch()
        layout.addLayout(detected_buttons)

        self.detected_items_table = QTableWidget(0, 9)
        self.detected_items_table.setHorizontalHeaderLabels([
            self.tr("select"),
            self.tr("item_id"),
            self.tr("material"),
            self.tr("category"),
            self.tr("mod"),
            self.tr("confidence"),
            self.tr("material_source"),
            self.tr("recipe"),
            self.tr("crafting"),
        ])
        self.detected_items_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.detected_items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.detected_items_table.setIconSize(QSize(32, 32))
        self.detected_items_table.verticalHeader().setDefaultSectionSize(38)
        self.detected_items_table.setColumnWidth(0, 70)
        self.detected_items_table.setColumnWidth(1, 300)
        self.detected_items_table.setColumnWidth(2, 120)
        self.detected_items_table.setColumnWidth(3, 110)
        self.detected_items_table.setColumnWidth(4, 130)
        self.detected_items_table.setColumnWidth(5, 90)
        self.detected_items_table.setColumnWidth(6, 260)
        self.detected_items_table.setColumnWidth(8, 110)
        self.detected_items_table.horizontalHeader().setSectionResizeMode(
            7,
            QHeaderView.ResizeMode.Stretch,
        )
        layout.addWidget(self.detected_items_table)
        return page

    def build_export_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        text = QLabel(self.tr("export_info"))
        text.setWordWrap(True)
        layout.addWidget(text)
        self.export_path = QLabel(str(Path.cwd() / "output" / "JobsRestrictions.zip"))
        self.export_path.setWordWrap(True)
        layout.addWidget(self.export_path)
        row = QHBoxLayout()
        choose = QPushButton(self.tr("choose_export"))
        choose.clicked.connect(self.choose_export_path)
        generate = QPushButton(self.tr("generate_pack"))
        generate.clicked.connect(self.generate)
        row.addWidget(choose)
        row.addWidget(generate)
        layout.addLayout(row)
        layout.addStretch()
        return page

    def refresh_rules_table(self) -> None:
        self.rules_table.setRowCount(len(self.rows))
        for row_number, row in enumerate(self.rows):
            selected = QCheckBox()
            self.rules_table.setCellWidget(row_number, 0, selected)
            enabled = QCheckBox()
            enabled.setChecked(row.enabled)
            self.rules_table.setCellWidget(row_number, 1, enabled)
            self.rules_table.setItem(
                row_number,
                2,
                self.make_item_id_cell(row.item_id),
            )
            job = QComboBox()
            for job_id in JOBS:
                job.addItem(self.tr(f"job_{job_id}"), job_id)
            selected_job = (
                "hunter"
                if row.use_job == "warrior"
                else row.use_job
            )
            selected_index = job.findData(selected_job)
            job.setCurrentIndex(max(0, selected_index))
            self.rules_table.setCellWidget(row_number, 3, job)
            use_level = NoScrollSpinBox()
            use_level.setRange(0, 999)
            use_level.setValue(row.use_level)
            self.rules_table.setCellWidget(row_number, 4, use_level)
            smith = NoScrollSpinBox()
            smith.setRange(0, 999)
            smith.setValue(row.smith_level)
            self.rules_table.setCellWidget(row_number, 5, smith)
            self.rules_table.setItem(row_number, 6, QTableWidgetItem(row.use_types))
            self.rules_table.setItem(row_number, 7, QTableWidgetItem(self.describe(row)))

    def make_item_id_cell(self, item_id: str) -> QTableWidgetItem:
        cell = QTableWidgetItem(item_id)
        icon_data = self.item_icons.get(item_id.strip().lower())
        if not icon_data:
            return cell

        pixmap = QPixmap()
        if pixmap.loadFromData(icon_data):
            cell.setIcon(QIcon(pixmap))
        return cell

    def show_recipe_dialog(self, item_id: str) -> None:
        normalized_id = item_id.strip().lower()
        recipe = self.recipe_by_item.get(normalized_id)
        if recipe is None:
            QMessageBox.information(
                self,
                self.tr("crafting"),
                self.tr("no_recipe"),
            )
            return

        payload = recipe.recipe_data
        recipe_type = str(payload.get("type", "custom"))
        dialog = QDialog(self)
        dialog.setWindowTitle(
            self.tr("recipe_title", item=normalized_id)
        )
        dialog.setMinimumWidth(520)
        layout = QVBoxLayout(dialog)

        title = QLabel(self.tr("recipe_title", item=normalized_id))
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        type_key = "recipe_custom"
        if (
            "smithing" in recipe_type
            or all(key in payload for key in ("base", "addition"))
        ):
            type_key = "recipe_smithing"
        elif isinstance(payload.get("pattern"), list):
            type_key = "recipe_shaped"
        elif isinstance(payload.get("ingredients"), list):
            type_key = "recipe_shapeless"
        layout.addWidget(QLabel(self.tr(
            "recipe_type",
            type=self.tr(type_key),
        )))

        if type_key == "recipe_smithing":
            smithing = QHBoxLayout()
            smithing.addWidget(self.create_recipe_slot(
                payload.get("template"),
                self.tr("recipe_template"),
            ))
            smithing.addWidget(QLabel("+"))
            smithing.addWidget(self.create_recipe_slot(
                payload.get("base"),
                self.tr("recipe_base"),
            ))
            smithing.addWidget(QLabel("+"))
            smithing.addWidget(self.create_recipe_slot(
                payload.get("addition"),
                self.tr("recipe_addition"),
            ))
            smithing.addWidget(QLabel("→"))
            smithing.addWidget(self.create_recipe_slot(
                {"item": normalized_id},
                self.tr("recipe_result"),
            ))
            layout.addLayout(smithing)
        else:
            grid_widget = QWidget()
            grid = QGridLayout(grid_widget)
            grid.setSpacing(5)
            slots: list[object | None] = [None] * 9

            pattern = payload.get("pattern")
            recipe_key = payload.get("key", {})
            if (
                isinstance(pattern, list)
                and isinstance(recipe_key, dict)
            ):
                rows = [
                    str(row)
                    for row in pattern[:3]
                ]
                vertical_offset = max(0, (3 - len(rows)) // 2)
                max_width = max(
                    (len(row) for row in rows),
                    default=0,
                )
                horizontal_offset = max(0, (3 - max_width) // 2)
                for row_number, row_pattern in enumerate(rows):
                    for column, symbol in enumerate(row_pattern[:3]):
                        if symbol == " ":
                            continue
                        index = (
                            (row_number + vertical_offset) * 3
                            + column
                            + horizontal_offset
                        )
                        if 0 <= index < 9:
                            slots[index] = recipe_key.get(symbol)
            else:
                ingredients = payload.get("ingredients")
                if not isinstance(ingredients, list):
                    ingredients = extract_ingredients(payload)
                for index, ingredient in enumerate(ingredients[:9]):
                    slots[index] = ingredient

            for index, ingredient in enumerate(slots):
                grid.addWidget(
                    self.create_recipe_slot(ingredient),
                    index // 3,
                    index % 3,
                )

            recipe_row = QHBoxLayout()
            recipe_row.addStretch()
            recipe_row.addWidget(grid_widget)
            recipe_row.addWidget(QLabel("→"))
            recipe_row.addWidget(
                self.create_recipe_slot(
                    {"item": normalized_id},
                    self.tr("recipe_result"),
                )
            )
            recipe_row.addStretch()
            layout.addLayout(recipe_row)

        close_button = QPushButton("OK")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec()

    def create_recipe_slot(
        self,
        ingredient,
        heading: str = "",
    ) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setFixedSize(108, 92)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        if heading:
            heading_label = QLabel(heading)
            heading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(heading_label)

        item_id, description = self.describe_ingredient(ingredient)
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if item_id:
            icon_data = self.item_icons.get(item_id)
            if icon_data:
                pixmap = QPixmap()
                if pixmap.loadFromData(icon_data):
                    icon_label.setPixmap(pixmap.scaled(
                        42,
                        42,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    ))
        layout.addWidget(icon_label, 1)

        text = QLabel(description)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setWordWrap(True)
        text.setToolTip(description)
        text.setStyleSheet("font-size: 10px;")
        layout.addWidget(text)
        return frame

    def describe_ingredient(
        self,
        ingredient,
    ) -> tuple[str | None, str]:
        if ingredient is None:
            return None, ""
        if isinstance(ingredient, str):
            normalized = ingredient.strip().lower()
            if normalized.startswith("#"):
                return (
                    self.icon_id_for_recipe_tag(normalized),
                    normalized,
                )
            return (
                normalized if ":" in normalized else None,
                normalized,
            )
        if isinstance(ingredient, list):
            descriptions = [
                self.describe_ingredient(value)
                for value in ingredient
            ]
            first_item = next(
                (
                    item_id
                    for item_id, _ in descriptions
                    if item_id
                ),
                None,
            )
            return first_item, " / ".join(
                description
                for _, description in descriptions
                if description
            )
        if not isinstance(ingredient, dict):
            return None, str(ingredient)

        for key in ("item", "id"):
            value = ingredient.get(key)
            if isinstance(value, str):
                normalized = value.strip().lower()
                return normalized, normalized
        tag = ingredient.get("tag")
        if isinstance(tag, str):
            normalized_tag = tag.strip().lower().lstrip("#")
            return (
                self.icon_id_for_recipe_tag(normalized_tag),
                f"#{normalized_tag}",
            )
        for key in ("ingredient", "value", "items"):
            if key in ingredient:
                return self.describe_ingredient(ingredient[key])
        return None, self.tr("recipe_ingredient")

    def icon_id_for_recipe_tag(self, tag: str) -> str | None:
        """Wybiera ikonę konkretnego przedmiotu należącego do tagu."""

        resolved_items = resolve_item_tag(
            tag,
            self.item_tag_registry,
        )
        for item_id in resolved_items:
            if item_id in self.item_icons:
                return item_id
        if resolved_items:
            return resolved_items[0]
        return builtin_icon_id_for_tag(tag)

    def translated_category(self, category: str) -> str:
        return self.tr(f"category_{category}")

    def translated_confidence(self, confidence: str) -> str:
        key = {
            "wysoka": "confidence_high",
            "średnia": "confidence_medium",
            "niska": "confidence_low",
        }.get(confidence, "")
        return self.tr(key) if key else confidence

    def translated_material_source(self, source: str) -> str:
        replacements = (
            ("receptura", "source_recipe"),
            ("tag/składnik", "source_tag"),
            ("składnik", "source_ingredient"),
            ("nazwa przedmiotu", "source_item_name"),
            ("nie wykryto", "source_not_detected"),
        )
        for original, key in replacements:
            if source == original:
                return self.tr(key)
            prefix = f"{original}: "
            if source.startswith(prefix):
                return f"{self.tr(key)}: {source[len(prefix):]}"
        return source

    def collect_rows(self) -> list[RestrictionRow]:
        rows: list[RestrictionRow] = []
        for row_number in range(self.rules_table.rowCount()):
            enabled_widget = self.rules_table.cellWidget(row_number, 1)
            item_widget = self.rules_table.item(row_number, 2)
            job_widget = self.rules_table.cellWidget(row_number, 3)
            use_widget = self.rules_table.cellWidget(row_number, 4)
            smith_widget = self.rules_table.cellWidget(row_number, 5)
            types_item = self.rules_table.item(row_number, 6)
            rows.append(RestrictionRow(
                item_id=item_widget.text().strip() if item_widget else "",
                use_job=str(job_widget.currentData()),
                use_level=use_widget.value(),
                smith_level=smith_widget.value(),
                use_types=types_item.text().strip() if types_item else "",
                enabled=enabled_widget.isChecked(),
            ))
        self.rows = rows
        return rows

    def sort_rules(self, *_args) -> None:
        if not hasattr(self, "rules_table"):
            return

        rows = self.collect_rows()
        sort_mode = self.rules_sort_combo.currentData()
        reverse = bool(self.rules_sort_direction.currentData())

        def sort_key(row: RestrictionRow):
            namespace = row.item_id.split(":", 1)[0].lower()
            if sort_mode == "mod":
                return namespace, row.item_id.lower()
            if sort_mode == "job":
                return row.use_job.lower(), row.item_id.lower()
            if sort_mode == "use_level":
                return row.use_level, row.item_id.lower()
            if sort_mode == "smith_level":
                return row.smith_level, row.item_id.lower()
            return row.item_id.lower(),

        self.rows = sorted(rows, key=sort_key, reverse=reverse)
        self.refresh_rules_table()

    def describe(self, row: RestrictionRow) -> str:
        parts: list[str] = []
        if row.smith_level:
            parts.append(
                self.tr("craft_description", level=row.smith_level)
            )
        if row.use_job != "none" and row.use_level:
            job_id = "hunter" if row.use_job == "warrior" else row.use_job
            parts.append(
                self.tr(
                    "use_description",
                    job=self.tr(f"job_{job_id}"),
                    level=row.use_level,
                )
            )
        return " • ".join(parts)

    def reset_vanilla(self) -> None:
        self.rows = vanilla_rows()
        self.refresh_rules_table()
        self.statusBar().showMessage(self.tr("vanilla_restored"))

    def add_row(self) -> None:
        self.collect_rows()
        self.rows.append(RestrictionRow("modid:item_name", "hunter", 20, 20, "use_item,item_break_block,hurt_entity,repair,enchant"))
        self.refresh_rules_table()
        self.rules_table.selectRow(len(self.rows) - 1)

    def delete_selected(self) -> None:
        selected_rows = [
            row for row in range(self.rules_table.rowCount())
            if self.rules_table.cellWidget(row, 0).isChecked()
        ]
        if not selected_rows:
            QMessageBox.information(
                self,
                self.tr("no_selection"),
                self.tr("select_items_to_delete"),
            )
            return
        self.collect_rows()
        for row in reversed(selected_rows):
            del self.rows[row]
        self.refresh_rules_table()

    def save_profile_dialog(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("save_profile"),
            "jobs_profile.json",
            "JSON (*.json)",
        )
        if path:
            save_profile(Path(path), self.collect_rows())
            self.statusBar().showMessage(self.tr("profile_saved"))

    def load_profile_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("load_profile"),
            "",
            "JSON (*.json)",
        )
        if not path:
            return
        try:
            self.rows = load_profile(Path(path))
            self.refresh_rules_table()
            self.statusBar().showMessage(self.tr("profile_loaded"))
        except (OSError, ValueError, KeyError) as error:
            QMessageBox.critical(self, self.tr("profile_error"), str(error))

    def choose_mods_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            self.tr("choose_mods_folder"),
        )
        if folder:
            self.mods_folder = Path(folder)
            self.folder_label.setText(folder)
            self.detected_mods = []
            self.detected_items = []
            self.mod_item_cache.clear()
            self.item_icons = read_builtin_item_icons()
            self.load_local_vanilla_icons()
            self.item_tag_registry.clear()
            self.recipe_by_item.clear()
            self.mods_table.setRowCount(0)
            self.load_mods_button.setEnabled(False)
            self.refresh_detected_items_table()
            self.refresh_rules_table()

    def load_local_vanilla_icons(self) -> Path | None:
        """Nadpisuje ikony zastępcze teksturami z lokalnego klienta gry."""

        if not self.mods_folder:
            return None
        minecraft_jar = find_minecraft_client_jar(self.mods_folder)
        if not minecraft_jar:
            return None
        self.item_icons.update(
            read_item_icons(minecraft_jar, builtin_item_ids())
        )
        return minecraft_jar

    def scan_mods(self) -> None:
        if not self.mods_folder:
            QMessageBox.information(
                self,
                self.tr("no_folder"),
                self.tr("choose_folder_first"),
            )
            return

        self.statusBar().showMessage(self.tr("scanning"))
        QApplication.processEvents()
        try:
            all_mods = scan_mods_folder(self.mods_folder)
        except OSError as error:
            QMessageBox.critical(self, self.tr("error"), str(error))
            return

        self.detected_mods = []
        self.mod_item_cache.clear()
        for mod in all_mods:
            items = merge_craftable_items(scan_jar_recipes(mod.file_path))
            if not items:
                continue
            self.detected_mods.append(mod)
            self.mod_item_cache[mod.file_path] = items
            QApplication.processEvents()

        self.refresh_mods_table()
        self.load_mods_button.setEnabled(bool(self.detected_mods))

        total_items = sum(
            len(items) for items in self.mod_item_cache.values()
        )
        hidden_count = len(all_mods) - len(self.detected_mods)
        self.statusBar().showMessage(self.tr(
            "mods_found_status",
            count=len(self.detected_mods),
        ))
        QMessageBox.information(
            self,
            self.tr("scan_finished"),
            self.tr(
                "scan_result",
                mods=len(self.detected_mods),
                items=total_items,
                hidden=hidden_count,
            ),
        )

    def refresh_mods_table(
        self,
        checked_paths: set[Path] | None = None,
    ) -> None:
        check_everything = checked_paths is None
        self.mods_table.setSortingEnabled(False)
        self.mods_table.setRowCount(len(self.detected_mods))
        for row_number, mod in enumerate(self.detected_mods):
            selected = QCheckBox()
            selected.setChecked(
                check_everything or mod.file_path in checked_paths
            )
            selected.setProperty("jar_path", str(mod.file_path))
            self.mods_table.setCellWidget(row_number, 0, selected)

            item_count = len(self.mod_item_cache.get(mod.file_path, []))
            values = (
                mod.display_name,
                mod.mod_id,
                str(item_count),
                self.translated_metadata(mod.version),
                self.translated_metadata(mod.authors),
                mod.loader,
                mod.file_name,
            )
            for column, value in enumerate(values, start=1):
                cell = QTableWidgetItem(value)
                if column == 3:
                    cell.setData(Qt.ItemDataRole.DisplayRole, item_count)
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.mods_table.setItem(row_number, column, cell)

        self.mods_table.setSortingEnabled(True)
        self.mods_table.sortItems(1, Qt.SortOrder.AscendingOrder)

    def translated_metadata(self, value: str) -> str:
        if value == "Nieznany":
            return self.tr("unknown")
        if value == "Nieznana":
            return self.tr("unknown_version")
        return value

    def set_all_mod_checkboxes(self, checked: bool) -> None:
        for row in range(self.mods_table.rowCount()):
            checkbox = self.mods_table.cellWidget(row, 0)
            if isinstance(checkbox, QCheckBox):
                checkbox.setChecked(checked)

    def selected_mod_paths(self) -> list[Path]:
        selected: list[Path] = []
        for row in range(self.mods_table.rowCount()):
            checkbox = self.mods_table.cellWidget(row, 0)
            if not isinstance(checkbox, QCheckBox) or not checkbox.isChecked():
                continue
            jar_path = checkbox.property("jar_path")
            if jar_path:
                selected.append(Path(str(jar_path)))
        return selected

    def load_selected_mods(self) -> None:
        selected_paths = self.selected_mod_paths()
        if not selected_paths:
            QMessageBox.information(
                self,
                self.tr("no_selection"),
                self.tr("select_mod_to_load"),
            )
            return

        self.statusBar().showMessage(self.tr("loading_items"))
        QApplication.processEvents()
        selected_items: list[CraftableItem] = []
        for jar_path in selected_paths:
            selected_items.extend(self.mod_item_cache.get(jar_path, []))
        self.detected_items = merge_craftable_items(selected_items)
        self.recipe_by_item = {
            item.item_id: item
            for item in self.detected_items
        }

        self.item_icons = read_builtin_item_icons()
        minecraft_jar = self.load_local_vanilla_icons()
        tag_sources = list(selected_paths)
        if minecraft_jar:
            tag_sources.append(minecraft_jar)
        self.item_tag_registry = read_item_tag_registry(tag_sources)

        all_icon_ids = {
            item.item_id
            for item in self.detected_items
        }
        for item in self.detected_items:
            all_icon_ids.update(
                extract_direct_ingredient_ids(item.recipe_data)
            )
            for tag_id in extract_ingredient_tag_ids(
                item.recipe_data
            ):
                all_icon_ids.update(resolve_item_tag(
                    tag_id,
                    self.item_tag_registry,
                ))
        for jar_path in selected_paths:
            self.item_icons.update(
                read_item_icons(jar_path, all_icon_ids)
            )
            QApplication.processEvents()

        if minecraft_jar:
            restriction_ids = {
                row.item_id.strip().lower()
                for row in self.collect_rows()
            }
            for vanilla_recipe in scan_jar_recipes(minecraft_jar):
                if vanilla_recipe.item_id in restriction_ids:
                    self.recipe_by_item.setdefault(
                        vanilla_recipe.item_id,
                        vanilla_recipe,
                    )

            minecraft_ids = {
                row.item_id.strip().lower()
                for row in self.rows
                if row.item_id.strip().lower().startswith("minecraft:")
            }
            minecraft_ids.update(
                item_id
                for item_id in all_icon_ids
                if item_id.startswith("minecraft:")
            )
            self.item_icons.update(
                read_item_icons(minecraft_jar, minecraft_ids)
            )

        self.add_detected_material_rules()
        self.refresh_detected_items_table()
        self.refresh_rules_table()
        self.tabs.setCurrentIndex(2)
        self.statusBar().showMessage(self.tr(
            "loaded_status",
            items=len(self.detected_items),
            icons=len(self.item_icons),
        ))
        QMessageBox.information(
            self,
            self.tr("loading_finished"),
            self.tr(
                "loading_result",
                mods=len(selected_paths),
                items=len(self.detected_items),
                icons=len(self.item_icons),
            ),
        )

    def refresh_material_rules_table(self) -> None:
        self.material_rules_table.setRowCount(len(self.material_rules))
        for row_number, rule in enumerate(self.material_rules):
            selected = QCheckBox()
            self.material_rules_table.setCellWidget(row_number, 0, selected)
            enabled = QCheckBox()
            enabled.setChecked(rule.enabled)
            self.material_rules_table.setCellWidget(row_number, 1, enabled)
            self.material_rules_table.setItem(row_number, 2, QTableWidgetItem(rule.material))
            level = NoScrollSpinBox()
            level.setRange(0, 999)
            level.setValue(rule.level)
            self.material_rules_table.setCellWidget(row_number, 3, level)

    def collect_material_rules(self) -> list[MaterialRule]:
        rules: list[MaterialRule] = []
        for row_number in range(self.material_rules_table.rowCount()):
            enabled = self.material_rules_table.cellWidget(row_number, 1).isChecked()
            material_item = self.material_rules_table.item(row_number, 2)
            level_widget = self.material_rules_table.cellWidget(row_number, 3)
            material = material_item.text().strip().lower() if material_item else ""
            rules.append(MaterialRule(material, level_widget.value(), enabled))
        self.material_rules = rules
        return rules

    def add_material_rule(self) -> None:
        self.collect_material_rules()
        self.material_rules.append(MaterialRule("new_material", 30, True))
        self.refresh_material_rules_table()
        self.material_rules_table.selectRow(len(self.material_rules) - 1)

    def delete_material_rule(self) -> None:
        selected_rows = [
            row for row in range(self.material_rules_table.rowCount())
            if self.material_rules_table.cellWidget(row, 0).isChecked()
        ]
        if not selected_rows:
            QMessageBox.information(
                self,
                self.tr("no_selection"),
                self.tr("select_materials_to_delete"),
            )
            return
        self.collect_material_rules()
        for row in reversed(selected_rows):
            del self.material_rules[row]
        self.refresh_material_rules_table()

    def add_detected_material_rules(self) -> None:
        self.collect_material_rules()
        existing = {rule.material.strip().lower() for rule in self.material_rules}
        detected = sorted({
            item.material.strip().lower()
            for item in self.detected_items
            if item.material.strip()
            and item.material.strip().lower() not in {"unknown", "nieznany", "none"}
        })
        added = 0
        for material in detected:
            if material not in existing:
                self.material_rules.append(MaterialRule(material, 0, True))
                existing.add(material)
                added += 1
        if added:
            self.refresh_material_rules_table()

    def refresh_detected_items_table(self, *_args) -> None:
        filter_text = self.item_filter.text().strip().lower() if hasattr(self, "item_filter") else ""
        visible = [item for item in self.detected_items if not filter_text or filter_text in " ".join((item.item_id, item.material, item.category, item.source_mod)).lower()]
        sort_mode = self.detected_sort_combo.currentData() if hasattr(self, "detected_sort_combo") else "item"
        reverse = bool(self.detected_sort_direction.currentData()) if hasattr(self, "detected_sort_direction") else False

        def sort_key(item: CraftableItem):
            if sort_mode == "mod":
                return item.source_mod.lower(), item.item_id.lower()
            if sort_mode == "material":
                return item.material.lower(), item.item_id.lower()
            if sort_mode == "category":
                return item.category.lower(), item.item_id.lower()
            if sort_mode == "recipe":
                return item.recipe_path.lower(), item.item_id.lower()
            return item.item_id.lower(),

        visible.sort(key=sort_key, reverse=reverse)
        self.detected_items_table.setRowCount(len(visible))
        for row_number, item in enumerate(visible):
            selected = QCheckBox()
            selected.setProperty("item_id", item.item_id)
            self.detected_items_table.setCellWidget(row_number, 0, selected)
            self.detected_items_table.setItem(
                row_number,
                1,
                self.make_item_id_cell(item.item_id),
            )
            values = (
                item.material,
                self.translated_category(item.category),
                item.source_mod,
                self.translated_confidence(item.confidence),
                self.translated_material_source(item.material_source),
                item.recipe_path,
            )
            for column, value in enumerate(values, start=2):
                self.detected_items_table.setItem(
                    row_number,
                    column,
                    QTableWidgetItem(value),
                )
            recipe_button = QPushButton(self.tr("show_recipe"))
            recipe_button.clicked.connect(
                lambda _checked=False, item_id=item.item_id:
                self.show_recipe_dialog(item_id)
            )
            self.detected_items_table.setCellWidget(
                row_number,
                8,
                recipe_button,
            )
        self.detected_summary.setText(self.tr(
            "visible_summary",
            visible=len(visible),
            total=len(self.detected_items),
        ))

    def delete_selected_detected_items(self) -> None:
        selected_ids = {
            str(self.detected_items_table.cellWidget(row, 0).property("item_id"))
            for row in range(self.detected_items_table.rowCount())
            if self.detected_items_table.cellWidget(row, 0).isChecked()
        }
        if not selected_ids:
            QMessageBox.information(
                self,
                self.tr("no_selection"),
                self.tr("select_detected_to_delete"),
            )
            return
        self.detected_items = [
            item for item in self.detected_items
            if item.item_id not in selected_ids
        ]
        self.refresh_detected_items_table()
        self.statusBar().showMessage(self.tr(
            "detected_deleted",
            count=len(selected_ids),
        ))

    def apply_material_rules(self) -> None:
        if not self.detected_items:
            QMessageBox.information(
                self,
                self.tr("no_items"),
                self.tr("scan_before_materials"),
            )
            return
        existing_rows = self.collect_rows()
        existing_ids = {row.item_id.strip().lower() for row in existing_rows}
        created, skipped = create_rows_from_material_rules(self.detected_items, self.collect_material_rules(), existing_ids)
        if not created:
            QMessageBox.information(
                self,
                self.tr("no_changes"),
                self.tr("no_material_matches"),
            )
            return
        self.rows = existing_rows + created
        self.refresh_rules_table()
        self.tabs.setCurrentIndex(0)
        QMessageBox.information(
            self,
            self.tr("rules_applied"),
            self.tr(
                "rules_applied_result",
                created=len(created),
                skipped=len(skipped),
            ),
        )
        self.statusBar().showMessage(self.tr(
            "rules_added_status",
            count=len(created),
        ))

    def choose_export_path(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("save_datapack"),
            self.export_path.text(),
            "ZIP (*.zip)",
        )
        if path:
            if not path.lower().endswith(".zip"):
                path += ".zip"
            self.export_path.setText(path)

    def generate(self) -> None:
        try:
            count, warnings = generate_pack(
                self.collect_rows(),
                Path(self.export_path.text()),
                language=self.language,
            )
        except OSError as error:
            QMessageBox.critical(self, self.tr("save_error"), str(error))
            return
        message = self.tr(
            "pack_created",
            count=count,
            path=self.export_path.text(),
        )
        if warnings:
            message += (
                f"\n\n{self.tr('warnings')}\n"
                + "\n".join(warnings[:10])
            )
        QMessageBox.information(self, self.tr("done"), message)
        self.statusBar().showMessage(self.tr("pack_generated"))
