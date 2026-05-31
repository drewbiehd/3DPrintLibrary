from PySide6.QtWidgets import (
    QScrollArea, QWidget, QGridLayout, QLabel, QSizePolicy
)
from PySide6.QtCore import Signal, Qt

from app.widgets.file_card import FileCard, CARD_WIDTH

CARD_SPACING = 12
GRID_MARGIN = 16


class LibraryGrid(QScrollArea):
    refresh_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QScrollArea { background: #1b2838; border: none; }
            QScrollBar:vertical {
                background: #1b2838; width: 8px; margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #2a3f5a; border-radius: 4px; min-height: 20px;
            }
            QScrollBar::handle:vertical:hover { background: #3a6b94; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        self._container = QWidget()
        self._container.setStyleSheet("background: #1b2838;")
        self._layout = QGridLayout(self._container)
        self._layout.setSpacing(CARD_SPACING)
        self._layout.setContentsMargins(GRID_MARGIN, GRID_MARGIN, GRID_MARGIN, GRID_MARGIN)
        self._layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.setWidget(self._container)

        self._cards: list[FileCard] = []
        self._empty_label = None

    def load_files(self, files: list):
        self._clear()
        for f in files:
            card = FileCard(f)
            card.refresh_requested.connect(self.refresh_requested)
            self._cards.append(card)
        self._relayout()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()

    def _clear(self):
        for card in self._cards:
            self._layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        if self._empty_label:
            self._layout.removeWidget(self._empty_label)
            self._empty_label.deleteLater()
            self._empty_label = None
        while self._layout.count():
            self._layout.takeAt(0)

    def _relayout(self):
        if not self._cards:
            self._show_empty()
            return

        while self._layout.count():
            self._layout.takeAt(0)

        available = self.viewport().width() - 2 * GRID_MARGIN
        cols = max(1, (available + CARD_SPACING) // (CARD_WIDTH + CARD_SPACING))

        for i, card in enumerate(self._cards):
            row, col = divmod(i, cols)
            self._layout.addWidget(card, row, col, Qt.AlignTop | Qt.AlignLeft)

        self._layout.setRowStretch(self._layout.rowCount(), 1)

    def _show_empty(self):
        self._empty_label = QLabel(
            "No files found.\n\nAdd a folder with the '+ Add Folder' button\nor use Settings to manage your library folders."
        )
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color: #546a7b; font-size: 14px; padding: 60px;")
        self._empty_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._layout.addWidget(self._empty_label, 0, 0)
