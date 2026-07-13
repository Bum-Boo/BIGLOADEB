from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
except ImportError:  # Multimedia libraries may be unavailable in test/minimal environments.
    QAudioOutput = None  # type: ignore[assignment]
    QMediaPlayer = None  # type: ignore[assignment]
    QVideoWidget = None  # type: ignore[assignment]
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
)

from ig_post_controller.config import APP_VERSION
from ig_post_controller.models import PostRecord
from ig_post_controller.services.image_cache_service import ImageCacheService
from ig_post_controller.ui.i18n import LanguageManager
from ig_post_controller.ui.theme import ThemeManager
from ig_post_controller.ui.widgets import ThumbnailLabel
from ig_post_controller.utils.paths import open_in_file_browser
from ig_post_controller.utils.text import build_default_download_title


class _TranslatedDialog(QDialog):
    def __init__(self, translator: LanguageManager | None = None, parent=None) -> None:
        super().__init__(parent)
        self.translator = translator
        if self.translator is not None:
            self.translator.language_changed.connect(self.retranslate_ui)

    def _t(self, key: str, **kwargs) -> str:
        if self.translator is None:
            return key
        return self.translator.tr(key, **kwargs)

    def retranslate_ui(self, *_args) -> None:
        return


class AddAccountDialog(_TranslatedDialog):
    def __init__(self, translator: LanguageManager | None = None, parent=None) -> None:
        super().__init__(translator, parent)
        self.setWindowTitle(self._t("add_account.title"))
        self.resize(420, 180)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText(self._t("add_account.placeholder.profile_url"))
        self.url_label = QLabel()
        form.addRow(self.url_label, self.url_edit)

        self.company_edit = QLineEdit()
        self.company_edit.setPlaceholderText(self._t("add_account.placeholder.company_name"))
        self.company_label = QLabel()
        form.addRow(self.company_label, self.company_edit)
        layout.addLayout(form)

        self.note_label = QLabel(self._t("add_account.note"))
        self.note_label.setWordWrap(True)
        self.note_label.setObjectName("settingsNoteLabel")
        layout.addWidget(self.note_label)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.retranslate_ui()

    def retranslate_ui(self, *_args) -> None:
        self.setWindowTitle(self._t("add_account.title"))
        self.url_label.setText(self._t("add_account.profile_url"))
        self.company_label.setText(self._t("add_account.company_name"))
        self.url_edit.setPlaceholderText(self._t("add_account.placeholder.profile_url"))
        self.company_edit.setPlaceholderText(self._t("add_account.placeholder.company_name"))
        self.note_label.setText(self._t("add_account.note"))
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(self._t("common.ok"))
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(self._t("common.cancel"))
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setMinimumHeight(38)
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setMinimumHeight(38)

    def accept(self) -> None:
        if not self.profile_url():
            QMessageBox.warning(self, self._t("add_account.warning.title"), self._t("add_account.warning.body"))
            return
        super().accept()

    def profile_url(self) -> str:
        return self.url_edit.text().strip()

    def company_name(self) -> str:
        return self.company_edit.text().strip()


class DownloadOptionsDialog(_TranslatedDialog):
    def __init__(self, post: PostRecord, translator: LanguageManager | None = None, parent=None) -> None:
        super().__init__(translator, parent)
        self.post = post
        self.setWindowTitle(self._t("download_options.title", action=self._t("post.redownload") if post.is_downloaded else self._t("post.download")))
        self.resize(460, 180)

        layout = QVBoxLayout(self)
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        form = QFormLayout()
        self.title_edit = QLineEdit(post.custom_title or "")
        self.title_edit.setPlaceholderText(self._t("download_options.placeholder"))
        self.title_label = QLabel()
        form.addRow(self.title_label, self.title_edit)
        layout.addLayout(form)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.retranslate_ui()

    def retranslate_ui(self, *_args) -> None:
        self.setWindowTitle(self._t("download_options.title", action=self._t("post.redownload") if self.post.is_downloaded else self._t("post.download")))
        self.info_label.setText(
            self._t(
                "download_options.info",
                title=build_default_download_title(self.post.taken_at, self.post.caption),
            )
        )
        self.title_label.setText(self._t("download_options.folder_title"))
        self.title_edit.setPlaceholderText(self._t("download_options.placeholder"))
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(self._t("common.ok"))
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(self._t("common.cancel"))
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setMinimumHeight(38)
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setMinimumHeight(38)

    def title_override(self) -> str | None:
        value = self.title_edit.text().strip()
        return value or None


