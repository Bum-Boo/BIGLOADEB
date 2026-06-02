$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

py -3 -m PyInstaller `
  --noconfirm `
  --clean `
  --onedir `
  --console `
  --debug=all `
  --name IGPostController-Debug `
  --icon assets\app_icon.ico `
  --add-data "assets\app_icon.png;assets" `
  --distpath dist-debug `
  --workpath build-debug `
  --specpath build-debug `
  --collect-all PySide6 `
  --collect-all shiboken6 `
  --hidden-import PySide6.QtMultimedia `
  --hidden-import PySide6.QtMultimediaWidgets `
  ig_post_controller\main.py
