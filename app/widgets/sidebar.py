from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, QHeaderView
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QFont

import app.database as db


class CategorySidebar(QWidget):
    # Emits (parent_category, subcategory) — subcategory is "" for parent-level clicks
    category_selected = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.setMinimumWidth(160)
        # No maximum — user can drag the splitter as wide as they need
        self.setStyleSheet("background: #171d25;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("LIBRARY")
        header.setStyleSheet("""
            color: #546a7b;
            font-size: 10px;
            font-weight: bold;
            padding: 14px 16px 6px 16px;
            letter-spacing: 1px;
        """)
        layout.addWidget(header)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(16)
        self.tree.setAnimated(True)
        self.tree.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tree.setTextElideMode(Qt.ElideNone)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background: transparent;
                border: none;
                outline: none;
                padding: 0;
                font-size: 13px;
            }
            QTreeWidget::item {
                color: #8f98a0;
                padding: 6px 8px 6px 4px;
                border-radius: 0;
            }
            QTreeWidget::item:hover {
                background: #1e2a38;
                color: #c6d4df;
            }
            QTreeWidget::item:selected {
                background: #2a475e;
                color: #ffffff;
                border-left: 3px solid #66c0f4;
            }
            QTreeWidget::branch {
                background: transparent;
            }
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {
                padding-left: 4px;
                color: #546a7b;
            }
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {
                padding-left: 4px;
                color: #546a7b;
            }
            QScrollBar:vertical {
                background: transparent; width: 5px; margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #3a5a7a; border-radius: 2px; min-height: 24px;
            }
            QScrollBar::handle:vertical:hover { background: #66c0f4; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
            QScrollBar:horizontal {
                background: transparent; height: 5px; margin: 0;
            }
            QScrollBar::handle:horizontal {
                background: #3a5a7a; border-radius: 2px; min-width: 24px;
            }
            QScrollBar::handle:horizontal:hover { background: #66c0f4; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
        """)
        self.tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.tree)

        self._current: tuple[str, str] = ("All", "")
        self._build_tree()

    # ── Public API ────────────────────────────────────────────────────────────

    def update_tree(self):
        """Rebuild the tree from the database (call after scan/change)."""
        cat, sub = self._current
        self._build_tree()
        self._restore_selection(cat, sub)

    def current_selection(self) -> tuple[str, str]:
        return self._current

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build_tree(self):
        self.tree.blockSignals(True)
        self.tree.clear()

        total = len(db.get_all_files())

        # "All" row
        all_item = QTreeWidgetItem(["  ★  All"])
        all_item.setData(0, Qt.UserRole, ("All", ""))
        all_item.setForeground(0, QColor("#c6d4df"))
        f = all_item.font(0)
        f.setBold(True)
        all_item.setFont(0, f)
        self._set_count(all_item, total)
        self.tree.addTopLevelItem(all_item)

        # Separator label
        sep = QTreeWidgetItem(["  CATEGORIES"])
        sep.setFlags(Qt.NoItemFlags)
        sep.setForeground(0, QColor("#546a7b"))
        sf = sep.font(0)
        sf.setPointSize(8)
        sep.setFont(0, sf)
        self.tree.addTopLevelItem(sep)

        tree_data = db.get_category_tree()
        for cat in tree_data:
            has_subs = any(s["count"] > 0 for s in cat["subcategories"])
            prefix = "▾ " if has_subs else "  "
            p_item = self._make_item(
                label=f"  {prefix}{cat['icon']}  {cat['name']}",
                data=(cat["name"], ""),
                color=cat["color"],
                count=cat["count"],
                bold=True,
            )
            for sub in cat["subcategories"]:
                if sub["count"] == 0:
                    continue   # hide empty subcategories to keep list tidy
                s_item = self._make_item(
                    label=f"  {sub['icon']}  {sub['name']}",
                    data=(cat["name"], sub["name"]),
                    color=sub["color"],
                    count=sub["count"],
                    bold=False,
                )
                p_item.addChild(s_item)

            self.tree.addTopLevelItem(p_item)
            # Collapsed by default — user clicks to expand

        self.tree.blockSignals(False)

    def _make_item(self, label: str, data: tuple, color: str,
                   count: int, bold: bool) -> QTreeWidgetItem:
        item = QTreeWidgetItem([label])
        item.setData(0, Qt.UserRole, data)
        item.setForeground(0, QColor(color if count > 0 else "#4a5a6a"))
        f = item.font(0)
        f.setBold(bold)
        item.setFont(0, f)
        self._set_count(item, count)
        return item

    @staticmethod
    def _set_count(item: QTreeWidgetItem, count: int):
        item.setData(0, Qt.UserRole + 1, count)
        # Append count to the label text
        current = item.text(0).rstrip()
        # Strip old count if present
        import re
        current = re.sub(r"\s+\(\d+\)\s*$", "", current)
        item.setText(0, f"{current}  ({count})")

    def _on_item_clicked(self, item: QTreeWidgetItem, _col: int):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        cat, sub = data
        self._current = (cat, sub)
        self.category_selected.emit(cat, sub)

    def _restore_selection(self, cat: str, sub: str):
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            d = top.data(0, Qt.UserRole)
            if d and d[0] == cat and d[1] == sub:
                self.tree.setCurrentItem(top)
                return
            for j in range(top.childCount()):
                child = top.child(j)
                d = child.data(0, Qt.UserRole)
                if d and d[0] == cat and d[1] == sub:
                    self.tree.setCurrentItem(child)
                    return
        # fallback: select All
        self.tree.setCurrentItem(self.tree.topLevelItem(0))
