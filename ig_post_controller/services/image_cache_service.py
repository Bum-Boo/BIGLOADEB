from __future__ import annotations

import hashlib
import logging
import threading
from pathlib import Path
from urllib.parse import urlparse

import requests

from ig_post_controller.config import REMOTE_REQUEST_TIMEOUT_SECONDS, get_thumbnail_cache_dir


logger = logging.getLogger(__name__)


class ImageCacheService:
    _fetch_semaphore = threading.BoundedSemaphore(2)

    def __init__(self) -> None:
        self.cache_dir = get_thumbnail_cache_dir()
        self.thumbnails_enabled = True
        self.session = requests.Session()
        self._session_lock = threading.Lock()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/132.0.0.0 Safari/537.36"
                )
            }
        )

    def fetch_image_bytes(self, source: str | None) -> bytes | None:
        if not source:
            return None
        if not self.thumbnails_enabled:
            logger.info("Thumbnail fetch skipped source=%s reason=disabled", source)
            return None
        if source.startswith("http://") or source.startswith("https://"):
            parsed = urlparse(source)
            suffix = Path(parsed.path).suffix or ".jpg"
            hashed_name = hashlib.sha256(source.encode("utf-8")).hexdigest()
            target = self.cache_dir / f"{hashed_name}{suffix}"
            with self._fetch_semaphore:
                if target.exists():
                    logger.info("Thumbnail fetch finished source=%s cache_hit=%s bytes=%s", source, True, target.stat().st_size)
                    return target.read_bytes()
                logger.info("Thumbnail fetch started source=%s cache_hit=%s", source, False)
                with self._session_lock:
                    response = self.session.get(source, timeout=REMOTE_REQUEST_TIMEOUT_SECONDS)
                response.raise_for_status()
                target.write_bytes(response.content)
                logger.info("Thumbnail fetch finished source=%s cache_hit=%s bytes=%s", source, False, len(response.content))
                return response.content
        path = Path(source)
        with self._fetch_semaphore:
            logger.info("Thumbnail fetch started source=%s cache_hit=%s", source, path.exists())
            data = path.read_bytes() if path.exists() else None
            logger.info("Thumbnail fetch finished source=%s cache_hit=%s bytes=%s", source, path.exists(), len(data) if data else 0)
            return data

    def ensure_local_image(self, source: str | None) -> Path | None:
        if not source:
            return None
        if source.startswith("http://") or source.startswith("https://"):
            parsed = urlparse(source)
            suffix = Path(parsed.path).suffix or ".jpg"
            hashed_name = hashlib.sha256(source.encode("utf-8")).hexdigest()
            target = self.cache_dir / f"{hashed_name}{suffix}"
            with self._fetch_semaphore:
                if target.exists():
                    return target
                with self._session_lock:
                    response = self.session.get(source, timeout=REMOTE_REQUEST_TIMEOUT_SECONDS)
                response.raise_for_status()
                target.write_bytes(response.content)
                return target
        path = Path(source)
        with self._fetch_semaphore:
            return path if path.exists() else None
