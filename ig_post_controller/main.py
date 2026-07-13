from __future__ import annotations

import faulthandler
import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import QLocale

from ig_post_controller.config import (
    APP_BRAND_NAME,
    APP_LANGUAGE_SETTING_KEY,
    APP_THEME_SETTING_KEY,
    DEFAULT_APP_LANGUAGE,
    normalize_app_language,
    normalize_app_theme,
)

_STARTUP_LOG_STREAM = None


def _get_startup_log_path() -> Path:
    local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    log_dir = local_app_data / "IGPostController" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "startup.log"


def _show_fatal_error(message: str) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, APP_BRAND_NAME, 0x10)
    except Exception:
        pass


def _resource_path(relative_path: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).resolve().parents[1] / relative_path


def _configure_startup_logging() -> logging.Logger:
    global _STARTUP_LOG_STREAM

    log_path = _get_startup_log_path()
    _STARTUP_LOG_STREAM = log_path.open("a", encoding="utf-8", buffering=1)

    faulthandler.enable(file=_STARTUP_LOG_STREAM, all_threads=True)

    handlers: list[logging.Handler] = [logging.StreamHandler(_STARTUP_LOG_STREAM)]
    if sys.stdout is not None and getattr(sys.stdout, "isatty", lambda: False)():
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
        force=True,
    )

    def _log_uncaught_exception(exc_type, exc, tb) -> None:
        logging.critical("Unhandled startup exception", exc_info=(exc_type, exc, tb))
        if _STARTUP_LOG_STREAM is not None:
            _STARTUP_LOG_STREAM.flush()
        _show_fatal_error(
            "BIGLOADEB를 시작하지 못했어요. 앱을 다시 실행해 주세요. "
            "문제가 계속되면 startup.log 파일을 전달해 주세요.\n\n"
            "BIGLOADEB could not start. Please restart the app or share startup.log."
        )

    sys.excepthook = _log_uncaught_exception
    return logging.getLogger("ig_post_controller.startup")


def _locale_for_language(language: str) -> QLocale:
    if language == "en":
        return QLocale(QLocale.Language.English)
    if language == "ja":
        return QLocale(QLocale.Language.Japanese)
    if language == "zh":
        return QLocale(QLocale.Language.Chinese)
    return QLocale(QLocale.Language.Korean)


def _resolve_app_language(database) -> str:
    saved_language = database.get_setting(APP_LANGUAGE_SETTING_KEY)
    language = normalize_app_language(saved_language)
    if saved_language != language:
        database.set_setting(APP_LANGUAGE_SETTING_KEY, language)
    return language


def _resolve_app_theme(database) -> str:
    saved_theme = database.get_setting(APP_THEME_SETTING_KEY)
    theme = normalize_app_theme(saved_theme)
    if saved_theme != theme:
        database.set_setting(APP_THEME_SETTING_KEY, theme)
    return theme


def main() -> int:
    logger = _configure_startup_logging()
    logger.info("Python process started")
    logger.info("frozen=%s executable=%s cwd=%s", getattr(sys, "frozen", False), sys.executable, Path.cwd())
    logger.info("argv=%s", sys.argv)
    logger.info("startup_log=%s", _get_startup_log_path())

    try:
        logger.info("Importing application modules")
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QApplication

        from ig_post_controller.config import APP_BRAND_NAME as CONFIG_APP_NAME, get_database_path
        from ig_post_controller.database import Database
        from ig_post_controller.services.account_service import AccountService
        from ig_post_controller.services.download_service import DownloadService
        from ig_post_controller.services.image_cache_service import ImageCacheService
        from ig_post_controller.services.instagram_service import InstagramService
        from ig_post_controller.ui.i18n import LanguageManager
        from ig_post_controller.ui.main_window import MainWindow
        from ig_post_controller.ui.theme import ThemeManager

        logger.info("Initializing database")
        database = Database(get_database_path())
        language = _resolve_app_language(database)
        theme = _resolve_app_theme(database)
        QLocale.setDefault(_locale_for_language(language))
        logger.info("App language resolved to %s", language or DEFAULT_APP_LANGUAGE)
        logger.info("App theme resolved to %s", theme)

        logger.info("Creating QApplication")
        app = QApplication(sys.argv)
        app.setApplicationName(CONFIG_APP_NAME)
        app.setApplicationDisplayName(CONFIG_APP_NAME)
        app.setStyle("Fusion")
        app.setProperty("app_language", language)
        app.setProperty("app_theme", theme)
        icon_path = _resource_path("assets/app_icon.png")
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
            logger.info("Application icon loaded from %s", icon_path)
        else:
            logger.warning("Application icon not found at %s", icon_path)
        logger.info("QApplication created")

        logger.info("Initializing services")
        account_service = AccountService(database)
        instagram_service = InstagramService(database, account_service)
        download_service = DownloadService(database)
        image_cache = ImageCacheService()
        translator = LanguageManager(language)
        theme_manager = ThemeManager(theme)
        theme_manager.bind_application(app)
        logger.info("Services initialized")

        logger.info("Constructing main window")
        window = MainWindow(account_service, instagram_service, download_service, image_cache, translator, theme_manager)
        if icon_path.exists():
            window.setWindowIcon(QIcon(str(icon_path)))
        logger.info("Main window constructed")

        window.show()
        logger.info("Main window shown")
        exit_code = app.exec()
        logger.info("Event loop exited with code %s", exit_code)
        return exit_code
    except Exception:
        logger.exception("Startup failed")
        _show_fatal_error(
            "BIGLOADEB를 시작하지 못했어요. 앱을 다시 실행해 주세요. "
            "문제가 계속되면 startup.log 파일을 전달해 주세요.\n\n"
            "BIGLOADEB could not start. Please restart the app or share startup.log."
        )
        return 1
    finally:
        if _STARTUP_LOG_STREAM is not None:
            _STARTUP_LOG_STREAM.flush()


if __name__ == "__main__":
    raise SystemExit(main())
