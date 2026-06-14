from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from ig_post_controller.database import Database
from ig_post_controller.models import MediaItem, PostRecord
from ig_post_controller.services.account_service import AccountService
from ig_post_controller.services.download_service import DownloadService
from ig_post_controller.services.instagram_service import InstagramService


def create_saved_post(db: Database) -> PostRecord:
    account_service = AccountService(db)
    account = account_service.save_account(
        profile_url="https://www.instagram.com/clienta/",
        username="clienta",
        display_name="Client A",
        company_name="Client A",
    )
    taken_at = datetime(2026, 4, 1, 9, 0, 0)
    media_json = (
        '[{"index": 0, "media_type": "image", '
        '"remote_url": "https://example.com/media.jpg", '
        '"thumbnail_url": "https://example.com/thumb.jpg", '
        '"local_path": null, "local_thumbnail_path": null}]'
    )
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
                media_json,
                taken_at.isoformat(),
                taken_at.isoformat(),
            ),
        ).lastrowid

    return PostRecord(
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


class DownloadServiceSafetyTests(unittest.TestCase):
    def test_failed_redownload_preserves_existing_folder_and_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            service = DownloadService(db)
            service.set_download_root(Path(tmpdir) / "downloads")
            post = create_saved_post(db)

            service._download_binary = lambda url, target: target.write_bytes(b"original")  # type: ignore[method-assign]
            saved = service.download_post(post)
            folder_path = Path(saved.folder_path or "")
            sentinel = folder_path / "keep.txt"
            sentinel.write_text("do not delete", encoding="utf-8")

            def fail_download(url: str, target: Path) -> None:
                raise RuntimeError("network failed")

            service._download_binary = fail_download  # type: ignore[method-assign]
            with self.assertRaises(RuntimeError):
                service.download_post(saved)

            self.assertTrue(folder_path.exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "do not delete")
            with db.connect() as connection:
                row = connection.execute("SELECT folder_path FROM downloads WHERE post_id = ?", (post.id,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(Path(row["folder_path"]), folder_path)

    def test_delete_downloaded_post_does_not_remove_path_outside_download_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            service = DownloadService(db)
            service.set_download_root(Path(tmpdir) / "downloads")
            post = create_saved_post(db)
            outside_folder = Path(tmpdir) / "outside-owned-folder"
            outside_folder.mkdir()
            sentinel = outside_folder / "keep.txt"
            sentinel.write_text("not owned by download root", encoding="utf-8")
            self._insert_download_record(db, post.id or 0, outside_folder)

            self.assertTrue(service.delete_downloaded_post(post.id or 0))
            self.assertTrue(outside_folder.exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "not owned by download root")
            with db.connect() as connection:
                row = connection.execute("SELECT 1 FROM downloads WHERE post_id = ?", (post.id,)).fetchone()
            self.assertIsNone(row)

    def test_delete_downloaded_post_does_not_remove_download_root_parent_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            service = DownloadService(db)
            root = service.set_download_root(Path(tmpdir) / "downloads")
            post = create_saved_post(db)
            parent_folder = root / "Client A"
            child_folder = parent_folder / "unrelated-download"
            child_folder.mkdir(parents=True)
            sentinel = child_folder / "keep.txt"
            sentinel.write_text("must stay", encoding="utf-8")
            self._insert_download_record(db, post.id or 0, parent_folder)

            self.assertTrue(service.delete_downloaded_post(post.id or 0))
            self.assertTrue(parent_folder.exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "must stay")

    def test_rename_failure_preserves_existing_target_folder_and_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            service = DownloadService(db)
            service.set_download_root(Path(tmpdir) / "downloads")
            post = create_saved_post(db)
            service._download_binary = lambda url, target: target.write_bytes(b"original")  # type: ignore[method-assign]
            saved = service.download_post(post)
            folder_path = Path(saved.folder_path or "")
            sentinel = folder_path / "keep.txt"
            sentinel.write_text("original folder", encoding="utf-8")
            original_rename = Path.rename

            def fail_temp_promote(self: Path, target: Path):
                if self.name.startswith(f".{folder_path.name}.tmp-"):
                    raise OSError("simulated promote failure")
                return original_rename(self, target)

            service._download_binary = lambda url, target: target.write_bytes(b"new")  # type: ignore[method-assign]
            with mock.patch.object(Path, "rename", fail_temp_promote):
                with self.assertRaises(OSError):
                    service.download_post(saved)

            self.assertTrue(folder_path.exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "original folder")
            with db.connect() as connection:
                row = connection.execute("SELECT folder_path FROM downloads WHERE post_id = ?", (post.id,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(Path(row["folder_path"]), folder_path)

    def test_download_does_not_move_target_folder_owned_by_another_shortcode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            service = DownloadService(db)
            root = service.set_download_root(Path(tmpdir) / "downloads")
            post = create_saved_post(db)
            target_dir = root / "Client A" / "posts" / "2026" / "04" / "2026-04-01_Caption text"
            target_dir.mkdir(parents=True)
            (target_dir / "caption.txt").write_text("other caption", encoding="utf-8")
            (target_dir / "meta.json").write_text('{"shortcode": "other-shortcode"}', encoding="utf-8")
            sentinel = target_dir / "keep.txt"
            sentinel.write_text("other folder", encoding="utf-8")
            service._download_binary = lambda url, target: target.write_bytes(b"new")  # type: ignore[method-assign]

            with self.assertRaises(FileExistsError):
                service.download_post(post)

            self.assertTrue(target_dir.exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "other folder")
            self.assertFalse(any(target_dir.parent.glob(f".{target_dir.name}.backup-*")))

    def test_download_does_not_move_plain_existing_target_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            service = DownloadService(db)
            root = service.set_download_root(Path(tmpdir) / "downloads")
            post = create_saved_post(db)
            target_dir = root / "Client A" / "posts" / "2026" / "04" / "2026-04-01_Caption text"
            target_dir.mkdir(parents=True)
            sentinel = target_dir / "manual.txt"
            sentinel.write_text("manual folder", encoding="utf-8")
            service._download_binary = lambda url, target: target.write_bytes(b"new")  # type: ignore[method-assign]

            with self.assertRaises(FileExistsError):
                service.download_post(post)

            self.assertTrue(target_dir.exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "manual folder")
            self.assertFalse(any(target_dir.parent.glob(f".{target_dir.name}.backup-*")))

    def test_list_downloaded_posts_marks_moved_folder_missing_and_uses_remote_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            service = DownloadService(db)
            service.set_download_root(Path(tmpdir) / "downloads")
            post = create_saved_post(db)
            service._download_binary = lambda url, target: target.write_bytes(b"image")  # type: ignore[method-assign]
            saved = service.download_post(post)
            folder_path = Path(saved.folder_path or "")
            moved_folder = Path(tmpdir) / "moved" / folder_path.name
            moved_folder.parent.mkdir()
            folder_path.rename(moved_folder)

            downloaded = service.list_downloaded_posts()

            self.assertEqual(len(downloaded), 1)
            self.assertTrue(downloaded[0].download_folder_missing)
            self.assertEqual(downloaded[0].get_preview_source(prefer_local=True), "https://example.com/thumb.jpg")

    def test_reconnect_downloaded_post_updates_moved_folder_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            service = DownloadService(db)
            service.set_download_root(Path(tmpdir) / "downloads")
            post = create_saved_post(db)
            service._download_binary = lambda url, target: target.write_bytes(b"image")  # type: ignore[method-assign]
            saved = service.download_post(post)
            old_folder = Path(saved.folder_path or "")
            moved_folder = Path(tmpdir) / "moved" / old_folder.name
            moved_folder.parent.mkdir()
            old_folder.rename(moved_folder)

            reconnected = service.reconnect_downloaded_post(post.id or 0, moved_folder)

            self.assertTrue(reconnected)
            downloaded = service.list_downloaded_posts()[0]
            self.assertFalse(downloaded.download_folder_missing)
            self.assertEqual(Path(downloaded.folder_path or ""), moved_folder)
            self.assertEqual(Path(downloaded.media_items[0].local_path or ""), moved_folder / "01.jpg")
            with db.connect() as connection:
                row = connection.execute(
                    "SELECT folder_path, caption_path, meta_path, media_json FROM downloads WHERE post_id = ?",
                    (post.id,),
                ).fetchone()
            self.assertEqual(Path(row["folder_path"]), moved_folder)
            self.assertEqual(Path(row["caption_path"]), moved_folder / "caption.txt")
            self.assertEqual(Path(row["meta_path"]), moved_folder / "meta.json")
            media_payload = json.loads(row["media_json"])
            self.assertEqual(Path(media_payload[0]["local_path"]), moved_folder / "01.jpg")

    def test_reconnect_downloaded_post_rejects_wrong_shortcode_without_changing_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            service = DownloadService(db)
            service.set_download_root(Path(tmpdir) / "downloads")
            post = create_saved_post(db)
            service._download_binary = lambda url, target: target.write_bytes(b"image")  # type: ignore[method-assign]
            saved = service.download_post(post)
            old_folder = Path(saved.folder_path or "")
            wrong_folder = Path(tmpdir) / "wrong"
            wrong_folder.mkdir()
            (wrong_folder / "caption.txt").write_text("wrong", encoding="utf-8")
            (wrong_folder / "meta.json").write_text('{"shortcode": "not-this-post", "media": []}', encoding="utf-8")

            with self.assertRaises(ValueError):
                service.reconnect_downloaded_post(post.id or 0, wrong_folder)

            with db.connect() as connection:
                row = connection.execute("SELECT folder_path FROM downloads WHERE post_id = ?", (post.id,)).fetchone()
            self.assertEqual(Path(row["folder_path"]), old_folder)

    def test_online_feed_marks_moved_download_folder_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            download_service = DownloadService(db)
            download_service.set_download_root(Path(tmpdir) / "downloads")
            post = create_saved_post(db)
            download_service._download_binary = lambda url, target: target.write_bytes(b"image")  # type: ignore[method-assign]
            saved = download_service.download_post(post)
            folder_path = Path(saved.folder_path or "")
            moved_folder = Path(tmpdir) / "moved" / folder_path.name
            moved_folder.parent.mkdir()
            folder_path.rename(moved_folder)
            instagram_service = InstagramService(db, AccountService(db))

            cached = instagram_service.get_cached_posts()

            self.assertEqual(len(cached), 1)
            self.assertTrue(cached[0].is_downloaded)
            self.assertTrue(cached[0].download_folder_missing)

    def test_delete_scope_is_false_for_reconnected_folder_outside_download_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            service = DownloadService(db)
            service.set_download_root(Path(tmpdir) / "downloads")
            post = create_saved_post(db)
            service._download_binary = lambda url, target: target.write_bytes(b"image")  # type: ignore[method-assign]
            saved = service.download_post(post)
            old_folder = Path(saved.folder_path or "")
            moved_folder = Path(tmpdir) / "moved" / old_folder.name
            moved_folder.parent.mkdir()
            old_folder.rename(moved_folder)
            self.assertTrue(service.reconnect_downloaded_post(post.id or 0, moved_folder))

            self.assertFalse(service.will_delete_download_files(post.id or 0))

    def test_reconnect_downloaded_post_rejects_wrong_post_url_without_changing_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            service = DownloadService(db)
            service.set_download_root(Path(tmpdir) / "downloads")
            post = create_saved_post(db)
            service._download_binary = lambda url, target: target.write_bytes(b"image")  # type: ignore[method-assign]
            saved = service.download_post(post)
            folder_path = Path(saved.folder_path or "")
            meta_path = folder_path / "meta.json"
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
            payload["post_url"] = "https://www.instagram.com/p/other-post/"
            meta_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(ValueError):
                service.reconnect_downloaded_post(post.id or 0, folder_path)

    def test_reconnect_downloaded_post_rejects_missing_post_url_without_changing_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            service = DownloadService(db)
            service.set_download_root(Path(tmpdir) / "downloads")
            post = create_saved_post(db)
            service._download_binary = lambda url, target: target.write_bytes(b"image")  # type: ignore[method-assign]
            saved = service.download_post(post)
            folder_path = Path(saved.folder_path or "")
            meta_path = folder_path / "meta.json"
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
            payload.pop("post_url", None)
            meta_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(ValueError):
                service.reconnect_downloaded_post(post.id or 0, folder_path)

    def test_reconnect_downloaded_post_rejects_broken_media_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            service = DownloadService(db)
            service.set_download_root(Path(tmpdir) / "downloads")
            post = create_saved_post(db)
            service._download_binary = lambda url, target: target.write_bytes(b"image")  # type: ignore[method-assign]
            saved = service.download_post(post)
            folder_path = Path(saved.folder_path or "")
            with db.connect() as connection:
                connection.execute("UPDATE downloads SET media_json = ? WHERE post_id = ?", ("{broken", post.id))

            with self.assertRaises(ValueError):
                service.reconnect_downloaded_post(post.id or 0, folder_path)

    def test_reconnect_downloaded_post_rejects_folder_without_media_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            service = DownloadService(db)
            service.set_download_root(Path(tmpdir) / "downloads")
            post = create_saved_post(db)
            service._download_binary = lambda url, target: target.write_bytes(b"image")  # type: ignore[method-assign]
            saved = service.download_post(post)
            folder_path = Path(saved.folder_path or "")
            (folder_path / "01.jpg").unlink()

            with self.assertRaises(ValueError):
                service.reconnect_downloaded_post(post.id or 0, folder_path)

    def test_broken_download_media_json_does_not_break_download_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            service = DownloadService(db)
            service.set_download_root(Path(tmpdir) / "downloads")
            post = create_saved_post(db)
            service._download_binary = lambda url, target: target.write_bytes(b"image")  # type: ignore[method-assign]
            service.download_post(post)
            with db.connect() as connection:
                connection.execute("UPDATE downloads SET media_json = ? WHERE post_id = ?", ("{broken", post.id))

            downloaded = service.list_downloaded_posts()

            self.assertEqual(len(downloaded), 1)
            self.assertEqual(downloaded[0].media_items, [])
            self.assertTrue(downloaded[0].download_folder_missing)

    def test_stale_temporary_download_folders_are_reported_not_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")
            service = DownloadService(db)
            root = service.set_download_root(Path(tmpdir) / "downloads")
            stale = root / "Client A" / "posts" / "2026" / "04" / ".post.tmp-old"
            stale.mkdir(parents=True)
            fresh = root / "Client A" / "posts" / "2026" / "04" / ".post.tmp-fresh"
            fresh.mkdir()
            old_time = time.time() - 48 * 3600
            os.utime(stale, (old_time, old_time))

            stale_paths = service.list_stale_temporary_download_folders(max_age_seconds=24 * 3600)

            self.assertIn(stale, stale_paths)
            self.assertNotIn(fresh, stale_paths)
            self.assertTrue(stale.exists())

    @staticmethod
    def _insert_download_record(db: Database, post_id: int, folder_path: Path) -> None:
        now = datetime.now().isoformat()
        with db.connect() as connection:
            connection.execute(
                """
                INSERT INTO downloads (
                    post_id, company_name, custom_title, folder_path, media_json,
                    caption_path, meta_path, posted_to_cafe, downloaded_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post_id,
                    "Client A",
                    "Unsafe path",
                    str(folder_path),
                    "[]",
                    str(folder_path / "caption.txt"),
                    str(folder_path / "meta.json"),
                    0,
                    now,
                    now,
                ),
            )


if __name__ == "__main__":
    unittest.main()
