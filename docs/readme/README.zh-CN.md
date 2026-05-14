# BIGLOADEB

> Account-first Instagram post collection and local media management for Windows.

[Overview](../../README.md) | [English](README.en.md) | [한국어](README.ko.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md)

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
