# UE PartyUp PC

Independent Windows desktop controller for Ultimate Ears PartyUp, with one main speaker and up to nine guests.

**Private preview, version 0.2.1.** Two EVERBOOMs have been tested with PC audio and a Start → Stop → Start cycle in the earlier controller. The expanded ten-speaker workflow, new controls and older-speaker adapter have automated tests; physical acceptance remains model- and control-specific. The repository stays private until the owner approves publication. Not affiliated with Logitech or Ultimate Ears.

## Use

Requirements: Windows 10/11, Bluetooth Classic and BLE, Python 3.13 with tkinter. Pair every speaker separately in Windows. The PC needs an audio connection only to the main speaker; speakers distribute PartyUp audio themselves.

1. Run `Setup.cmd` once in a fresh checkout to install the pinned project dependency.
2. Turn the speakers on and close the mobile UE app. If it retains the control connection, temporarily turn phone Bluetooth off.
3. Open `Open PartyUp.cmd`.
4. Choose your main audio speaker, then select up to nine guests.
5. Start the selected group and play Windows audio through the chosen main speaker.
6. Add or remove selected guests individually. Check status reads host configuration and receiver reports; these do not prove audible playback.
7. Stop ends host broadcasting and attempts to clear every selected guest. An unreachable guest is reported separately. Closing the idle app leaves audio playing.

Change the main speaker deliberately: stop the old group, choose the new main and guests, start the new group, then switch Windows audio output. Automatic migration and automatic Windows output switching are not implemented.

The original development launcher can reuse the approved local Bluetooth environment. A fresh clone uses Setup.cmd. Selection and remembered identities are saved under ignored `data/`; addresses are never included in project documentation or committed diagnostic reports.

## Interface

Version 0.2.1 adds a dark, dependency-free Tkinter control-desk theme with a prominent source-to-receiver overview, clear speaker-count and broadcast-state indicators, distinct Start/Stop button colors and a compact local diagnostics view. Each tab can scroll to reach its controls at smaller window sizes, while the four Group actions remain pinned above the activity log. Selecting a device does not assume it is online, and a broadcast-state result does not claim audible playback. All feature eligibility still comes from actual speaker replies.

All UI styling lives in `ue_partyup/theme.py` and can be changed without altering the Bluetooth protocol. See [UI design and review notes](docs/UI.md).

## Controls

The desktop has separate group, speaker, sound and PartyUp tabs. Read a speaker's controls first; supported features enable the corresponding controls. Available implementations include volume, battery readout, renaming, advertised EQ presets and five custom bands, outdoor mode, remote activation setting, power off, playback commands, persistent PartyUp, identification, group volume sync and source-backed channel assignment. Some model-specific units or readbacks remain unresolved and are labelled accordingly.

Older BOOM and MEGABOOM speakers use an explicitly enabled experimental adapter. Protocol and identity queries must succeed before writes. Basic legacy controls include name, 16/32-step volume, sticky/public PartyUp, battery announcement, power off, and group operations. Marketing names alone do not choose a protocol; BOOM 3 has both legacy and CPP revisions in the current app.

See [control coverage and limits](docs/CONTROLS.md), [model compatibility](docs/COMPATIBILITY.md), [protocol evidence](docs/PROTOCOL.md), and [acceptance results](docs/TESTING.md). A recovered command and an ACK are implementation evidence, not a hardware compatibility claim. Mobile streaming integrations, alarms, megaphone, firmware updates and remote waking are not completed by this preview.

## Failure behavior

Bluetooth connection, send and receive operations are bounded. Requests use fresh correlated IDs, read-only retries and typed reply checks. Mutations are sent once; a missing reply leaves their result unknown. One failing guest does not stop the successfully joined guests. Stop continues through guest failures and separately checks whether the host is off.

The UI runs operations away from its main thread and reports progress for each guest. It does not perform grouping automatically at startup. The PC sends control messages, not duplicated Windows audio streams; this is synchronized multi-speaker music rather than discrete 5.1/7.1 surround audio.

## Development

Run `python -m unittest discover -s tests -v`. Tests mock speaker I/O and cover ten distinct members, invalid/duplicate selections, partial failures, individual removal, response correlation, legacy command validation, settings serialization and bounded transport cleanup. Run `python -m ue_partyup --smoke` to construct and close the UI without speaker commands.

No accounts, telemetry or cloud playback are required. Raw captures, phone bug reports, APKs, decompiled source, credentials and local selections are excluded. No public release until hardware acceptance and explicit owner approval.
