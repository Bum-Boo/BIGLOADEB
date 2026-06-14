from __future__ import annotations

import logging
import time

from PySide6.QtCore import QPoint, QRect, QTimer, Signal
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


class OnlineFeedView(QWidget):
    RENDER_BATCH_SIZE = 6
    VISIBLE_THUMBNAIL_BATCH_SIZE = 2
    LAZY_THUMBNAIL_BATCH_SIZE = 1
    THUMBNAIL_SETTLE_DELAY_MS = 140
    THUMBNAIL_VISIBLE_BATCH_DELAY_MS = 70
    THUMBNAIL_LAZY_BATCH_DELAY_MS = 180

    filters_changed = Signal()
    refresh_requested = Signal()
    post_open_requested = Signal(object)
    download_requested = Signal(object)
    render_finished = Signal(int)
    settled = Signal()

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
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel()
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setObjectName("sectionSubtitleLabel")
        layout.addWidget(self.subtitle_label)

        self.loading_label = QLabel()
        self.loading_label.setObjectName("loadingLabel")
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
        layout.addWidget(self.empty_label)

        self._render_generation = 0
        self._pending_posts: list[PostRecord] = []
        self._pending_index = 0
        self._rendered_cards: list[QWidget] = []
        self._render_started_at = 0.0
        self._thumbnail_activation_generation = 0
        self._pending_visible_cards: list[PostCard] = []
        self._pending_lazy_cards: list[PostCard] = []
        self._tracked_first_batch_keys: set[str] = set()
        self._first_batch_apply_started_at = 0.0
        self._first_batch_tracking_started = False
        self._settled_generation = -1
        self._loading_message_key = "online.loading"
        self._loading_message_kwargs: dict[str, object] = {}
        self._thumbnail_activation_timer = QTimer(self)
        self._thumbnail_activation_timer.setSingleShot(True)
        self._thumbnail_activation_timer.timeout.connect(self._activate_next_visible_batch)
        self._lazy_thumbnail_timer = QTimer(self)
        self._lazy_thumbnail_timer.setSingleShot(True)
        self._lazy_thumbnail_timer.timeout.connect(self._activate_next_lazy_batch)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._schedule_visible_thumbnail_activation)
        self.scroll_area.horizontalScrollBar().valueChanged.connect(self._schedule_visible_thumbnail_activation)

        self.set_accounts([])
        self.set_posts([])
        self.retranslate_ui()
        self.translator.language_changed.connect(self.retranslate_ui)

    def _emit_filters_changed(self, *_args) -> None:
        logger.info(
            "Online feed filters changed account_id=%s media_filter=%s sort_order=%s",
            self.selected_account_id(),
            self.selected_media_filter(),
            self.selected_sort_order(),
        )
        self.filters_changed.emit()

    def _emit_refresh_requested(self, *_args) -> None:
        self.refresh_requested.emit()

    def _t(self, key: str, **kwargs) -> str:
        return self.translator.tr(key, **kwargs)

    def set_accounts(self, accounts: list[AccountRecord]) -> None:
        current_account_id = self.selected_account_id()
        self._accounts = accounts
        self.account_filter.blockSignals(True)
        self.account_filter.clear()
        self.account_filter.addItem(self._t("online.account.all"), None)
        for account in accounts:
            self.account_filter.addItem(f"{account.company_name} ({account.username})", account.id)
        if current_account_id is not None:
            for index in range(self.account_filter.count()):
                if self.account_filter.itemData(index) == current_account_id:
                    self.account_filter.setCurrentIndex(index)
                    break
        self.account_filter.blockSignals(False)

    def set_selected_account(self, account_id: int | None) -> None:
        for index in range(self.account_filter.count()):
            if self.account_filter.itemData(index) == account_id:
                self.account_filter.setCurrentIndex(index)
                break

    def selected_account_id(self) -> int | None:
        return self.account_filter.currentData()

    def selected_media_filter(self) -> str:
        return self.media_filter.currentData()

    def selected_sort_order(self) -> str:
        return self.sort_filter.currentData()

    def show_loading_message(self, message: str) -> None:
        self._render_generation += 1
        self._thumbnail_activation_generation += 1
        self._pending_posts = []
        self._pending_index = 0
        self._rendered_cards = []
        self._pending_visible_cards = []
        self._pending_lazy_cards = []
        self._tracked_first_batch_keys = set()
        self._first_batch_apply_started_at = 0.0
        self._first_batch_tracking_started = False
        self._settled_generation = -1
        self._loading_message_key = message
        self._loading_message_kwargs = {}
        self._thumbnail_activation_timer.stop()
        self._lazy_thumbnail_timer.stop()
        self.grid_widget.set_layout_frozen(False, reason="loading-reset")
        self.grid_widget.clear_cards()
        self.loading_label.setText(self._t(message))
        self.loading_label.setVisible(True)
        self.empty_label.setVisible(False)
        self.scroll_area.setVisible(False)

    def set_posts(self, posts: list[PostRecord]) -> None:
        self._render_generation += 1
        self._thumbnail_activation_generation += 1
        self._posts = list(posts)
        self._pending_posts = list(posts)
        self._pending_index = 0
        self._rendered_cards = []
        self._pending_visible_cards = []
        self._pending_lazy_cards = []
        self._tracked_first_batch_keys = set()
        self._first_batch_apply_started_at = 0.0
        self._first_batch_tracking_started = False
        self._settled_generation = -1
        self._thumbnail_activation_timer.stop()
        self._lazy_thumbnail_timer.stop()
        self.grid_widget.set_layout_frozen(False, reason="set-posts-reset")
        self.grid_widget.clear_cards()

        if not posts:
            self.loading_label.setVisible(False)
            self.empty_label.setVisible(True)
            self.scroll_area.setVisible(False)
            self.grid_widget.set_layout_frozen(False, reason="empty-feed")
            self._mark_settled()
            return

        self.empty_label.setVisible(False)
        self._loading_message_key = "online.rendering_posts"
        self._loading_message_kwargs = {"count": len(posts)}
        self.loading_label.setText(self._t(self._loading_message_key, **self._loading_message_kwargs))
        self.loading_label.setVisible(True)
        self.scroll_area.setVisible(True)
        self._render_started_at = time.perf_counter()
        logger.info("UI card render started feed=online count=%s", len(posts))
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
                prefer_local_preview=False,
                card_mode="online",
                defer_thumbnail_load=True,
                translator=self.translator,
                task_handles=self.thumbnail_task_handles,
            )
            card.clicked.connect(self.post_open_requested.emit)
            card.download_requested.connect(self.download_requested.emit)
            card.thumbnail_applied.connect(self._handle_thumbnail_applied)
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
            "UI card render finished feed=online count=%s elapsed_ms=%.1f",
            len(self._rendered_cards),
            (time.perf_counter() - self._render_started_at) * 1000 if self._render_started_at else 0.0,
        )
        self.grid_widget.set_layout_frozen(True, reason="first-visible-thumbnail-batch")
        self._schedule_thumbnail_activation(generation)
        self.render_finished.emit(len(self._rendered_cards))

    def retranslate_ui(self, *_args) -> None:
        self.title_label.setText(self._t("online.title"))
        self.subtitle_label.setText(self._t("online.subtitle"))
        if self._loading_message_key:
            self.loading_label.setText(self._t(self._loading_message_key, **self._loading_message_kwargs))
        self.empty_label.setText(self._t("online.empty"))
        self.refresh_button.setText(self._t("online.refresh"))
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
        self.account_filter.addItem(self._t("online.account.all"), None)
        for account in self._accounts:
            self.account_filter.addItem(f"{account.company_name} ({account.username})", account.id)
        self.media_filter.setItemText(0, self._t("online.media.all"))
        self.media_filter.setItemText(1, self._t("online.media.image"))
        self.media_filter.setItemText(2, self._t("online.media.video"))
        self.sort_filter.setItemText(0, self._t("online.sort.newest"))
        self.sort_filter.setItemText(1, self._t("online.sort.oldest"))
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

    def _schedule_visible_thumbnail_activation(self, *_args) -> None:
        if not self._rendered_cards or not self.scroll_area.isVisible():
            return
        self._schedule_thumbnail_activation(self._render_generation, delay_ms=70)

    def _schedule_thumbnail_activation(self, generation: int, delay_ms: int | None = None) -> None:
        if generation != self._render_generation:
            return
        self._thumbnail_activation_generation = generation
        if delay_ms is None:
            delay_ms = self.THUMBNAIL_SETTLE_DELAY_MS
        self._thumbnail_activation_timer.start(delay_ms)

    def _activate_next_visible_batch(self) -> None:
        generation = self._thumbnail_activation_generation
        if generation != self._render_generation:
            return
        visible_cards = self._visible_cards_needing_activation()
        visible_count = len(visible_cards)
        if not visible_cards:
            self.grid_widget.set_layout_frozen(False, reason="no-visible-thumbnail-batch")
            self._mark_settled()
            self._schedule_lazy_thumbnail_activation()
            return
        logger.info(
            "Thumbnail activation start generation=%s visible_cards=%s total_cards=%s",
            generation,
            visible_count,
            len(self._rendered_cards),
        )
        self._pending_visible_cards = visible_cards
        batch_cards = visible_cards[: self.VISIBLE_THUMBNAIL_BATCH_SIZE]
        if not self._first_batch_tracking_started:
            self._first_batch_tracking_started = True
            self._tracked_first_batch_keys = {card.thumbnail_label.debug_key for card in batch_cards}
            self._first_batch_apply_started_at = time.perf_counter()
            logger.info("Visible-card thumbnail count generation=%s count=%s", generation, len(self._tracked_first_batch_keys))
        self._activate_card_batch(self._pending_visible_cards, self.VISIBLE_THUMBNAIL_BATCH_SIZE)
        if self._pending_visible_cards:
            self._thumbnail_activation_timer.start(self.THUMBNAIL_VISIBLE_BATCH_DELAY_MS)
        else:
            self._schedule_lazy_thumbnail_activation()

    def _schedule_lazy_thumbnail_activation(self) -> None:
        if self._lazy_thumbnail_timer.isActive():
            return
        if not self._first_batch_tracking_started:
            self.grid_widget.set_layout_frozen(False, reason="lazy-thumbnail-only")
            self._mark_settled()
        self._pending_lazy_cards = [
            card for card in self._rendered_cards if card not in self._visible_cards_needing_activation() and card.needs_thumbnail_activation()
        ]
        if not self._pending_lazy_cards:
            return
        self._lazy_thumbnail_timer.start(self.THUMBNAIL_LAZY_BATCH_DELAY_MS)

    def _activate_next_lazy_batch(self) -> None:
        if self._thumbnail_activation_generation != self._render_generation:
            return
        if not self._pending_lazy_cards:
            self._schedule_lazy_thumbnail_activation()
            return
        self._activate_card_batch(self._pending_lazy_cards, self.LAZY_THUMBNAIL_BATCH_SIZE)
        if self._pending_lazy_cards:
            self._lazy_thumbnail_timer.start(self.THUMBNAIL_LAZY_BATCH_DELAY_MS)

    def _activate_card_batch(self, cards: list[PostCard], batch_size: int) -> None:
        batch = cards[:batch_size]
        del cards[:batch_size]
        for card in batch:
            card.activate_thumbnail()

    def _visible_cards_needing_activation(self) -> list[PostCard]:
        viewport = self.scroll_area.viewport()
        viewport_rect = viewport.rect()
        visible_cards: list[PostCard] = []
        for card in self._rendered_cards:
            if not isinstance(card, PostCard) or not card.needs_thumbnail_activation():
                continue
            top_left = card.mapTo(viewport, QPoint(0, 0))
            card_rect = QRect(top_left, card.size())
            if viewport_rect.intersects(card_rect):
                visible_cards.append(card)
        return visible_cards

    def _handle_thumbnail_applied(self, debug_key: str, elapsed_ms: float, success: bool) -> None:
        if debug_key not in self._tracked_first_batch_keys:
            return
        self._tracked_first_batch_keys.remove(debug_key)
        if not self._tracked_first_batch_keys and self._first_batch_apply_started_at:
            total_elapsed_ms = (time.perf_counter() - self._first_batch_apply_started_at) * 1000
            logger.info(
                "First visible thumbnail batch finished elapsed_ms=%.1f last_apply_ms=%.1f success=%s",
                total_elapsed_ms,
                elapsed_ms,
                success,
            )
            self.grid_widget.set_layout_frozen(False, reason="first-visible-thumbnail-batch-finished")
            self._mark_settled()

    def _mark_settled(self) -> None:
        if self._settled_generation == self._render_generation:
            return
        self._settled_generation = self._render_generation
        logger.info("Online feed settled generation=%s", self._render_generation)
        self.settled.emit()

    def is_thumbnail_activation_busy(self) -> bool:
        return bool(
            self._tracked_first_batch_keys
            or self._pending_visible_cards
            or self._pending_lazy_cards
            or self._thumbnail_activation_timer.isActive()
            or self._lazy_thumbnail_timer.isActive()
            or any(isinstance(card, PostCard) and card.needs_thumbnail_activation() for card in self._rendered_cards)
        )
