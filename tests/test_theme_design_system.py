from __future__ import annotations

import unittest

from ig_post_controller.ui.theme import ThemeManager


class ThemeDesignSystemTests(unittest.TestCase):
    def test_stylesheet_uses_unified_font_stack_and_typographic_scale(self) -> None:
        stylesheet = ThemeManager("clean_light").stylesheet()

        self.assertIn('font-family: "Malgun Gothic", "맑은 고딕", "Segoe UI", "Noto Sans KR", "Apple SD Gothic Neo", Arial, sans-serif;', stylesheet)
        self.assertIn("font-size: 14px;", stylesheet)
        self.assertIn("QLabel#appTitleLabel", stylesheet)
        self.assertIn("font-size: 24px;", stylesheet)
        self.assertIn("letter-spacing: -0.4px;", stylesheet)

    def test_stylesheet_has_polished_component_states(self) -> None:
        stylesheet = ThemeManager("clean_light").stylesheet()

        self.assertIn("QPushButton:disabled", stylesheet)
        self.assertIn("QPushButton#primaryButton", stylesheet)
        self.assertIn("QPushButton#dangerButton:pressed", stylesheet)
        self.assertIn("QToolTip", stylesheet)
        self.assertIn("QStatusBar", stylesheet)

    def test_stylesheet_has_consistent_surface_and_card_rhythm(self) -> None:
        stylesheet = ThemeManager("clean_light").stylesheet()

        self.assertIn("border-radius: 16px;", stylesheet)
        self.assertIn("padding: 10px 14px;", stylesheet)
        self.assertIn("QFrame#postCard:hover", stylesheet)
        self.assertIn("QLabel#cardStatusLabel", stylesheet)
        self.assertIn("QFrame#settingsPanel", stylesheet)


if __name__ == "__main__":
    unittest.main()
