# BIGLOADEB

BIGLOADEB is a Windows-only internal desktop app for collecting and managing public Instagram posts from multiple business/client accounts.

It is designed for older, non-technical staff and focuses on a simple account-first workflow, clear feeds, and predictable local folder organization.

## Features

- Register public Instagram profile URLs manually
- Start on an account list screen with username and display name
- Check registered accounts for new posts on app launch
- View a combined online feed or a per-account feed
- Filter by image-only or video-only posts
- Sort by date
- Open a post detail view with carousel support, caption copy, and media preview
- Download posts into account-based local folders
- Track downloaded posts in SQLite
- Mark downloaded posts as `posted to cafe`
- Delete downloaded posts from local storage and local tracking
- Switch language and theme from Settings

## Project Layout

- `ig_post_controller/` - app source code
- `tests/` - regression and smoke tests
- `build.ps1` - Windows release build script
- `build_debug.ps1` - console debug build
- `build_debug_onefile.ps1` - console one-file debug build
- `IGPostController.spec` - PyInstaller spec file

## Development Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run in Dev Mode

```powershell
python -m ig_post_controller
```

## Windows Release

### Download

1. Open the GitHub Releases page for this repository.
2. Download the latest Windows release asset.
3. Extract the archive if the release is packaged as a `.zip`.
4. Run `IGPostController.exe`.

### User Data Locations

- App settings and local database: `%LOCALAPPDATA%\IGPostController`
- Thumbnail cache: `%LOCALAPPDATA%\IGPostController\thumb_cache`
- Default download root: `Documents\IG Post Controller Downloads`

## Build a Release

```powershell
.\build.ps1
```

The release executable is produced under `dist\IGPostController.exe`.

## Versioning

The application version is stored in `ig_post_controller/version.py` as `__version__`.

## Known Limitations

- Public Instagram access can be rate-limited or blocked by Instagram.
- The app does not support stories, likes/comments counts, login/auth, role permissions, auto-update, or upload automation.
- Original-quality downloads are limited to the best public media variant Instagram exposes.
- The app is intended for internal use only.

