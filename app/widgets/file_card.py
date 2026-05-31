import os
from pathlib import Path
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QMenu, QInputDialog, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QColor, QPainter, QBrush, QFont, QCursor

from app.database import (
    update_file_category, update_custom_name, update_file_notes,
    delete_file, get_configured_slicers
)
from app.slicer import open_in_slicer
from app.thumbnail import clear_thumbnail

CARD_WIDTH = 210
CARD_HEIGHT = 295
THUMB_HEIGHT = 180

CATEGORY_COLORS = {
    "Tools":              "#e8873a",
    "Clicker Toys":       "#b3a0d6",
    "Toys":               "#66c0f4",
    "Gaming & Tabletop":  "#9b7fd4",
    "Cosplay & Props":    "#e05c99",
    "Household":          "#5ba85a",
    "Art & Decor":        "#e8c43a",
    "Gadgets & Electronics": "#3ab8e8",
    "Utility":            "#4a9e7a",
    "Outdoors & Garden":  "#7ab85a",
    "Fashion & Jewelry":  "#e87ab3",
    "3D Printer Parts":   "#e87a3a",
    "Education":          "#5a9be8",
    "Repairs":            "#e05c5c",
    "Uncategorized":      "#8f98a0",
}

FORMAT_COLORS = {
    "3MF": "#5ba85a",
    "STL": "#66c0f4",
    "OBJ": "#e8873a",
    "STEP": "#b3a0d6",
    "STP": "#b3a0d6",
    "GCODE": "#e05c5c",
}

ALL_CATEGORIES = [
    "Tools", "Clicker Toys", "Toys", "Gaming & Tabletop",
    "Cosplay & Props", "Household", "Art & Decor",
    "Gadgets & Electronics", "Utility", "Outdoors & Garden",
    "Fashion & Jewelry", "3D Printer Parts", "Education",
    "Repairs", "Uncategorized",
]


def _make_placeholder(width: int, height: int, fmt: str) -> QPixmap:
    px = QPixmap(width, height)
    px.fill(QColor("#1e2d3d"))
    painter = QPainter(px)
    painter.setRenderHint(QPainter.Antialiasing)

    # Gradient-ish background
    painter.fillRect(0, 0, width, height, QColor("#1a2535"))

    # Format text centered
    color = FORMAT_COLORS.get(fmt, "#66c0f4")
    painter.setPen(QColor(color))
    font = QFont("Arial", 24, QFont.Bold)
    painter.setFont(font)
    painter.drawText(0, 0, width, height, Qt.AlignCenter, f".{fmt.lower()}")

    painter.end()
    return px


