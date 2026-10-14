# UE PartyUp PC

Independent Windows desktop controller for grouping two Ultimate Ears EVERBOOM speakers without a phone during normal use.

**Private preview, version 0.1.0.** A PC-created group has been verified with audible playback on one pair of EVERBOOMs. The refactored application's complete stop/restart flow still needs hardware acceptance testing. No other UE model is supported yet. Not affiliated with or endorsed by Logitech or Ultimate Ears.

## Use

Requirements: Windows 10/11 with Bluetooth Classic and BLE support; Python 3.13 with tkinter; two EVERBOOMs paired separately in Windows.

1. Run `Setup.cmd` once to create a local environment and install the pinned dependency. This requires internet access and explicitly downloads packages.
2. Turn both speakers on and close the mobile UE app. If it retains the connection, temporarily disable phone Bluetooth.
3. Open `Open PartyUp.cmd`.
4. Select different main and second speakers. Labels use the final four address digits to distinguish identical names. Find those digits in Windows device details if needed.
5. Click **Start PartyUp**, then play laptop audio through the selected main speaker using Windows sound settings.
6. **Check status** queries host configuration; it does not claim the guest is audible. **Stop PartyUp** sends the captured stop/clear sequence and verifies host broadcasting is off.

The launcher in the original development checkout can reuse the approved project environment. A fresh clone requires Setup.cmd.

## What it does

The main speaker receives framed RFCOMM commands. The guest receives a BLE write referencing the selected host. The speakers distribute the audio themselves; the app does not duplicate Windows audio streams. Connections close after operations; this does not inherently end the speaker group. Closing the app leaves the group running.

Selection is remembered under ignored `data/selection.json`. No cloud services, telemetry, account login, firmware changes or automatic capture uploads. Raw phone bug reports and Bluetooth captures are excluded from this repository.

If the guest operation fails after the host changes mode, the controller attempts to restore the previous host configuration and reports whether that restoration was acknowledged. It cannot guarantee restoration of the guest's previous group membership. No automated reconnect/background grouping happens on startup.

## Troubleshooting

- Connection timeout: keep both speakers powered on, close the phone app, wait briefly and retry. Check your Bluetooth adapter supports both Classic and BLE.
- Only the main speaker plays: confirm Windows output is the selected main speaker; check the guest is nearby and not playing another source. The app reports if it did not observe a receiver confirmation.
- Access denied inside a sandbox: run the launcher from your normal Windows session. Admin access is not assumed.
- Renamed speakers may not appear: current discovery filters cached device names containing EVERBOOM. Support for renamed devices is pending.
- Windows speaker labels may match: use address suffixes to distinguish the two; renaming alone is not yet supported.

## Development

`python -m unittest discover -s tests -v`

Tests use captured-packet fixtures and input/acknowledgement checks, without Bluetooth writes. Hardware evidence and limitations are in [docs/TESTING.md](docs/TESTING.md). Wire framing and provenance are in [docs/PROTOCOL.md](docs/PROTOCOL.md).

No public release until the acceptance checklist passes and the owner explicitly approves publication. Other UE families require model-specific captures and tests before being enabled.
