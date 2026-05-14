# BIGLOADEB

> Account-first Instagram post collection and local media management for Windows.

[English](#english) | [한국어](#한국어) | [中文](#中文) | [日本語](#日本語)

| Area | Detail |
|---|---|
| Platform | Windows desktop |
| Main user | Non-technical staff managing public Instagram account content |
| Storage | Local SQLite database and account-based download folders |
| Current scope | Internal-use collector, feed checker, and downloaded-post manager |

## English

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

---

## 한국어

BIGLOADEB는 여러 비즈니스/클라이언트 Instagram 공개 계정의 게시물을 수집하고 로컬에서 관리하는 Windows 전용 데스크톱 앱입니다.

비개발자도 계정 목록에서 시작해 피드를 확인하고, 다운로드된 게시물을 로컬 폴더 구조로 관리할 수 있도록 단순한 흐름에 맞춰져 있습니다.

### 주요 기능

- Instagram 공개 프로필 URL 직접 등록
- 계정별 피드 확인과 통합 피드 확인
- 이미지/동영상 게시물 필터링
- 게시물 상세 화면에서 캐러셀, 캡션 복사, 미디어 미리보기 확인
- 계정별 로컬 폴더로 게시물 다운로드
- SQLite로 다운로드 기록 관리
- 다운로드된 게시물의 재다운로드/삭제 관리
- 설정에서 언어와 테마 전환

### 실행

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m ig_post_controller
```

### 데모 흐름

1. `dist\IGPostController.exe`를 실행합니다.
2. 왼쪽 메뉴에서 `계정`을 선택합니다.
3. 등록된 계정 행의 `피드` 버튼을 누릅니다.
4. 왼쪽 메뉴에서 `다운로드된 게시물`을 선택합니다.
5. 저장된 게시물 카드에서 썸네일, 캡션, 다시 다운로드, 삭제 동작을 확인합니다.

데모 스크린샷은 위 English 섹션의 같은 화면 흐름을 참고하면 됩니다.

---

## 中文

BIGLOADEB 是一款 Windows 桌面应用，用于收集和管理多个业务或客户 Instagram 公开账号的帖子。

它面向非技术人员，采用以账号为起点的简单流程：选择账号、检查 Feed、再管理已下载的本地帖子。

### 主要功能

- 手动注册 Instagram 公开 Profile URL
- 查看账号列表、单账号 Feed 和合并 Feed
- 按图片或视频帖子筛选
- 在详情页查看轮播、复制文案并预览媒体
- 按账号保存到本地文件夹
- 使用 SQLite 跟踪下载记录
- 管理已下载帖子的重新下载和删除
- 在设置中切换语言和主题

### 运行

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m ig_post_controller
```

### 演示流程

1. 运行 `dist\IGPostController.exe`。
2. 在左侧导航中选择 `Accounts`。
3. 点击已注册账号行中的 `Feed` 按钮。
4. 在左侧导航中选择 `Downloaded Posts`。
5. 在已保存帖子卡片中查看缩略图、文案、重新下载和删除操作。

演示截图与 English 部分中的画面流程相同。

---

## 日本語

BIGLOADEB は、複数のビジネス/クライアント用 Instagram 公開アカウントの投稿を収集し、ローカルで管理する Windows デスクトップアプリです。

非エンジニアでも使いやすいように、アカウント一覧から Feed を確認し、ダウンロード済み投稿を管理する流れを中心にしています。

### 主な機能

- Instagram 公開 Profile URL の手動登録
- アカウント別 Feed と統合 Feed の確認
- 画像のみ/動画のみの投稿フィルタ
- 詳細画面でのカルーセル、キャプションコピー、メディアプレビュー
- アカウント別ローカルフォルダへの投稿ダウンロード
- SQLite によるダウンロード履歴管理
- ダウンロード済み投稿の再ダウンロード/削除
- 設定からの言語とテーマ切り替え

### 実行

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m ig_post_controller
```

### デモ手順

1. `dist\IGPostController.exe` を実行します。
2. 左側ナビゲーションで `Accounts` を選択します。
3. 登録済みアカウント行の `Feed` ボタンをクリックします。
4. 左側ナビゲーションで `Downloaded Posts` を選択します。
5. 保存済み投稿カードで、サムネイル、キャプション、再ダウンロード、削除操作を確認します。

デモ画像は English セクションの同じ画面フローを参照してください。
