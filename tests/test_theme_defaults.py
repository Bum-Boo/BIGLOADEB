from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ig_post_controller.config import (
    APP_THEME_SETTING_KEY,
    DEFAULT_APP_THEME,
    normalize_app_theme,
)
from ig_post_controller.database import Database
from ig_post_controller.main import _resolve_app_theme
from ig_post_controller.ui.dialogs import SettingsDialog
from ig_post_controller.ui.i18n import LanguageManager
from ig_post_controller.ui.theme import ThemeManager


class ThemeDefaultTests(unittest.TestCase):
    def test_normalize_app_theme_defaults_to_clean_light(self) -> None:
        self.assertEqual(normalize_app_theme(None), DEFAULT_APP_THEME)
        self.assertEqual(normalize_app_theme(""), DEFAULT_APP_THEME)
        self.assertEqual(normalize_app_theme("invalid"), DEFAULT_APP_THEME)
        self.assertEqual(normalize_app_theme("clean-light"), "clean_light")
        self.assertEqual(normalize_app_theme("soft dark slate"), "soft_dark_slate")
        self.assertEqual(normalize_app_theme("warm_paper"), "warm_paper")
        self.assertEqual(normalize_app_theme("neon-utility"), "neon_utility")
        self.assertEqual(normalize_app_theme("gquuuuuux-signal"), "gquuuuuux_signal")

    def test_resolve_app_theme_persists_default_when_missing_or_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")

            self.assertEqual(_resolve_app_theme(db), DEFAULT_APP_THEME)
            self.assertEqual(db.get_setting(APP_THEME_SETTING_KEY), DEFAULT_APP_THEME)

            db.set_setting(APP_THEME_SETTING_KEY, "dark")
            self.assertEqual(_resolve_app_theme(db), "soft_dark_slate")
            self.assertEqual(db.get_setting(APP_THEME_SETTING_KEY), "soft_dark_slate")

    def test_gquuuuuux_palette_is_dark_and_distinct(self) -> None:
        palette = ThemeManager("gquuuuuux_signal").palette()
        self.assertEqual(palette.window_bg, "#08112A")
        self.assertEqual(palette.sidebar_bg, "#101C3C")
        self.assertEqual(palette.surface_bg, "#16264A")
        self.assertEqual(palette.surface_alt_bg, "#1B2F5A")
        self.assertEqual(palette.card_bg, "#16264A")
        self.assertEqual(palette.border, "#243A63")
        self.assertEqual(palette.text, "#F4F7FB")
        self.assertEqual(palette.muted, "#A9B4C8")
        self.assertEqual(palette.accent, "#2B63D9")
        self.assertEqual(palette.selection_bg, "#2B63D9")
        self.assertEqual(palette.selection_text, "#FFFFFF")
        self.assertEqual(palette.danger, "#D94A4A")
        self.assertEqual(palette.warning, "#F2C84B")

    def test_settings_dialog_retranslates_label_rows_and_theme_names(self) -> None:
        app = QApplication.instance() or QApplication([])
        self.assertIsNotNone(app)

        translator = LanguageManager("ko")
        theme_manager = ThemeManager("gquuuuuux_signal")
        dialog = SettingsDialog("ko", "gquuuuuux_signal", translator, theme_manager)

        self.assertEqual(dialog.language_label.text(), translator.tr("settings.language"))
        self.assertEqual(dialog.theme_label.text(), translator.tr("settings.theme"))
        self.assertEqual(dialog.note_label.text(), translator.tr("settings.note"))

        ko_index = next(
            index for index in range(dialog.language_combo.count()) if dialog.language_combo.itemData(index) == "ko"
        )
        self.assertEqual(dialog.language_combo.itemText(ko_index), translator.tr("settings.language.ko"))
        self.assertEqual(dialog.theme_combo.currentData(), "gquuuuuux_signal")
        self.assertEqual(dialog.theme_combo.currentText(), translator.tr("settings.theme.gquuuuuux_signal"))

        translator.set_language("en")
        dialog.retranslate_ui()

        self.assertEqual(dialog.language_label.text(), "Language")
        self.assertEqual(dialog.theme_label.text(), "Theme")
        self.assertEqual(
            dialog.note_label.text(),
            "Choose the app language. The selection is saved and applied immediately.",
        )

        en_index = next(
            index for index in range(dialog.language_combo.count()) if dialog.language_combo.itemData(index) == "en"
        )
        self.assertEqual(dialog.language_combo.itemText(en_index), "English")
        self.assertEqual(dialog.theme_combo.currentText(), "GQuuuuuuX Signal")


if __name__ == "__main__":
    unittest.main()
