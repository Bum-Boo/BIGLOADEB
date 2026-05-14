# BIGLOADEB

> Account-first Instagram post collection and local media management for Windows.

[Overview](../../README.md) | [English](README.en.md) | [한국어](README.ko.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md)

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
