# BIGLOADEB / IG Post Controller Changelog

## 0.1.3 - 2026-07-13

### Added
- Automatic recovery to a safe per-user download folder when a saved drive or folder is unavailable.
- Organized and flat post-folder layout choices for future downloads.
- Bounded bulk reconnection for moved download folders using verified post metadata.
- Database backup before schema migration and archived-account handling for accounts with retained downloads.

### Improved
- Storage failures no longer stop the whole app; existing paths and download records remain unchanged.
- Account removal preserves downloaded files and their tracking records.
- Storage, account, download, and recovery actions use clearer Korean, English, Japanese, and Chinese labels.
- Optional Qt multimedia failures now disable video preview only instead of preventing app startup.
- Demo screenshots now use a distinct, sanitized online-feed example.

### Notes
- Existing downloaded folders are not moved automatically when the layout setting changes.
- The installer remains unsigned unless a code-signing certificate is configured separately.

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
