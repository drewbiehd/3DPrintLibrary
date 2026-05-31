from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QColor, QFont

CATEGORY_ICONS = {
    "All":                "★",
    "Tools":              "🔧",
    "Clicker Toys":       "🖱",
    "Toys":               "🚗",
    "Gaming & Tabletop":  "🎲",
    "Cosplay & Props":    "⚔",
    "Household":          "🏠",
    "Art & Decor":        "🎨",
    "Gadgets & Electronics": "💡",
    "Utility":            "📦",
    "Outdoors & Garden":  "🌿",
    "Fashion & Jewelry":  "💎",
    "3D Printer Parts":   "🖨",
    "Education":          "📚",
    "Repairs":            "🔩",
    "Uncategorized":      "📁",
}

CATEGORY_COLORS = {
    "All":                "#c6d4df",
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


class CategorySidebar(QWidget):
    category_selected = Signal(str)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(180)
        self.setStyleSheet("background: #171d25;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("LIBRARY")
        header.setStyleSheet("""
            color: #8f98a0;
            font-size: 10px;
            font-weight: bold;
            padding: 14px 16px 8px 16px;
            letter-spacing: 1px;
        """)
        layout.addWidget(header)

        self.list = QListWidget()
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                padding: 0;
            }
            QListWidget::item {
                color: #8f98a0;
                padding: 8px 16px;
                border-radius: 0px;
                font-size: 13px;
            }
            QListWidget::item:hover {
                background: #1e2a38;
                color: #c6d4df;
            }
            QListWidget::item:selected {
                background: #2a475e;
                color: #ffffff;
                border-left: 3px solid #66c0f4;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 5px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #3a5a7a;
                border-radius: 2px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover { background: #66c0f4; }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { height: 0; border: none; }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical { background: transparent; }
        """)
        self.list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list)

        self._categories = []
        self._populate([], 0)

    def _populate(self, categories: list, total: int):
        self.list.clear()

        all_item = QListWidgetItem(f"  {CATEGORY_ICONS.get('All', '★')}  All  ({total})")
        all_item.setData(Qt.UserRole, "All")
        self.list.addItem(all_item)

        # Add separator spacer
        sep = QListWidgetItem("")
        sep.setFlags(Qt.NoItemFlags)
        sep.setSizeHint(QSize(0, 6))
        self.list.addItem(sep)

        label_item = QListWidgetItem("  CATEGORIES")
        label_item.setFlags(Qt.NoItemFlags)
        font = label_item.font()
        font.setPointSize(8)
        label_item.setFont(font)
        label_item.setForeground(QColor("#546a7b"))
        self.list.addItem(label_item)

        ordered = [
            "Tools", "Clicker Toys", "Toys", "Gaming & Tabletop",
            "Cosplay & Props", "Household", "Art & Decor",
            "Gadgets & Electronics", "Utility", "Outdoors & Garden",
            "Fashion & Jewelry", "3D Printer Parts", "Education",
            "Repairs", "Uncategorized",
        ]
        cat_counts = {c["category"]: c["count"] for c in categories}

        for cat in ordered:
            count = cat_counts.get(cat, 0)
            icon = CATEGORY_ICONS.get(cat, "📁")
            item = QListWidgetItem(f"  {icon}  {cat}  ({count})")
            item.setData(Qt.UserRole, cat)
            color = CATEGORY_COLORS.get(cat, "#8f98a0")
            item.setForeground(QColor(color if count > 0 else "#4a5a6a"))
            self.list.addItem(item)

        # Select "All" by default
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    def update_categories(self, categories: list, total: int):
        current = self.current_category()
        self._populate(categories, total)
        # Restore selection
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item and item.data(Qt.UserRole) == current:
                self.list.setCurrentItem(item)
                break

    def _on_item_clicked(self, item: QListWidgetItem):
        cat = item.data(Qt.UserRole)
        if cat:
            self.category_selected.emit(cat)

    def current_category(self) -> str:
        item = self.list.currentItem()
        if item:
            cat = item.data(Qt.UserRole)
            if cat:
                return cat
        return "All"
