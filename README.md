# UE PartyUp PC

Independent Windows desktop controller for Ultimate Ears PartyUp, with one main speaker and up to nine guests.

**Experimental Windows alpha candidate, version 0.7.5. Publication pending owner approval.** Two EVERBOOMs have been tested with PC audio and a Start → Stop → Start cycle in the earlier controller. The expanded ten-speaker workflow, new controls and older-speaker adapter have automated tests; physical acceptance remains model- and control-specific. The repository stays private until the owner approves publication. Not affiliated with Logitech or Ultimate Ears.

## Alpha support and known limits

Tested hardware: one pair of EVERBOOMs on Windows. Up to ten selected speakers are software-tested; larger physical groups and older BOOM/MEGABOOM models remain unverified. This is music grouping, not discrete surround sound.

- Guest reads/settings/EQ controls are disabled while the selected main reports active PartyUp or group state is unchecked. Stop PartyUp and use Check group to confirm it is off before these controls unlock. Stop the group explicitly before controlling a guest. A failed or malformed main-state check also blocks guest access.
- Remember PartyUp group controls are disabled while broadcasting or unchecked. Live changes previously interrupted playback; the underlying cause is unresolved.
- A missing receiver report is unknown membership, not proof that a guest is disconnected. Listen to confirm playback.
- Outdoor lookup can time out; stereo balance readback is undecoded. Wake, power-cycle persistence, actual sleep timing, channel acoustics and older models lack complete hardware acceptance.
- No measured audio/video delay correction is included. This unsigned alpha may prompt Windows security notices.
- No firmware update, factory reset, mobile streaming integration, alarm or megaphone implementation is included.

See [release checks](docs/RELEASE-AUDIT.md), [testing](docs/TESTING.md), [privacy](PRIVACY.md), and [third-party notices](THIRD_PARTY_NOTICES.md). Source is licensed under [MIT](LICENSE); dependencies and fonts retain their own licenses.

## Standalone Windows app

Version 0.7.5 includes a standalone Windows x64 folder bundle; Python is not needed on the receiving PC. Extract the complete private release ZIP and run Install Private.cmd to install for the current user, then open PartyUp PC from the Start menu. No admin rights, automatic startup, telemetry or automatic updates are used. The bundle is an unsigned private preview.

Settings live in `%LOCALAPPDATA%/PartyUpPC/data`; bounded redacted failure logs live in its `logs` folder. Versioned app files live under `%LOCALAPPDATA%/Programs/PartyUpPC`. Source and packaged launches share the same settings location and single-instance guard. On a source launch, missing settings are imported from the old project data directory without overwriting current files. The installer also accepts an explicit `--import-settings` directory for a local migration. User data is never bundled.

Help provides version/support limits and a local diagnostic summary with no speaker names or addresses. The app never uploads it. `--self-check --report <file>` verifies assets/dependency metadata without Bluetooth activity; `--smoke` constructs and closes the GUI without discovery or commands.

## Source setup and use

Requirements: Windows 10/11, Bluetooth Classic and BLE, Python 3.13 with tkinter. Pair every speaker separately in Windows. The PC needs an audio connection only to the main speaker; speakers distribute PartyUp audio themselves.

1. Run `Setup.cmd` once in a fresh checkout to install the pinned project dependencies (Bleak and Pillow).
2. Turn the speakers on and close the mobile UE app. If it retains the control connection, temporarily turn phone Bluetooth off.
3. Open `Open PartyUp.cmd`.
4. Choose your main audio speaker, then select up to nine guests.
5. Start the selected group and play Windows audio through the chosen main speaker.
6. Add or remove selected guests individually. Check status reads host configuration and receiver reports; these do not prove audible playback.
7. Stop ends host broadcasting and attempts to clear every selected guest. An unreachable guest is reported separately. Closing the idle app leaves audio playing.

Change the main speaker deliberately: stop the old group, choose the new main and guests, start the new group, then switch Windows audio output. Automatic migration and automatic Windows output switching are not implemented.

The launcher prefers an existing standalone build; otherwise it uses the checkout's .venv after Setup.cmd. Selection and remembered identities stay in the current user's local app data; the old project data directory remains ignored and is preserved after migration. Addresses are never included in committed diagnostic reports.

## Interface

Version 0.6.0 adds private standalone packaging/current-user installation, consistent saved-data paths, a single-instance guard, local crash logging and Help/support export. Driver-originated cancellation is reported per guest so remaining cleanup can continue; deliberate task cancellation is propagated. Corrupt EQ memory files are not silently overwritten on save. See [release audit](docs/RELEASE-AUDIT.md) for verified results and remaining acceptance.

Version 0.5.0 adds Quick tuning on Sound: Bass −/+, Undo, Reset changes, Read EQ and Save as. Each adjustment reads fresh speaker EQ, preserves the current preset for bass steps, sends one write, and requires exact readback. A stale reading refreshes the starting sound without writing. Uncertain results lock further EQ changes until an explicit successful read. The panel identifies the selected main/guest target and shows steps from the starting sound; it never changes volume or automatically copies EQ to other speakers. Existing sliders and mode-aware preset memories remain available. Factory-preset band changes are stored/read back on the tested pair; their audible effect is not established by readback alone.