class FileCard(QFrame):
    refresh_requested = Signal()

    def __init__(self, file_data: dict, parent=None):
        super().__init__(parent)
        self.file_data = file_data
        self.setFixedSize(CARD_WIDTH, CARD_HEIGHT)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self._build_ui()
        self._load_thumbnail()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _build_ui(self):
        self.setStyleSheet(f"""
            FileCard {{
                background: #1e2d3d;
                border-radius: 6px;
                border: 1px solid #2a3f5a;
            }}
            FileCard:hover {{
                border: 1px solid #4a7ab5;
                background: #243447;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Thumbnail area
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(CARD_WIDTH, THUMB_HEIGHT)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet("""
            QLabel {
                background: #1a2535;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
        """)
        layout.addWidget(self.thumb_label)

        # Info area
        info = QFrame()
        info.setStyleSheet("background: transparent;")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(8, 6, 8, 6)
        info_layout.setSpacing(4)

        # Filename
        display_name = self.file_data.get("custom_name") or self.file_data.get("filename", "")
        self.name_label = QLabel(Path(display_name).stem)
        self.name_label.setWordWrap(True)
        self.name_label.setFixedHeight(34)
        self.name_label.setStyleSheet("color: #c6d4df; font-size: 12px; font-weight: bold;")
        self.name_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        info_layout.addWidget(self.name_label)

        # Badges row
        badges = QHBoxLayout()
        badges.setSpacing(4)
        badges.setContentsMargins(0, 0, 0, 0)

        fmt = self.file_data.get("format", "STL")
        fmt_color = FORMAT_COLORS.get(fmt, "#66c0f4")
        fmt_badge = QLabel(fmt)
        fmt_badge.setStyleSheet(f"""
            background: {fmt_color}22; color: {fmt_color};
            border: 1px solid {fmt_color}55;
            border-radius: 3px; padding: 1px 5px; font-size: 10px; font-weight: bold;
        """)
        badges.addWidget(fmt_badge)

        cat = self.file_data.get("category", "Uncategorized")
        cat_color = CATEGORY_COLORS.get(cat, "#8f98a0")
        cat_badge = QLabel(cat)
        cat_badge.setStyleSheet(f"""
            background: {cat_color}22; color: {cat_color};
            border: 1px solid {cat_color}55;
            border-radius: 3px; padding: 1px 5px; font-size: 10px;
        """)
        cat_badge.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        badges.addWidget(cat_badge)
        info_layout.addLayout(badges)

        # Open / Import in slicer button
        # 3MF files are *imported* (geometry only) to avoid overriding slicer settings
        is_3mf = self.file_data.get("format", "") == "3MF"
        btn_label = "⬇  Import to Slicer" if is_3mf else "▶  Open in Slicer"
        self.slicer_btn = QPushButton(btn_label)
        self.slicer_btn.setStyleSheet("""
            QPushButton {
                background: #2a475e;
                color: #66c0f4;
                border: 1px solid #3a6b94;
                border-radius: 4px;
                padding: 5px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background: #3a6b94; color: white; }
            QPushButton:pressed { background: #1a3a56; }
        """)
        self.slicer_btn.clicked.connect(self._open_in_slicer)
        info_layout.addWidget(self.slicer_btn)

        layout.addWidget(info)

    def _load_thumbnail(self):
        thumb_path = self.file_data.get("thumbnail_path")
        fmt = self.file_data.get("format", "STL")
        if thumb_path and Path(thumb_path).exists():
            px = QPixmap(thumb_path)
            if not px.isNull():
                px = px.scaled(CARD_WIDTH, THUMB_HEIGHT, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.thumb_label.setPixmap(px)
                return
        self.thumb_label.setPixmap(_make_placeholder(CARD_WIDTH, THUMB_HEIGHT, fmt))

    def _open_in_slicer(self, import_mode: bool | None = None):
        """
        Send this file to the slicer.

        import_mode=None  → auto: True for 3MF, False for everything else.
        import_mode=True  → strip printer/filament settings from the 3MF before
                            sending.  Geometry, painted colors, multi-material
                            object assignments and modifier meshes are all kept.
        import_mode=False → send the original file unchanged (loads full project).
        """
        if import_mode is None:
            import_mode = self.file_data.get("format", "") == "3MF"

        slicers = get_configured_slicers()
        if not slicers:
            QMessageBox.information(
                self, "No Slicer Configured",
                "No slicers are configured.\nGo to Settings → Slicers to add one."
            )
            return

        if len(slicers) == 1:
            err = open_in_slicer(self.file_data["path"], slicers[0]["path"], import_mode)
            if err:
                QMessageBox.warning(self, "Error", err)
        else:
            menu = QMenu(self)
            menu.setStyleSheet(_menu_style())
            for s in slicers:
                action = menu.addAction(s["name"])
                action.setData(s["path"])
            chosen = menu.exec(self.slicer_btn.mapToGlobal(self.slicer_btn.rect().bottomLeft()))
            if chosen:
                err = open_in_slicer(self.file_data["path"], chosen.data(), import_mode)
                if err:
                    QMessageBox.warning(self, "Error", err)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(_menu_style())

        # Open / Import in slicer submenu
        is_3mf = self.file_data.get("format", "") == "3MF"
        slicers = get_configured_slicers()
        if slicers:
            top_label = "⬇  Import to Slicer" if is_3mf else "▶  Open in Slicer"
            slicer_menu = menu.addMenu(top_label)
            slicer_menu.setStyleSheet(_menu_style())
            for s in slicers:
                act = slicer_menu.addAction(s["name"])
                act.setData(("slicer_import", s["path"]))

            # For 3MF files also offer a "Open as Project" option (loads all settings)
            if is_3mf:
                proj_menu = menu.addMenu("📂  Open as Project")
                proj_menu.setStyleSheet(_menu_style())
                proj_menu.setToolTip("Loads printer & filament settings from the 3MF file")
                for s in slicers:
                    act = proj_menu.addAction(s["name"])
                    act.setData(("slicer_project", s["path"]))
        else:
            act = menu.addAction("▶  Open in Slicer")
            act.setEnabled(False)

        menu.addSeparator()

        # Change category submenu
        cat_menu = menu.addMenu("🏷  Change Category")
        cat_menu.setStyleSheet(_menu_style())
        for cat in ALL_CATEGORIES:
            a = cat_menu.addAction(cat)
            a.setData(("category", cat))

        menu.addAction("✏  Rename").setData(("rename", None))
        menu.addAction("📝  Edit Notes").setData(("notes", None))
        menu.addAction("🔄  Refresh Thumbnail").setData(("refresh_thumb", None))
        menu.addSeparator()
        menu.addAction("📂  Open File Location").setData(("open_location", None))
        menu.addSeparator()
        menu.addAction("🗑  Remove from Library").setData(("delete", None))

        chosen = menu.exec(self.mapToGlobal(pos))
        if not chosen:
            return
        data = chosen.data()
        if not data:
            return

        action_type, value = data

        if action_type == "slicer_import":
            # 3MF → extract geometry to temp STL; STL/OBJ → pass directly
            import_mode = self.file_data.get("format", "") == "3MF"
            err = open_in_slicer(self.file_data["path"], value, import_mode)
            if err:
                QMessageBox.warning(self, "Error", err)

        elif action_type == "slicer_project":
            # Always pass the file directly (loads full project settings)
            err = open_in_slicer(self.file_data["path"], value, import_mode=False)
            if err:
                QMessageBox.warning(self, "Error", err)

        elif action_type == "category":
            update_file_category(self.file_data["id"], value)
            self.file_data["category"] = value
            self.refresh_requested.emit()

        elif action_type == "rename":
            current = self.file_data.get("custom_name") or Path(self.file_data["filename"]).stem
            name, ok = QInputDialog.getText(self, "Rename File", "Display name:", text=current)
            if ok and name.strip():
                update_custom_name(self.file_data["id"], name.strip())
                self.file_data["custom_name"] = name.strip()
                self.name_label.setText(name.strip())

        elif action_type == "notes":
            current = self.file_data.get("notes", "")
            notes, ok = QInputDialog.getMultiLineText(self, "Edit Notes", "Notes:", current)
            if ok:
                update_file_notes(self.file_data["id"], notes)
                self.file_data["notes"] = notes

        elif action_type == "refresh_thumb":
            clear_thumbnail(self.file_data["path"])
            self.file_data["thumbnail_path"] = None
            self._load_thumbnail()

        elif action_type == "open_location":
            folder = str(Path(self.file_data["path"]).parent)
            import subprocess
            subprocess.Popen(["explorer", "/select,", self.file_data["path"]])

        elif action_type == "delete":
            reply = QMessageBox.question(
                self, "Remove from Library",
                f"Remove '{self.file_data['filename']}' from library?\n(File will NOT be deleted from disk)",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                delete_file(self.file_data["id"])
                self.refresh_requested.emit()


def _menu_style() -> str:
    return """
        QMenu {
            background: #1e2d3d;
            color: #c6d4df;
            border: 1px solid #2a3f5a;
            border-radius: 4px;
            padding: 4px;
        }
        QMenu::item { padding: 6px 20px; border-radius: 3px; }
        QMenu::item:selected { background: #2a475e; color: white; }
        QMenu::separator { background: #2a3f5a; height: 1px; margin: 3px 8px; }
    """
