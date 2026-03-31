from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urlparse

INVALID_WINDOWS_CHARS = r'[<>:"/\\|?*]'
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


def extract_username_from_input(value: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError("Enter an Instagram profile URL or username.")
    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        parts = [segment for segment in parsed.path.split("/") if segment]
        if not parts:
            raise ValueError("Could not read the username from that Instagram URL.")
        return parts[0].lstrip("@")
    return value.lstrip("@")


def sanitize_for_path(value: str, fallback: str = "untitled", max_length: int = 80) -> str:
    value = (value or "").replace("\r", " ").replace("\n", " ").strip()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(INVALID_WINDOWS_CHARS, "", value)
    value = value.strip(" .")
    value = value or fallback
    if value.upper() in WINDOWS_RESERVED_NAMES:
        value = f"{value}_"
    if max_length > 0 and len(value) > max_length:
        value = f"{value[: max(1, max_length - 2)].rstrip(' .')}.."
    return value or fallback


def caption_snippet(caption: str, limit: int = 15) -> str:
    cleaned = (caption or "").replace("\r", " ").replace("\n", " ").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        return ""
    return cleaned if len(cleaned) <= limit else f"{cleaned[:limit]}.."


def build_default_download_title(post_date: datetime, caption: str) -> str:
    snippet = caption_snippet(caption)
    raw_title = f"{post_date:%Y-%m-%d}_{snippet}" if snippet else f"{post_date:%Y-%m-%d}"
    return sanitize_for_path(raw_title, max_length=80)


def merge_media_items(remote_items: list, local_items: list) -> list:
    if not local_items:
        return remote_items
    local_by_index = {item.index: item for item in local_items}
    merged = []
    for item in remote_items:
        local = local_by_index.get(item.index)
        if not local:
            merged.append(item)
            continue
        item.local_path = local.local_path
        item.local_thumbnail_path = local.local_thumbnail_path
        merged.append(item)
    return merged