Version 0.4.1 extends the House Party presentation to Sound and Settings: matching branding/navigation, speaker artwork, pixel headings, stepped action buttons and segmented sliders. Sound uses side-by-side volume/outdoor and EQ/memory panels. Every original action and feature gate remains available, including the Group, Speaker, PartyUp settings and Guide pages. Long content stays scrollable at smaller sizes. This is a presentation update with mocked verification; physical speaker/EQ tests remain deferred.

Version 0.4.0 implements the approved House Party direction: a detailed illustrated four-room night house, original peach/lavender speaker sprites, chunky stepped buttons, a speaker drawer, and a selected-speaker sidebar with volume and EQ controls. All ten selected speakers fit in the house. Room names and placement are local organizational choices, not sensed physical locations. Selecting or moving a speaker within the house uses cached data; Read explicitly refreshes controls. Dragging a drawer speaker into the house invokes the existing join action, and returning a guest to the drawer invokes removal. Start, Check and Stop remain pinned below the scene. Sound and Settings retain the complete detailed controls with a return-to-house button.

Artwork and the licensed Silkscreen font are bundled locally; Pillow renders the assets, and the font is registered privately for the process. There is no runtime generation, image service or animation loop. See [artwork provenance](docs/ART.md).

Version 0.3.0 added group-member shortcuts, host-targeted volume sync, 20 local named EQ memories and an in-app feature guide. Check PC output compares the default Windows multimedia endpoint with the selected speakers without changing audio settings. Remote wake remains a source-backed, opt-in modern EVERBOOM preview awaiting physical testing.


Version 0.2.1 adds a dark, dependency-free Tkinter control-desk theme with a prominent source-to-receiver overview, clear speaker-count and broadcast-state indicators, distinct Start/Stop button colors and a compact local diagnostics view. Each tab can scroll to reach its controls at smaller window sizes, while the four Group actions remain pinned above the activity log. Selecting a device does not assume it is online, and a broadcast-state result does not claim audible playback. All feature eligibility still comes from actual speaker replies.

Shared theme tokens live in `ue_partyup/theme.py`; the House Party view, layout and controls live in `house_view.py`, `house_layout.py` and `house_widgets.py`. Styling does not alter the Bluetooth protocol. See [UI design and review notes](docs/UI.md).

## Controls

The desktop has separate group, speaker, sound and PartyUp tabs. Opening Sound triggers a bounded, read-only check for volume and EQ on the selected supported speaker, without requiring a full settings scan. Drag and release the volume slider to send one level change (0–31 on modern CPP devices), then confirm the result by readback. Dragging a supported Custom EQ band selects the advertised Custom preset and applies on release; other EQ presets use Apply EQ. Unsupported or unconfirmed controls stay disabled. Use Read controls for other speaker settings and for manual retries. Available implementations include volume, battery readout, renaming, advertised EQ presets and five custom bands, outdoor mode, remote activation setting, power off, playback commands, persistent PartyUp, identification, group volume sync and source-backed channel assignment. Some model-specific units or readbacks remain unresolved and are labelled accordingly.

Older BOOM and MEGABOOM speakers use an explicitly enabled experimental adapter. Protocol and identity queries must succeed before writes. Basic legacy controls include name, 16/32-step volume, sticky/public PartyUp, battery announcement, power off, and group operations. Marketing names alone do not choose a protocol; BOOM 3 has both legacy and CPP revisions in the current app.

See [control coverage and limits](docs/CONTROLS.md), [model compatibility](docs/COMPATIBILITY.md), [protocol evidence](docs/PROTOCOL.md), and [acceptance results](docs/TESTING.md). A recovered command and an ACK are implementation evidence, not a hardware compatibility claim. Mobile streaming integrations, alarms, megaphone, and firmware updates remain unimplemented. Remote wake is an opt-in preview with no physical acceptance yet.

## Failure behavior

Bluetooth connection, send and receive operations are bounded. Requests use fresh correlated IDs, read-only retries and typed reply checks. Mutations are sent once; a missing reply leaves their result unknown. One failing guest does not stop the successfully joined guests. Stop continues through guest failures and separately checks whether the host is off.

The UI runs operations away from its main thread and reports progress for each guest. It does not perform grouping automatically at startup. The PC sends control messages, not duplicated Windows audio streams; this is synchronized multi-speaker music rather than discrete 5.1/7.1 surround audio.

## Development

Run `python -m unittest discover -s tests -v`. Tests mock speaker I/O and cover ten distinct members, invalid/duplicate selections, partial failures, individual removal, response correlation, legacy command validation, settings serialization and bounded transport cleanup. Run `python -m ue_partyup --smoke` to construct and close the UI without speaker commands.

No accounts, telemetry or cloud playback are required. Raw captures, phone bug reports, APKs, decompiled source, credentials and local selections are excluded. No public release until hardware acceptance and explicit owner approval.

## Private builds

Install requirements.txt and requirements-build.txt in a dedicated environment, or reproduce the pinned build environment from requirements-build.lock. Run Build Private.ps1 with that environment’s Python path. PartyUpPC.spec explicitly bundles artwork/font files and Windows Bluetooth modules while excluding local data, research and captures. Build outputs are ignored by Git. Packaging follows the official [PyInstaller documentation](https://pyinstaller.org/en/stable/usage.html).
