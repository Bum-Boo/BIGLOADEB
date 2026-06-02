from __future__ import annotations

import os
import unittest
from datetime import datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ig_post_controller.models import AccountRecord
from ig_post_controller.services.image_cache_service import ImageCacheService
from ig_post_controller.ui.downloaded_feed_view import DownloadedFeedView
from ig_post_controller.ui.i18n import LanguageManager
from ig_post_controller.ui.online_feed_view import OnlineFeedView


class FeedSignalSmokeTests(unittest.TestCase):
    def _make_accounts(self) -> list[AccountRecord]:
        now = datetime(2026, 4, 1, 9, 0)
        return [
            AccountRecord(
                id=1,
                profile_url="https://www.instagram.com/account-a/",
                username="accounta",
                display_name="Account A",
                company_name="Company A",
                created_at=now,
                updated_at=now,
            ),
            AccountRecord(
                id=2,
                profile_url="https://www.instagram.com/account-b/",
                username="accountb",
                display_name="Account B",
                company_name="Company B",
                created_at=now,
                updated_at=now,
            ),
        ]

    def test_feed_controls_accept_qt_arguments(self) -> None:
        app = QApplication.instance() or QApplication([])
        image_cache = ImageCacheService()
        translator = LanguageManager("ko")
        accounts = self._make_accounts()

        for view_cls in (OnlineFeedView, DownloadedFeedView):
            view = view_cls(image_cache, translator)
            try:
                view.set_accounts(accounts)
                view.account_filter.setCurrentIndex(1)
                view.media_filter.setCurrentIndex(1)
                view.sort_filter.setCurrentIndex(1)
                view.refresh_button.click()
                app.processEvents()
            finally:
                view.deleteLater()


if __name__ == "__main__":
    unittest.main()
