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
