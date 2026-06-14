# BIGLOADEB / IG Post Controller Changelog

## 0.1.2 - 2026-06-15

### Added
- Windows release version metadata and update manifest support.
- In-app update check flow from Settings: check manifest, download installer, verify SHA256, launch installer, and close the app.
- Per-user Windows installer script for `%LOCALAPPDATA%\Programs\IGPostController`.
- Release build script that builds the app, creates the installer, computes SHA256, and writes `update.json`.

### Improved
- Download folder safety: moved/missing folders are detected and can be reconnected safely.
- Reconnect validation checks shortcode, post URL, and expected media files before changing stored paths.
- Safer delete messaging when folders are outside the current download root.
- Unified Windows/PySide design system: font stack, buttons, cards, input controls, tables, scrollbars, and status UI.

### Notes
- User data remains in `%LOCALAPPDATA%\IGPostController` and is not removed during app updates.
- The installer is currently unsigned unless a code-signing certificate is configured separately.
