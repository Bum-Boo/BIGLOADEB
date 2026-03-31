from __future__ import annotations

import base64
import os
import tempfile
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ig_post_controller.database import Database
from ig_post_controller.config import APP_BRAND_NAME
from ig_post_controller.models import MediaItem, NewPostCheckResult, PostRecord
from ig_post_controller.services.account_service import AccountService
from ig_post_controller.services.download_service import DownloadService
from ig_post_controller.services.image_cache_service import ImageCacheService
from ig_post_controller.ui.i18n import LanguageManager
from ig_post_controller.ui.main_window import MainWindow
from ig_post_controller.ui.widgets import PostCard

IMAGE_BYTES = base64.b64decode("R0lGODlhAQABAIABAP///wAAACwAAAAAAQABAAACAkQBADs=")


class SlowFeedInstagramService:
    def __init__(self, delay_seconds: float = 0.25) -> None:
        self.delay_seconds = delay_seconds
        self.cached_calls = 0
        self.cached_thread_ids: list[int] = []
        self.refresh_calls = 0
        self.refresh_thread_ids: list[int] = []

    def resolve_profile(self, profile_input: str) -> dict[str, str]:
        raise ValueError("Not used in this test")

    def initial_sync_account(self, account_id: int, limit: int = 24):
        return []

    def refresh_account_posts(self, account_id: int, limit: int = 24):
        self.refresh_calls += 1
        self.refresh_thread_ids.append(threading.get_ident())
        time.sleep(self.delay_seconds)
        return []

    def refresh_all_accounts(self, limit: int = 24):
        self.refresh_calls += 1
        self.refresh_thread_ids.append(threading.get_ident())
        time.sleep(self.delay_seconds)
        return []

    def check_for_new_posts(self, limit: int = 12) -> NewPostCheckResult:
        return NewPostCheckResult(new_posts=[], checked_accounts=0)

    def get_cached_posts(self, **kwargs):
        self.cached_calls += 1
        self.cached_thread_ids.append(threading.get_ident())
        time.sleep(self.delay_seconds)
        return []

    def get_post_by_shortcode(self, shortcode: str):
        return None

    def refresh_post(self, shortcode: str):
        raise ValueError("Not used in this test")


class FourPostInstagramService(SlowFeedInstagramService):
    def __init__(self, thumbnail_source: str | None = None) -> None:
        super().__init__(delay_seconds=0.05)
        base_time = datetime(2026, 4, 1, 9, 0, 0)
        self._posts = [
            PostRecord(
                id=index + 1,
                account_id=1,
                username="accounta",
                display_name="Account A",
                company_name="Company A",
                shortcode=f"code{index}",
                caption=f"Caption {index}",
                taken_at=base_time,
                post_type="image",
                has_image=True,
                has_video=False,
                thumbnail_url=thumbnail_source,
                source_url=f"https://www.instagram.com/p/code{index}/",
                media_items=[MediaItem(index=0, media_type="image", thumbnail_url=thumbnail_source)],
            )
            for index in range(4)
        ]

    def get_cached_posts(self, **kwargs):
        self.cached_calls += 1
        self.cached_thread_ids.append(threading.get_ident())
        time.sleep(self.delay_seconds)
        return list(self._posts)


class SlowThumbnailImageCacheService(ImageCacheService):
    def __init__(self, delay_seconds: float = 0.2) -> None:
        super().__init__()
        self.delay_seconds = delay_seconds
        self.fetch_calls = 0

    def fetch_image_bytes(self, source: str | None) -> bytes | None:
        self.fetch_calls += 1
        time.sleep(self.delay_seconds)
        return IMAGE_BYTES


