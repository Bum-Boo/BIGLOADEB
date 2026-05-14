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
## Demo Walkthrough

실제 데모는 등록된 Instagram 계정을 선택하고, 피드 확인 후 로컬에 저장된 게시물 목록을 확인하는 흐름입니다.

1. `dist\IGPostController.exe`를 실행합니다.
2. 왼쪽에서 `계정`을 선택합니다.
3. 등록된 계정 행의 `피드` 버튼을 누릅니다.
4. 왼쪽에서 `다운로드된 게시물`을 선택합니다.
5. 저장된 게시물 카드에서 썸네일, 캡션, `다시 다운로드`, `삭제` 버튼을 확인합니다.

앱이 열리면 왼쪽 메뉴에서 `계정`을 선택합니다. 등록된 계정 행에 있는 `피드` 버튼을 눌러 계정별 게시물 확인을 시작합니다.

![Registered account list](docs/demo-screenshots/bigloadeb-use-01-account-list.png)

피드 확인 후에는 같은 계정 목록에서 최근 확인 시간과 실행 가능한 버튼 상태를 확인합니다.

![Feed check result](docs/demo-screenshots/bigloadeb-use-02-feed-result.png)

`다운로드된 게시물` 메뉴로 이동하면 저장된 게시물 카드가 나오며, 여기서 썸네일, 캡션, 다시 다운로드/삭제 버튼을 확인할 수 있습니다.

![Downloaded posts](docs/demo-screenshots/bigloadeb-use-03-downloaded-posts.png)
