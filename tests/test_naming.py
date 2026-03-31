import unittest
from datetime import datetime

from ig_post_controller.utils.text import build_default_download_title, caption_snippet, sanitize_for_path


class NamingRuleTests(unittest.TestCase):
    def test_caption_snippet_truncates_long_text(self) -> None:
        self.assertEqual(caption_snippet("abcdefghijklmnopqrstuvwxyz", limit=15), "abcdefghijklmno..")

    def test_build_default_download_title_uses_date_prefix(self) -> None:
        title = build_default_download_title(datetime(2026, 3, 31), "Spring collection launch")
        self.assertTrue(title.startswith("2026-03-31_"))

    def test_sanitize_for_path_removes_windows_invalid_chars(self) -> None:
        self.assertEqual(sanitize_for_path('Bad:/\\\\Name*?"'), "BadName")

    def test_sanitize_for_path_truncates_long_names_safely(self) -> None:
        value = sanitize_for_path("a" * 100, max_length=20)
        self.assertEqual(len(value), 20)
        self.assertTrue(value.endswith(".."))

    def test_sanitize_for_path_avoids_reserved_windows_names(self) -> None:
        self.assertEqual(sanitize_for_path("CON"), "CON_")


if __name__ == "__main__":
    unittest.main()
