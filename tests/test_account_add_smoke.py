from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox

from ig_post_controller.database import Database
from ig_post_controller.models import NewPostCheckResult
from ig_post_controller.services.account_service import AccountService
from ig_post_controller.services.download_service import DownloadService
from ig_post_controller.services.image_cache_service import ImageCacheService
from ig_post_controller.services.instagram_service import InstagramAccessError
from ig_post_controller.ui.i18n import LanguageManager
from ig_post_controller.ui.main_window import MainWindow


class FailingInstagramService:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def resolve_profile(self, profile_input: str) -> dict[str, str]:
        raise self.exc

    def initial_sync_account(self, account_id: int, limit: int = 24):
        return []


class InitialSyncLimitedInstagramService(FailingInstagramService):
    def __init__(self) -> None:
        super().__init__(InstagramAccessError("Instagram limited feed access"))

    def resolve_profile(self, profile_input: str) -> dict[str, str]:
        return {
            "profile_url": "https://www.instagram.com/katarinabluu/",
            "username": "katarinabluu",
            "display_name": "Katarina Blue",
        }

    def initial_sync_account(self, account_id: int, limit: int = 24):
        raise self.exc

    def refresh_account_posts(self, account_id: int, limit: int = 24):
        return []

    def refresh_all_accounts(self, limit: int = 24):
        return []

    def check_for_new_posts(self, limit: int = 12) -> NewPostCheckResult:
        return NewPostCheckResult(new_posts=[], checked_accounts=0)

    def get_cached_posts(self, **kwargs):
        return []

    def get_post_by_shortcode(self, shortcode: str):
        return None

    def refresh_post(self, shortcode: str):
        raise self.exc


def wait_until(predicate, app: QApplication, timeout_seconds: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    app.processEvents()
    return predicate()


class AccountAddSmokeTests(unittest.TestCase):
    def test_invalid_or_unreachable_url_does_not_crash(self) -> None:
        app = QApplication.instance() or QApplication([])

        cases = [
            ValueError("Invalid Instagram profile URL"),
            ConnectionError("Instagram is unreachable"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            database = Database(db_path)
            account_service = AccountService(database)
            download_service = DownloadService(database)
            download_service.set_download_root(Path(tmpdir) / "downloads")
            image_cache = ImageCacheService()
            translator = LanguageManager("ko")

            for exc in cases:
                instagram_service = FailingInstagramService(exc)
                window = MainWindow(account_service, instagram_service, download_service, image_cache, translator)
                try:
                    with mock.patch.object(QMessageBox, "critical", return_value=QMessageBox.StandardButton.Ok) as critical:
                        window.start_account_add("https://example.invalid/client/")
                        self.assertTrue(
                            wait_until(lambda: window.active_task_count() == 0, app),
                            "Background task did not finish cleanly",
                        )
                        self.assertGreaterEqual(critical.call_count, 1)
                finally:
                    window.close()

    def test_access_limited_initial_sync_still_saves_account(self) -> None:
        app = QApplication.instance() or QApplication([])

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            database = Database(db_path)
            account_service = AccountService(database)
            download_service = DownloadService(database)
            download_service.set_download_root(Path(tmpdir) / "downloads")
            image_cache = ImageCacheService()
            translator = LanguageManager("ko")
            instagram_service = InitialSyncLimitedInstagramService()
            window = MainWindow(account_service, instagram_service, download_service, image_cache, translator)
            try:
                with mock.patch.object(QMessageBox, "critical", return_value=QMessageBox.StandardButton.Ok) as critical:
                    with mock.patch.object(QMessageBox, "information", return_value=QMessageBox.StandardButton.Ok) as information:
                        window.start_account_add("https://www.instagram.com/katarinabluu/")
                        self.assertTrue(
                            wait_until(lambda: window.active_task_count() == 0, app),
                            "Background task did not finish cleanly",
                        )

                accounts = account_service.list_accounts()
                self.assertEqual(len(accounts), 1)
                self.assertEqual(accounts[0].username, "katarinabluu")
                self.assertEqual(critical.call_count, 0)
                self.assertGreaterEqual(information.call_count, 1)
                self.assertIn("계정은 저장되었습니다", information.call_args.args[2])
                self.assertIn("피드는 나중에 새로고침", information.call_args.args[2])
            finally:
                window.close()


if __name__ == "__main__":
    unittest.main()
