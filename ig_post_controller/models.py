from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class MediaItem:
    index: int
    media_type: str
    remote_url: str | None = None
    thumbnail_url: str | None = None
    local_path: str | None = None
    local_thumbnail_path: str | None = None

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "index": self.index,
            "media_type": self.media_type,
            "remote_url": self.remote_url,
            "thumbnail_url": self.thumbnail_url,
            "local_path": self.local_path,
            "local_thumbnail_path": self.local_thumbnail_path,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, str | int | None]) -> "MediaItem":
        return cls(
            index=int(payload.get("index", 0) or 0),
            media_type=str(payload.get("media_type", "image")),
            remote_url=payload.get("remote_url") or None,
            thumbnail_url=payload.get("thumbnail_url") or None,
            local_path=payload.get("local_path") or None,
            local_thumbnail_path=payload.get("local_thumbnail_path") or None,
        )

    def preview_source(self, prefer_local: bool = False) -> str | None:
        if prefer_local and self.local_thumbnail_path and Path(self.local_thumbnail_path).exists():
            return self.local_thumbnail_path
        if prefer_local and self.local_path and self.media_type == "image" and Path(self.local_path).exists():
            return self.local_path
        return self.thumbnail_url or self.remote_url or self.local_thumbnail_path or self.local_path

    def playable_source(self, prefer_local: bool = False) -> str | None:
        if prefer_local and self.local_path and Path(self.local_path).exists():
            return self.local_path
        return self.remote_url or self.local_path


@dataclass(slots=True)
class AccountRecord:
    id: int
    profile_url: str
    username: str
    display_name: str
    company_name: str
    created_at: datetime
    updated_at: datetime
    last_checked_at: datetime | None = None
    last_seen_post_shortcode: str | None = None


@dataclass(slots=True)
class PostRecord:
    id: int | None
    account_id: int
    username: str
    display_name: str
    company_name: str
    shortcode: str
    caption: str
    taken_at: datetime
    post_type: str
    has_image: bool
    has_video: bool
    thumbnail_url: str | None
    source_url: str
    media_items: list[MediaItem] = field(default_factory=list)
    is_downloaded: bool = False
    folder_path: str | None = None
    custom_title: str | None = None
    posted_to_cafe: bool = False
    downloaded_at: datetime | None = None
    download_id: int | None = None
    download_folder_missing: bool = False

    @property
    def caption_preview(self) -> str:
        text = (self.caption or "").replace("\r", " ").replace("\n", " ").strip()
        if not text:
            return ""
        return text if len(text) <= 90 else f"{text[:87]}..."

    @property
    def action_label(self) -> str:
        return "Redownload" if self.is_downloaded else "Download"

    def get_preview_source(self, *, prefer_local: bool = False) -> str | None:
        if not self.media_items:
            return self.thumbnail_url
        return self.media_items[0].preview_source(prefer_local=prefer_local) or self.thumbnail_url


@dataclass(slots=True)
class NewPostCheckResult:
    new_posts: list[PostRecord]
    checked_accounts: int
