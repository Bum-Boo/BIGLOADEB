# BIGLOADEB

> Account-first Instagram post collection and local media management for Windows.

[Overview](README.md) | [English](docs/readme/README.en.md) | [한국어](docs/readme/README.ko.md) | [中文](docs/readme/README.zh-CN.md) | [日本語](docs/readme/README.ja.md)

| Area | Detail |
|---|---|
| Platform | Windows desktop |
| Main user | Non-technical staff managing public Instagram account content |
| Storage | Local SQLite database and account-based download folders |
| Current scope | Internal-use collector, feed checker, and downloaded-post manager |

## Preview

The account-first screen is the main entry point for checking feeds and downloaded posts.

![Registered account list](docs/demo-screenshots/bigloadeb-use-01-account-list.png)

<details>
<summary>View full demo walkthrough</summary>

The demo flow selects a registered Instagram account, checks its feed, then reviews the posts saved locally.

1. Run `dist\IGPostController.exe`.
2. Select `Accounts` from the left navigation.
3. Click the `Feed` button on a registered account row.
4. Select `Downloaded Posts` from the left navigation.
5. Check the saved post card for its thumbnail, caption, `Download again`, and `Delete` actions.

When the app opens, go to the account list. Click the `Feed` button on the account row to start checking posts for that account.

![Registered account list](docs/demo-screenshots/bigloadeb-use-01-account-list.png)

After the feed check, the same account list shows the latest check time and the available action buttons.

![Feed check result](docs/demo-screenshots/bigloadeb-use-02-feed-result.png)

Open `Downloaded Posts` to review the saved post card, including its thumbnail, caption, and re-download/delete controls.

![Downloaded posts](docs/demo-screenshots/bigloadeb-use-03-downloaded-posts.png)

</details>

## Quick Start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m ig_post_controller
```

## Documentation

- [English README](docs/readme/README.en.md)
- [한국어 README](docs/readme/README.ko.md)
- [中文 README](docs/readme/README.zh-CN.md)
- [日本語 README](docs/readme/README.ja.md)

## Notes

This overview is intentionally short. Detailed setup, architecture, limitations, and localized walkthroughs live in the linked README files.
