# Release Checklist

Use this checklist before publishing a GitHub Release.

## Code and Build

- [ ] Run the test suite
- [ ] Build the Windows release EXE
- [ ] Verify the EXE launches on a clean Windows machine or VM
- [ ] Confirm account add, feed open, download, redownload, and delete flows still work
- [ ] Confirm the selected language and theme persist after restart
- [ ] Confirm the downloaded-posts screen loads local data correctly
- [ ] Confirm no unwanted build artifacts are being committed

## Packaging

- [ ] Include `dist\\IGPostController.exe`
- [ ] Decide whether to ship a `.zip` archive or the raw EXE
- [ ] Include a short release notes file or GitHub release summary
- [ ] Confirm the release name matches the app version
- [ ] Confirm the release assets are clearly labeled for Windows

## Validation

- [ ] Check that the release uses the current version string from `ig_post_controller/version.py`
- [ ] Verify no machine-specific paths are present in the packaged app
- [ ] Verify local app data is written under `%LOCALAPPDATA%\\IGPostController`
- [ ] Verify downloaded media is written only to the configured download root
- [ ] Verify logs are created in the local app data folder

## Publish

- [ ] Tag the release in Git
- [ ] Attach the Windows asset(s) to the GitHub Release
- [ ] Publish release notes
- [ ] Announce the version to internal users

