from __future__ import annotations

from dataclasses import dataclass
import logging
import time
from functools import partial

from PySide6.QtCore import QSignalBlocker, QTimer, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressDialog,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ig_post_controller.config import (
    APP_BRAND_NAME,
    APP_LANGUAGE_SETTING_KEY,
    APP_THEME_SETTING_KEY,
    normalize_app_language,
    normalize_app_theme,
)
from ig_post_controller.models import PostRecord
from ig_post_controller.services.account_service import AccountService
from ig_post_controller.services.download_service import DownloadService
from ig_post_controller.services.image_cache_service import ImageCacheService
from ig_post_controller.services.instagram_service import InstagramService
from ig_post_controller.ui.account_view import AccountListView
from ig_post_controller.ui.dialogs import (
    AddAccountDialog,
    BulkDownloadDialog,
    DownloadOptionsDialog,
    PostDetailDialog,
    SettingsDialog,
)
from ig_post_controller.ui.downloaded_feed_view import DownloadedFeedView
from ig_post_controller.ui.i18n import LanguageManager
from ig_post_controller.ui.online_feed_view import OnlineFeedView
from ig_post_controller.ui.theme import ThemeManager
from ig_post_controller.ui.worker import TaskHandle, create_task_handle
from ig_post_controller.utils.paths import open_in_file_browser


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FeedLoadResult:
    account_id: int | None
    media_filter: str
    sort_order: str
    posts: list[PostRecord]
    elapsed_ms: float


