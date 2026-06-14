from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ig_post_controller.services.update_service import UpdateService, compare_versions


class UpdateServiceTests(unittest.TestCase):
    def test_compare_versions_handles_release_and_prerelease(self) -> None:
        self.assertLess(compare_versions("0.1.0", "0.1.1"), 0)
        self.assertLess(compare_versions("0.1.0-rc1", "0.1.0"), 0)
        self.assertGreater(compare_versions("0.2.0", "0.1.9"), 0)
        self.assertEqual(compare_versions("0.1.0", "0.1.0"), 0)

    def test_check_for_update_parses_manifest_and_detects_newer_windows_installer(self) -> None:
        payload = {
            "version": "0.1.1",
            "channel": "stable",
            "release_notes_url": "https://example.test/releases/0.1.1",
            "windows": {
                "installer_url": "https://example.test/IGPostController-Setup-0.1.1.exe",
                "sha256": "abc123",
                "size": 1234,
            },
        }
        service = UpdateService("0.1.0", "https://example.test/update.json")

        with mock.patch.object(service, "_read_url_text", return_value=json.dumps(payload)):
            result = service.check_for_update()

        self.assertTrue(result.available)
        self.assertEqual(result.version, "0.1.1")
        self.assertEqual(result.asset.installer_url, "https://example.test/IGPostController-Setup-0.1.1.exe")
        self.assertEqual(result.asset.sha256, "abc123")

    def test_check_for_update_ignores_same_or_older_version(self) -> None:
        payload = {"version": "0.1.0", "windows": {"installer_url": "https://example.test/setup.exe"}}
        service = UpdateService("0.1.0", "https://example.test/update.json")

        with mock.patch.object(service, "_read_url_text", return_value=json.dumps(payload)):
            result = service.check_for_update()

        self.assertFalse(result.available)

    def test_download_installer_verifies_sha256(self) -> None:
        content = b"installer bytes"
        expected = hashlib.sha256(content).hexdigest().upper()
        service = UpdateService("0.1.0", "https://example.test/update.json")

        with tempfile.TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir) / "setup.exe"
            with mock.patch.object(service, "_download_url_bytes", return_value=content):
                output = service.download_installer("https://example.test/setup.exe", destination, expected)

            self.assertEqual(output, destination)
            self.assertEqual(destination.read_bytes(), content)

    def test_download_installer_rejects_hash_mismatch_and_removes_partial_file(self) -> None:
        service = UpdateService("0.1.0", "https://example.test/update.json")

        with tempfile.TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir) / "setup.exe"
            with mock.patch.object(service, "_download_url_bytes", return_value=b"bad"):
                with self.assertRaises(ValueError):
                    service.download_installer("https://example.test/setup.exe", destination, "00")

            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
