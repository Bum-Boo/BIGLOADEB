# BIGLOADEB Portfolio Case Study

## Problem

Content operations teams often need to review posts from multiple public accounts, save selected media, track what has already been downloaded, and hand off assets into other workflows. Doing that manually in a browser can be repetitive and error-prone, especially for older or non-technical users.

## Target Users

- Non-technical staff managing public Instagram account content.
- Small internal teams that need predictable local media folders.
- Operators who need account-first review rather than developer tooling.

## Design Goal

Turn a repeated content-collection process into a local Windows app with account rows, feed actions, downloaded-post cards, local folders, and SQLite tracking.

## Core Workflow

1. Register public Instagram profile URLs.
2. Review accounts from the account list.
3. Open a per-account feed or combined feed.
4. Preview post media and captions.
5. Download selected posts into account-based local folders.
6. Review downloaded posts later.
7. Mark posts as handled or remove local saved copies.

## Architecture Summary

The repository is a Python Windows desktop app with service layers for account management, image caching, downloads, SQLite storage, UI views, language/theme support, and regression tests around UI and workflow behavior.

## Safety / Privacy Decisions

- Public-account content only.
- No Instagram password storage.
- No upload/post automation.
- Local SQLite tracking and media folders stay on the user's machine.
- Public demos should avoid private accounts, private posts, client/customer data, staff notes, and claims of bypassing platform limits.

## Technical Highlights

- Account-first desktop workflow.
- Local SQLite-backed tracking.
- Account-based folder organization.
- Downloaded-post review UI.
- Language/theme support.
- Windows ZIP release asset.

## Current Limitations

- Public Instagram access can be rate-limited or blocked by Instagram.
- Stories, login/auth management, role permissions, auto-update, and upload automation are not part of the current scope.
- Best presented as internal-use or sanitized case-study material unless all sensitive assumptions are removed.

## Next Steps

- Keep safety/privacy scope near the top of README.
- Add sanitized case-study demo assets if real account data cannot be shown.
- Keep private/client data out of screenshots and release notes.
- Document validation commands before each public release.

## Portfolio Value

BIGLOADEB demonstrates internal tool design for non-technical users, content-operations workflow modeling, local media organization, desktop UI flow design, SQLite tracking, and honest limitation handling for platform-dependent behavior.
