import subprocess
from pathlib import Path
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QMenu, QInputDialog, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QColor, QPainter, QFont, QCursor

import app.database as db
from app.slicer import open_in_slicer
from app.thumbnail import clear_thumbnail

CARD_WIDTH   = 210
CARD_HEIGHT  = 295
THUMB_HEIGHT = 180

FORMAT_COLORS = {
    "3MF":   "#5ba85a",
    "STL":   "#66c0f4",
    "OBJ":   "#e8873a",
    "STEP":  "#b3a0d6",
    "STP":   "#b3a0d6",
    "GCODE": "#e05c5c",
}


def _cat_color(category: str, subcategory: str = "") -> str:
    """Look up color from the live categories table; fall back to grey."""
    tree = db.get_category_tree()
    for node in tree:
        if node["name"] == category:
            if subcategory:
                for child in node["subcategories"]:
                    if child["name"] == subcategory:
                        return child["color"]
            return node["color"]
    return "#8f98a0"


def _make_placeholder(width: int, height: int, fmt: str) -> QPixmap:
    px = QPixmap(width, height)
    px.fill(QColor("#1e2d3d"))
    painter = QPainter(px)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.fillRect(0, 0, width, height, QColor("#1a2535"))
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

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setStyleSheet("""
            FileCard {
                background: #1e2d3d;
                border-radius: 6px;
                border: 1px solid #2a3f5a;
            }
            FileCard:hover {
                border: 1px solid #4a7ab5;
                background: #243447;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Thumbnail
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
        il = QVBoxLayout(info)
        il.setContentsMargins(8, 6, 8, 6)
        il.setSpacing(4)

        # Name
        display_name = self.file_data.get("custom_name") or self.file_data.get("filename", "")
        self.name_label = QLabel(Path(display_name).stem)
        self.name_label.setWordWrap(True)
        self.name_label.setFixedHeight(34)
        self.name_label.setStyleSheet("color: #c6d4df; font-size: 12px; font-weight: bold;")
        self.name_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        il.addWidget(self.name_label)

        # Badges row
        badges = QHBoxLayout()
        badges.setSpacing(4)
        badges.setContentsMargins(0, 0, 0, 0)

        fmt = self.file_data.get("format", "STL")
        fc  = FORMAT_COLORS.get(fmt, "#66c0f4")
        fmt_badge = QLabel(fmt)
        fmt_badge.setStyleSheet(
            f"background:{fc}22; color:{fc}; border:1px solid {fc}55;"
            f"border-radius:3px; padding:1px 5px; font-size:10px; font-weight:bold;"
        )
        badges.addWidget(fmt_badge)

        cat     = self.file_data.get("category", "Uncategorized")
        sub     = self.file_data.get("subcategory", "") or ""
        cc      = _cat_color(cat, sub)
        cat_lbl = f"{cat} › {sub}" if sub else cat
        self.cat_badge = QLabel(cat_lbl)
        self.cat_badge.setStyleSheet(
            f"background:{cc}22; color:{cc}; border:1px solid {cc}55;"
            f"border-radius:3px; padding:1px 5px; font-size:10px;"
        )
        self.cat_badge.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        badges.addWidget(self.cat_badge)
        il.addLayout(badges)

        # Slicer button
        is_3mf = fmt == "3MF"
        btn_label = "⬇  Import to Slicer" if is_3mf else "▶  Open in Slicer"
        self.slicer_btn = QPushButton(btn_label)
        self.slicer_btn.setStyleSheet("""
            QPushButton {
                background: #2a475e; color: #66c0f4;
                border: 1px solid #3a6b94; border-radius: 4px;
                padding: 5px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover  { background: #3a6b94; color: white; }
            QPushButton:pressed { background: #1a3a56; }
        """)
        self.slicer_btn.clicked.connect(self._open_in_slicer)
        il.addWidget(self.slicer_btn)

        layout.addWidget(info)

    def _load_thumbnail(self):
        thumb_path = self.file_data.get("thumbnail_path")
        fmt = self.file_data.get("format", "STL")
        if thumb_path and Path(thumb_path).exists():
            px = QPixmap(thumb_path)
            if not px.isNull():
                px = px.scaled(CARD_WIDTH, THUMB_HEIGHT,
                               Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.thumb_label.setPixmap(px)
                return
        self.thumb_label.setPixmap(_make_placeholder(CARD_WIDTH, THUMB_HEIGHT, fmt))

    # ── Slicer ────────────────────────────────────────────────────────────────

    def _open_in_slicer(self, import_mode: bool | None = None):
        if import_mode is None:
            import_mode = self.file_data.get("format", "") == "3MF"

        slicers = db.get_configured_slicers()
        if not slicers:
            QMessageBox.information(self, "No Slicer Configured",
                "No slicers configured.\nGo to Settings → Slicers to add one.")
            return
        if len(slicers) == 1:
            err = open_in_slicer(self.file_data["path"], slicers[0]["path"], import_mode)
            if err:
                QMessageBox.warning(self, "Error", err)
        else:
            menu = QMenu(self)
            menu.setStyleSheet(_menu_style())
            for s in slicers:
                a = menu.addAction(s["name"])
                a.setData(s["path"])
            chosen = menu.exec(
                self.slicer_btn.mapToGlobal(self.slicer_btn.rect().bottomLeft())
            )
            if chosen:
                err = open_in_slicer(self.file_data["path"], chosen.data(), import_mode)
                if err:
                    QMessageBox.warning(self, "Error", err)

    # ── Context menu ──────────────────────────────────────────────────────────

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(_menu_style())
        is_3mf = self.file_data.get("format", "") == "3MF"

        # Slicer submenu
        slicers = db.get_configured_slicers()
        if slicers:
            top_lbl = "⬇  Import to Slicer" if is_3mf else "▶  Open in Slicer"
            slicer_menu = menu.addMenu(top_lbl)
            slicer_menu.setStyleSheet(_menu_style())
            for s in slicers:
                a = slicer_menu.addAction(s["name"])
                a.setData(("slicer_import", s["path"]))
            if is_3mf:
                proj_menu = menu.addMenu("📂  Open as Project")
                proj_menu.setStyleSheet(_menu_style())
                for s in slicers:
                    a = proj_menu.addAction(s["name"])
                    a.setData(("slicer_project", s["path"]))
        else:
            menu.addAction("▶  Open in Slicer").setEnabled(False)

        menu.addSeparator()

        # Two-level category picker built from live DB tree
        cat_menu = menu.addMenu("🏷  Change Category")
        cat_menu.setStyleSheet(_menu_style())
        for node in db.get_category_tree():
            parent_act = cat_menu.addAction(
                f"{node['icon']}  {node['name']}"
            )
            parent_act.setData(("category", node["name"], ""))
            # Subcategory sub-menu (if any exist in DB, not just non-empty ones)
            if node["subcategories"]:
                sub_menu = cat_menu.addMenu(f"    └ {node['name']} ›")
                sub_menu.setStyleSheet(_menu_style())
                for child in node["subcategories"]:
                    a = sub_menu.addAction(f"{child['icon']}  {child['name']}")
                    a.setData(("category", node["name"], child["name"]))

        menu.addSeparator()
        menu.addAction("✏  Rename").setData(("rename", None, None))
        menu.addAction("📝  Edit Notes").setData(("notes", None, None))
        menu.addAction("🔄  Refresh Thumbnail").setData(("refresh_thumb", None, None))
        menu.addSeparator()
        menu.addAction("📂  Open File Location").setData(("open_location", None, None))
        menu.addSeparator()
        menu.addAction("🗑  Remove from Library").setData(("delete", None, None))

        chosen = menu.exec(self.mapToGlobal(pos))
        if not chosen:
            return
        data = chosen.data()
        if not data:
            return

        action = data[0]

        if action == "slicer_import":
            import_mode = self.file_data.get("format", "") == "3MF"
            err = open_in_slicer(self.file_data["path"], data[1], import_mode)
            if err:
                QMessageBox.warning(self, "Error", err)

        elif action == "slicer_project":
            err = open_in_slicer(self.file_data["path"], data[1], import_mode=False)
            if err:
                QMessageBox.warning(self, "Error", err)

        elif action == "category":
            _, cat, sub = data
            db.update_file_category(self.file_data["id"], cat, sub)
            self.file_data["category"] = cat
            self.file_data["subcategory"] = sub
            # Refresh badge
            cc  = _cat_color(cat, sub)
            lbl = f"{cat} › {sub}" if sub else cat
            self.cat_badge.setText(lbl)
            self.cat_badge.setStyleSheet(
                f"background:{cc}22; color:{cc}; border:1px solid {cc}55;"
                f"border-radius:3px; padding:1px 5px; font-size:10px;"
            )
            self.refresh_requested.emit()

        elif action == "rename":
            current = self.file_data.get("custom_name") or Path(self.file_data["filename"]).stem
            name, ok = QInputDialog.getText(self, "Rename", "Display name:", text=current)
            if ok and name.strip():
                db.update_custom_name(self.file_data["id"], name.strip())
                self.file_data["custom_name"] = name.strip()
                self.name_label.setText(name.strip())

        elif action == "notes":
            current = self.file_data.get("notes", "")
            notes, ok = QInputDialog.getMultiLineText(self, "Notes", "Notes:", current)
            if ok:
                db.update_file_notes(self.file_data["id"], notes)
                self.file_data["notes"] = notes

        elif action == "refresh_thumb":
            clear_thumbnail(self.file_data["path"])
            self.file_data["thumbnail_path"] = None
            self._load_thumbnail()

        elif action == "open_location":
            subprocess.Popen(["explorer", "/select,", self.file_data["path"]])

        elif action == "delete":
            reply = QMessageBox.question(
                self, "Remove from Library",
                f"Remove '{self.file_data['filename']}' from library?\n"
                "(File stays on disk)",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                db.delete_file(self.file_data["id"])
                self.refresh_requested.emit()


def _menu_style() -> str:
    return """
        QMenu {
            background: #1e2d3d; color: #c6d4df;
            border: 1px solid #2a3f5a; border-radius: 4px; padding: 4px;
        }
        QMenu::item { padding: 6px 20px; border-radius: 3px; }
        QMenu::item:selected { background: #2a475e; color: white; }
        QMenu::separator { background: #2a3f5a; height: 1px; margin: 3px 8px; }
    """
