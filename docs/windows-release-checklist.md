# Windows Release Checklist

Use this checklist before publishing a BIGLOADEB / IG Post Controller Windows release.

## Build identity

- App version in `ig_post_controller/config.py` is updated.
- `installer/IGPostController.iss` uses the same version.
- Changelog and release notes mention the same version.
- Installer output name follows `IGPostController-Setup-<version>.exe`.

## Local gates

- Run full test suite from WSL:
  ```bash
  QT_QPA_PLATFORM=offscreen LD_LIBRARY_PATH=/tmp/bigloadeb-libs/usr/lib/x86_64-linux-gnu:/tmp/bigloadeb-libs/usr/lib/x86_64-linux-gnu/pulseaudio:${LD_LIBRARY_PATH:-} /tmp/bigloadeb-test-venv/bin/python -m unittest discover -s tests
  ```
- Run added-line security scan for secrets/shell/eval/SQL string formatting.
- Build Windows release:
  ```powershell
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_release.ps1
  ```
- Confirm `release\<version>\IGPostController-Setup-<version>.exe` exists.
- Confirm `release\<version>\update.json` exists and SHA256 matches the installer.

## Clean Windows smoke test

Use a clean Windows user profile or VM if possible.

1. Install `IGPostController-Setup-<version>.exe`.
2. Launch from Start Menu shortcut.
3. Confirm Korean text renders correctly.
4. Confirm startup log is created:
   `%LOCALAPPDATA%\IGPostController\logs\startup.log`
5. Add a public Instagram profile or verify that access-limit errors are shown without crashing.
6. Download one post into a test folder.
7. Move the folder, verify `폴더 없음/이동됨`, reconnect it, then delete the record.
8. Confirm user data remains under `%LOCALAPPDATA%\IGPostController` after reinstall/update.
9. Confirm uninstall removes app files but does not silently remove user downloads.

## Update publication

- Upload the installer and `update.json` to the release channel.
- For GitHub Releases, attach both:
  - `IGPostController-Setup-<version>.exe`
  - `update.json`
- The in-app updater checks:
  `https://github.com/Bum-Boo/BIGLOADER-with-Ai-agent/releases/latest/download/update.json`

## Signing

- If a code-signing certificate is available, sign the installer before publishing.
- If unsigned, clearly warn users that Windows SmartScreen may show an unknown publisher warning.

## Do not

- Do not delete `%LOCALAPPDATA%\IGPostController` during update.
- Do not change the Inno Setup `AppId` between versions.
- Do not publish a release if the installer hash in `update.json` does not match the uploaded file.
