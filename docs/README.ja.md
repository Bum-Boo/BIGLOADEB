# BIGLOADEB

> Windows 向けのアカウント中心 Instagram 投稿収集とローカルメディア管理ツール。

[English](../README.md) | [한국어](README.ko.md) | [日本語](README.ja.md) | [中文](README.zh-CN.md)

BIGLOADEB は、複数の business/client accounts から public Instagram posts を収集・管理するための Windows desktop app です。

年配または非技術 staff でも使えるように、シンプルな account-first workflow、明確な feeds、予測しやすい local folder organization を重視しています。

## Safety / Privacy Boundaries

- public または authorized content のみを対象にします。
- private access を迂回しません。
- password や credential を保存しません。
- media と metadata は local storage と SQLite に保存されます。
- upload/post automation は実装していません。
- public Instagram access は Instagram の policy、rate limit、session state によって制限されることがあります。
- 許可された目的とアカウントの公開 Instagram コンテンツにのみ使用してください。

## Features

- public Instagram profile URLs の手動登録。
- username と display name を持つ account list screen から開始。
- app launch 時に registered accounts の new posts を確認。
- combined online feed または per-account feed を表示。
- image-only / video-only posts で filter。
- date で sort。
- carousel support、caption copy、media preview を持つ post detail view。
- account-based local folders に posts を download。
- downloaded posts を SQLite で tracking。
- downloaded posts を `posted to cafe` として mark。
- local storage と local tracking から downloaded posts を delete。
- Settings で language と theme を切り替え。

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

1. この repository の GitHub Releases page を開きます。
2. latest Windows release asset をダウンロードします。
3. release が `.zip` として packaged されている場合は archive を展開します。
4. `IGPostController.exe` を実行します。

### User Data Locations

- App settings and local database: `%LOCALAPPDATA%\IGPostController`
- Thumbnail cache: `%LOCALAPPDATA%\IGPostController\thumb_cache`
- Default download root: `Documents\BIGLOADEB Downloads`

## Build a Release

```powershell
.\build.ps1
```

release executable は `dist\IGPostController.exe` に生成されます。

## Versioning

application version は `ig_post_controller/version.py` の `__version__` に保存されています。

## Known Limitations

- Public Instagram access は Instagram によって rate-limited または blocked されることがあります。
- stories、likes/comments counts、login/auth、role permissions、auto-update、upload automation はサポートしていません。
- Original-quality downloads は Instagram が公開する best public media variant に制限されます。
- ダウンロードする権限のある公開コンテンツにのみ使用してください。

## Demo Walkthrough

demo flow では registered Instagram account を選択し、feed を確認し、locally saved posts を review します。

1. `dist\IGPostController.exe` を実行します。
2. 左 navigation から `Accounts` を選択します。
3. 登録済みアカウント行の `投稿を見る` ボタンをクリックします。
4. 左 navigation から `Downloaded Posts` を選択します。
5. 保存済み投稿カードのサムネイル、キャプション、`ファイルを再ダウンロード`、`削除` を確認します。

アプリを開いたらアカウント一覧に移動します。アカウント行の `投稿を見る` ボタンをクリックして投稿の確認を始めます。

![Registered account list](demo-screenshots/bigloadeb-use-01-account-list.png)

feed check 後、同じ account list に latest check time と available action buttons が表示されます。

![Feed check result](demo-screenshots/bigloadeb-use-02-feed-result.png)

`Downloaded Posts` を開くと、thumbnail、caption、re-download/delete controls を含む saved post card を確認できます。

![Downloaded posts](demo-screenshots/bigloadeb-use-03-downloaded-posts.png)

## クレジット

フォーク、デモ、記事、派生物を公開する際は、[@Bum-Boo](https://github.com/Bum-Boo) と元のリポジトリへの言及をお願いします。これは礼儀としてのお願いであり、追加のライセンス条件や制限ではありません。
