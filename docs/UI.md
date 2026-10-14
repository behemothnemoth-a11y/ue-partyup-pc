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
