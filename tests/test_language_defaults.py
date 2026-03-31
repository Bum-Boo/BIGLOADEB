from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ig_post_controller.config import (
    APP_LANGUAGE_SETTING_KEY,
    DEFAULT_APP_LANGUAGE,
    normalize_app_language,
)
from ig_post_controller.database import Database
from ig_post_controller.main import _resolve_app_language


class LanguageDefaultTests(unittest.TestCase):
    def test_normalize_app_language_defaults_to_ko(self) -> None:
        self.assertEqual(normalize_app_language(None), DEFAULT_APP_LANGUAGE)
        self.assertEqual(normalize_app_language(""), DEFAULT_APP_LANGUAGE)
        self.assertEqual(normalize_app_language("invalid"), DEFAULT_APP_LANGUAGE)
        self.assertEqual(normalize_app_language("ko-KR"), "ko")
        self.assertEqual(normalize_app_language("en-US"), "en")
        self.assertEqual(normalize_app_language("ja-JP"), "ja")
        self.assertEqual(normalize_app_language("zh-CN"), "zh")
        self.assertEqual(normalize_app_language("english"), "en")
        self.assertEqual(normalize_app_language("korean"), "ko")

    def test_resolve_app_language_persists_default_when_missing_or_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")

            self.assertEqual(_resolve_app_language(db), DEFAULT_APP_LANGUAGE)
            self.assertEqual(db.get_setting(APP_LANGUAGE_SETTING_KEY), DEFAULT_APP_LANGUAGE)

            db.set_setting(APP_LANGUAGE_SETTING_KEY, "fr")
            self.assertEqual(_resolve_app_language(db), DEFAULT_APP_LANGUAGE)
            self.assertEqual(db.get_setting(APP_LANGUAGE_SETTING_KEY), DEFAULT_APP_LANGUAGE)

            db.set_setting(APP_LANGUAGE_SETTING_KEY, "en-US")
            self.assertEqual(_resolve_app_language(db), "en")
            self.assertEqual(db.get_setting(APP_LANGUAGE_SETTING_KEY), "en")


if __name__ == "__main__":
    unittest.main()
