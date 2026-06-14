from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal

from ig_post_controller.config import DEFAULT_APP_THEME, normalize_app_theme
from ig_post_controller.ui.i18n import LanguageManager


@dataclass(slots=True)
class ThemeOption:
    code: str
    label: str


@dataclass(frozen=True, slots=True)
class ThemePalette:
    window_bg: str
    sidebar_bg: str
    surface_bg: str
    surface_alt_bg: str
    card_bg: str
    border: str
    text: str
    muted: str
    accent: str
    accent_text: str
    danger: str
    warning: str
    selection_bg: str
    selection_text: str


THEME_LABEL_KEYS = {
    "clean_light": "settings.theme.clean_light",
    "soft_dark_slate": "settings.theme.soft_dark_slate",
    "warm_paper": "settings.theme.warm_paper",
    "neon_utility": "settings.theme.neon_utility",
    "gquuuuuux_signal": "settings.theme.gquuuuuux_signal",
}


THEME_PALETTES: dict[str, ThemePalette] = {
    "clean_light": ThemePalette(
        window_bg="#F8FAFC",
        sidebar_bg="#EEF2F7",
        surface_bg="#FFFFFF",
        surface_alt_bg="#F6F8FC",
        card_bg="#FFFFFF",
        border="#D6DEE8",
        text="#101828",
        muted="#475467",
        accent="#2563EB",
        accent_text="#FFFFFF",
        danger="#B42318",
        warning="#B54708",
        selection_bg="#DBEAFE",
        selection_text="#1D4ED8",
    ),
    "soft_dark_slate": ThemePalette(
        window_bg="#0F172A",
        sidebar_bg="#111827",
        surface_bg="#1E293B",
        surface_alt_bg="#172036",
        card_bg="#1E293B",
        border="#334155",
        text="#E5E7EB",
        muted="#94A3B8",
        accent="#38BDF8",
        accent_text="#0F172A",
        danger="#F87171",
        warning="#FBBF24",
        selection_bg="#1D4ED8",
        selection_text="#F8FAFC",
    ),
    "warm_paper": ThemePalette(
        window_bg="#F7F1E6",
        sidebar_bg="#E9DFC9",
        surface_bg="#FFF9F0",
        surface_alt_bg="#F4EBDC",
        card_bg="#FFF9F0",
        border="#D6C3A5",
        text="#2B2A28",
        muted="#6B6258",
        accent="#A16207",
        accent_text="#FFF9F0",
        danger="#C2410C",
        warning="#B45309",
        selection_bg="#EAD7B1",
        selection_text="#5B3E12",
    ),
    "neon_utility": ThemePalette(
        window_bg="#0B1020",
        sidebar_bg="#10172A",
        surface_bg="#151B2E",
        surface_alt_bg="#18203A",
        card_bg="#151B2E",
        border="#2A3553",
        text="#E6EDF3",
        muted="#8AA0B8",
        accent="#22D3EE",
        accent_text="#0B1020",
        danger="#FB7185",
        warning="#F59E0B",
        selection_bg="#164E63",
        selection_text="#E6FFFB",
    ),
    "gquuuuuux_signal": ThemePalette(
        window_bg="#08112A",
        sidebar_bg="#101C3C",
        surface_bg="#16264A",
        surface_alt_bg="#1B2F5A",
        card_bg="#16264A",
        border="#243A63",
        text="#F4F7FB",
        muted="#A9B4C8",
        accent="#2B63D9",
        accent_text="#FFFFFF",
        danger="#D94A4A",
        warning="#F2C84B",
        selection_bg="#2B63D9",
        selection_text="#FFFFFF",
    ),
}


