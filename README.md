# BIGLOADEB

> Account-first Instagram post collection and local media management for Windows.

[Overview](README.md) | [English](docs/readme/README.en.md) | [Korean](docs/readme/README.ko.md) | [Chinese](docs/readme/README.zh-CN.md) | [Japanese](docs/readme/README.ja.md)

| Area | Detail |
|---|---|
| Platform | Windows desktop |
| Main user | Non-technical staff managing public Instagram account content |
| Storage | Local SQLite database and account-based download folders |
| Current scope | Internal-use collector, feed checker, and downloaded-post manager |

## Safety / Privacy Scope

- Works with public Instagram account content only; do not use it for private, unauthorized, or client-sensitive data.
- Stores app settings, SQLite tracking data, thumbnails, and downloaded media locally on the user's Windows machine.
- Does not store Instagram passwords.
- Does not implement upload/post automation.
- Public demos and screenshots should use sanitized accounts and captions.
- Platform access can be rate-limited or blocked by Instagram; the tool does not claim to bypass platform limits.

## Download / Release

Latest release: [BIGLOADEB v0.1.1](https://github.com/Bum-Boo/BIGLOADEB/releases/tag/v0.1.1)

Windows ZIP:

- [BIGLOADEB-win64.zip](https://github.com/Bum-Boo/BIGLOADEB/releases/download/v0.1.1/BIGLOADEB-win64.zip)

Release artifacts should be distributed through GitHub Releases, not committed into the source tree.

## Preview

The account-first screen is the main entry point for checking feeds and downloaded posts.

![Registered account list](docs/demo-screenshots/bigloadeb-use-01-account-list.png)

<details>
<summary>View demo walkthrough</summary>

1. Run `dist\IGPostController.exe`.
2. Select `Accounts` from the left navigation.
3. Click the `Feed` button on a registered account row.
4. Select `Downloaded Posts` from the left navigation.
5. Check the saved post card for its thumbnail, caption, `Download again`, and `Delete` actions.

![Feed check result](docs/demo-screenshots/bigloadeb-use-02-feed-result.png)

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
- [Korean README](docs/readme/README.ko.md)
- [Chinese README](docs/readme/README.zh-CN.md)
- [Japanese README](docs/readme/README.ja.md)
- [Portfolio case study](docs/portfolio-case-study.md)
- [GitHub metadata note](docs/github-metadata.md)

## Status

BIGLOADEB is best presented as an internal workflow/case-study project unless all account details, private posts, client references, and staff workflow data are sanitized.