class MainWindow(QMainWindow):
    PAGE_ACCOUNTS = 0
    PAGE_ONLINE = 1
    PAGE_DOWNLOADED = 2

    def __init__(
        self,
        account_service: AccountService,
        instagram_service: InstagramService,
        download_service: DownloadService,
        image_cache: ImageCacheService,
        translator: LanguageManager | None = None,
        theme_manager: ThemeManager | None = None,
    ) -> None:
        super().__init__()
        self.account_service = account_service
        self.instagram_service = instagram_service
        self.download_service = download_service
        self.image_cache = image_cache
        self.translator = translator or LanguageManager()
        self.theme_manager = theme_manager or ThemeManager()
        self._active_tasks: dict[int, TaskHandle] = {}
        self._thumbnail_tasks: list[TaskHandle] = []
        self._active_progress: dict[int, QProgressDialog] = {}
        self._task_counter = 0
        self._online_feed_dirty = True
        self._downloaded_feed_dirty = True
        self._online_feed_load_generation = 0
        self._downloaded_feed_load_generation = 0
        self._active_online_refresh_account_id: int | None = None
        self._pending_online_refresh_account_id: int | None = None
        self._pending_online_reload_reason: str | None = None
        self._pending_online_reload_force = False
        self._startup_timer = QTimer(self)
        self._startup_timer.setSingleShot(True)
        self._startup_timer.timeout.connect(self._startup_check_for_new_posts)
        self._delayed_online_refresh_timer = QTimer(self)
        self._delayed_online_refresh_timer.setSingleShot(True)
        self._delayed_online_refresh_timer.timeout.connect(self._run_pending_online_refresh)
        self._delayed_online_reload_timer = QTimer(self)
        self._delayed_online_reload_timer.setSingleShot(True)
        self._delayed_online_reload_timer.timeout.connect(self._run_pending_online_reload)

        self.resize(1460, 920)

        central = QWidget()
        central.setObjectName("mainWindowCentral")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        nav_panel = QWidget()
        nav_panel.setObjectName("sidebarPanel")
        nav_panel.setFixedWidth(210)
        nav_layout = QVBoxLayout(nav_panel)
        nav_layout.setContentsMargins(18, 22, 18, 22)
        nav_layout.setSpacing(12)

        self.app_title_label = QLabel()
        self.app_title_label.setObjectName("appTitleLabel")
        self.app_title_label.setStyleSheet("font-size: 26px; font-weight: 800;")
        nav_layout.addWidget(self.app_title_label)

        self.accounts_button = self._make_nav_button("nav.accounts", self.PAGE_ACCOUNTS)
        self.online_button = self._make_nav_button("nav.online_feed", self.PAGE_ONLINE)
        self.downloaded_button = self._make_nav_button("nav.downloaded_posts", self.PAGE_DOWNLOADED)
        nav_layout.addWidget(self.accounts_button)
        nav_layout.addWidget(self.online_button)
        nav_layout.addWidget(self.downloaded_button)
        nav_layout.addStretch(1)
        self.settings_button = self._make_nav_button("nav.settings", -1, checkable=False)
        self.settings_button.clicked.connect(lambda *_: self._open_settings())
        nav_layout.addWidget(self.settings_button)
        root.addWidget(nav_panel)

        content = QWidget()
        content.setObjectName("contentPanel")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(18, 18, 18, 18)
        content_layout.setSpacing(14)
        root.addWidget(content, 1)

        folder_bar = QWidget()
        folder_layout = QHBoxLayout(folder_bar)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(8)

        self.folder_label = QLabel()
        self.folder_label.setObjectName("folderLabel")
        self.folder_label.setStyleSheet("font-weight: 700;")
        folder_layout.addWidget(self.folder_label)

        self.download_root_edit = QLineEdit()
        self.download_root_edit.setReadOnly(True)
        folder_layout.addWidget(self.download_root_edit, 1)

        self.choose_folder_button = QPushButton()
        self.choose_folder_button.clicked.connect(lambda *_: self._choose_download_root())
        folder_layout.addWidget(self.choose_folder_button)

        self.open_folder_button = QPushButton()
        self.open_folder_button.clicked.connect(lambda *_: self._open_download_root())
        folder_layout.addWidget(self.open_folder_button)
        content_layout.addWidget(folder_bar)

        self.pages = QStackedWidget()
        self.account_view = AccountListView(self.translator)
        self.online_feed_view = OnlineFeedView(self.image_cache, self.translator, self._thumbnail_tasks)
        self.downloaded_feed_view = DownloadedFeedView(self.image_cache, self.translator, self._thumbnail_tasks)
        self.pages.addWidget(self.account_view)
        self.pages.addWidget(self.online_feed_view)
        self.pages.addWidget(self.downloaded_feed_view)
        content_layout.addWidget(self.pages, 1)

        self._connect_signals()
        self.theme_manager.bind_application(self._get_application())
        self.theme_manager.theme_changed.connect(self._handle_theme_changed)
        self._update_download_root_display()
        self.translator.language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()
        self._switch_page(self.PAGE_ACCOUNTS)
        self._reload_all_views()

        self._startup_timer.start(400)

    def closeEvent(self, event) -> None:  # noqa: N802
        logger.info("Main window close requested visible=%s active_tasks=%s", self.isVisible(), self.active_task_count())
        self._startup_timer.stop()
        self._delayed_online_refresh_timer.stop()
        self._delayed_online_reload_timer.stop()
        self._shutdown_background_tasks()
        super().closeEvent(event)

    def _t(self, key: str, **kwargs) -> str:
        return self.translator.tr(key, **kwargs)

    def retranslate_ui(self, *_args) -> None:
        self.setWindowTitle(APP_BRAND_NAME)
        self.app_title_label.setText(APP_BRAND_NAME)
        self.accounts_button.setText(self._t("nav.accounts"))
        self.online_button.setText(self._t("nav.online_feed"))
        self.downloaded_button.setText(self._t("nav.downloaded_posts"))
        self.settings_button.setText(self._t("nav.settings"))
        self.folder_label.setText(self._t("main.download_folder"))
        self.choose_folder_button.setText(self._t("main.change_folder"))
        self.open_folder_button.setText(self._t("main.open_folder"))

    def _handle_theme_changed(self, *_args) -> None:
        logger.info("Theme changed theme=%s", self.theme_manager.theme)
        self.update()

    def _connect_signals(self) -> None:
        self.account_view.add_account_requested.connect(self._add_account)
        self.account_view.refresh_account_requested.connect(self._refresh_account_posts)
        self.account_view.delete_account_requested.connect(self._delete_account)
        self.account_view.open_online_feed_requested.connect(self._show_account_feed)

        self.online_feed_view.filters_changed.connect(self._schedule_online_feed_reload)
        self.online_feed_view.refresh_requested.connect(self._refresh_online_feed_remote)
        self.online_feed_view.post_open_requested.connect(partial(self._open_post_detail, prefer_local=False))
        self.online_feed_view.download_requested.connect(self._begin_single_download)
        self.online_feed_view.render_finished.connect(self._log_online_feed_visibility_after_render)
        self.online_feed_view.settled.connect(self._handle_online_feed_settled)

        self.downloaded_feed_view.filters_changed.connect(self._schedule_downloaded_feed_reload)
        self.downloaded_feed_view.refresh_requested.connect(self._schedule_downloaded_feed_reload)
        self.downloaded_feed_view.post_open_requested.connect(partial(self._open_post_detail, prefer_local=True))
        self.downloaded_feed_view.download_requested.connect(self._begin_single_download)
        self.downloaded_feed_view.delete_requested.connect(self._delete_downloaded_post)
        self.downloaded_feed_view.posted_to_cafe_changed.connect(self._set_posted_to_cafe)

    def _make_nav_button(self, label_key: str, page_index: int, *, checkable: bool = True) -> QPushButton:
        button = QPushButton(self._t(label_key))
        button.setObjectName("navButton")
        button.setCheckable(True)
        if not checkable:
            button.setCheckable(False)
        button.setMinimumHeight(48)
        if page_index >= 0:
            button.clicked.connect(lambda *_: self._switch_page(page_index))
        return button

    def _get_application(self):
        from PySide6.QtWidgets import QApplication

        return QApplication.instance()

    def _switch_page(self, page_index: int) -> None:
        self.pages.setCurrentIndex(page_index)
        self.accounts_button.setChecked(page_index == self.PAGE_ACCOUNTS)
        self.online_button.setChecked(page_index == self.PAGE_ONLINE)
        self.downloaded_button.setChecked(page_index == self.PAGE_DOWNLOADED)
        current_widget = self.pages.currentWidget()
        logger.info(
            "Page switched index=%s current_widget=%s visible=%s",
            page_index,
            type(current_widget).__name__ if current_widget is not None else None,
            current_widget.isVisible() if current_widget is not None else False,
        )
        if page_index == self.PAGE_ONLINE and self._online_feed_dirty:
            self._schedule_online_feed_reload(force=True, reason="page-switch")
        if page_index == self.PAGE_DOWNLOADED and self._downloaded_feed_dirty:
            self._schedule_downloaded_feed_reload(force=True)
        if page_index != self.PAGE_ONLINE:
            self._delayed_online_refresh_timer.stop()
            self._delayed_online_reload_timer.stop()
            self._pending_online_refresh_account_id = None
            self._pending_online_reload_reason = None
            self._pending_online_reload_force = False

    def _update_download_root_display(self) -> None:
        self.download_root_edit.setText(str(self.download_service.get_download_root()))

    def _reload_all_views(self, *, refresh_online_feed: bool = True, refresh_downloaded_feed: bool = True) -> None:
        accounts = self.account_service.list_accounts()
        self.account_view.set_accounts(accounts)
        self.online_feed_view.set_accounts(accounts)
        self.downloaded_feed_view.set_accounts(accounts)
        if refresh_online_feed:
            self._online_feed_dirty = True
        if refresh_downloaded_feed:
            self._downloaded_feed_dirty = True
        if refresh_online_feed and self.pages.currentIndex() == self.PAGE_ONLINE:
            self._schedule_online_feed_reload(force=True, reason="reload-all-views")
        elif refresh_downloaded_feed and self.pages.currentIndex() == self.PAGE_DOWNLOADED:
            self._schedule_downloaded_feed_reload(force=True)

    def _reload_online_feed(self) -> None:
        logger.info(
            "Online feed reload started current_index=%s selected_account_id=%s media_filter=%s sort_order=%s thumbnails_busy=%s",
            self.pages.currentIndex(),
            self.online_feed_view.selected_account_id(),
            self.online_feed_view.selected_media_filter(),
            self.online_feed_view.selected_sort_order(),
            self.online_feed_view.is_thumbnail_activation_busy(),
        )
        if self.pages.currentIndex() != self.PAGE_ONLINE:
            self._online_feed_dirty = True
            logger.info("Online feed reload aborted reason=page-not-visible")
            return

        self._online_feed_dirty = False
        self._online_feed_load_generation += 1
        generation = self._online_feed_load_generation
        started_at = time.perf_counter()
        account_id = self.online_feed_view.selected_account_id()
        media_filter = self.online_feed_view.selected_media_filter()
        sort_order = self.online_feed_view.selected_sort_order()
        self.online_feed_view.show_loading_message("online.loading")

        def job() -> FeedLoadResult:
            posts = self.instagram_service.get_cached_posts(
                account_id=account_id,
                media_filter=media_filter,
                sort_order=sort_order,
            )
            return FeedLoadResult(
                account_id=account_id,
                media_filter=media_filter,
                sort_order=sort_order,
                posts=posts,
                elapsed_ms=(time.perf_counter() - started_at) * 1000,
            )

        def handle_success(result: FeedLoadResult) -> None:
            if generation != self._online_feed_load_generation:
                return
            logger.info(
                "Online feed data loaded account_id=%s media_filter=%s sort_order=%s posts=%s elapsed_ms=%.1f",
                result.account_id,
                result.media_filter,
                result.sort_order,
                len(result.posts),
                result.elapsed_ms,
            )
            self.online_feed_view.set_posts(result.posts)

        def handle_error(message: str) -> None:
            if generation != self._online_feed_load_generation:
                return
            self._online_feed_dirty = True
            self.online_feed_view.show_loading_message("online.unable_to_load_feed")
            QMessageBox.critical(self, self._t("main.message.feed_load_failed"), message)

        self._run_worker(
            job,
            success_handler=handle_success,
            error_handler=handle_error,
        )

    def _schedule_online_feed_reload(self, force: bool = False, reason: str = "signal") -> None:
        logger.info(
            "Online feed reload scheduled force=%s current_index=%s dirty=%s reason=%s thumbnails_busy=%s",
            force,
            self.pages.currentIndex(),
            self._online_feed_dirty,
            reason,
            self.online_feed_view.is_thumbnail_activation_busy(),
        )
        self._online_feed_dirty = True
        if not force and self.pages.currentIndex() != self.PAGE_ONLINE:
            logger.info("Online feed reload skipped reason=page-not-visible")
            return
        QTimer.singleShot(0, self._reload_online_feed)

    def _reload_downloaded_feed(self) -> None:
        if self.pages.currentIndex() != self.PAGE_DOWNLOADED:
            self._downloaded_feed_dirty = True
            return

        self._downloaded_feed_dirty = False
        self._downloaded_feed_load_generation += 1
        generation = self._downloaded_feed_load_generation
        started_at = time.perf_counter()
        account_id = self.downloaded_feed_view.selected_account_id()
        media_filter = self.downloaded_feed_view.selected_media_filter()
        sort_order = self.downloaded_feed_view.selected_sort_order()
        self.downloaded_feed_view.show_loading_message("downloaded.loading")

        def job() -> FeedLoadResult:
            posts = self.download_service.list_downloaded_posts(
                account_id=account_id,
                media_filter=media_filter,
                sort_order=sort_order,
            )
            return FeedLoadResult(
                account_id=account_id,
                media_filter=media_filter,
                sort_order=sort_order,
                posts=posts,
                elapsed_ms=(time.perf_counter() - started_at) * 1000,
            )

        def handle_success(result: FeedLoadResult) -> None:
            if generation != self._downloaded_feed_load_generation:
                return
            logger.info(
                "Downloaded feed data loaded account_id=%s media_filter=%s sort_order=%s posts=%s elapsed_ms=%.1f",
                result.account_id,
                result.media_filter,
                result.sort_order,
                len(result.posts),
                result.elapsed_ms,
            )
            self.downloaded_feed_view.set_posts(result.posts)

        def handle_error(message: str) -> None:
            if generation != self._downloaded_feed_load_generation:
                return
            self._downloaded_feed_dirty = True
            self.downloaded_feed_view.show_loading_message("downloaded.unable_to_load_downloads")
            QMessageBox.critical(self, self._t("main.message.download_feed_failed"), message)

        self._run_worker(
            job,
            success_handler=handle_success,
            error_handler=handle_error,
        )

    def _schedule_downloaded_feed_reload(self, force: bool = False) -> None:
        self._downloaded_feed_dirty = True
        if not force and self.pages.currentIndex() != self.PAGE_DOWNLOADED:
            return
        QTimer.singleShot(0, self._reload_downloaded_feed)

    def _show_account_feed(self, account_id: int) -> None:
        logger.info("Feed open requested account_id=%s", account_id)
        with QSignalBlocker(self.online_feed_view.account_filter):
            self.online_feed_view.set_selected_account(account_id)
        self._online_feed_dirty = True
        self._switch_page(self.PAGE_ONLINE)
        self._queue_online_refresh_after_settle(account_id)

    def _log_online_feed_visibility_after_render(self, card_count: int) -> None:
        current_widget = self.pages.currentWidget()
        is_active_page = current_widget is self.online_feed_view and self.pages.currentIndex() == self.PAGE_ONLINE
        logger.info(
            "Online feed page visible after render active=%s current_index=%s current_widget=%s page_visible=%s window_visible=%s cards=%s",
            is_active_page,
            self.pages.currentIndex(),
            type(current_widget).__name__ if current_widget is not None else None,
            self.online_feed_view.isVisible(),
            self.isVisible(),
            card_count,
        )

    def _add_account(self) -> None:
        dialog = AddAccountDialog(self.translator, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        self.start_account_add(dialog.profile_url(), dialog.company_name())

    def _after_account_added(self) -> None:
        self._reload_all_views()
        QMessageBox.information(
            self,
            self._t("main.message.account_added_title"),
            self._t("main.message.account_added"),
        )

    def _refresh_account_posts(self, account_id: int) -> None:
        self._run_worker(
            lambda: self.instagram_service.refresh_account_posts(account_id),
            loading_text=self._t("main.message.refreshing_selected_account"),
            success_handler=lambda _: self._after_remote_refresh(self._t("main.status.account_feed_refreshed")),
        )

    def _refresh_online_feed_remote(self) -> None:
        self._pending_online_refresh_account_id = None
        self._delayed_online_refresh_timer.stop()
        account_id = self.online_feed_view.selected_account_id()
        self._start_background_online_refresh(account_id, show_progress=True, source="manual")

    def _after_remote_refresh(self, message: str) -> None:
        self._reload_all_views()
        self.statusBar().showMessage(message, 5000)

    def _delete_account(self, account_id: int) -> None:
        answer = QMessageBox.question(
            self,
            self._t("account.delete"),
            self._t("account.delete_confirm"),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.account_service.delete_account(account_id)
        self._reload_all_views()

    def _choose_download_root(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            self._t("main.change_folder"),
            str(self.download_service.get_download_root()),
        )
        if not selected:
            return
        self.download_service.set_download_root(selected)
        self._update_download_root_display()

    def _open_download_root(self) -> None:
        open_in_file_browser(self.download_service.get_download_root())

    def _open_post_detail(self, post: PostRecord, *, prefer_local: bool) -> None:
        dialog = PostDetailDialog(
            post,
            self.image_cache,
            self._thumbnail_tasks,
            prefer_local=prefer_local,
            translator=self.translator,
            parent=self,
        )
        dialog.download_requested.connect(self._begin_single_download)
        dialog.delete_requested.connect(lambda requested_post, dlg=dialog: self._delete_downloaded_post(requested_post, after_delete=dlg.accept))
        dialog.exec()

    def _begin_single_download(self, post: PostRecord) -> None:
        dialog = DownloadOptionsDialog(post, self.translator, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        title_override = dialog.title_override()

        def job():
            refreshed = self.instagram_service.refresh_post(post.shortcode)
            return self.download_service.download_post(refreshed, title_override=title_override)

        self._run_worker(
            job,
            loading_text=self._t("main.message.downloading_selected_post"),
            success_handler=lambda _: self._after_download_complete(single=True),
        )

    def _after_download_complete(self, *, single: bool) -> None:
        self._reload_all_views()
        QMessageBox.information(
            self,
            self._t("main.message.download_complete_title"),
            self._t("main.message.download_complete_single" if single else "main.message.download_complete_batch"),
        )

    def _set_posted_to_cafe(self, post_id: int, checked: bool) -> None:
        self.download_service.set_posted_to_cafe(post_id, checked)
        if self.pages.currentIndex() != self.PAGE_DOWNLOADED:
            self._downloaded_feed_dirty = True

    def _delete_downloaded_post(self, post: PostRecord, *, after_delete=None) -> None:
        if post.id is None:
            QMessageBox.warning(
                self,
                self._t("downloaded.delete_confirm.title"),
                self._t("downloaded.delete_confirm.missing"),
            )
            return
        answer = QMessageBox.question(
            self,
            self._t("downloaded.delete_confirm.title"),
            self._t("downloaded.delete_confirm.body"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            deleted = self.download_service.delete_downloaded_post(post.id)
        except Exception as exc:  # pragma: no cover - UI safety path
            QMessageBox.critical(
                self,
                self._t("main.message.operation_failed"),
                self._t("main.message.task_ui_failed", error=exc),
            )
            return
        if not deleted:
            QMessageBox.information(
                self,
                self._t("downloaded.delete_confirm.title"),
                self._t("downloaded.delete_confirm.not_found"),
            )
            return
        self._reload_all_views(refresh_online_feed=True, refresh_downloaded_feed=True)
        self.statusBar().showMessage(self._t("downloaded.delete_success"), 5000)
        if after_delete is not None:
            after_delete()

    def _startup_check_for_new_posts(self) -> None:
        if not self.account_service.list_accounts():
            return
        self._run_worker(
            self.instagram_service.check_for_new_posts,
            loading_text=self._t("main.message.checking_new_posts"),
            success_handler=self._handle_startup_check_result,
        )

    def _handle_startup_check_result(self, result) -> None:
        self._reload_all_views(
            refresh_online_feed=bool(result.new_posts),
            refresh_downloaded_feed=False,
        )
        if not result.new_posts:
            self.statusBar().showMessage(self._t("main.status.no_new_posts"), 5000)
            return

        answer = QMessageBox.question(
            self,
            self._t("main.message.new_posts_title"),
            self._t(
                "main.message.new_posts_body",
                count=len(result.new_posts),
                checked_accounts=result.checked_accounts,
            ),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        dialog = BulkDownloadDialog(len(result.new_posts), self.translator, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        batch_rule = dialog.batch_rule()

        def job():
            downloaded = []
            for index, post in enumerate(result.new_posts, start=1):
                refreshed = self.instagram_service.refresh_post(post.shortcode)
                downloaded.append(
                    self.download_service.download_post(
                        refreshed,
                        batch_rule=batch_rule,
                        batch_index=index if batch_rule else None,
                    )
                )
            return downloaded

        self._run_worker(
            job,
            loading_text=self._t("main.message.downloading_new_posts"),
            success_handler=lambda _: self._after_download_complete(single=False),
        )

    def start_account_add(self, profile_url: str, company_name: str = "") -> int:
        def job():
            resolved = self.instagram_service.resolve_profile(profile_url)
            resolved_company_name = company_name or resolved["display_name"] or resolved["username"]
            account = self.account_service.save_account(
                profile_url=resolved["profile_url"],
                username=resolved["username"],
                display_name=resolved["display_name"],
                company_name=resolved_company_name,
            )
            self.instagram_service.initial_sync_account(account.id)
            return account

        return self._run_worker(
            job,
            loading_text=self._t("main.message.adding_account"),
            success_handler=lambda _: self._after_account_added(),
        )

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.translator.language, self.theme_manager.theme, self.translator, self.theme_manager, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        selected_language = normalize_app_language(dialog.selected_language())
        selected_theme = normalize_app_theme(dialog.selected_theme())
        self._save_language(selected_language)
        self._save_theme(selected_theme)
        self.translator.set_language(selected_language)
        self.theme_manager.set_theme(selected_theme)
        self.statusBar().showMessage(self._t("settings.saved"), 3000)

    def _save_language(self, language: str) -> None:
        self.account_service.database.set_setting(APP_LANGUAGE_SETTING_KEY, normalize_app_language(language))

    def _save_theme(self, theme: str) -> None:
        self.account_service.database.set_setting(APP_THEME_SETTING_KEY, normalize_app_theme(theme))

    def active_task_count(self) -> int:
        return len(self._active_tasks)

    def _shutdown_background_tasks(self) -> None:
        self._shutdown_task_handles(self._active_tasks, finalize=self._finalize_task)
        self._shutdown_task_handles(self._thumbnail_tasks)

    def _shutdown_task_handles(self, handles, *, finalize=None) -> None:
        seen_threads = set()
        for handle in list(handles.values()) if isinstance(handles, dict) else list(handles):
            thread = handle.thread
            if id(thread) in seen_threads:
                continue
            seen_threads.add(id(thread))
            thread.requestInterruption()
            thread.quit()

        if isinstance(handles, dict):
            items = list(handles.items())
            for task_id, handle in items:
                handle.thread.wait()
                if finalize is not None:
                    finalize(task_id)
        else:
            for handle in list(handles):
                handle.thread.wait()
                if handle in handles:
                    handles.remove(handle)

    def _finalize_task(self, task_id: int) -> None:
        progress = self._active_progress.pop(task_id, None)
        if progress is not None:
            progress.close()
            progress.deleteLater()
        self._active_tasks.pop(task_id, None)

    def _run_worker(
        self,
        fn,
        *,
        success_handler,
        loading_text: str | None = None,
        error_handler=None,
    ) -> int:
        progress = None
        if loading_text:
            progress = QProgressDialog(loading_text, None, 0, 0, self)
            progress.setWindowTitle(APP_BRAND_NAME)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setCancelButton(None)
            progress.setMinimumDuration(0)
            progress.show()

        task_id = self._task_counter
        self._task_counter += 1

        def handle_success(result) -> None:
            try:
                success_handler(result)
            except Exception as exc:  # pragma: no cover - UI safety path
                QMessageBox.critical(
                    self,
                    self._t("main.message.operation_failed"),
                    self._t("main.message.task_ui_failed", error=exc),
                )

        def handle_error(message: str) -> None:
            if error_handler is not None:
                error_handler(message)
                return
            QMessageBox.critical(self, self._t("main.message.operation_failed"), message)

        def finalize_task() -> None:
            self._finalize_task(task_id)

        handle = create_task_handle(
            fn,
            on_result=handle_success,
            on_error=handle_error,
            on_thread_finished=finalize_task,
        )
        self._active_tasks[task_id] = handle
        if progress is not None:
            self._active_progress[task_id] = progress
        handle.thread.start()
        return task_id

    def _queue_online_refresh_after_settle(self, account_id: int | None) -> None:
        self._pending_online_refresh_account_id = account_id
        self._delayed_online_refresh_timer.stop()
        logger.info("Online feed auto refresh queued account_id=%s state=waiting-for-settle", account_id)

    def _handle_online_feed_settled(self) -> None:
        if self._pending_online_refresh_account_id is None:
            return
        if self.pages.currentIndex() != self.PAGE_ONLINE:
            return
        logger.info(
            "Online feed settled; delayed auto refresh armed account_id=%s selected_account_id=%s",
            self._pending_online_refresh_account_id,
            self.online_feed_view.selected_account_id(),
        )
        self._delayed_online_refresh_timer.start(350)

    def _run_pending_online_refresh(self) -> None:
        account_id = self._pending_online_refresh_account_id
        self._pending_online_refresh_account_id = None
        if self.pages.currentIndex() != self.PAGE_ONLINE:
            logger.info("Online feed auto refresh skipped reason=page-not-visible")
            return
        if account_id != self.online_feed_view.selected_account_id():
            logger.info(
                "Online feed auto refresh skipped reason=account-changed queued_account_id=%s selected_account_id=%s",
                account_id,
                self.online_feed_view.selected_account_id(),
            )
            return
        logger.info("Online feed auto refresh starting account_id=%s reason=page-settled", account_id)
        self._start_background_online_refresh(account_id, show_progress=False, source="auto-delayed")

    def _start_background_online_refresh(
        self,
        account_id: int | None,
        *,
        show_progress: bool = False,
        source: str = "background",
    ) -> None:
        if account_id is None:
            job = self.instagram_service.refresh_all_accounts
            loading_text = self._t("main.message.refreshing_all_accounts")
        else:
            if self._active_online_refresh_account_id == account_id:
                return
            job = lambda: self.instagram_service.refresh_account_posts(account_id)
            loading_text = self._t("main.message.refreshing_selected_account")

        self._active_online_refresh_account_id = account_id
        logger.info("Remote feed fetch started account_id=%s source=%s", account_id, source)

        def finish_refresh() -> None:
            if self._active_online_refresh_account_id == account_id:
                self._active_online_refresh_account_id = None

        def handle_success(result) -> None:
            loaded_count = len(result) if result is not None else 0
            thumbnails_busy = self.online_feed_view.is_thumbnail_activation_busy()
            logger.info(
                "Remote feed fetch finished account_id=%s loaded_posts=%s source=%s thumbnails_busy=%s",
                account_id,
                loaded_count,
                source,
                thumbnails_busy,
            )
            finish_refresh()
            self._online_feed_dirty = True
            logger.info(
                "Background refresh completion -> feed reload scheduling account_id=%s source=%s force=%s thumbnails_busy=%s",
                account_id,
                source,
                self.pages.currentIndex() == self.PAGE_ONLINE,
                thumbnails_busy,
            )
            if thumbnails_busy and self.pages.currentIndex() == self.PAGE_ONLINE:
                self._queue_online_reload_after_thumbnails(
                    reason=f"background-refresh:{source}",
                    force=True,
                )
            else:
                self._schedule_online_feed_reload(
                    force=self.pages.currentIndex() == self.PAGE_ONLINE,
                    reason=f"background-refresh:{source}",
                )
            self.statusBar().showMessage(self._t("main.status.online_feed_refreshed"), 5000)

        def handle_error(message: str) -> None:
            finish_refresh()
            QMessageBox.critical(self, self._t("main.message.remote_feed_refresh_failed"), message)

        self._run_worker(
            job,
            loading_text=loading_text if show_progress else None,
            success_handler=handle_success,
            error_handler=handle_error,
        )

    def _queue_online_reload_after_thumbnails(self, *, reason: str, force: bool) -> None:
        self._pending_online_reload_reason = reason
        self._pending_online_reload_force = force
        logger.info(
            "Online feed reload deferred reason=%s force=%s thumbnails_busy=%s",
            reason,
            force,
            self.online_feed_view.is_thumbnail_activation_busy(),
        )
        self._delayed_online_reload_timer.start(350)

    def _run_pending_online_reload(self) -> None:
        if self._pending_online_reload_reason is None:
            return
        if self.pages.currentIndex() != self.PAGE_ONLINE:
            logger.info("Online feed reload deferred task skipped reason=page-not-visible")
            self._pending_online_reload_reason = None
            self._pending_online_reload_force = False
            return
        if self.online_feed_view.is_thumbnail_activation_busy():
            logger.info(
                "Online feed reload still waiting for thumbnails reason=%s",
                self._pending_online_reload_reason,
            )
            self._delayed_online_reload_timer.start(350)
            return
        reason = self._pending_online_reload_reason
        force = self._pending_online_reload_force
        self._pending_online_reload_reason = None
        self._pending_online_reload_force = False
        self._schedule_online_feed_reload(force=force, reason=reason)
