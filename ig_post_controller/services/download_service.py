from __future__ import annotations

import json
import mimetypes
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

from ig_post_controller.config import get_default_download_root
from ig_post_controller.database import Database
from ig_post_controller.models import MediaItem, PostRecord
from ig_post_controller.utils.text import build_default_download_title, sanitize_for_path


class DownloadService:
    DOWNLOAD_ROOT_SETTING = "download_root"

    def __init__(self, database: Database) -> None:
        self.database = database
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/132.0.0.0 Safari/537.36"
                )
            }
        )

    def get_download_root(self) -> Path:
        configured = self.database.get_setting(self.DOWNLOAD_ROOT_SETTING)
        if configured:
            path = Path(configured)
            path.mkdir(parents=True, exist_ok=True)
            return path
        default = get_default_download_root()
        self.set_download_root(default)
        return default

    def set_download_root(self, path: str | Path) -> Path:
        target = Path(path)
        target.mkdir(parents=True, exist_ok=True)
        self.database.set_setting(self.DOWNLOAD_ROOT_SETTING, str(target))
        return target

    def list_downloaded_posts(
        self,
        *,
        account_id: int | None = None,
        media_filter: str = "all",
        sort_order: str = "newest",
    ) -> list[PostRecord]:
        clauses = ["d.id IS NOT NULL"]
        params: list[object] = []
        if account_id:
            clauses.append("a.id = ?")
            params.append(account_id)
        if media_filter == "image":
            clauses.append("p.has_image = 1")
        elif media_filter == "video":
            clauses.append("p.has_video = 1")
        order_by = "p.taken_at DESC" if sort_order == "newest" else "p.taken_at ASC"
        query = f"""
            SELECT
                p.*,
                a.username,
                a.display_name,
                a.company_name,
                d.id AS download_id,
                d.folder_path,
                d.custom_title,
                d.media_json AS download_media_json,
                d.posted_to_cafe,
                d.downloaded_at
            FROM posts p
            JOIN accounts a ON a.id = p.account_id
            JOIN downloads d ON d.post_id = p.id
            WHERE {" AND ".join(clauses)}
            ORDER BY {order_by}
        """
        with self.database.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_post(row) for row in rows]

    def set_posted_to_cafe(self, post_id: int, value: bool) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE downloads
                SET posted_to_cafe = ?, updated_at = ?
                WHERE post_id = ?
                """,
                (1 if value else 0, datetime.now().isoformat(), post_id),
            )

    def delete_downloaded_post(self, post_id: int) -> bool:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT folder_path FROM downloads WHERE post_id = ?",
                (post_id,),
            ).fetchone()
            if row is None:
                return False
            folder_path = row["folder_path"]
            connection.execute(
                "DELETE FROM downloads WHERE post_id = ?",
                (post_id,),
            )

        if folder_path:
            target = Path(folder_path)
            if target.exists():
                shutil.rmtree(target)
        return True

    def download_post(
        self,
        post: PostRecord,
        *,
        title_override: str | None = None,
        batch_rule: str | None = None,
        batch_index: int | None = None,
    ) -> PostRecord:
        if post.id is None:
            raise ValueError("This post has not been saved locally yet, so it cannot be downloaded.")

        target_title = self._build_target_title(
            post,
            title_override=title_override,
            batch_rule=batch_rule,
            batch_index=batch_index,
        )
        root = self.get_download_root()
        company_dir = root / sanitize_for_path(
            post.company_name or post.display_name or post.username,
            max_length=60,
        )
        target_dir = company_dir / "posts" / post.taken_at.strftime("%Y") / post.taken_at.strftime("%m") / target_title
        existing_folder = Path(post.folder_path) if post.folder_path else None

        if existing_folder and existing_folder.exists() and existing_folder != target_dir:
            shutil.rmtree(existing_folder)
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        local_media_items: list[MediaItem] = []
        for media in post.media_items:
            source = media.playable_source()
            if not source:
                continue
            suffix = self._suffix_for_media(source, media.media_type)
            filename = f"{media.index + 1:02d}{suffix}"
            local_path = target_dir / filename
            self._download_binary(source, local_path)

            local_thumbnail_path = None
            if media.media_type == "video" and media.thumbnail_url:
                local_thumbnail = target_dir / f"{media.index + 1:02d}_thumb.jpg"
                self._download_binary(media.thumbnail_url, local_thumbnail)
                local_thumbnail_path = str(local_thumbnail)

            local_media_items.append(
                MediaItem(
                    index=media.index,
                    media_type=media.media_type,
                    remote_url=media.remote_url,
                    thumbnail_url=media.thumbnail_url,
                    local_path=str(local_path),
                    local_thumbnail_path=local_thumbnail_path,
                )
            )

        caption_path = target_dir / "caption.txt"
        caption_path.write_text(post.caption or "", encoding="utf-8")

        meta_path = target_dir / "meta.json"
        meta_payload = {
            "shortcode": post.shortcode,
            "profile_username": post.username,
            "display_name": post.display_name,
            "company_name": post.company_name,
            "post_url": post.source_url,
            "post_type": post.post_type,
            "caption": post.caption,
            "taken_at": post.taken_at.isoformat(),
            "downloaded_at": datetime.now().isoformat(),
            "folder_title": target_title,
            "media": [item.to_dict() for item in local_media_items],
        }
        meta_path.write_text(json.dumps(meta_payload, indent=2, ensure_ascii=False), encoding="utf-8")

        now = datetime.now().isoformat()
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO downloads (
                    post_id,
                    company_name,
                    custom_title,
                    folder_path,
                    media_json,
                    caption_path,
                    meta_path,
                    posted_to_cafe,
                    downloaded_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE((
                    SELECT posted_to_cafe FROM downloads WHERE post_id = ?
                ), 0), ?, ?)
                ON CONFLICT(post_id) DO UPDATE SET
                    company_name = excluded.company_name,
                    custom_title = excluded.custom_title,
                    folder_path = excluded.folder_path,
                    media_json = excluded.media_json,
                    caption_path = excluded.caption_path,
                    meta_path = excluded.meta_path,
                    downloaded_at = excluded.downloaded_at,
                    updated_at = excluded.updated_at
                """,
                (
                    post.id,
                    post.company_name,
                    target_title,
                    str(target_dir),
                    json.dumps([item.to_dict() for item in local_media_items], ensure_ascii=False),
                    str(caption_path),
                    str(meta_path),
                    post.id,
                    now,
                    now,
                ),
            )
        post.is_downloaded = True
        post.folder_path = str(target_dir)
        post.custom_title = target_title
        post.media_items = local_media_items
        post.downloaded_at = datetime.fromisoformat(now)
        return post

    @staticmethod
    def _build_target_title(
        post: PostRecord,
        *,
        title_override: str | None,
        batch_rule: str | None,
        batch_index: int | None,
    ) -> str:
        if title_override:
            return sanitize_for_path(title_override, max_length=80)
        if batch_rule:
            base = sanitize_for_path(batch_rule, max_length=72)
            if batch_index is None:
                return base
            return sanitize_for_path(f"{base}_{batch_index:02d}", max_length=80)
        return build_default_download_title(post.taken_at, post.caption)

    def _download_binary(self, url: str, target_path: Path) -> None:
        response = self.session.get(url, timeout=60, stream=True)
        response.raise_for_status()
        with target_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 128):
                if chunk:
                    handle.write(chunk)

    @staticmethod
    def _suffix_for_media(url: str, media_type: str) -> str:
        parsed = urlparse(url)
        suffix = Path(parsed.path).suffix
        if suffix:
            return suffix
        if media_type == "video":
            return ".mp4"
        guessed = mimetypes.guess_extension(mimetypes.guess_type(url)[0] or "")
        return guessed or ".jpg"

    @staticmethod
    def _row_to_post(row) -> PostRecord:
        media_items = [MediaItem.from_dict(item) for item in json.loads(row["download_media_json"])]
        return PostRecord(
            id=row["id"],
            account_id=row["account_id"],
            username=row["username"],
            display_name=row["display_name"],
            company_name=row["company_name"],
            shortcode=row["shortcode"],
            caption=row["caption"],
            taken_at=datetime.fromisoformat(row["taken_at"]),
            post_type=row["post_type"],
            has_image=bool(row["has_image"]),
            has_video=bool(row["has_video"]),
            thumbnail_url=media_items[0].preview_source(prefer_local=True) if media_items else None,
            source_url=row["source_url"],
            media_items=media_items,
            is_downloaded=True,
            folder_path=row["folder_path"],
            custom_title=row["custom_title"],
            posted_to_cafe=bool(row["posted_to_cafe"]),
            downloaded_at=datetime.fromisoformat(row["downloaded_at"]) if row["downloaded_at"] else None,
            download_id=row["download_id"],
        )
