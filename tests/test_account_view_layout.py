from __future__ import annotations

import os
import unittest
from datetime import datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton

from ig_post_controller.models import AccountRecord
from ig_post_controller.ui.account_view import AccountListView
from ig_post_controller.ui.i18n import LanguageManager
from ig_post_controller.ui.theme import ThemeManager


class AccountViewLayoutTests(unittest.TestCase):
    def test_account_table_action_cell_has_visible_separator_and_button_budget(self) -> None:
        app = QApplication.instance() or QApplication([])
        self.assertIsNotNone(app)

        theme = ThemeManager("clean_light")
        theme.bind_application(app)
        view = AccountListView(LanguageManager("ko"))
        account = AccountRecord(
            id=1,
            profile_url="https://www.instagram.com/clienta/",
            username="clienta",
            display_name="클라이언트A",
            company_name="클라이언트 A",
            created_at=datetime(2026, 4, 1, 9, 0, 0),
            updated_at=datetime(2026, 4, 1, 9, 0, 0),
            last_checked_at=datetime(2026, 4, 1, 10, 0, 0),
        )
        view.set_accounts([account])
        view.show()
        app.processEvents()

        self.assertIn("QWidget#accountActionCell", app.styleSheet())
        self.assertIn("border-bottom", app.styleSheet())
        self.assertEqual(view.table.rowHeight(0), view.ACTION_ROW_HEIGHT)

        action_cell = view.table.cellWidget(0, 4)
        self.assertIsNotNone(action_cell)
        self.assertGreaterEqual(view.table.columnWidth(4), action_cell.minimumWidth())

        buttons = action_cell.findChildren(QPushButton)
        self.assertEqual(len(buttons), 3)
        for button in buttons:
            self.assertGreaterEqual(button.minimumHeight(), view.ACTION_BUTTON_HEIGHT)
            self.assertGreaterEqual(button.minimumWidth(), button.sizeHint().width())


if __name__ == "__main__":
    unittest.main()
