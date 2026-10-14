# Pre-release acceptance

## Verified before refactor

- Windows serial connections to both EVERBOOMs.
- Recovered current framing checksum matched 62 complete captured outgoing packets.
- Initialization, name and host-state queries replied on the tested host.
- Host broadcast enable acknowledged; guest BLE join write accepted; host reported matching guest.
- User confirmed both speakers played laptop audio with phone Bluetooth disabled.

## Required on the refactored app

- [ ] Speaker selectors distinguish both speakers and reject duplicate selections.
- [ ] Start from an ungrouped state; confirm both speakers play.
- [ ] Stop; confirm guest stops receiving host audio and host mode is off.
- [ ] Restart; confirm both play again.
- [ ] Swap host/guest selection and Windows audio output; confirm both play.
- [ ] Power off guest; verify failure messaging and host restoration behavior.
- [ ] Power off host; verify timeout messaging and UI remains responsive.
- [ ] Phone holds control connection; verify useful failure message.
- [ ] Closing idle app leaves active audio group intact.
- [ ] Relaunch remembers selection.
- [ ] Fresh Windows checkout installs and launches successfully.
- [ ] Raw captures, reports, device addresses and unrelated diagnostics absent from tracked files.

Automated tests do not prove hardware support. Stop, rollback, selector persistence and new UI are not marked verified until exercised. No firmware updates or resets are part of acceptance.

Publication requires explicit owner approval. Initial compatibility must be advertised as EVERBOOM only.

## REA-guided repair, version 0.1.1

The owner's current installed APK was copied locally through authorized ADB. REA/JADX analysis identified the actual three-byte framing length and fresh 1–15 software request IDs. The repaired controller has regression tests for fragmented/multiple replies, high length bits, nonzero device IDs, request-ID rollover and sequential workflow IDs.

Hardware controller cycle completed successfully on the selected pair:

| Action | Verified result |
|---|---|
| Start | Matching guest receiver reported; host state 3 |
| Stop | Guest clear write accepted; host state 0 read back |
| Restart | Matching guest receiver reported; host state 3 |
| Playback after restart | Owner confirmed both speakers play |

This cycle used the same controller called by the GUI, through direct local execution. It does not certify the reloaded GUI buttons or swapped-host behavior. Audible silence of the guest during Stop was not separately confirmed by the owner. Twelve automated tests pass. Group left enabled at completion.

## 2026-10-14 interface test

Native window and speaker selectors were exercised. The default non-host selection produced connection failures. On the original host, an early state query failed before Stop sent any group mutation. Stop/restart audible acceptance remains open.

Bounded connection and initialization retries added; eight regression tests pass. A subsequent direct call to the refactored Start controller completed and reported the matching guest. This verifies the controller path, not the complete UI stop/restart cycle. Actual audio after this recovery still needs user confirmation.

## 2026-10-14 expanded v0.2.0 local recovery (software only)

Recovered the uncommitted private v0.2.0 checkout after a session usage cutoff, without replacing its newer group, control, session, settings or legacy-adapter work with the earlier v0.1.1 GitHub snapshot.

- The approved local Python environment completed `python -m unittest discover -s tests -v`: **107/107 tests passed**.
- `python -m ue_partyup --smoke` exited successfully after creating and closing the native GUI, without discovery or speaker commands.
- `git diff --check` passed; ignored `data/` files remain excluded from commits. Source review found only synthetic MAC addresses in test fixtures and no matching private-key or API-key patterns.
- No live Bluetooth mutations, speaker stop/restart, audio playback tests, firmware operations or changes to unrelated services were performed in this recovery stage.

These are software regression and UI construction checks, **not** an acceptance result for additional hardware models, multiple real guests or live control writes. Next bounded acceptance stage: exercise GUI discovery, selection persistence, read-only group status and supported speaker-control readback on the owner's EVERBOOM pair. A GUI Start/Stop/Restart and audible confirmation test should be separately announced before changing playback.

## 2026-10-14 v0.2.0 read-only live check on MSI

Launched the existing native UI with the approved project Python/Bluetooth environment. Its window was observed visible and responsive, showing both paired EVERBOOMs, one saved main speaker and one selected guest. A screenshot was inspected locally; no screenshot or device identity is being committed.

A separate one-shot read-only diagnostic in the Codex work area used the same `discover()`, `GroupManager.run('status')` and `Settings.snapshot()` code paths as the UI. The following values were observed:

- Two supported paired EVERBOOM records and one local Bluetooth adapter; both saved speaker choices matched discovery.
- **Group status:** completed in 8.8 seconds; main speaker reported PartyUp enabled, one receiver matched the saved guest, with zero warnings. This is receiver-list confirmation, **not** independent listening confirmation.
- **Main speaker readback:** completed in 46.3 seconds. Name, battery, volume, EQ and advertised presets, sleep timer, remote activation, sticky group and public visibility returned values. Outdoor mode had no usable value; Apollo stereo-balance readback remains intentionally undecoded.
- **Guest speaker readback:** completed in 17.5 seconds, but none of the displayed settings getters yielded a usable value. Some feature lookups were positive, others negative or unknown. Do not interpret unknown values as unsupported controls or claim the guest cannot play audio.
- The UI activity log had also shown a successful group-state report and an intermittent WinSock/Bluetooth connection timeout 10060 on a later attempt. Connection reliability remains an acceptance concern.

This pass sent **no PartyUp Start/Stop, BLE join/leave, power, volume, EQ, channel, firmware or other settings-mutation request**. No new audible playback or stop-silence result is claimed. The fully interactive GUI button flow was not systematically certified by the independent read-only runner; continue to distinguish backend readback from GUI usability. Do not attempt a disruptive group restart without announcing it first.

Next: reproduce and characterize guest-control readback limits and sporadic connection timeouts using read-only, bounded requests; then run owner-observed GUI control actions and listening acceptance in a separate stage.

## 2026-10-14 v0.2.1 presentation-only redesign

Implemented a local Tkinter/ttk dark audio-console theme, tab scrolling, always-visible Group Start/Add/Check/Stop controls, per-speaker paired-record count and a broadcast-status label that never implies audible audio from an unobserved state. Existing controls and callback semantics were retained. No hardware/group commands were sent to validate the appearance; default launched discovery reads Windows paired records only.

The first automated pass detected an unsupported Tk Text styling property. Removed that property and reran the full suite: 107/107 passing; an additional two UI regression tests were subsequently added, bringing the expected count to 109. The full **109/109 automated tests passed**, as did the GUI smoke launch. The minimum 960 × 760 layout check kept status and diagnostics visible while the four tab contents remained scrollable. A captured local v0.2.1 Group window was inspected for contrast, layout, a visible Start/Stop footer and unclipped status, log and closing advice; an initial clipped-bottom issue was resolved with bounded tab viewports and a pinned action footer.

No screenshot, MAC/address, raw Bluetooth capture or PC-specific diagnostic file is to be committed. This is a software/UI milestone, not new device compatibility evidence.
