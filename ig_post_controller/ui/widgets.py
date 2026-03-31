from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics, QMouseEvent, QPixmap, QTextLayout
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ig_post_controller.models import PostRecord
from ig_post_controller.services.image_cache_service import ImageCacheService
from ig_post_controller.ui.i18n import LanguageManager
from ig_post_controller.ui.worker import TaskHandle, create_task_handle


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ThumbnailPayload:
    generation: int
    source: str | None
    data: bytes | None


class ThumbnailLabel(QLabel):
    _pixmap_cache: dict[str, QPixmap] = {}
    _scaled_pixmap_cache: dict[tuple[str, int, int], QPixmap] = {}

    apply_finished = Signal(str, float, bool)

    def __init__(
        self,
        image_cache: ImageCacheService,
        *,
        translator: LanguageManager | None = None,
        width: int = 266,
        height: int = 180,
        debug_key: str = "",
        task_handles: list[TaskHandle] | None = None,
    ) -> None:
        super().__init__(translator.tr("post_preview.no") if translator is not None else "")
        self.image_cache = image_cache
        self.translator = translator
        self.target_width = width
        self.target_height = height
        self.debug_key = debug_key or f"thumbnail-{id(self)}"
        self._pixmap: QPixmap | None = None
        self._task_handles = task_handles if task_handles is not None else []
        self._load_generation = 0
        self._source: str | None = None
        self._last_scaled_size: tuple[int, int] = (0, 0)
        self._load_started = False
        self.setFixedSize(width, height)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setObjectName("thumbnailLabel")

    def _t(self, key: str, **kwargs) -> str:
        if self.translator is None:
            return key
        return self.translator.tr(key, **kwargs)

    def set_source(self, source: str | None, *, activate: bool = True) -> None:
        if source == self._source and (self._load_started or self._pixmap is not None):
            logger.info("Thumbnail queue skipped key=%s source=%s reason=same-source", self.debug_key, source)
            return
        self._source = source
        self._pixmap = None
        self._last_scaled_size = (0, 0)
        self._load_started = False
        self.clear()
        self._load_generation += 1
        self.setText(
            self._t("post_preview.ready")
            if source and not activate
            else self._t("post_preview.loading") if source else self._t("post_preview.no")
        )
        if not source:
            return
        if activate:
            self.activate_source()

    def needs_activation(self) -> bool:
        return bool(self._source) and not self._load_started and self._pixmap is None

    def activate_source(self) -> None:
        source = self._source
        if not source:
            return
        if self._load_started:
            logger.info("Thumbnail activation skipped key=%s source=%s reason=already-started", self.debug_key, source)
            return
        self._load_started = True
        generation = self._load_generation
        self.setText(self._t("post_preview.loading"))
        logger.info("Thumbnail activation started key=%s generation=%s source=%s", self.debug_key, generation, source)
        if not self.image_cache.thumbnails_enabled:
            logger.info("Thumbnail queue skipped key=%s source=%s reason=disabled", self.debug_key, source)
            self.setText(self._t("post_preview.unavailable"))
            self.apply_finished.emit(self.debug_key, 0.0, False)
            return

        def load_payload() -> ThumbnailPayload:
            return ThumbnailPayload(
                generation=generation,
                source=source,
                data=self.image_cache.fetch_image_bytes(source),
            )

        def release_handle() -> None:
            self._release_task_handle(handle)

        handle = create_task_handle(
            load_payload,
            on_result=self._handle_loaded_payload,
            on_error=self._handle_error,
            on_thread_finished=release_handle,
        )
        self._task_handles.append(handle)
        handle.thread.start()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._pixmap is None:
            return
        if event.size() == event.oldSize():
            return
        self._apply_scaled_pixmap()

    def _release_task_handle(self, handle: TaskHandle) -> None:
        if handle in self._task_handles:
            self._task_handles.remove(handle)

    def _handle_loaded_payload(self, payload: ThumbnailPayload) -> None:
        if payload.generation != self._load_generation:
            logger.info(
                "Thumbnail UI update skipped key=%s generation=%s reason=stale current_generation=%s",
                self.debug_key,
                payload.generation,
                self._load_generation,
            )
            return
        apply_started_at = time.perf_counter()
        logger.info("Thumbnail UI apply start key=%s generation=%s has_data=%s", self.debug_key, payload.generation, bool(payload.data))
        if not payload.data:
            self.setText(self._t("post_preview.unavailable"))
            self.apply_finished.emit(self.debug_key, (time.perf_counter() - apply_started_at) * 1000, False)
            return
        pixmap = self._pixmap_cache.get(payload.source or "")
        if pixmap is None:
            pixmap = QPixmap()
            if pixmap.loadFromData(payload.data):
                self._pixmap_cache[payload.source or ""] = pixmap
            else:
                pixmap = QPixmap()
        if pixmap.isNull():
            self.setText(self._t("post_preview.unavailable"))
            self.apply_finished.emit(self.debug_key, (time.perf_counter() - apply_started_at) * 1000, False)
            return
        self._pixmap = pixmap
        self._apply_scaled_pixmap()
        elapsed_ms = (time.perf_counter() - apply_started_at) * 1000
        logger.info("Thumbnail UI apply finish key=%s generation=%s elapsed_ms=%.1f", self.debug_key, payload.generation, elapsed_ms)
        self.apply_finished.emit(self.debug_key, elapsed_ms, True)

    def _handle_error(self, message: str) -> None:
        logger.info("Thumbnail UI update failed key=%s message=%s", self.debug_key, message)
        self.setText(message or self._t("post_preview.unavailable"))
        self.apply_finished.emit(self.debug_key, 0.0, False)

    def _apply_scaled_pixmap(self) -> None:
        if not self._pixmap:
            return
        target_size = (self.target_width, self.target_height)
        if target_size == self._last_scaled_size:
            return
        self._last_scaled_size = target_size
        source = self._source or self.debug_key
        cache_key = (source, self.target_width, self.target_height)
        scaled = self._scaled_pixmap_cache.get(cache_key)
        if scaled is None:
            scaled = self._pixmap.scaled(
                self.target_width,
                self.target_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._scaled_pixmap_cache[cache_key] = scaled
        self.setPixmap(scaled)


def clamp_multiline_text(text: str, font, width: int, max_lines: int = 3) -> str:
    normalized = " ".join((text or "").replace("\r", " ").replace("\n", " ").split()).strip()
    if not normalized:
        return ""

    layout = QTextLayout(normalized, font)
    layout.beginLayout()
    lines: list[str] = []
    consumed = 0
    while len(lines) < max_lines:
        line = layout.createLine()
        if not line.isValid():
            break
        line.setLineWidth(width)
        start = line.textStart()
        length = line.textLength()
        segment = normalized[start : start + length].rstrip()
        if not segment:
            break
        lines.append(segment)
        consumed = start + length
    layout.endLayout()

    if not lines:
        return QFontMetrics(font).elidedText(normalized, Qt.TextElideMode.ElideRight, width)

    if consumed < len(normalized):
        lines[-1] = QFontMetrics(font).elidedText(
            f"{lines[-1]} {normalized[consumed:].lstrip()}",
            Qt.TextElideMode.ElideRight,
            width,
        )

    return "\n".join(lines[:max_lines])


class PostCard(QFrame):
    CARD_WIDTH = 290
    CONTENT_WIDTH = 266
    THUMBNAIL_HEIGHT = 200
    ACTION_ROW_HEIGHT = 60
    POSTED_ROW_HEIGHT = 24
    CARD_HEIGHT = 404
    DOWNLOAD_CARD_HEIGHT = CARD_HEIGHT + POSTED_ROW_HEIGHT

    clicked = Signal(object)
    download_requested = Signal(object)
    delete_requested = Signal(object)
    posted_to_cafe_changed = Signal(int, bool)
    thumbnail_applied = Signal(str, float, bool)

    def __init__(
        self,
        post: PostRecord,
        image_cache: ImageCacheService,
        *,
        show_posted_checkbox: bool = False,
        prefer_local_preview: bool = False,
        card_mode: str = "online",
        defer_thumbnail_load: bool = False,
        show_delete_button: bool = False,
        translator: LanguageManager | None = None,
        task_handles: list[TaskHandle] | None = None,
    ) -> None:
        super().__init__()
        self.post = post
        self.image_cache = image_cache
        self.prefer_local_preview = prefer_local_preview
        self.card_mode = card_mode
        self.defer_thumbnail_load = defer_thumbnail_load
        self.show_delete_button = show_delete_button
        self.translator = translator
        self._clamp_caption_preview = True
        self.setObjectName("postCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumWidth(self.CARD_WIDTH)
        self.setMaximumWidth(self.CARD_WIDTH)
        fixed_height = self.DOWNLOAD_CARD_HEIGHT if show_posted_checkbox else self.CARD_HEIGHT
        self.setMinimumHeight(fixed_height)
        self.setMaximumHeight(fixed_height)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)

        self.date_row_widget = QWidget()
        self.date_row_widget.setFixedHeight(22)
        date_row = QHBoxLayout(self.date_row_widget)
        date_row.setContentsMargins(0, 0, 0, 0)
        date_row.setSpacing(0)
        self.date_label = QLabel()
        self.date_label.setObjectName("cardDateLabel")
        self.date_label.setStyleSheet("font-size: 12px;")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        date_row.addWidget(self.date_label)
        date_row.addStretch(1)
        layout.addWidget(self.date_row_widget)

        self.caption_label = QLabel()
        self.caption_label.setObjectName("cardCaptionLabel")
        self.caption_label.setStyleSheet("font-size: 13px;")
        self.caption_label.setWordWrap(False)
        self.caption_label.setTextFormat(Qt.TextFormat.PlainText)
        self.caption_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.caption_label.setFixedHeight(self._caption_preview_height())
        layout.addWidget(self.caption_label)

        self.status_row_widget = QWidget()
        self.status_row_widget.setFixedHeight(22)
        status_row = QHBoxLayout(self.status_row_widget)
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(0)
        self.status_label = QLabel()
        self.status_label.setObjectName("cardStatusLabel")
        self.status_label.setStyleSheet("font-weight: 600;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        status_row.addWidget(self.status_label)
        status_row.addStretch(1)
        layout.addWidget(self.status_row_widget)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.setContentsMargins(0, 0, 0, 0)
        self.download_button = QPushButton()
        self.download_button.setMinimumHeight(40)
        self.download_button.clicked.connect(lambda *_: self.download_requested.emit(self.post))
        controls.addWidget(self.download_button)

        self.delete_button = None
        if self.show_delete_button:
            self.delete_button = QPushButton()
            self.delete_button.setObjectName("dangerButton")
            self.delete_button.setMinimumHeight(40)
            self.delete_button.clicked.connect(lambda *_: self.delete_requested.emit(self.post))
            controls.addWidget(self.delete_button)

        self.posted_checkbox = None
        self.posted_row_widget = None
        if show_posted_checkbox and post.id is not None:
            self.posted_checkbox = QCheckBox()
            self.posted_checkbox.clicked.connect(
                lambda checked: self.posted_to_cafe_changed.emit(self.post.id or 0, checked)
            )
            self.posted_row_widget = QWidget()
            self.posted_row_widget.setFixedHeight(self.POSTED_ROW_HEIGHT)
            posted_row = QHBoxLayout(self.posted_row_widget)
            posted_row.setContentsMargins(0, 0, 0, 0)
            posted_row.setSpacing(0)
            posted_row.addWidget(self.posted_checkbox)
            posted_row.addStretch(1)

        controls.addStretch(1)
        controls_widget = QWidget()
        controls_widget.setLayout(controls)
        controls_widget.setMinimumHeight(self.ACTION_ROW_HEIGHT)
        controls_widget.setMaximumHeight(self.ACTION_ROW_HEIGHT)
        layout.addWidget(controls_widget)
        if self.posted_row_widget is not None:
            layout.addWidget(self.posted_row_widget)
        self.thumbnail_label = ThumbnailLabel(
            image_cache,
            translator=translator,
            width=self.CONTENT_WIDTH,
            height=self.THUMBNAIL_HEIGHT,
            debug_key=f"{post.shortcode}:{card_mode}",
            task_handles=task_handles,
        )
        self.thumbnail_label.apply_finished.connect(self.thumbnail_applied.emit)
        layout.insertWidget(0, self.thumbnail_label)
        self.refresh(post)

    def refresh(self, post: PostRecord) -> None:
        self.post = post
        self.date_label.setText(post.taken_at.strftime("%Y-%m-%d %H:%M"))
        caption = (post.caption or "").strip()
        self.caption_label.setText(
            clamp_multiline_text(caption if caption else self._t("post.no_caption"), self.caption_label.font(), self.CONTENT_WIDTH, 2)
        )
        if self.card_mode == "downloaded":
            self.status_label.setText(self._t("post.status.saved"))
        else:
            self.status_label.setText(self._t("post.status.downloaded_local") if post.is_downloaded else self._t("post.status.remote_only"))
        self.download_button.setText(self._t("post.redownload") if post.is_downloaded else self._t("post.download"))
        if self.delete_button is not None:
            self.delete_button.setText(self._t("post.delete"))
        self.thumbnail_label.set_source(
            post.get_preview_source(prefer_local=self.prefer_local_preview),
            activate=not self.defer_thumbnail_load,
        )
        if self.posted_checkbox is not None:
            self.posted_checkbox.setChecked(post.posted_to_cafe)
            self.posted_checkbox.setText(self._t("post.posted_to_cafe"))

    def _t(self, key: str, **kwargs) -> str:
        if self.translator is None:
            return key
        return self.translator.tr(key, **kwargs)

    def _caption_preview_height(self) -> int:
        metrics = QFontMetrics(self.caption_label.font())
        return metrics.lineSpacing() * 2 + 4

    def activate_thumbnail(self) -> None:
        self.thumbnail_label.activate_source()

    def needs_thumbnail_activation(self) -> bool:
        return self.thumbnail_label.needs_activation()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.post)
        super().mousePressEvent(event)


class CardGridWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.cards: list[QWidget] = []
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(4, 4, 4, 4)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)
        self._current_columns = 0
        self._relayout_count = 0
        self._layout_frozen = False
        self._pending_relayout_reason: str | None = None
        self._pending_columns = 0

    def clear_cards(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        self.cards = []
        self._current_columns = 0
        self._layout_frozen = False
        self._pending_columns = 0
        self._pending_relayout_reason = None

    def set_cards(self, cards: list[QWidget]) -> None:
        self.clear_cards()
        self.cards = list(cards)
        self._relayout(reason="set-cards")

    def append_cards(self, cards: list[QWidget]) -> None:
        if not cards:
            return
        start_index = len(self.cards)
        self.cards.extend(cards)
        if self._current_columns == 0:
            self._current_columns = self._compute_columns()
        self._place_cards(cards, start_index, self._current_columns)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        new_columns = self._compute_columns()
        if new_columns == self._current_columns:
            return
        logger.info(
            "Card grid relayout trigger reason=%s width=%s previous_columns=%s new_columns=%s cards=%s frozen=%s",
            "resize-column-change",
            self.width(),
            self._current_columns,
            new_columns,
            len(self.cards),
            self._layout_frozen,
        )
        if self._layout_frozen:
            self._pending_columns = new_columns
            self._pending_relayout_reason = "resize-column-change"
            logger.info(
                "Card grid relayout deferred reason=%s previous_columns=%s pending_columns=%s",
                self._pending_relayout_reason,
                self._current_columns,
                self._pending_columns,
            )
            return
        self._relayout(reason="resize-column-change", requested_columns=new_columns)

    def _relayout(self, *, reason: str, requested_columns: int | None = None) -> None:
        self._relayout_count += 1
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        if not self.cards:
            return
        previous_columns = self._current_columns
        self._current_columns = requested_columns if requested_columns is not None else self._compute_columns()
        logger.info(
            "Card grid relayout started count=%s reason=%s previous_columns=%s new_columns=%s cards=%s width=%s",
            self._relayout_count,
            reason,
            previous_columns,
            self._current_columns,
            len(self.cards),
            self.width(),
        )
        self._place_cards(self.cards, 0, self._current_columns)
        logger.info(
            "Card grid relayout finished count=%s reason=%s columns=%s cards=%s",
            self._relayout_count,
            reason,
            self._current_columns,
            len(self.cards),
        )

    def _place_cards(self, cards: list[QWidget], start_index: int, columns: int | None = None) -> None:
        if columns is None:
            columns = self._compute_columns()
        for offset, card in enumerate(cards):
            index = start_index + offset
            row = index // columns
            column = index % columns
            self.grid.addWidget(
                card,
                row,
                column,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            )
        self.grid.setColumnStretch(columns, 1)

    def _compute_columns(self) -> int:
        card_width = PostCard.CARD_WIDTH
        available_width = max(self.width(), card_width)
        return max(1, available_width // card_width)

    def set_layout_frozen(self, frozen: bool, *, reason: str) -> None:
        if self._layout_frozen == frozen:
            return
        self._layout_frozen = frozen
        logger.info(
            "Card grid layout frozen=%s reason=%s current_columns=%s pending_columns=%s cards=%s",
            frozen,
            reason,
            self._current_columns,
            self._pending_columns,
            len(self.cards),
        )
        if not frozen and self.cards:
            if self._pending_relayout_reason is not None and self._pending_columns != self._current_columns:
                pending_columns = self._pending_columns
                pending_reason = self._pending_relayout_reason
                self._pending_relayout_reason = None
                self._pending_columns = 0
                self._relayout(reason=f"unfreeze:{pending_reason}", requested_columns=pending_columns)
            else:
                self._pending_relayout_reason = None
                self._pending_columns = 0


def format_last_checked(timestamp: datetime | None, translator: LanguageManager | None = None) -> str:
    if timestamp:
        return timestamp.strftime("%Y-%m-%d %H:%M")
    if translator is not None:
        return translator.tr("account.last_checked.never")
    return ""
