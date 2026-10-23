# PartyUp control-desk interface

## Visual design, private v0.2.1

An entirely local Tkinter/ttk theme (no browser, framework download, paid API or background server) now provides:

- A charcoal/navy header and four consistent tabs for Group, Speaker, Sound and PartyUp settings.
- Clear contrast between routine commands, teal primary Start/read actions and muted-red disruptive Stop/power-off actions.
- A top-right **paired records** count, never an assertion that devices are awake or playing.
- A **broadcast state** indicator that starts as **status not checked**. It changes only when GroupManager returns an actual result.
- Scrollable content for all tabs, accommodating large font scaling and shorter Windows desktops. The Group tab's Start, Add, Check and Stop controls remain visible at the bottom of its viewport.
- A persistent status line and compact, locally rendered activity log.
- Distinct unavailable control styling to avoid implying unsupported hardware behavior.

## Boundaries

The visual update does not change protocol framing, firmware, BLE join/leave operations, discovery decisions, persistence format, error handling or background processes. A software preview does not establish new hardware compatibility. The existing two-EVERBOOM audible start/stop/restart evidence remains the only physical group test.

## Development

Theme tokens, ttk styles, Windows dark-caption hint and scrollable viewport live in `ue_partyup/theme.py`. Widget composition and callbacks remain in `ue_partyup/app.py`. All existing function entry points, feature-gating rules and GUI safety guards are preserved. The added layout tests in `tests/test_app.py` check pinned Group actions and truthful status labels without Bluetooth connections.

Run `python -m unittest discover -s tests -v` then `python -m ue_partyup --smoke`. Review at the default 1180 × 900 and minimum 960 × 760 sizes. If a tab's controls extend beyond the viewport, use its scrollbar or mouse wheel. Avoid sending Group Start/Stop during appearance reviews; the hardware workflow is a separate acceptance stage.

Color/typography/spacing are provisional UI choices, not a new product style locked without owner feedback.

## Volume and EQ interactions, private v0.2.2

Opening the Sound tab automatically requests only the selected **modern CPP speaker's** volume, current EQ settings and advertised EQ modes. This uses read-only commands and runs in a worker; opening Sound does not send a mutation. An experimental legacy speaker requires the explicit manual Read controls route. A failed read leaves its control disabled and tells the user to retry manually, without converting a timeout into an unsupported-feature verdict.

- **Volume:** 0–31 level scale, shows the pending percentage while dragging. One request is sent when the pointer or arrow key is released. The existing Set volume button also works. Neither pressing a key without a value change nor a mouse-up on the current value sends a command.
- **Five custom EQ sliders:** operate only if the speaker advertised Custom (wire code 4) and returned a current EQ band set. Releasing a band chooses Custom, sends all five signed values once, and requests EQ readback. Presets remain selectable through Apply EQ.
- **Targeted feedback:** volume or EQ writes now read back that field only, rather than taking a full snapshot of every unrelated feature. An acknowledged write whose readback fails is labelled **unconfirmed**, never silently assumed successful. Other settings preserve their existing behavior.
- **Stereo balance:** remains an explicitly opted-in experimental slider. Its current-value decoding and real-world stereo effect remain unverified; it is not promoted as working live balance.
- **Guest speakers:** independent direct control may be unavailable while receiving a PartyUp stream. Unknown getter replies must not be mistaken for unsupported firmware.

The slider callbacks and read-only tab behavior are in `ue_partyup/app.py`. Protocol bytes, source-backed setter values and hardware compatibility claims are unchanged. GUI regression tests mock all writes; no speaker volume or EQ was changed during this development stage.

## Interface polish, 2026-10-15

Retained the working controller and slider interactions. Updated the presentation with a compact header, charcoal and mint palette, quieter secondary actions, simpler Group labels, a larger volume readout, longer EQ sliders with numeric values, and activity details that collapse by default. Start/Stop remain pinned to the Group viewport; all existing activity messages continue accumulating when hidden.

Validation: 121 automated tests passed. A sample-data window was inspected before the changes, showing the oversized header and crowded workspace under Windows scaling. The user stopped Computer Use with Escape before the final visual review; final appearance across all tabs and minimum window sizes is not visually certified. No speaker connections or control writes were made for this appearance update. Changes remain local for review.

The activity log retains the latest 500 lines. Idle event handling backs off to 300 ms; active work uses 60 ms, with bounded batches to keep the interface responsive. These timers never poll speakers. Settings setters use focused readback when available; acknowledgement-only commands clearly say their effect has not been independently verified.

## Pixel Party, private v0.3.0

Original plum/cream/mint pixel-console presentation, static house-party artwork, ten selected-slot silhouettes and monospace display headings. Normal body labels remain readable; no animation loop, web runtime, telemetry or additional dependency. The illustrated banner is decoration; the speaker map represents selection, never inferred connectivity.

Added drag-to-join/remove alongside keyboard-accessible action buttons, a selected-member control shortcut, main-targeted volume sync, PC-local named EQ memories, read-only Windows output check and a feature guide with explicit support limits. Memory loading changes sliders only; Apply EQ is required to send. Preview wake requires explicit opt-in and a modern speaker selection. See APP-PARITY.md for unfinished work and ART.md for generation provenance.

Offscreen fixture previews were rendered using only a newly created test window, with synthetic devices and no desktop mouse/keyboard input. Initial native window captures omitted widget redraws; explicitly exposed the fixture widgets and recaptured before visual review. No actual speaker commands were used in these previews.


