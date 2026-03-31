$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name IGPostController `
  --collect-all PySide6 `
  --collect-all shiboken6 `
  --hidden-import PySide6.QtMultimedia `
  --hidden-import PySide6.QtMultimediaWidgets `
  ig_post_controller\main.py
