from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ig_post_controller.config import APP_VERSION
from ig_post_controller.ui.dialogs import SettingsDialog
from ig_post_controller.ui.i18n import TRANSLATIONS, LanguageManager
from ig_post_controller.ui.theme import ThemeManager


class SettingsUpdateUiTests(unittest.TestCase):
    def test_all_languages_include_every_english_translation_key(self) -> None:
        english_keys = set(TRANSLATIONS["en"])

        for language in ("ko", "ja", "zh"):
            with self.subTest(language=language):
                self.assertEqual(set(TRANSLATIONS[language]), english_keys)

    def test_settings_dialog_shows_version_and_update_button(self) -> None:
        app = QApplication.instance() or QApplication([])
        self.assertIsNotNone(app)

        dialog = SettingsDialog("ko", "clean_light", LanguageManager("ko"), ThemeManager("clean_light"))

        self.assertIn(APP_VERSION, dialog.version_label.text())
        self.assertEqual(dialog.update_button.text(), "업데이트 확인")

    def test_settings_dialog_emits_update_check_requested(self) -> None:
        app = QApplication.instance() or QApplication([])
        self.assertIsNotNone(app)

        dialog = SettingsDialog("ko", "clean_light", LanguageManager("ko"), ThemeManager("clean_light"))
        seen: list[bool] = []
        dialog.update_check_requested.connect(lambda: seen.append(True))

        dialog.update_button.click()

        self.assertEqual(seen, [True])

    def test_settings_dialog_exposes_download_layout_choice(self) -> None:
        app = QApplication.instance() or QApplication([])
        self.assertIsNotNone(app)

        dialog = SettingsDialog(
            "ko",
            "clean_light",
            LanguageManager("ko"),
            ThemeManager("clean_light"),
            current_download_layout="flat",
        )

        self.assertEqual(dialog.selected_download_layout(), "flat")
        self.assertEqual(dialog.download_layout_label.text(), "파일 저장 방식")
        self.assertEqual(dialog.download_layout_combo.currentText(), "한 폴더에 모두 모으기")


if __name__ == "__main__":
    unittest.main()