## Approved House Party implementation, private v0.4.0 (2026-10-20)

Owner approved the mockup and explicitly requested full detail with generated assets. The default view now uses a detailed four-room nighttime house, original transparent peach/lavender speaker artwork, private-process Silkscreen headings, stepped Pocket Party buttons, segmented sliders, a drawer and selected-speaker sidebar. Room plaques and live controls are coded separately from the illustration. Main and guest badges, selection corners and the selected count describe selection; they do not certify playback.

All ten speakers have distinct positions across the four rooms. Names and arrangement persist only in ignored local data/house-layout.json. Moving a selected speaker changes that local arrangement without Bluetooth I/O. A new drawer drop chooses a free slot in the requested room rather than displacing the main. An eleventh speaker is blocked before a group action. Failed guest removal retains selection; accepted leave clears it.

The sidebar reuses existing capability gates and serialized command callbacks. Selecting speakers reads cached state only, including when the hidden legacy Sound tab was last selected. Explicit Read refreshes controls. Sound and Settings expose the complete prior detailed interface with an explicit return button. No protocol or hardware support claim changes.

Default client size 1440x960; minimum 1120x800. The house preserves its aspect ratio, the drawer can scroll horizontally, the sidebar scrolls vertically and the three group buttons remain pinned. Event-driven redraws are debounced; no animation or speaker polling was added. Asset/font provenance is in ART.md.

Reviewed synthetic two- and ten-speaker renders at default size, and a two-speaker render at minimum size using only isolated fixture windows. No desktop input automation, real app relaunch, speaker commands or EQ hardware tests during this implementation. Fixture window capture occasionally omitted native repaint areas; complete repaints were visually inspected before selecting the final previews. Hardware acceptance remains deferred until the owner is home.


## Sound and Settings, private v0.4.1 (2026-10-20)

Owner requested matching House Party styling while keeping every control. Added a common pixel header/navigation, selected-page mint highlight, titled speaker-art panel, Silkscreen section/card headings and stepped action buttons throughout the detailed interface. Sound is now a two-column console: volume and outdoor mode on the left, preset/five EQ bands/local memories on the right. The volume/EQ/balance sliders use the shared segmented PixelSlider; releases retain the existing callbacks and feature gates. No Bluetooth protocol changes.

The entire prior Group, Speaker, PartyUp settings and Guide page set remains reachable; name, power, wake preview, sleep, playback, group preferences, availability, identify, experimental balance, PC output checks and local diagnostics remain present. Regression coverage compares original action labels and feature gates against the styled version. Sound memory loading still stages values without sending; apply/release semantics are unchanged.

Reviewed sample-device renders at 1440x960 and 1120x800, including the scrolled lower sound and playback sections. Native offscreen PrintWindow sometimes omitted paint regions; those incomplete captures were rejected as preview evidence. No desktop input automation, live app restart or real speaker/EQ tests for this change. No live app restart was performed; the next launch loads v0.4.1. No Workspace Control services used.

EQ memories now preserve the selected advertised preset mode plus five bands. Legacy band-only entries load as Custom. Saved modes unavailable on the target speaker are rejected without staging; loading never sends a command and Apply EQ is still required.


## Quick tuning, private v0.5.0 (2026-10-23)

Added a compact stepped-button card above the Sound panels: Bass −/+, Undo, Reset changes, Read EQ, Save as. Existing five EQ sliders, presets, memories, volume, outdoor mode and all detailed tabs remain. Quick bass steps always preserve the confirmed preset mode. The card labels confirmed main/guest target and bass delta from the starting reading. Staged memory/slider changes are separate until Apply EQ; quick steps operate on confirmed sound. Save as stores the confirmed mode and bands without volume or device identifiers.

Every actual HousePartyApp EQ write now runs through a fresh-read/advertised-mode/single-write/exact-readback transaction on the existing serialized worker. Repeated clicks cannot queue; external drift produces a refreshed baseline and no write. Uncertainty locks all EQ controls until Read EQ succeeds; switching speakers cannot bypass that lock. Undo is bounded to 20 confirmed changes and clears when target or external state changes. Reset restores the starting mode and bands. Late replies update only the correct speaker cache, not the new target's undo state. Bluetooth cancellation is surfaced as a terminal result rather than leaving the interface busy forever.

Factory preset memories no longer require Custom to be advertised; recall still requires the saved mode to be advertised. Legacy band-only memories remain Custom. The live Metal record remains mode 5/bands [113,76,-25,29,98]. No automatic EQ/group propagation is claimed.

Isolated fixture geometry checked at 1440x960 and 1120x800: quick action row ends at x597, viewport widths1385/1065, content requested width883. Content is vertically scrollable. Native offscreen screenshot capture returned incomplete white repaint regions and was rejected/deleted; full pixel-level visual review of the new card remains pending. No mouse/keyboard automation or live app relaunch was used.

## Music classroom — 0.7.0
The group screen uses a pixel-art music room with a piano, guitars and notation on the chalkboard. The selected main occupies the teacher chair; up to nine guests occupy individual student chairs. Guest seating can be rearranged locally; changing the main assigns the new teacher. Selection alone never establishes connectivity: badges distinguish selection, accepted join and main-speaker reports. Seating is stored separately in classroom-layout.json. Sound, Settings and all existing controls remain available.
