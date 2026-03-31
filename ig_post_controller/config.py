from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "IG Post Controller"
APP_BRAND_NAME = "BIGLOADEB"
FETCH_LIMIT = 24
STARTUP_CHECK_LIMIT = 12
THUMBNAIL_CACHE_DIRNAME = "thumb_cache"
DATABASE_FILENAME = "ig_post_controller.db"
APP_LANGUAGE_SETTING_KEY = "app_language"
APP_THEME_SETTING_KEY = "app_theme"
DEFAULT_APP_LANGUAGE = "ko"
DEFAULT_APP_THEME = "clean_light"
SUPPORTED_APP_LANGUAGES = {"en", "ko", "ja", "zh"}
SUPPORTED_APP_THEMES = {
    "clean_light",
    "soft_dark_slate",
    "warm_paper",
    "neon_utility",
    "gquuuuuux_signal",
}
REMOTE_REQUEST_TIMEOUT_SECONDS = 20


def get_app_data_dir() -> Path:
    local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    path = local_app_data / "IGPostController"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_database_path() -> Path:
    return get_app_data_dir() / DATABASE_FILENAME


def get_default_download_root() -> Path:
    documents = Path.home() / "Documents"
    path = documents / "IG Post Controller Downloads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_thumbnail_cache_dir() -> Path:
    path = get_app_data_dir() / THUMBNAIL_CACHE_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def normalize_app_language(value: str | None) -> str:
    cleaned = (value or "").strip().lower().replace("_", "-")
    if cleaned:
        cleaned = cleaned.split("-", 1)[0]
    aliases = {
        "english": "en",
        "korean": "ko",
        "japanese": "ja",
        "chinese": "zh",
    }
    normalized = aliases.get(cleaned, cleaned)
    return normalized if normalized in SUPPORTED_APP_LANGUAGES else DEFAULT_APP_LANGUAGE


def normalize_app_theme(value: str | None) -> str:
    cleaned = (value or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "light": "clean_light",
        "cleanlight": "clean_light",
        "dark": "soft_dark_slate",
        "slate": "soft_dark_slate",
        "paper": "warm_paper",
        "utility": "neon_utility",
        "neon": "neon_utility",
        "signal": "gquuuuuux_signal",
    }
    normalized = aliases.get(cleaned, cleaned)
    return normalized if normalized in SUPPORTED_APP_THEMES else DEFAULT_APP_THEME
