$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --console `
  --debug=all `
  --name IGPostController-OnefileDebug `
  --distpath dist-debug-onefile `
  --workpath build-debug-onefile `
  --specpath build-debug-onefile `
  --collect-all PySide6 `
  --collect-all shiboken6 `
  --hidden-import PySide6.QtMultimedia `
  --hidden-import PySide6.QtMultimediaWidgets `
  ig_post_controller\main.py
