$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$version = (py -3 -c "from ig_post_controller.config import APP_VERSION; print(APP_VERSION)").Trim()
if (-not $version) { throw "Could not resolve APP_VERSION" }

$issPath = Join-Path $root "installer\IGPostController.iss"
$issText = Get-Content $issPath -Raw
if ($issText -notmatch "#define MyAppVersion `"$([regex]::Escape($version))`"") {
  throw "installer\IGPostController.iss MyAppVersion does not match APP_VERSION=$version"
}

$isccCommand = Get-Command iscc.exe -ErrorAction SilentlyContinue
if (-not $isccCommand) { $isccCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue }
$isccPath = if ($isccCommand) { $isccCommand.Source } else { $null }
if (-not $isccPath) {
  foreach ($candidate in @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
  )) {
    if (Test-Path $candidate) { $isccPath = $candidate; break }
  }
}
if (-not $isccPath) {
  throw "Inno Setup 6 ISCC.exe was not found. Install it with: winget install --id JRSoftware.InnoSetup -e"
}

$releaseDir = Join-Path $root "release\$version"
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

Write-Host "Building PyInstaller onedir app for version $version..."
py -3 -m PyInstaller `
  --noconfirm `
  --clean `
  --onedir `
  --windowed `
  --name IGPostController `
  --icon assets\app_icon.ico `
  --add-data "assets\app_icon.png;assets" `
  --collect-all PySide6 `
  --collect-all shiboken6 `
  --hidden-import PySide6.QtMultimedia `
  --hidden-import PySide6.QtMultimediaWidgets `
  ig_post_controller\main.py

Write-Host "Building installer with Inno Setup..."
& $isccPath $issPath

$installerName = "IGPostController-Setup-$version.exe"
$installerPath = Join-Path $releaseDir $installerName
if (-not (Test-Path $installerPath)) {
  throw "Installer was not created: $installerPath"
}

$hash = (Get-FileHash $installerPath -Algorithm SHA256).Hash.ToUpperInvariant()
$size = (Get-Item $installerPath).Length
$downloadBase = "https://github.com/Bum-Boo/BIGLOADEB/releases/latest/download"
$manifest = [ordered]@{
  version = $version
  channel = "stable"
  release_notes_url = "https://github.com/Bum-Boo/BIGLOADEB/releases/tag/v$version"
  mandatory = $false
  windows = [ordered]@{
    installer_url = "$downloadBase/$installerName"
    sha256 = $hash
    size = $size
  }
}
$manifestPath = Join-Path $releaseDir "update.json"
$manifest | ConvertTo-Json -Depth 5 | Set-Content -Path $manifestPath -Encoding UTF8
$hash | Set-Content -Path (Join-Path $releaseDir "$installerName.sha256") -Encoding ASCII
Copy-Item -Force (Join-Path $root "CHANGELOG.md") (Join-Path $releaseDir "CHANGELOG.md")
Copy-Item -Force (Join-Path $root "docs\windows-release-checklist.md") (Join-Path $releaseDir "windows-release-checklist.md")

Write-Host "Release complete: $releaseDir"
Write-Host "Installer: $installerPath"
Write-Host "SHA256: $hash"
Write-Host "Manifest: $manifestPath"