def wait_until(predicate, app: QApplication, timeout_seconds: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    app.processEvents()
    return predicate()


class FeedOpenAsyncTests(unittest.TestCase):
    def test_open_account_feed_uses_background_workers(self) -> None:
        app = QApplication.instance() or QApplication([])
        main_thread_id = threading.get_ident()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            database = Database(db_path)
            account_service = AccountService(database)
            account = account_service.save_account(
                profile_url="https://www.instagram.com/accounta/",
                username="accounta",
                display_name="Account A",
                company_name="Company A",
            )
            download_service = DownloadService(database)
            download_service.set_download_root(Path(tmpdir) / "downloads")
            image_cache = ImageCacheService()
            translator = LanguageManager("ko")
            instagram_service = SlowFeedInstagramService()

            window = MainWindow(account_service, instagram_service, download_service, image_cache, translator)
            try:
                self.assertEqual(instagram_service.cached_calls, 0)

                started_at = time.perf_counter()
                window._show_account_feed(account.id)
                elapsed_ms = (time.perf_counter() - started_at) * 1000

                self.assertLess(elapsed_ms, 120, "Opening the feed blocked the UI thread")
                self.assertTrue(
                    wait_until(lambda: instagram_service.cached_calls >= 1 and instagram_service.refresh_calls >= 1, app),
                    "Feed load tasks never started",
                )
                self.assertTrue(
                    wait_until(lambda: window.active_task_count() == 0, app),
                    "Feed background tasks did not finish cleanly",
                )
                self.assertTrue(instagram_service.cached_thread_ids)
                self.assertTrue(instagram_service.refresh_thread_ids)
                self.assertTrue(all(thread_id != main_thread_id for thread_id in instagram_service.cached_thread_ids))
                self.assertTrue(all(thread_id != main_thread_id for thread_id in instagram_service.refresh_thread_ids))
            finally:
                window.close()

    def test_open_account_feed_shows_online_page_and_cards(self) -> None:
        app = QApplication.instance() or QApplication([])

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            database = Database(db_path)
            account_service = AccountService(database)
            account = account_service.save_account(
                profile_url="https://www.instagram.com/accounta/",
                username="accounta",
                display_name="Account A",
                company_name="Company A",
            )
            download_service = DownloadService(database)
            download_service.set_download_root(Path(tmpdir) / "downloads")
            image_cache = ImageCacheService()
            translator = LanguageManager("ko")
            instagram_service = FourPostInstagramService()

            window = MainWindow(account_service, instagram_service, download_service, image_cache, translator)
            window.show()
            try:
                self.assertTrue(wait_until(window.isVisible, app), "Main window never became visible")
                self.assertEqual(window.windowTitle(), APP_BRAND_NAME)
                self.assertEqual(window.app_title_label.text(), APP_BRAND_NAME)

                window._show_account_feed(account.id)

                self.assertTrue(
                    wait_until(lambda: window.pages.currentWidget() is window.online_feed_view, app),
                    "Online feed page never became active",
                )
                self.assertTrue(
                    wait_until(lambda: len(window.online_feed_view.grid_widget.cards) == 4, app),
                    "Online feed cards never finished rendering",
                )

                self.assertEqual(window.pages.currentIndex(), MainWindow.PAGE_ONLINE)
                self.assertIs(window.pages.currentWidget(), window.online_feed_view)
                self.assertTrue(window.online_feed_view.isVisible())
                self.assertTrue(window.isVisible())
                self.assertEqual(len(window.online_feed_view.grid_widget.cards), 4)
                self.assertTrue(
                    all(card.width() == PostCard.CARD_WIDTH for card in window.online_feed_view.grid_widget.cards),
                    "Rendered cards did not keep a stable fixed width",
                )
                self.assertTrue(
                    all(card.height() == PostCard.CARD_HEIGHT for card in window.online_feed_view.grid_widget.cards),
                    "Rendered cards did not keep a stable fixed height",
                )
                self.assertTrue(
                    all(card.thumbnail_label.width() == PostCard.CONTENT_WIDTH for card in window.online_feed_view.grid_widget.cards),
                    "Thumbnail previews did not keep a stable fixed width",
                )
                self.assertTrue(
                    all(card.caption_label.text().count("\n") <= 2 for card in window.online_feed_view.grid_widget.cards),
                    "Online feed captions were not clamped to the expected preview lines",
                )
                self.assertFalse(window.isHidden())
            finally:
                window.close()

    def test_open_account_feed_with_thumbnails_disabled_renders_without_thumbnail_tasks(self) -> None:
        app = QApplication.instance() or QApplication([])

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            database = Database(db_path)
            account_service = AccountService(database)
            account = account_service.save_account(
                profile_url="https://www.instagram.com/accounta/",
                username="accounta",
                display_name="Account A",
                company_name="Company A",
            )
            download_service = DownloadService(database)
            download_service.set_download_root(Path(tmpdir) / "downloads")
            image_cache = ImageCacheService()
            image_cache.thumbnails_enabled = False
            thumbnail_path = Path(tmpdir) / "thumb.jpg"
            thumbnail_path.write_bytes(b"not-an-image-but-still-a-source")
            instagram_service = FourPostInstagramService(str(thumbnail_path))
            translator = LanguageManager("ko")

            window = MainWindow(account_service, instagram_service, download_service, image_cache, translator)
            window.show()
            try:
                window._show_account_feed(account.id)
                self.assertTrue(
                    wait_until(lambda: len(window.online_feed_view.grid_widget.cards) == 4, app),
                    "Online feed cards never finished rendering",
                )
                self.assertEqual(len(window._thumbnail_tasks), 0)
                self.assertTrue(window.isVisible())
            finally:
                window.close()

    def test_auto_refresh_waits_until_feed_settles(self) -> None:
        app = QApplication.instance() or QApplication([])

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            database = Database(db_path)
            account_service = AccountService(database)
            account = account_service.save_account(
                profile_url="https://www.instagram.com/accounta/",
                username="accounta",
                display_name="Account A",
                company_name="Company A",
            )
            download_service = DownloadService(database)
            download_service.set_download_root(Path(tmpdir) / "downloads")
            image_cache = SlowThumbnailImageCacheService(delay_seconds=0.18)
            thumbnail_path = Path(tmpdir) / "thumb.gif"
            thumbnail_path.write_bytes(IMAGE_BYTES)
            instagram_service = FourPostInstagramService(str(thumbnail_path))
            translator = LanguageManager("ko")

            window = MainWindow(account_service, instagram_service, download_service, image_cache, translator)
            window.show()
            try:
                window._show_account_feed(account.id)
                self.assertTrue(
                    wait_until(lambda: len(window.online_feed_view.grid_widget.cards) == 4, app),
                    "Online feed cards never finished rendering",
                )
                self.assertEqual(
                    instagram_service.refresh_calls,
                    0,
                    "Auto refresh started before the feed settled",
                )
                self.assertTrue(
                    wait_until(lambda: instagram_service.refresh_calls == 1, app, timeout_seconds=3.0),
                    "Delayed auto refresh never started after the feed settled",
                )
            finally:
                window.close()

    def test_feed_stays_responsive_while_first_visible_thumbnails_apply(self) -> None:
        app = QApplication.instance() or QApplication([])

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            database = Database(db_path)
            account_service = AccountService(database)
            account = account_service.save_account(
                profile_url="https://www.instagram.com/accounta/",
                username="accounta",
                display_name="Account A",
                company_name="Company A",
            )
            download_service = DownloadService(database)
            download_service.set_download_root(Path(tmpdir) / "downloads")
            image_cache = SlowThumbnailImageCacheService()
            thumbnail_path = Path(tmpdir) / "thumb.gif"
            thumbnail_path.write_bytes(IMAGE_BYTES)
            instagram_service = FourPostInstagramService(str(thumbnail_path))
            translator = LanguageManager("ko")

            window = MainWindow(account_service, instagram_service, download_service, image_cache, translator)
            window.show()
            try:
                window._show_account_feed(account.id)
                self.assertTrue(
                    wait_until(lambda: len(window.online_feed_view.grid_widget.cards) == 4, app),
                    "Online feed cards never finished rendering",
                )
                self.assertTrue(window.isVisible())
                self.assertEqual(window.pages.currentIndex(), MainWindow.PAGE_ONLINE)
                self.assertTrue(
                    wait_until(lambda: len(window._thumbnail_tasks) > 0, app, timeout_seconds=2.0),
                    "Visible thumbnail activation never started",
                )
                self.assertLessEqual(
                    len(window._thumbnail_tasks),
                    window.online_feed_view.VISIBLE_THUMBNAIL_BATCH_SIZE,
                    "Too many thumbnail tasks started at once for the first visible batch",
                )
                for _ in range(8):
                    app.processEvents()
                    self.assertTrue(window.isVisible())
                    self.assertIs(window.pages.currentWidget(), window.online_feed_view)
                    time.sleep(0.02)
            finally:
                window.close()


if __name__ == "__main__":
    unittest.main()