class BulkDownloadDialog(_TranslatedDialog):
    def __init__(self, count: int, translator: LanguageManager | None = None, parent=None) -> None:
        super().__init__(translator, parent)
        self.count = count
        self.setWindowTitle(self._t("bulk_download.title"))
        self.resize(480, 180)

        layout = QVBoxLayout(self)
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        form = QFormLayout()
        self.batch_title_edit = QLineEdit()
        self.batch_title_edit.setPlaceholderText(self._t("bulk_download.placeholder"))
        self.batch_title_label = QLabel()
        form.addRow(self.batch_title_label, self.batch_title_edit)
        layout.addLayout(form)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.retranslate_ui()

    def retranslate_ui(self, *_args) -> None:
        self.setWindowTitle(self._t("bulk_download.title"))
        self.info_label.setText(self._t("bulk_download.info", count=self.count))
        self.batch_title_label.setText(self._t("bulk_download.batch_title"))
        self.batch_title_edit.setPlaceholderText(self._t("bulk_download.placeholder"))
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(self._t("common.ok"))
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(self._t("common.cancel"))
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setMinimumHeight(38)
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setMinimumHeight(38)

    def batch_rule(self) -> str | None:
        value = self.batch_title_edit.text().strip()
        return value or None


class SettingsDialog(_TranslatedDialog):
    language_selected = Signal(str)
    theme_selected = Signal(str)
    download_layout_selected = Signal(str)
    update_check_requested = Signal()

    def __init__(
        self,
        current_language: str,
        current_theme: str,
        translator: LanguageManager | None = None,
        theme_manager: ThemeManager | None = None,
        parent=None,
        current_download_layout: str = "organized",
    ) -> None:
        super().__init__(translator, parent)
        self._current_language = current_language
        self._current_theme = current_theme
        self._current_download_layout = current_download_layout
        self.theme_manager = theme_manager
        self.setWindowTitle(self._t("settings.title"))
        self.resize(380, 220)

        layout = QVBoxLayout(self)
        self.note_label = QLabel()
        self.note_label.setWordWrap(True)
        self.note_label.setObjectName("settingsNoteLabel")
        layout.addWidget(self.note_label)

        form = QFormLayout()
        self.language_combo = QComboBox()
        self.language_label = QLabel()
        form.addRow(self.language_label, self.language_combo)
        self.theme_combo = QComboBox()
        self.theme_label = QLabel()
        form.addRow(self.theme_label, self.theme_combo)
        self.download_layout_combo = QComboBox()
        self.download_layout_label = QLabel()
        form.addRow(self.download_layout_label, self.download_layout_combo)
        self.version_label = QLabel()
        self.version_label.setObjectName("settingsNoteLabel")
        self.version_title_label = QLabel()
        form.addRow(self.version_title_label, self.version_label)
        layout.addLayout(form)

        update_row = QHBoxLayout()
        self.update_status_label = QLabel()
        self.update_status_label.setObjectName("settingsNoteLabel")
        self.update_button = QPushButton()
        self.update_button.setObjectName("primaryButton")
        self.update_button.clicked.connect(self.update_check_requested.emit)
        update_row.addWidget(self.update_status_label, 1)
        update_row.addWidget(self.update_button)
        layout.addLayout(update_row)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self._accept_settings)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.retranslate_ui()
        self._set_current_language(current_language)
        self._set_current_theme(current_theme)
        self._set_current_download_layout(current_download_layout)

    def _set_current_language(self, language: str) -> None:
        self.language_combo.blockSignals(True)
        self.language_combo.clear()
        for option in self.translator.language_options() if self.translator is not None else []:
            self.language_combo.addItem(option.label, option.code)
        if self.language_combo.count() == 0:
            self.language_combo.addItem("English", "en")
            self.language_combo.addItem("Korean", "ko")
            self.language_combo.addItem("Japanese", "ja")
            self.language_combo.addItem("Chinese", "zh")
        target = language or "ko"
        for index in range(self.language_combo.count()):
            if self.language_combo.itemData(index) == target:
                self.language_combo.setCurrentIndex(index)
                break
        self.language_combo.blockSignals(False)

    def _set_current_theme(self, theme: str) -> None:
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        options = self.theme_manager.theme_options(self.translator) if self.theme_manager is not None else []
        for option in options:
            self.theme_combo.addItem(option.label, option.code)
        if self.theme_combo.count() == 0:
            self.theme_combo.addItem("Clean Light", "clean_light")
            self.theme_combo.addItem("Soft Dark Slate", "soft_dark_slate")
            self.theme_combo.addItem("Warm Paper", "warm_paper")
            self.theme_combo.addItem("Neon Utility", "neon_utility")
            self.theme_combo.addItem("GQuuuuuuX Signal", "gquuuuuux_signal")
        target = theme or "clean_light"
        for index in range(self.theme_combo.count()):
            if self.theme_combo.itemData(index) == target:
                self.theme_combo.setCurrentIndex(index)
                break
        self.theme_combo.blockSignals(False)

    def _set_current_download_layout(self, layout: str) -> None:
        self.download_layout_combo.blockSignals(True)
        self.download_layout_combo.clear()
        self.download_layout_combo.addItem(self._t("settings.download_layout.organized"), "organized")
        self.download_layout_combo.addItem(self._t("settings.download_layout.flat"), "flat")
        target = layout if layout in {"organized", "flat"} else "organized"
        for index in range(self.download_layout_combo.count()):
            if self.download_layout_combo.itemData(index) == target:
                self.download_layout_combo.setCurrentIndex(index)
                break
        self.download_layout_combo.blockSignals(False)

    def retranslate_ui(self, *_args) -> None:
        self.setWindowTitle(self._t("settings.title"))
        self.language_label.setText(self._t("settings.language"))
        self.theme_label.setText(self._t("settings.theme"))
        self.download_layout_label.setText(self._t("settings.download_layout"))
        self.version_title_label.setText(self._t("settings.version"))
        self.version_label.setText(self._t("settings.version_value", version=APP_VERSION))
        self.update_status_label.setText(self._t("settings.update_hint"))
        self.update_button.setText(self._t("settings.check_update"))
        self.note_label.setText(self._t("settings.note"))
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setText(self._t("settings.save"))
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(self._t("settings.cancel"))
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setMinimumHeight(38)
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setMinimumHeight(38)
        current = self.language_combo.currentData()
        self._set_current_language(current or self._current_language)
        current_theme = self.theme_combo.currentData()
        self._set_current_theme(current_theme or self._current_theme)
        current_layout = self.download_layout_combo.currentData()
        self._set_current_download_layout(current_layout or self._current_download_layout)

    def _accept_settings(self) -> None:
        self.language_selected.emit(self.selected_language())
        self.theme_selected.emit(self.selected_theme())
        self.download_layout_selected.emit(self.selected_download_layout())
        self.accept()

    def selected_language(self) -> str:
        return str(self.language_combo.currentData() or "ko")

    def selected_theme(self) -> str:
        return str(self.theme_combo.currentData() or "clean_light")

    def selected_download_layout(self) -> str:
        return str(self.download_layout_combo.currentData() or "organized")