class ThemeManager(QObject):
    theme_changed = Signal(str)

    def __init__(self, theme: str | None = None) -> None:
        super().__init__()
        self._theme = normalize_app_theme(theme)
        self._application = None

    @property
    def theme(self) -> str:
        return self._theme

    def bind_application(self, application) -> None:
        self._application = application
        self._apply_application_stylesheet()

    def set_theme(self, theme: str | None) -> str:
        normalized = normalize_app_theme(theme)
        if normalized == self._theme:
            return self._theme
        self._theme = normalized
        self._apply_application_stylesheet()
        self.theme_changed.emit(self._theme)
        return self._theme

    def theme_options(self, translator: LanguageManager) -> list[ThemeOption]:
        return [ThemeOption(code=code, label=translator.tr(label_key)) for code, label_key in THEME_LABEL_KEYS.items()]

    def palette(self) -> ThemePalette:
        return THEME_PALETTES[self._theme]

    def _apply_application_stylesheet(self) -> None:
        if self._application is None:
            return
        self._application.setStyleSheet(self.stylesheet())

    def stylesheet(self) -> str:
        p = self.palette()
        return f"""
            QWidget {{
                color: {p.text};
                font-family: "Malgun Gothic", "맑은 고딕", "Segoe UI", "Noto Sans KR", "Apple SD Gothic Neo", Arial, sans-serif;
                font-size: 14px;
            }}
            QWidget#mainWindowCentral {{
                background: {p.window_bg};
            }}
            QWidget#contentPanel, QStackedWidget, QStackedWidget > QWidget {{
                background: {p.window_bg};
            }}
            QWidget#sidebarPanel {{
                background: {p.sidebar_bg};
                border-right: 1px solid {p.border};
            }}
            QMainWindow, QDialog {{
                background: {p.window_bg};
            }}
            QLabel#appTitleLabel {{
                color: {p.text};
                font-size: 24px;
                font-weight: 800;
                letter-spacing: -0.4px;
            }}
            QLabel#sectionTitleLabel {{
                color: {p.text};
                font-size: 22px;
                font-weight: 750;
                letter-spacing: -0.35px;
            }}
            QLabel#sectionSubtitleLabel, QLabel#emptyLabel, QLabel#settingsNoteLabel, QLabel#metaLineLabel, QLabel#cardDateLabel, QLabel#accountIntroLabel {{
                color: {p.muted};
            }}
            QLabel#emptyLabel {{
                padding: 24px;
            }}
            QLabel#loadingLabel {{
                color: {p.accent};
                font-weight: 650;
                padding: 6px 0px;
            }}
            QLabel#folderLabel {{
                color: {p.muted};
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 0.2px;
            }}
            QFrame#postCard, QFrame#settingsPanel {{
                background: {p.card_bg};
                border: 1px solid {p.border};
                border-radius: 16px;
            }}
            QFrame#postCard:hover {{
                border-color: {p.accent};
                background: {p.surface_bg};
            }}
            QLabel#thumbnailLabel {{
                background: {p.surface_alt_bg};
                color: {p.muted};
                border: 1px solid {p.border};
                border-radius: 12px;
                padding: 0px;
            }}
            QFrame#cardBodyFrame {{
                background: transparent;
            }}
            QLabel#cardCaptionLabel {{
                color: {p.text};
                font-size: 13px;
                line-height: 130%;
            }}
            QLabel#cardDateLabel {{
                font-size: 12px;
                font-weight: 600;
            }}
            QLabel#cardStatusLabel {{
                color: {p.accent};
                font-size: 12px;
                font-weight: 750;
            }}
            QPushButton {{
                background: {p.surface_bg};
                border: 1px solid {p.border};
                border-radius: 11px;
                color: {p.text};
                padding: 10px 14px;
                min-height: 38px;
                font-weight: 650;
            }}
            QPushButton:hover {{
                background: {p.surface_alt_bg};
                border-color: {p.muted};
            }}
            QPushButton:pressed {{
                background: {p.selection_bg};
                border-color: {p.accent};
            }}
            QPushButton:disabled {{
                color: {p.muted};
                background: {p.surface_alt_bg};
                border-color: {p.border};
            }}
            QPushButton:checked, QPushButton#primaryButton {{
                background: {p.accent};
                border-color: {p.accent};
                color: {p.accent_text};
            }}
            QPushButton#primaryButton:hover {{
                background: {p.accent};
                border-color: {p.accent};
            }}
            QPushButton:focus {{
                border-color: {p.accent};
            }}
            QPushButton#navButton {{
                text-align: left;
                padding: 12px 14px;
                border-radius: 13px;
                background: transparent;
                color: {p.text};
                font-weight: 750;
                min-height: 48px;
            }}
            QPushButton#navButton:hover {{
                background: {p.surface_alt_bg};
                border-color: {p.border};
            }}
            QPushButton#navButton:checked {{
                background: {p.accent};
                border-color: {p.accent};
                color: {p.accent_text};
            }}
            QPushButton#dangerButton {{
                color: {p.danger};
                border: 1px solid {p.danger};
                background: transparent;
            }}
            QPushButton#dangerButton:hover {{
                background: {p.surface_alt_bg};
                border-color: {p.danger};
            }}
            QPushButton#dangerButton:pressed {{
                background: {p.warning};
                color: {p.accent_text};
                border-color: {p.warning};
            }}
            QComboBox, QLineEdit, QPlainTextEdit {{
                background: {p.surface_bg};
                border: 1px solid {p.border};
                border-radius: 11px;
                color: {p.text};
                padding: 8px 34px 8px 11px;
                min-height: 38px;
                selection-background-color: {p.selection_bg};
                selection-color: {p.selection_text};
            }}
            QComboBox:hover, QLineEdit:hover, QPlainTextEdit:hover {{
                border-color: {p.muted};
            }}
            QComboBox:focus, QLineEdit:focus, QPlainTextEdit:focus {{
                border-color: {p.accent};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left: 1px solid {p.border};
                background: {p.surface_alt_bg};
                border-top-right-radius: 11px;
                border-bottom-right-radius: 11px;
            }}
            QComboBox::down-arrow {{
                width: 10px;
                height: 10px;
            }}
            QComboBox QAbstractItemView {{
                background: {p.surface_bg};
                color: {p.text};
                selection-background-color: {p.selection_bg};
                selection-color: {p.selection_text};
                border: 1px solid {p.border};
                border-radius: 10px;
                outline: 0;
                padding: 4px;
            }}
            QAbstractScrollArea, QScrollArea, QTableView {{
                background: {p.window_bg};
                border: none;
            }}
            QAbstractScrollArea QWidget, QScrollArea QWidget, QTableView QWidget {{
                background: {p.window_bg};
            }}
            QWidget#feedViewport, QWidget#cardGridWidget, QWidget#contentPanel {{
                background: {p.window_bg};
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 4px 2px 4px 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {p.border};
                min-height: 28px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {p.muted};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                height: 0px;
                background: transparent;
            }}
            QScrollBar:horizontal {{
                background: transparent;
                height: 10px;
                margin: 2px 4px 2px 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: {p.border};
                min-width: 28px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {p.muted};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                width: 0px;
                background: transparent;
            }}
            QTableWidget {{
                background: {p.surface_bg};
                color: {p.text};
                border: 1px solid {p.border};
                border-radius: 14px;
                gridline-color: {p.border};
                selection-background-color: {p.selection_bg};
                selection-color: {p.selection_text};
                alternate-background-color: {p.surface_alt_bg};
            }}
            QWidget#accountTableViewport {{
                background: {p.surface_bg};
            }}
            QWidget#accountActionCell {{
                background: transparent;
                border-bottom: 1px solid {p.border};
            }}
            QPushButton[accountAction="true"] {{
                min-height: 34px;
                padding: 5px 10px;
                border-radius: 9px;
            }}
            QTableWidget::item {{
                background: transparent;
                border: none;
                border-bottom: 1px solid {p.border};
                padding: 9px 10px;
            }}
            QTableWidget::item:selected,
            QTableWidget::item:selected:active,
            QTableWidget::item:selected:!active {{
                background: {p.selection_bg};
                color: {p.selection_text};
            }}
            QTableWidget::item:focus {{
                outline: none;
            }}
            QTableWidget::item:hover {{
                background: {p.surface_alt_bg};
            }}
            QHeaderView::section {{
                background: {p.surface_alt_bg};
                color: {p.muted};
                border: none;
                border-bottom: 1px solid {p.border};
                padding: 9px 10px;
                font-weight: 750;
            }}
            QDialog QLabel {{
                color: {p.text};
            }}
            QCheckBox {{
                color: {p.text};
                spacing: 8px;
                font-weight: 600;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 5px;
                border: 1px solid {p.border};
                background: {p.surface_bg};
            }}
            QCheckBox::indicator:hover {{
                border-color: {p.accent};
            }}
            QCheckBox::indicator:checked {{
                background: {p.accent};
                border-color: {p.accent};
            }}
            QMenuBar {{
                background: {p.sidebar_bg};
                color: {p.text};
            }}
            QMenuBar::item:selected {{
                background: {p.selection_bg};
            }}
            QMenu {{
                background: {p.surface_bg};
                color: {p.text};
                border: 1px solid {p.border};
                border-radius: 10px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 24px;
                border-radius: 7px;
            }}
            QMenu::item:selected {{
                background: {p.selection_bg};
                color: {p.selection_text};
            }}
            QToolTip {{
                background: {p.surface_bg};
                color: {p.text};
                border: 1px solid {p.border};
                border-radius: 8px;
                padding: 6px 8px;
            }}
            QStatusBar {{
                background: {p.window_bg};
                color: {p.muted};
                border-top: 1px solid {p.border};
            }}
            QProgressDialog {{
                background: {p.window_bg};
            }}
        """
