from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ig_post_controller.models import AccountRecord
from ig_post_controller.ui.i18n import LanguageManager
from ig_post_controller.ui.widgets import format_last_checked


class AccountListView(QWidget):
    ACTION_ROW_HEIGHT = 88
    ACTION_BUTTON_HEIGHT = 36
    ACTION_BUTTON_EXTRA_WIDTH = 16
    ACTION_CELL_H_MARGIN = 10
    ACTION_CELL_V_MARGIN = 12
    ACTION_CELL_SPACING = 6
    ACTION_COLUMN_MIN_WIDTH = 236

    add_account_requested = Signal()
    refresh_account_requested = Signal(int)
    delete_account_requested = Signal(int)
    open_online_feed_requested = Signal(int)

    def __init__(self, translator: LanguageManager) -> None:
        super().__init__()
        self.translator = translator
        self._accounts: list[AccountRecord] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        self.title_label = QLabel()
        self.title_label.setObjectName("sectionTitleLabel")
        layout.addWidget(self.title_label)

        self.intro_label = QLabel()
        self.intro_label.setWordWrap(True)
        self.intro_label.setObjectName("accountIntroLabel")
        layout.addWidget(self.intro_label)

        actions = QHBoxLayout()
        self.add_button = QPushButton()
        self.add_button.setObjectName("primaryButton")
        self.add_button.clicked.connect(self._emit_add_account_requested)
        actions.addWidget(self.add_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.table = QTableWidget(0, 5)
        self._table_header_keys = [
            "account.table.company",
            "account.table.username",
            "account.table.display_name",
            "account.table.last_checked",
            "account.table.actions",
        ]
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(self.ACTION_ROW_HEIGHT)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setObjectName("accountTable")
        self.table.viewport().setObjectName("accountTableViewport")
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setWordWrap(True)
        layout.addWidget(self.table)

        self.empty_label = QLabel()
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setObjectName("emptyLabel")
        layout.addWidget(self.empty_label)
        self.retranslate_ui()
        self.translator.language_changed.connect(self.retranslate_ui)

    def _emit_add_account_requested(self, *_args) -> None:
        self.add_account_requested.emit()

    def retranslate_ui(self, *_args) -> None:
        self.title_label.setText(self.translator.tr("account.title"))
        self.intro_label.setText(self.translator.tr("account.intro"))
        self.add_button.setText(self.translator.tr("account.add_button"))
        self.table.setHorizontalHeaderLabels([self.translator.tr(key) for key in self._table_header_keys])
        self.empty_label.setText(self.translator.tr("account.empty"))
        self.set_accounts(self._accounts)

    def set_accounts(self, accounts: list[AccountRecord]) -> None:
        self._accounts = list(accounts)
        self.table.setRowCount(len(accounts))
        self.empty_label.setVisible(not accounts)
        self.table.setVisible(bool(accounts))
        max_action_width = self.ACTION_COLUMN_MIN_WIDTH

        for row_index, account in enumerate(accounts):
            self.table.setItem(row_index, 0, QTableWidgetItem(account.company_name))
            self.table.setItem(row_index, 1, QTableWidgetItem(account.username))
            self.table.setItem(row_index, 2, QTableWidgetItem(account.display_name))
            self.table.setItem(row_index, 3, QTableWidgetItem(format_last_checked(account.last_checked_at, self.translator)))

            action_cell = QWidget()
            action_cell.setObjectName("accountActionCell")
            action_layout = QHBoxLayout(action_cell)
            action_layout.setContentsMargins(
                self.ACTION_CELL_H_MARGIN,
                self.ACTION_CELL_V_MARGIN,
                self.ACTION_CELL_H_MARGIN,
                self.ACTION_CELL_V_MARGIN,
            )
            action_layout.setSpacing(self.ACTION_CELL_SPACING)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            feed_button = QPushButton(self.translator.tr("account.feed"))
            feed_button.setProperty("accountAction", True)
            feed_button.ensurePolished()
            feed_button.setMinimumHeight(self.ACTION_BUTTON_HEIGHT)
            feed_button.setMaximumHeight(self.ACTION_BUTTON_HEIGHT)
            feed_button.setMinimumWidth(feed_button.sizeHint().width() + self.ACTION_BUTTON_EXTRA_WIDTH)
            feed_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            feed_button.clicked.connect(lambda *_, account_id=account.id: self.open_online_feed_requested.emit(account_id))
            action_layout.addWidget(feed_button)

            refresh_button = QPushButton(self.translator.tr("account.refresh"))
            refresh_button.setProperty("accountAction", True)
            refresh_button.ensurePolished()
            refresh_button.setMinimumHeight(self.ACTION_BUTTON_HEIGHT)
            refresh_button.setMaximumHeight(self.ACTION_BUTTON_HEIGHT)
            refresh_button.setMinimumWidth(refresh_button.sizeHint().width() + self.ACTION_BUTTON_EXTRA_WIDTH)
            refresh_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            refresh_button.clicked.connect(lambda *_, account_id=account.id: self.refresh_account_requested.emit(account_id))
            action_layout.addWidget(refresh_button)

            delete_button = QPushButton(self.translator.tr("account.delete"))
            delete_button.setProperty("accountAction", True)
            delete_button.ensurePolished()
            delete_button.setMinimumHeight(self.ACTION_BUTTON_HEIGHT)
            delete_button.setMaximumHeight(self.ACTION_BUTTON_HEIGHT)
            delete_button.setObjectName("dangerButton")
            delete_button.setMinimumWidth(delete_button.sizeHint().width() + self.ACTION_BUTTON_EXTRA_WIDTH)
            delete_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            delete_button.clicked.connect(lambda *_, account_id=account.id: self.delete_account_requested.emit(account_id))
            action_layout.addWidget(delete_button)

            action_min_width = (
                feed_button.minimumWidth()
                + refresh_button.minimumWidth()
                + delete_button.minimumWidth()
                + action_layout.spacing() * 2
                + action_layout.contentsMargins().left()
                + action_layout.contentsMargins().right()
            )
            max_action_width = max(max_action_width, action_min_width)
            self.table.setCellWidget(row_index, 4, action_cell)
            self.table.setRowHeight(row_index, self.ACTION_ROW_HEIGHT)
            action_cell.setMinimumSize(action_min_width, self.ACTION_ROW_HEIGHT - (self.ACTION_CELL_V_MARGIN * 2))

        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(1)
        self.table.resizeColumnToContents(3)
        self.table.setColumnWidth(4, max(self.ACTION_COLUMN_MIN_WIDTH, max_action_width + 8))
