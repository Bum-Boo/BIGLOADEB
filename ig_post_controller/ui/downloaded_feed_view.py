from __future__ import annotations

import logging
import time

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ig_post_controller.models import AccountRecord, PostRecord
from ig_post_controller.services.image_cache_service import ImageCacheService
from ig_post_controller.ui.i18n import LanguageManager
from ig_post_controller.ui.widgets import CardGridWidget, PostCard


logger = logging.getLogger(__name__)


class DownloadedFeedView(QWidget):
    RENDER_BATCH_SIZE = 6

    filters_changed = Signal()
    refresh_requested = Signal()
    post_open_requested = Signal(object)
    download_requested = Signal(object)
    delete_requested = Signal(object)
    posted_to_cafe_changed = Signal(int, bool)

    def __init__(self, image_cache: ImageCacheService, translator: LanguageManager, thumbnail_task_handles: list | None = None) -> None:
        super().__init__()
        self.image_cache = image_cache
        self.translator = translator
        self.thumbnail_task_handles = thumbnail_task_handles
        self._accounts: list[AccountRecord] = []
        self._posts: list[PostRecord] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        self.title_label = QLabel()
        self.title_label.setObjectName("sectionTitleLabel")
        self.title_label.setStyleSheet("font-size: 22px; font-weight: 700;")
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel()
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setObjectName("sectionSubtitleLabel")
        layout.addWidget(self.subtitle_label)

        self.loading_label = QLabel()
        self.loading_label.setObjectName("loadingLabel")
        self.loading_label.setStyleSheet("padding: 4px 0;")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        controls = QHBoxLayout()
        self.account_filter = QComboBox()
        self.account_filter.currentIndexChanged.connect(self._emit_filters_changed)
        controls.addWidget(self.account_filter)

        self.media_filter = QComboBox()
        self.media_filter.addItem("All Media", "all")
        self.media_filter.addItem("Image Only", "image")
        self.media_filter.addItem("Video Only", "video")
        self.media_filter.currentIndexChanged.connect(self._emit_filters_changed)
        controls.addWidget(self.media_filter)

        self.sort_filter = QComboBox()
        self.sort_filter.addItem("Newest First", "newest")
        self.sort_filter.addItem("Oldest First", "oldest")
        self.sort_filter.currentIndexChanged.connect(self._emit_filters_changed)
        controls.addWidget(self.sort_filter)

        self.refresh_button = QPushButton()
        self.refresh_button.clicked.connect(self._emit_refresh_requested)
        controls.addWidget(self.refresh_button)
        layout.addLayout(controls)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("feedScrollArea")
        self.scroll_area.viewport().setObjectName("feedViewport")
        self.scroll_area.setWidgetResizable(True)
        self.grid_widget = CardGridWidget()
        self.grid_widget.setObjectName("cardGridWidget")
        self.scroll_area.setWidget(self.grid_widget)
        layout.addWidget(self.scroll_area, 1)

        self.empty_label = QLabel()
        self.empty_label.setObjectName("emptyLabel")
        self.empty_label.setStyleSheet("padding: 20px;")
        layout.addWidget(self.empty_label)

        self._render_generation = 0
        self._pending_posts: list[PostRecord] = []
        self._pending_index = 0
        self._rendered_cards: list[QWidget] = []
        self._render_started_at = 0.0
        self._loading_message_key = "downloaded.loading"
        self._loading_message_kwargs: dict[str, object] = {}

        self.set_accounts([])
        self.set_posts([])
        self.retranslate_ui()
        self.translator.language_changed.connect(self.retranslate_ui)

    def _emit_filters_changed(self, *_args) -> None:
        self.filters_changed.emit()

    def _emit_refresh_requested(self, *_args) -> None:
        self.refresh_requested.emit()

    def _t(self, key: str, **kwargs) -> str:
        return self.translator.tr(key, **kwargs)

    def set_accounts(self, accounts: list[AccountRecord]) -> None:
        self._accounts = list(accounts)
        current_account_id = self.selected_account_id()
        self.account_filter.blockSignals(True)
        self.account_filter.clear()
        self.account_filter.addItem(self._t("downloaded.account.all"), None)
        for account in accounts:
            self.account_filter.addItem(f"{account.company_name} ({account.username})", account.id)
        if current_account_id is not None:
            for index in range(self.account_filter.count()):
                if self.account_filter.itemData(index) == current_account_id:
                    self.account_filter.setCurrentIndex(index)
                    break
        self.account_filter.blockSignals(False)

    def selected_account_id(self) -> int | None:
        return self.account_filter.currentData()

    def selected_media_filter(self) -> str:
        return self.media_filter.currentData()

    def selected_sort_order(self) -> str:
        return self.sort_filter.currentData()

    def show_loading_message(self, message: str) -> None:
        self._render_generation += 1
        self._pending_posts = []
        self._pending_index = 0
        self._rendered_cards = []
        self._loading_message_key = message
        self._loading_message_kwargs = {}
        self.grid_widget.clear_cards()
        self.loading_label.setText(self._t(message))
        self.loading_label.setVisible(True)
        self.empty_label.setVisible(False)
        self.scroll_area.setVisible(False)

    def set_posts(self, posts: list[PostRecord]) -> None:
        self._render_generation += 1
        self._posts = list(posts)
        self._pending_posts = list(posts)
        self._pending_index = 0
        self._rendered_cards = []
        self.grid_widget.clear_cards()

        if not posts:
            self.loading_label.setVisible(False)
            self.empty_label.setVisible(True)
            self.scroll_area.setVisible(False)
            return

        self.empty_label.setVisible(False)
        self._loading_message_key = "downloaded.rendering_posts"
        self._loading_message_kwargs = {"count": len(posts)}
        self.loading_label.setText(self._t(self._loading_message_key, **self._loading_message_kwargs))
        self.loading_label.setVisible(True)
        self.scroll_area.setVisible(True)
        self._render_started_at = time.perf_counter()
        logger.info("UI card render started feed=downloaded count=%s", len(posts))
        generation = self._render_generation
        QTimer.singleShot(0, lambda gen=generation: self._render_next_batch(gen))

    def _render_next_batch(self, generation: int) -> None:
        if generation != self._render_generation:
            return

        batch_cards: list[QWidget] = []
        end_index = min(self._pending_index + self.RENDER_BATCH_SIZE, len(self._pending_posts))
        if self._pending_index >= end_index:
            self._finish_render(generation)
            return

        for post in self._pending_posts[self._pending_index:end_index]:
            card = PostCard(
                post,
                self.image_cache,
                show_posted_checkbox=True,
                prefer_local_preview=True,
                card_mode="downloaded",
                show_delete_button=True,
                translator=self.translator,
                task_handles=self.thumbnail_task_handles,
            )
            card.clicked.connect(self.post_open_requested.emit)
            card.download_requested.connect(self.download_requested.emit)
            card.delete_requested.connect(self.delete_requested.emit)
            card.posted_to_cafe_changed.connect(self.posted_to_cafe_changed.emit)
            self._rendered_cards.append(card)
            batch_cards.append(card)

        self._pending_index = end_index
        self.grid_widget.append_cards(batch_cards)

        if self._pending_index < len(self._pending_posts):
            QTimer.singleShot(0, lambda gen=generation: self._render_next_batch(gen))
        else:
            self._finish_render(generation)

    def _finish_render(self, generation: int) -> None:
        if generation != self._render_generation:
            return

        self.loading_label.setVisible(False)
        self.empty_label.setVisible(False)
        self.scroll_area.setVisible(bool(self._rendered_cards))
        logger.info(
            "UI card render finished feed=downloaded count=%s elapsed_ms=%.1f",
            len(self._rendered_cards),
            (time.perf_counter() - self._render_started_at) * 1000 if self._render_started_at else 0.0,
        )

    def retranslate_ui(self, *_args) -> None:
        self.title_label.setText(self._t("downloaded.title"))
        self.subtitle_label.setText(self._t("downloaded.subtitle"))
        if self._loading_message_key:
            self.loading_label.setText(self._t(self._loading_message_key, **self._loading_message_kwargs))
        self.empty_label.setText(self._t("downloaded.empty"))
        self.refresh_button.setText(self._t("downloaded.refresh"))
        self._rebuild_filter_labels()
        for card in self._rendered_cards:
            if isinstance(card, PostCard):
                card.refresh(card.post)

    def _rebuild_filter_labels(self) -> None:
        account_id = self.selected_account_id()
        media_filter = self.selected_media_filter()
        sort_order = self.selected_sort_order()
        self.account_filter.blockSignals(True)
        self.media_filter.blockSignals(True)
        self.sort_filter.blockSignals(True)
        self.account_filter.clear()
        self.account_filter.addItem(self._t("downloaded.account.all"), None)
        for account in self._accounts:
            self.account_filter.addItem(f"{account.company_name} ({account.username})", account.id)
        self.media_filter.setItemText(0, self._t("downloaded.media.all"))
        self.media_filter.setItemText(1, self._t("downloaded.media.image"))
        self.media_filter.setItemText(2, self._t("downloaded.media.video"))
        self.sort_filter.setItemText(0, self._t("downloaded.sort.newest"))
        self.sort_filter.setItemText(1, self._t("downloaded.sort.oldest"))
        for index in range(self.account_filter.count()):
            if self.account_filter.itemData(index) == account_id:
                self.account_filter.setCurrentIndex(index)
                break
        for index in range(self.media_filter.count()):
            if self.media_filter.itemData(index) == media_filter:
                self.media_filter.setCurrentIndex(index)
                break
        for index in range(self.sort_filter.count()):
            if self.sort_filter.itemData(index) == sort_order:
                self.sort_filter.setCurrentIndex(index)
                break
        self.account_filter.blockSignals(False)
        self.media_filter.blockSignals(False)
        self.sort_filter.blockSignals(False)
