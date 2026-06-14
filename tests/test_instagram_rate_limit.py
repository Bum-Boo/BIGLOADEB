from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import requests

from ig_post_controller.database import Database
from ig_post_controller.services.account_service import AccountService
from ig_post_controller.services.instagram_service import (
    InstagramAccessError,
    InstagramRateLimitError,
    InstagramService,
)


def make_response(status_code: int, *, url: str = "https://www.instagram.com/client/", text: str = "") -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response.url = url
    response._content = text.encode("utf-8")
    response.encoding = "utf-8"
    response.request = requests.Request("GET", url).prepare()
    return response


class InstagramAccessLimitTests(unittest.TestCase):
    def make_service(self) -> InstagramService:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        database = Database(Path(tmpdir.name) / "test.db")
        account_service = AccountService(database)
        return InstagramService(database, account_service)

    def test_feed_401_is_instagram_access_error(self) -> None:
        service = self.make_service()
        response = make_response(
            401,
            url="https://www.instagram.com/api/v1/feed/user/katarinabluu/username/?count=12",
        )

        with self.assertRaises(InstagramAccessError):
            service._raise_for_status(response)

    def test_feed_429_is_rate_limit_access_error(self) -> None:
        service = self.make_service()
        response = make_response(429, url="https://www.instagram.com/client/")

        with self.assertRaises(InstagramRateLimitError):
            service._raise_for_status(response)

    def test_login_redirect_is_instagram_access_error(self) -> None:
        service = self.make_service()
        response = make_response(
            200,
            url="https://www.instagram.com/accounts/login/?next=/client/",
            text="<html>login</html>",
        )

        with self.assertRaises(InstagramAccessError):
            service._raise_for_status(response)

    def test_resolve_profile_falls_back_when_profile_page_is_limited(self) -> None:
        service = self.make_service()
        with mock.patch.object(service, "_fetch_profile_page", return_value=make_response(429)):
            profile = service.resolve_profile("https://www.instagram.com/katarinabluu/")

        self.assertEqual(profile["username"], "katarinabluu")
        self.assertEqual(profile["display_name"], "katarinabluu")
        self.assertEqual(profile["profile_url"], "https://www.instagram.com/katarinabluu/")

    def test_resolve_profile_uses_html_display_name_when_feed_is_limited(self) -> None:
        service = self.make_service()
        html = '<meta property="og:title" content="Katarina Blue (@katarinabluu) • Instagram photos and videos">'
        with mock.patch.object(service, "_fetch_profile_page", return_value=make_response(200, text=html)):
            with mock.patch.object(service, "_fetch_feed_items", side_effect=InstagramAccessError("limited")):
                profile = service.resolve_profile("katarinabluu")

        self.assertEqual(profile["username"], "katarinabluu")
        self.assertEqual(profile["display_name"], "Katarina Blue")

    def test_refresh_all_skips_access_limited_account(self) -> None:
        service = self.make_service()
        service.account_service.save_account(
            profile_url="https://www.instagram.com/katarinabluu/",
            username="katarinabluu",
            display_name="Katarina Blue",
            company_name="Katarina Blue",
        )
        with mock.patch.object(service, "_sync_account", side_effect=InstagramAccessError("limited")):
            posts = service.refresh_all_accounts()

        self.assertEqual(posts, [])


if __name__ == "__main__":
    unittest.main()