class PostDetailDialog(_TranslatedDialog):
    download_requested = Signal(object)
    delete_requested = Signal(object)
    reconnect_requested = Signal(object)

    def __init__(
        self,
        post: PostRecord,
        image_cache: ImageCacheService,
        thumbnail_task_handles: list | None = None,
        *,
        prefer_local: bool = False,
        translator: LanguageManager | None = None,
        parent=None,
    ) -> None:
        super().__init__(translator, parent)
        self.post = post
        self.image_cache = image_cache
        self.prefer_local = prefer_local
        self.current_index = 0

        self.setWindowTitle(self._t("post_detail.title", display_name=post.display_name, shortcode=post.shortcode))
        self.resize(860, 760)

        root = QVBoxLayout(self)
        root.setSpacing(12)

        self.preview_stack = QStackedWidget()
        self.image_preview = ThumbnailLabel(image_cache, translator=translator, height=420, task_handles=thumbnail_task_handles)
        self.preview_stack.addWidget(self.image_preview)

        if QVideoWidget is not None and QMediaPlayer is not None and QAudioOutput is not None:
            self.video_widget = QVideoWidget()
            self.player = QMediaPlayer(self)
            self.audio_output = QAudioOutput(self)
            self.player.setAudioOutput(self.audio_output)
            self.player.setVideoOutput(self.video_widget)
        else:
            self.video_widget = QLabel(self._t("post_preview.video_unavailable"))
            self.video_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.player = None
            self.audio_output = None
        self.preview_stack.addWidget(self.video_widget)

        root.addWidget(self.preview_stack)

        nav = QHBoxLayout()
        self.previous_button = QPushButton()
        self.previous_button.clicked.connect(lambda *_: self._change_index(-1))
        nav.addWidget(self.previous_button)

        self.counter_label = QLabel()
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(self.counter_label, 1)

        self.next_button = QPushButton()
        self.next_button.clicked.connect(lambda *_: self._change_index(1))
        nav.addWidget(self.next_button)

        self.play_button = QPushButton()
        self.play_button.clicked.connect(lambda *_: self._toggle_playback())
        nav.addWidget(self.play_button)

        root.addLayout(nav)

        self.meta_line = QLabel()
        self.meta_line.setObjectName("metaLineLabel")
        root.addWidget(self.meta_line)

        self.caption_box = QPlainTextEdit(post.caption or "")
        self.caption_box.setReadOnly(True)
        self.caption_box.setMinimumHeight(170)
        root.addWidget(self.caption_box)

        actions = QHBoxLayout()
        self.copy_button = QPushButton()
        self.copy_button.clicked.connect(lambda *_: self._copy_caption())
        actions.addWidget(self.copy_button)

        self.open_post_button = QPushButton()
        self.open_post_button.clicked.connect(lambda *_: QDesktopServices.openUrl(QUrl(self.post.source_url)))
        actions.addWidget(self.open_post_button)

        if self.post.is_downloaded:
            self.delete_button = QPushButton()
            self.delete_button.setObjectName("dangerButton")
            self.delete_button.clicked.connect(lambda *_: self._request_delete())
            actions.addWidget(self.delete_button)
        else:
            self.delete_button = None

        if post.folder_path and not post.download_folder_missing:
            self.open_folder_button = QPushButton()
            self.open_folder_button.clicked.connect(lambda *_: open_in_file_browser(post.folder_path))
            actions.addWidget(self.open_folder_button)
        else:
            self.open_folder_button = None

        if post.is_downloaded and post.download_folder_missing:
            self.reconnect_folder_button = QPushButton()
            self.reconnect_folder_button.setObjectName("primaryButton")
            self.reconnect_folder_button.clicked.connect(lambda *_: self.reconnect_requested.emit(self.post))
            actions.addWidget(self.reconnect_folder_button)
        else:
            self.reconnect_folder_button = None

        actions.addStretch(1)
        self.download_button = QPushButton()
        self.download_button.setObjectName("primaryButton")
        self.download_button.clicked.connect(lambda *_: self._request_download())
        actions.addWidget(self.download_button)
        root.addLayout(actions)

        self.retranslate_ui()
        self._update_preview()

    def retranslate_ui(self, *_args) -> None:
        self.setWindowTitle(self._t("post_detail.title", display_name=self.post.display_name, shortcode=self.post.shortcode))
        self.previous_button.setText(self._t("post_detail.previous"))
        self.next_button.setText(self._t("post_detail.next"))
        self.play_button.setText(self._t("post_detail.play_pause"))
        self.copy_button.setText(self._t("post_detail.copy_caption"))
        self.open_post_button.setText(self._t("post_detail.open_post"))
        if self.delete_button is not None:
            self.delete_button.setText(self._t("post.delete"))
        if self.open_folder_button is not None:
            self.open_folder_button.setText(self._t("post_detail.open_folder"))
        if self.reconnect_folder_button is not None:
            self.reconnect_folder_button.setText(self._t("post_detail.reconnect_folder"))
        self.download_button.setText(self._t("post.redownload") if self.post.is_downloaded else self._t("post.download"))
        self.caption_box.setPlainText(self.post.caption or "")
        self.meta_line.setText(
            self._t(
                "post_detail.meta",
                username=self.post.username,
                display_name=self.post.display_name,
                date=self.post.taken_at.strftime("%Y-%m-%d %H:%M"),
                post_type=self.post.post_type.title(),
            )
        )
        self._update_preview()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.player is not None:
            self.player.stop()
        super().closeEvent(event)

    def _change_index(self, delta: int) -> None:
        if not self.post.media_items:
            return
        self.current_index = (self.current_index + delta) % len(self.post.media_items)
        self._update_preview()

    def _toggle_playback(self) -> None:
        if self.player is None or QMediaPlayer is None:
            return
        if self.preview_stack.currentWidget() is not self.video_widget:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _copy_caption(self) -> None:
        QApplication.clipboard().setText(self.post.caption or "")
        QMessageBox.information(self, self._t("post_detail.caption_copied.title"), self._t("post_detail.caption_copied.body"))

    def _request_download(self) -> None:
        self.download_requested.emit(self.post)
        self.accept()

    def _request_delete(self) -> None:
        self.delete_requested.emit(self.post)

    def _update_preview(self) -> None:
        count = len(self.post.media_items)
        self.previous_button.setEnabled(count > 1)
        self.next_button.setEnabled(count > 1)
        self.counter_label.setText(f"{self.current_index + 1} / {count or 1}")

        if not self.post.media_items:
            self.image_preview.set_source(self.post.thumbnail_url)
            self.preview_stack.setCurrentWidget(self.image_preview)
            self.play_button.setEnabled(False)
            return

        current = self.post.media_items[self.current_index]
        prefer_local = self.prefer_local or self.post.is_downloaded

        if current.media_type == "video":
            source = current.playable_source(prefer_local=prefer_local)
            if not source or self.player is None:
                self.image_preview.setText(self._t("post_preview.video_unavailable"))
                self.preview_stack.setCurrentWidget(self.image_preview)
                self.play_button.setEnabled(False)
                return
            url = QUrl.fromLocalFile(source) if Path(source).exists() else QUrl(source)
            self.player.setSource(url)
            self.preview_stack.setCurrentWidget(self.video_widget)
            self.play_button.setEnabled(True)
        else:
            if self.player is not None:
                self.player.stop()
            self.image_preview.set_source(current.preview_source(prefer_local=prefer_local))
            self.preview_stack.setCurrentWidget(self.image_preview)
            self.play_button.setEnabled(False)
