from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ig_post_controller.database import Database
from ig_post_controller.models import MediaItem, PostRecord
from ig_post_controller.services.account_service import AccountService
from ig_post_controller.services.download_service import DownloadService
from ig_post_controller.services.image_cache_service import ImageCacheService
from ig_post_controller.ui.i18n import LanguageManager
from ig_post_controller.ui.widgets import PostCard


class DownloadedPostDeleteTests(unittest.TestCase):
    def test_delete_downloaded_post_removes_folder_and_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            account_service = AccountService(db)
            account = account_service.save_account(
                profile_url="https://www.instagram.com/clienta/",
                username="clienta",
                display_name="Client A",
                company_name="Client A",
            )
            taken_at = datetime(2026, 4, 1, 9, 0, 0)
            with db.connect() as connection:
                post_id = connection.execute(
                    """
                    INSERT INTO posts (
                        account_id, shortcode, caption, taken_at, post_type,
                        has_image, has_video, thumbnail_url, source_url, media_json,
                        first_seen_at, last_refreshed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        account.id,
                        "shortcode-1",
                        "Caption text",
                        taken_at.isoformat(),
                        "image",
                        1,
                        0,
                        "https://example.com/thumb.jpg",
                        "https://www.instagram.com/p/shortcode-1/",
                        "[{\"index\": 0, \"media_type\": \"image\", \"remote_url\": \"https://example.com/media.jpg\", \"thumbnail_url\": \"https://example.com/thumb.jpg\", \"local_path\": null, \"local_thumbnail_path\": null}]",
                        taken_at.isoformat(),
                        taken_at.isoformat(),
                    ),
                ).lastrowid

            post = PostRecord(
                id=post_id,
                account_id=account.id,
                username=account.username,
                display_name=account.display_name,
                company_name=account.company_name,
                shortcode="shortcode-1",
                caption="Caption text",
                taken_at=taken_at,
                post_type="image",
                has_image=True,
                has_video=False,
                thumbnail_url="https://example.com/thumb.jpg",
                source_url="https://www.instagram.com/p/shortcode-1/",
                media_items=[
                    MediaItem(
                        index=0,
                        media_type="image",
                        remote_url="https://example.com/media.jpg",
                        thumbnail_url="https://example.com/thumb.jpg",
                    )
                ],
            )

            download_service = DownloadService(db)
            download_service.set_download_root(Path(tmpdir) / "downloads")
            download_service._download_binary = lambda url, target: target.write_bytes(b"data")  # type: ignore[method-assign]

            saved = download_service.download_post(post)
            folder_path = Path(saved.folder_path or "")
            self.assertTrue(folder_path.exists())

            self.assertTrue(download_service.delete_downloaded_post(post_id))
            self.assertFalse(folder_path.exists())
            with db.connect() as connection:
                row = connection.execute("SELECT 1 FROM downloads WHERE post_id = ?", (post_id,)).fetchone()
            self.assertIsNone(row)

    def test_downloaded_post_card_is_fixed_size_and_clamps_caption(self) -> None:
        app = QApplication.instance() or QApplication([])
        self.assertIsNotNone(app)

        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            account_service = AccountService(db)
            account = account_service.save_account(
                profile_url="https://www.instagram.com/clienta/",
                username="clienta",
                display_name="Client A",
                company_name="Client A",
            )
            post = PostRecord(
                id=1,
                account_id=account.id,
                username=account.username,
                display_name=account.display_name,
                company_name=account.company_name,
                shortcode="shortcode-1",
                caption="이것은 다운로드 카드의 캡션 미리보기 길이를 확인하기 위한 매우 긴 한국어 문장입니다. 카드 높이가 늘어나지 않아야 합니다.",
                taken_at=datetime(2026, 4, 1, 9, 0, 0),
                post_type="image",
                has_image=True,
                has_video=False,
                thumbnail_url="https://example.com/thumb.jpg",
                source_url="https://www.instagram.com/p/shortcode-1/",
                media_items=[
                    MediaItem(
                        index=0,
                        media_type="image",
                        remote_url="https://example.com/media.jpg",
                        thumbnail_url="https://example.com/thumb.jpg",
                    )
                ],
                is_downloaded=True,
                folder_path=str(Path(tmpdir) / "Client A" / "posts"),
            )

            image_cache = ImageCacheService()
            image_cache.thumbnails_enabled = False
            card = PostCard(
                post,
                image_cache=image_cache,
                card_mode="downloaded",
                show_posted_checkbox=True,
                show_delete_button=True,
                translator=LanguageManager("ko"),
            )

            self.assertEqual(card.minimumWidth(), PostCard.CARD_WIDTH)
            self.assertEqual(card.maximumWidth(), PostCard.CARD_WIDTH)
            self.assertEqual(card.minimumHeight(), PostCard.DOWNLOAD_CARD_HEIGHT)
            self.assertEqual(card.maximumHeight(), PostCard.DOWNLOAD_CARD_HEIGHT)
            self.assertLessEqual(card.caption_label.text().count("\n"), 2)
            self.assertLessEqual(
                card.caption_label.height(),
                card.caption_label.fontMetrics().lineSpacing() * 3 + 4,
            )


if __name__ == "__main__":
    unittest.main()
