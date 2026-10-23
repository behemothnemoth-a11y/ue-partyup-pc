# Alpha candidate release checks — 0.7.2

Prepared 2026-10-23. Publication requires explicit owner approval. Repository remains private. No public release or tag has been created.

## Passed

- 201 automated tests, including interface callback/result handling for both guard failures: clear error status, busy state released, main selection still usable, cached persistent setting unchanged.
- Standalone asset/dependency check and UI smoke; current-user installation and live 0.7.1 appearance/playback owner-approved; 0.7.2 live review pending.
- Isolated empty LOCALAPPDATA/APPDATA test: self-check, smoke, install and installed smoke exit0; shortcut created; no imported speaker settings. Existing user data untouched. This is the same Windows host, not a second machine/account.
- Current source and 159 unique historical Git blobs scanned for common credential formats, personal project paths and exact current selected speaker identifiers: no matches. This is a bounded scan, not proof of absence of all private information.
- MIT selected by owner; LICENSE and third-party notices included, including Python, Tk, Silkscreen, PyWinRT and pinned dependency license files.
- Fresh exact-pin dependency advisory check: no known vulnerabilities. See private session evidence for audit output; advisory coverage is not proof of security.
- Active-main live guards: persistent toggle blocked before setter; guest access blocked before guest transport. Owner confirmed uninterrupted playback after each.

## Pending before owner approval

- Guest guard owner-visible message/recovery passed in 0.7.1 with uninterrupted playback. Persistent-group visible rejection and checkbox restoration pending in 0.7.2.
- Final local archive manifest verification and current acceptance notes before approval.
- Fresh installation on a second Windows machine is not established. Candidate is unsigned. These must stay explicit alpha limitations.

## Restricted and unverified

Direct guest reads and persistent toggles during active PartyUp caused audio interruptions. 0.7.2 blocks those operations; underlying causes remain unresolved. Main receiver reports may be absent. Only the tested EVERBOOM pair is hardware-accepted. Ten physical speakers, older models, full preview control coverage, actual sleep/wake/power-cycle persistence and acoustic channel behavior are not accepted.

## Distribution

`tools/package_alpha.py --output <local-folder>` packages the built app with docs/notices, source commit, per-file SHA256 manifest and external ZIP checksum. It does not publish anything. Extract the entire ZIP; run Install Private.cmd. Installation refuses to overwrite an existing version. Keep an older installed version for manual rollback; settings are shared across versions. Never include raw diagnostics, APKs, captures, user-data files or credentials in an issue or release.

