import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

APP_STYLE = """
QWidget { background-color: #1e1f22; color: #f0f0f0; font-family: "Segoe UI"; font-size: 13px; }
QLabel#titleLabel { font-size: 25px; font-weight: 700; }
QLabel#mutedLabel { color: #b7bbc4; }
QPushButton { background-color: #3b82f6; border: 0; border-radius: 6px; padding: 9px 14px; font-weight: 600; }
QPushButton:hover { background-color: #2563eb; }
QPushButton:disabled { background-color: #4b5563; color: #9ca3af; }
QLineEdit, QSpinBox, QComboBox { background-color: #2b2d31; border: 1px solid #45474d; border-radius: 5px; padding: 6px; }
QTableWidget { background-color: #25262a; alternate-background-color: #2b2d31; border: 1px solid #45474d; gridline-color: #45474d; selection-background-color: #f59e0b; selection-color: #111827; }
QTableWidget::item:selected { background-color: #f59e0b; color: #111827; font-weight: 700; }
QHeaderView::section { background-color: #313338; border: 0; border-right: 1px solid #45474d; border-bottom: 1px solid #45474d; padding: 7px; font-weight: 700; }
QTabWidget::pane { border: 1px solid #45474d; }
QTabBar::tab { background: #2b2d31; padding: 9px 16px; }
QTabBar::tab:selected { background: #3b82f6; }
QStatusBar { background-color: #18191c; color: #d1d5db; }
"""

def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Restriction Generator")
    app.setApplicationVersion("1.0.2")
    app.setStyleSheet(APP_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
