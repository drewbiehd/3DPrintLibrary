import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor, QFont
from PySide6.QtCore import Qt

from app.database import init_db
from app.main_window import MainWindow


def apply_dark_theme(app: QApplication):
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.Window,          QColor("#1b2838"))
    p.setColor(QPalette.WindowText,      QColor("#c6d4df"))
    p.setColor(QPalette.Base,            QColor("#2a475e"))
    p.setColor(QPalette.AlternateBase,   QColor("#1b2838"))
    p.setColor(QPalette.ToolTipBase,     QColor("#1e2d3d"))
    p.setColor(QPalette.ToolTipText,     QColor("#c6d4df"))
    p.setColor(QPalette.Text,            QColor("#c6d4df"))
    p.setColor(QPalette.Button,          QColor("#2a475e"))
    p.setColor(QPalette.ButtonText,      QColor("#c6d4df"))
    p.setColor(QPalette.BrightText,      QColor("#ffffff"))
    p.setColor(QPalette.Link,            QColor("#66c0f4"))
    p.setColor(QPalette.Highlight,       QColor("#66c0f4"))
    p.setColor(QPalette.HighlightedText, QColor("#1b2838"))
    p.setColor(QPalette.Mid,             QColor("#2a3f5a"))
    p.setColor(QPalette.Shadow,          QColor("#0d1520"))
    app.setPalette(p)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("3D Print Library")
    app.setOrganizationName("3DPrintLib")

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    apply_dark_theme(app)
    init_db()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
