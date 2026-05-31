from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLineEdit,
    QPushButton, QLabel, QStatusBar, QSplitter, QToolBar,
    QFileDialog, QMessageBox, QComboBox, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QAction, QIcon

from app.widgets.sidebar import CategorySidebar
from app.widgets.library_grid import LibraryGrid
from app.scanner import scan_folder, detect_category
from app.thumbnail import get_or_create_thumbnail
import app.database as db
from app.settings_dialog import SettingsDialog


TOOLBAR_STYLE = """
    QToolBar {
        background: #171d25;
        border-bottom: 1px solid #2a3f5a;
        spacing: 6px;
        padding: 6px 10px;
    }
    QToolButton {
        color: #c6d4df;
        padding: 5px 10px;
        border-radius: 4px;
        font-size: 12px;
        border: none;
    }
    QToolButton:hover { background: #2a475e; }
    QToolButton:pressed { background: #1a3a56; }
    QToolBar::separator {
        background: #2a3f5a;
        width: 1px;
        margin: 4px 4px;
    }
"""

SORT_OPTIONS = ["Date Added (newest)", "Date Added (oldest)", "Name A–Z", "Name Z–A", "Format", "Size"]


class ScanWorker(QThread):
    progress = Signal(str)
    finished = Signal(int)

    def __init__(self, folders: list, enable_3d: bool, enable_search: bool):
        super().__init__()
        self.folders = folders
        self.enable_3d = enable_3d
        self.enable_search = enable_search
        self._running = True

    def run(self):
        count = 0
        for folder in self.folders:
            if not self._running:
                break
            self.progress.emit(f"Scanning  {folder} …")
            for path, filename, fmt, size in scan_folder(folder):
                if not self._running:
                    break
                category, subcategory = detect_category(filename)
                thumb = get_or_create_thumbnail(
                    path, fmt,
                    enable_3d_render=self.enable_3d,
                    enable_search=self.enable_search,
                )
                db.upsert_file(path, filename, fmt, size, category, subcategory, thumb)
                count += 1
                if count % 10 == 0:
                    self.progress.emit(f"Scanning … {count} files processed")
        self.finished.emit(count)

    def stop(self):
        self._running = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D Print Library")
        self.setMinimumSize(1000, 680)
        self.resize(1440, 900)
        self._scan_worker = None
        self._setup_ui()
        self._load_library()
        QTimer.singleShot(200, self._check_initial_setup)

    # ── UI setup ──────────────────────────────────────────────────────────────

    def _setup_ui(self):
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self.setStyleSheet("QMainWindow { background: #1b2838; }")

    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)
        tb.setStyleSheet(TOOLBAR_STYLE)

        # Search
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍  Search files…")
        self.search_box.setFixedWidth(280)
        self.search_box.setStyleSheet("""
            QLineEdit {
                background: #2a3f5a; color: #c6d4df;
                border: 1px solid #3d5a75; border-radius: 4px;
                padding: 6px 12px; font-size: 13px;
            }
            QLineEdit:focus { border-color: #66c0f4; }
        """)
        self.search_box.textChanged.connect(self._on_search)
        tb.addWidget(self.search_box)

        tb.addSeparator()

        add_btn = QAction("+ Add Folder", self)
        add_btn.triggered.connect(self._add_folder)
        tb.addAction(add_btn)

        self.scan_action = QAction("↻  Scan Now", self)
        self.scan_action.triggered.connect(self._scan_folders)
        tb.addAction(self.scan_action)

        tb.addSeparator()

        # Sort combo
        sort_label = QLabel("Sort:")
        sort_label.setStyleSheet("color: #8f98a0; font-size: 12px; padding: 0 4px;")
        tb.addWidget(sort_label)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(SORT_OPTIONS)
        self.sort_combo.setStyleSheet("""
            QComboBox {
                background: #2a3f5a; color: #c6d4df;
                border: 1px solid #3d5a75; border-radius: 4px;
                padding: 5px 10px; font-size: 12px; min-width: 180px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #1e2d3d; color: #c6d4df;
                border: 1px solid #3d5a75; selection-background-color: #2a475e;
            }
        """)
        self.sort_combo.currentIndexChanged.connect(lambda _: self._load_library())
        tb.addWidget(self.sort_combo)

        # Spacer
        from PySide6.QtWidgets import QSizePolicy
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

        settings_action = QAction("⚙  Settings", self)
        settings_action.triggered.connect(self._open_settings)
        tb.addAction(settings_action)

    def _build_central(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle { background: #2a3f5a; width: 1px; }
        """)

        self.sidebar = CategorySidebar()
        self.sidebar.category_selected.connect(lambda _cat, _sub: self._load_library())
        splitter.addWidget(self.sidebar)

        self.grid = LibraryGrid()
        self.grid.refresh_requested.connect(self._load_library)
        splitter.addWidget(self.grid)

        splitter.setSizes([180, 1200])
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def _build_statusbar(self):
        sb = QStatusBar()
        sb.setStyleSheet("QStatusBar { background: #171d25; color: #8f98a0; border-top: 1px solid #2a3f5a; }")
        self.setStatusBar(sb)

        self.status_label = QLabel("Ready")
        sb.addWidget(self.status_label)

        self.scan_btn_status = QPushButton("Stop Scan")
        self.scan_btn_status.setStyleSheet("""
            QPushButton {
                background: #e05c5c; color: white; border-radius: 3px;
                padding: 2px 10px; font-size: 11px; border: none;
            }
            QPushButton:hover { background: #c03a3a; }
        """)
        self.scan_btn_status.hide()
        self.scan_btn_status.clicked.connect(self._stop_scan)
        sb.addPermanentWidget(self.scan_btn_status)

        self.file_count_label = QLabel("")
        self.file_count_label.setStyleSheet("color: #546a7b; margin-right: 8px;")
        sb.addPermanentWidget(self.file_count_label)

    # ── Library loading ───────────────────────────────────────────────────────

    def _load_library(self):
        cat, sub = self.sidebar.current_selection()
        search = self.search_box.text().strip() or None
        files = db.get_all_files(
            category=cat if cat != "All" else None,
            subcategory=sub if sub else None,
            search=search,
        )
        files = self._sort_files(files, self.sort_combo.currentIndex())
        self.grid.load_files(files)
        self.sidebar.update_tree()

        total = len(db.get_all_files())
        self.file_count_label.setText(f"{len(files)} shown  /  {total} total")

    def _sort_files(self, files: list, sort_idx: int) -> list:
        if sort_idx == 0:  # newest
            return sorted(files, key=lambda f: f.get("date_added", ""), reverse=True)
        elif sort_idx == 1:  # oldest
            return sorted(files, key=lambda f: f.get("date_added", ""))
        elif sort_idx == 2:  # A-Z
            return sorted(files, key=lambda f: (f.get("custom_name") or f.get("filename", "")).lower())
        elif sort_idx == 3:  # Z-A
            return sorted(files, key=lambda f: (f.get("custom_name") or f.get("filename", "")).lower(), reverse=True)
        elif sort_idx == 4:  # format
            return sorted(files, key=lambda f: f.get("format", ""))
        elif sort_idx == 5:  # size
            return sorted(files, key=lambda f: f.get("size", 0), reverse=True)
        return files

    # ── Scanning ──────────────────────────────────────────────────────────────

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder containing 3D print files")
        if folder:
            db.add_watch_folder(folder)
            self._scan_folders()

    def _scan_folders(self):
        if self._scan_worker and self._scan_worker.isRunning():
            return

        folders = db.get_watch_folders()
        if not folders:
            self._add_folder()
            return

        enable_3d = db.get_setting("enable_3d_render", "1") == "1"
        enable_search = db.get_setting("enable_search", "1") == "1"

        self._scan_worker = ScanWorker(folders, enable_3d, enable_search)
        self._scan_worker.progress.connect(self.status_label.setText)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.start()

        self.scan_action.setEnabled(False)
        self.scan_btn_status.show()
        self.status_label.setText("Scanning…")

    def _stop_scan(self):
        if self._scan_worker:
            self._scan_worker.stop()

    def _on_scan_finished(self, count: int):
        removed = db.remove_missing_files()
        self._load_library()
        self.scan_action.setEnabled(True)
        self.scan_btn_status.hide()
        msg = f"Scan complete — {count} files found"
        if removed:
            msg += f", {removed} missing files removed"
        self.status_label.setText(msg)

    # ── Search & settings ─────────────────────────────────────────────────────

    def _on_search(self, text: str):
        self._load_library()

    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self._load_library()

    # ── Initial setup ─────────────────────────────────────────────────────────

    def _check_initial_setup(self):
        # Auto-detect slicers silently on first launch
        if not db.get_configured_slicers():
            from app.slicer import detect_slicers
            found = detect_slicers()
            if found:
                slicers = [{"name": n, "path": p} for n, p in found.items()]
                db.save_slicers(slicers)
                names = ", ".join(found.keys())
                self.status_label.setText(f"Auto-detected: {names}")

        if not db.get_watch_folders():
            msg = QMessageBox(self)
            msg.setWindowTitle("Welcome to 3D Print Library")
            msg.setText(
                "No folders configured yet.\n\n"
                "Would you like to add a folder containing your 3D print files?"
            )
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setStyleSheet("""
                QMessageBox { background: #1b2838; color: #c6d4df; }
                QLabel { color: #c6d4df; }
                QPushButton {
                    background: #2a475e; color: #c6d4df;
                    border: 1px solid #3a6b94; border-radius: 4px;
                    padding: 6px 18px; min-width: 60px;
                }
                QPushButton:hover { background: #3a6b94; color: white; }
            """)
            if msg.exec() == QMessageBox.Yes:
                self._add_folder()

    def closeEvent(self, event):
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.stop()
            self._scan_worker.wait(3000)
        super().closeEvent(event)
