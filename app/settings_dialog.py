from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QFileDialog,
    QCheckBox, QLineEdit, QFormLayout, QMessageBox, QGroupBox,
    QDialogButtonBox, QInputDialog
)
from PySide6.QtCore import Qt

import app.database as db
from app.slicer import detect_slicers

DIALOG_STYLE = """
    QDialog { background: #1b2838; color: #c6d4df; }
    QTabWidget::pane { border: 1px solid #2a3f5a; background: #1b2838; }
    QTabBar::tab {
        background: #171d25; color: #8f98a0;
        padding: 8px 16px; border: 1px solid #2a3f5a;
        border-bottom: none;
    }
    QTabBar::tab:selected { background: #1b2838; color: #c6d4df; }
    QPushButton {
        background: #2a475e; color: #c6d4df;
        border: 1px solid #3a6b94; border-radius: 4px; padding: 6px 14px;
    }
    QPushButton:hover { background: #3a6b94; color: white; }
    QPushButton:pressed { background: #1a3a56; }
    QListWidget {
        background: #171d25; color: #c6d4df;
        border: 1px solid #2a3f5a; border-radius: 4px;
    }
    QListWidget::item:selected { background: #2a475e; }
    QLineEdit {
        background: #2a3f5a; color: #c6d4df;
        border: 1px solid #3d5a75; border-radius: 4px; padding: 5px 10px;
    }
    QCheckBox { color: #c6d4df; spacing: 8px; }
    QCheckBox::indicator {
        width: 16px; height: 16px;
        background: #2a3f5a; border: 1px solid #3d5a75; border-radius: 3px;
    }
    QCheckBox::indicator:checked { background: #66c0f4; border-color: #66c0f4; }
    QLabel { color: #c6d4df; }
    QGroupBox {
        color: #8f98a0; border: 1px solid #2a3f5a; border-radius: 4px;
        margin-top: 8px; padding-top: 8px; font-size: 11px;
    }
    QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
"""


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(560, 460)
        self.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)

        tabs = QTabWidget()
        tabs.addTab(self._build_folders_tab(), "📁  Folders")
        tabs.addTab(self._build_slicers_tab(), "▶  Slicers")
        tabs.addTab(self._build_thumbnails_tab(), "🖼  Thumbnails")
        layout.addWidget(tabs)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.setStyleSheet("""
            QDialogButtonBox QPushButton { min-width: 80px; }
        """)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    # ── Folders tab ──────────────────────────────────────────────────────────

    def _build_folders_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Watch folders — the library scans these for 3D print files:"))

        self.folder_list = QListWidget()
        for folder in db.get_watch_folders():
            self.folder_list.addItem(folder)
        layout.addWidget(self.folder_list)

        btns = QHBoxLayout()
        add_btn = QPushButton("+ Add Folder")
        add_btn.clicked.connect(self._add_folder)
        btns.addWidget(add_btn)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_folder)
        btns.addWidget(remove_btn)
        btns.addStretch()
        layout.addLayout(btns)

        return w

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            db.add_watch_folder(folder)
            self.folder_list.addItem(folder)

    def _remove_folder(self):
        item = self.folder_list.currentItem()
        if item:
            db.remove_watch_folder(item.text())
            self.folder_list.takeItem(self.folder_list.row(item))

    # ── Slicers tab ──────────────────────────────────────────────────────────

    def _build_slicers_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Configured slicers (name + executable path):"))

        self.slicer_list = QListWidget()
        self._reload_slicer_list()
        layout.addWidget(self.slicer_list)

        btns = QHBoxLayout()

        auto_btn = QPushButton("🔍 Auto-Detect")
        auto_btn.clicked.connect(self._auto_detect)
        btns.addWidget(auto_btn)

        add_btn = QPushButton("+ Add Manually")
        add_btn.clicked.connect(self._add_slicer)
        btns.addWidget(add_btn)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_slicer)
        btns.addWidget(remove_btn)

        btns.addStretch()
        layout.addLayout(btns)

        note = QLabel(
            "Tip: The first slicer in the list is the default. "
            "If you have multiple slicers, a submenu will appear when opening files."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #8f98a0; font-size: 11px;")
        layout.addWidget(note)

        return w

    def _reload_slicer_list(self):
        self.slicer_list.clear()
        for s in db.get_configured_slicers():
            item = QListWidgetItem(f"{s['name']}  —  {s['path']}")
            item.setData(Qt.UserRole, s)
            self.slicer_list.addItem(item)

    def _auto_detect(self):
        found = detect_slicers()
        if not found:
            QMessageBox.information(self, "Auto-Detect", "No known slicers found in default locations.")
            return
        current = {s["path"] for s in db.get_configured_slicers()}
        added = []
        slicers = db.get_configured_slicers()
        for name, path in found.items():
            if path not in current:
                slicers.append({"name": name, "path": path})
                added.append(name)
        db.save_slicers(slicers)
        self._reload_slicer_list()
        if added:
            QMessageBox.information(self, "Auto-Detect", f"Found and added:\n" + "\n".join(added))
        else:
            QMessageBox.information(self, "Auto-Detect", "All detected slicers are already configured.")

    def _add_slicer(self):
        name, ok = QInputDialog.getText(self, "Add Slicer", "Slicer name (e.g. OrcaSlicer):")
        if not ok or not name.strip():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, f"Find {name} Executable", "C:\\Program Files",
            "Executables (*.exe);;All Files (*)"
        )
        if path:
            slicers = db.get_configured_slicers()
            slicers.append({"name": name.strip(), "path": path})
            db.save_slicers(slicers)
            self._reload_slicer_list()

    def _remove_slicer(self):
        item = self.slicer_list.currentItem()
        if not item:
            return
        s = item.data(Qt.UserRole)
        slicers = [x for x in db.get_configured_slicers() if x["path"] != s["path"]]
        db.save_slicers(slicers)
        self._reload_slicer_list()

    # ── Thumbnails tab ───────────────────────────────────────────────────────

    def _build_thumbnails_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        group = QGroupBox("STL Thumbnail Options")
        g_layout = QVBoxLayout(group)
        g_layout.setSpacing(10)

        self.search_cb = QCheckBox(
            "Search internet for preview images (DuckDuckGo — no API key required)"
        )
        self.search_cb.setChecked(db.get_setting("enable_search", "1") == "1")
        g_layout.addWidget(self.search_cb)

        self.render_cb = QCheckBox(
            "Generate 3D render thumbnail when no image found\n"
            "(uses matplotlib — disable if your PC is slow)"
        )
        self.render_cb.setChecked(db.get_setting("enable_3d_render", "1") == "1")
        g_layout.addWidget(self.render_cb)

        layout.addWidget(group)

        clear_btn = QPushButton("🗑  Clear All Cached Thumbnails")
        clear_btn.clicked.connect(self._clear_thumbnails)
        layout.addWidget(clear_btn)

        note = QLabel(
            "Thumbnails are stored in your home folder under .3dprintlibrary/thumbnails/\n"
            "Changes take effect on the next scan."
        )
        note.setStyleSheet("color: #8f98a0; font-size: 11px;")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()

        return w

    def _clear_thumbnails(self):
        from pathlib import Path
        from app.thumbnail import THUMB_DIR
        import shutil
        if THUMB_DIR.exists():
            count = len(list(THUMB_DIR.glob("*.png")))
            reply = QMessageBox.question(
                self, "Clear Thumbnails",
                f"Delete {count} cached thumbnails?\nThey will be regenerated on next scan.",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                shutil.rmtree(str(THUMB_DIR), ignore_errors=True)
                # Clear thumbnail_path in DB
                with db.get_connection() as conn:
                    conn.execute("UPDATE files SET thumbnail_path = NULL")
                QMessageBox.information(self, "Done", "Thumbnail cache cleared.")

    def accept(self):
        db.set_setting("enable_search", "1" if self.search_cb.isChecked() else "0")
        db.set_setting("enable_3d_render", "1" if self.render_cb.isChecked() else "0")
        super().accept()
