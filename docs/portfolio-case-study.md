# BIGLOADEB Portfolio Case Study

BIGLOADEB is a Windows desktop workflow tool for collecting, organizing, and reviewing public Instagram posts from multiple accounts. It is framed as an internal content-operations utility for non-technical staff, not as a public scraping product.

## Positioning

BIGLOADEB fits the portfolio theme of creative and content operations tooling. Its value is in the workflow design: account-first navigation, simple feed checking, local saved-post management, and predictable folders for staff who should not need to understand implementation details.

The public framing should stay conservative:

- internal workflow tool
- public-account post collection
- local organization and review
- non-technical staff usability
- clear platform and rate-limit limitations

## Problem

Content operations teams often need to review posts from multiple public accounts, save selected media, track what has already been downloaded, and hand off assets into other workflows. Doing that manually in a browser can be repetitive and error-prone, especially for older or non-technical users.

BIGLOADEB turns that process into a local Windows app with account rows, feed actions, downloaded-post cards, local folders, and SQLite tracking.

## Product Shape

The main workflow is account-first:

1. Register public Instagram profile URLs.
2. Review accounts from the account list.
3. Open a per-account feed or combined feed.
4. Preview post media and captions.
5. Download selected posts into account-based local folders.
6. Review downloaded posts later.
7. Mark posts as handled or remove local saved copies.

The app focuses on clear screens and predictable local storage rather than advanced automation.

## Safety and Publication Boundaries

This project should be presented carefully because it touches third-party platform content and potentially business/client workflows.

Public materials should avoid:

- private accounts
- private posts
- real client/customer data
- staff names or operational notes
- claims of bypassing Instagram limits
- upload automation or engagement automation framing

Public screenshots and demos should use sanitized accounts or synthetic examples.

## Implementation Notes

The repository is a Python Windows desktop app with service layers for account management, image caching, downloads, SQLite storage, UI views, language/theme support, and regression tests around UI and workflow behavior.

The app stores local data in user-controlled Windows locations and keeps downloaded media organized by account.

## Portfolio Value

BIGLOADEB demonstrates:

- internal tool design for non-technical users
- practical content-operations workflow modeling
- local data and media organization
- desktop UI flow design
- SQLite-backed tracking
- explicit limitation handling for platform-dependent behavior

## Next Steps

- Keep the public README focused on workflow, screenshots, and limitations.
- Add a sanitized case-study demo if real account data cannot be shown.
- Keep private/client data out of the repository and screenshots.
- Document exactly which commands validate the app before release.
- Consider whether public source or case-study-only visibility is the right long-term portfolio choice.
