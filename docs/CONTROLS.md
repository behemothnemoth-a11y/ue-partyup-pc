# Speaker controls and implementation status

This private preview distinguishes three kinds of evidence: a command recovered
from the current app, a tested independent implementation, and an acceptance
test on physical hardware. Advertising a feature ID establishes a candidate
control. A timeout establishes an unavailable reading, not a disabled setting.

The current CPP implementation uses feature-ID lookup on each connected speaker.
It does not assume that the runtime feature indices observed on the owner's
EVERBOOMs apply to other firmware or models. The legacy adapter is separate; see
the compatibility documentation and its experimental opt-in.

## Current inventory

| Control | Implementation | Acceptance status / limitation |
|---|---|---|
| Start / Stop / restart PartyUp | Group manager, up to one main and nine guests | Earlier two-EVERBOOM cycle and audible restart verified. Ten physical speakers remain untested. |
| Add / remove individual guests | Group manager | Source/capture-backed; each guest result is reported independently. Multi-guest and older-speaker acceptance tests pending. |
| Main-speaker and individual-speaker selection | Desktop UI / sessions | Control transport targets the selected device; Windows still selects its audio output separately. |
| Speaker volume | CPP volume read/write | Current app uses **0–31** for all CPP speakers; no guessed 0–255 slider. EVERBOOM readback verified; mutation acceptance tracked in the test checklist. |
| Group volume synchronization | XUp `ResetVolume` | Source-backed, tested with fake sessions; group acoustics and model-specific effects need listening checks. |
| Speaker name / rename | UTF-8, one-byte length; queries device maximum | EVERBOOM name readback verified. Rename rejects overlong encoded names before writing. |
| Battery / charging | Both raw battery and user state-of-charge bytes retained | EVERBOOM readback verified. Display uses the user SOC value only when 0–100; unknown values are not presented as a percentage. |
| EQ presets | Reads the speaker's advertised preset subset | EVERBOOM preset list and selected mode readback verified. Only mapped and advertised preset codes can be written. |
| Five custom EQ bands | Five signed bytes, −128…127 | Source and signed decoding verified; these are protocol levels, **not dB**. Current EVERBOOM EQ readback verified. |
| Outdoor mode | Inverted boolean read/write | Exact current-app serialization recovered, but the tested EVERBOOM did not return a matching GET reply. The UI must keep it unavailable until a successful reading. |
| Auto-sleep | 15 / 30 / 60 / 180 minutes, or 0 = Never | Current Android choices recovered; EVERBOOM 15-minute readback verified. Arbitrary byte values are rejected. |
| Remote activation setting | BLE remote-on enable read/write over CPP | EVERBOOM reading verified. Enabling the setting is distinct from implementing an actual wake command. |
| Power off | CPP shutdown with optional `silent` flag | Source-backed; not silently run during tests. The flag suppresses sound; it does **not** mean standby. |
| Play / pause / toggle / next / previous / stop | AVRCP proxy via speaker | Source-backed command values 0–5; requires the audio source's Bluetooth MAC. Audio applications may handle AVRCP differently; acceptance pending. |
| Fast-forward / rewind press and release, group navigation | Additional AVRCP proxy codes | Source-backed backend API; not all are exposed in the preview UI or verified with a PC media player. |
| Persistent group | XUp sticky flag read/write | EVERBOOM flag reading verified; persistence across power cycles not yet tested. |
| PartyUp public / private visibility | XUpReceiver promiscuous-mode read/write | Source-backed; CPP feature ID comes from the supplied APK's constant **517**, not a newer library's unrelated value. Hardware acceptance pending. |
| Identify main or an individual guest | LED signal through XUp broadcaster | Source-backed destination / MAC / signal payload. Default is a 15-second Bluetooth LED blink; hardware acceptance pending. |
| Identification sounds | Backend signal catalog | Only sonification commands, including a factory-reset **sound**; no factory reset command. The UI exposes a small useful subset. |
| Stereo balance | Apollo feature setter | The current app uses Apollo, separate from PartyUp XUp. Readback and model-specific user range are not decoded, so UI availability remains limited. No fabricated left/right state. |
| Wake from powered off | Pending | Remote-on setting implemented, actual BLE wake path not yet implemented or verified. |
| Stereo channel assignment / true stereo group | Pending | Requires the current app's audio-mode flow and compatible hardware; stereo-balance setter alone is insufficient. |
| Firmware updates | Pending / deliberately unavailable | No verified end-to-end updater, package verification, or recovery flow; no firmware bytes are written. |
| Alarm / music alarm | Pending | Requires alarm payload, time zone, music-source and persistence semantics, plus model support. |
| Magic Button / playlists / streaming-service connections | Pending | App-side and service-specific workflows remain unimplemented; source control is not equivalent to account integration. |
| Megaphone | Pending | Requires a PC microphone-to-speaker audio path and model support, not just a settings command. |
| Bluetooth source management / Block Party | Pending | Separate source-switching / multi-phone mechanisms; not implemented as PartyUp group controls. |
| Voice notifications / language / sound settings | Pending | Exposed by some models; no model-complete implementation or acceptance test yet. |

“All controls” remains the project scope; the pending rows are outstanding work,
not completed features. The application should not present them as working.

## Protocol summary

`Settings(session)` shares an already-connected CPP session. The caller owns the
session and its connection lifetime. Getters use `read=True`; setters await a
matching acknowledgement. None of the snapshot operations mutates settings.

| Feature ID | Control | Function / payload |
|---|---|---|
| `0x0101` | Name | 0 GET, 1 SET length + UTF-8, 3 maximum encoded length |
| `0x0104` | Battery SOC | 0 GET: battery byte, user SOC byte, charging code |
| `0x0106` | Remote power | 0 GET enable, 1 SET bool, 2 shutdown + silent bool |
| `0x0108` | Auto-sleep | 0 GET, 1 SET minutes byte |
| `0x0200` | Volume | 0 GET, 1 SET level 0–31 |
| `0x0201` | EQ | 0 GET, 1 SET mode + five signed bytes, 2 advertised modes |
| `0x0202` | Apollo broadcaster | 4 SET stereo balance byte; unresolved readback |
| `0x0204` | XUp broadcaster | 8 SET sticky, 9 GET sticky, 10 identify destination + MAC + signal, 12 synchronize volume |
| `0x0205` | XUp receiver | 0 GET public visibility, 1 SET bool |
| `0x0207` | AVRCP controls | 0 send app command byte + six-byte source MAC |
| `0x020D` | Outdoor mode | 0 GET, 1 SET **inverse** of enabled boolean |

CPP preset codes are not the enum ordinal values used elsewhere in the app.
Mapped codes: 0 Voices, 1 Cramped spaces, 2 Bass jump, 3 Standard, 4 Custom,
5 Bass boost, 6 Outdoor, 7 Game/Cinema, 8 Podcast, 9 Vocal,
10 Reflective room, 12 Deep relax, 13 Podcast/Vocal. Unknown presets may appear
in readback but are not offered for mutation.

## API

```python
async with Session(speaker) as session:
    settings = Settings(session)
    snapshot = await settings.snapshot()   # read only, field-specific errors
    await settings.set_volume(9)          # explicit user action
```

Main methods:

- `name()`, `max_name_length()`, `rename(name)`
- `battery()`, `volume()`, `set_volume(level)`
- `eq()`, `eq_modes()`, `set_eq(mode, bands)`
- `outdoor()`, `set_outdoor(enabled)`
- `sleep_timer()`, `set_sleep_timer(minutes)`
- `remote_activation()`, `set_remote_activation(enabled)`
- `power_off(silent=False)`
- `playback(command, source_address)`
- `sync_volume()`, `sticky()`, `set_sticky(enabled)`
- `public()`, `set_public(enabled)`
- `identify(target_address=None, signal='blink')`
- `set_stereo_balance(value)`; `stereo_balance()` explicitly reports unresolved readback

The snapshot contains `name`, `battery`, `volume`, `max_volume`, `eq`,
`supported_eq_modes`, `outdoor`, `sleep_timer`, `sleep_timer_unit`,
`remote_activation`, `sticky`, `public`, `stereo_balance`, `capabilities`, and
`errors`. `BatteryInfo` retains all three bytes and offers `percent`, `level`, and
`charging_state` properties. `EQInfo` contains `mode`, five `bands`, and `label`.
Capabilities are `True`, `False` (explicitly not advertised), or `None` (lookup
unavailable). A failed getter returns `None` and a field-specific error, never a
made-up zero or false value.

## Provenance and verification

The independent code follows static observations from the owner's installed UE
app, analyzed with REA 6.5.0 and its pinned JADX 0.7.1 engine, plus the supplied
Bluetooth capture and earlier tests. The input base APK SHA-256 was
`018e9d6159311034327780480ee3798a7cdf31c5e7d174b6c496bf2254410e76`.
It is not redistributed. Raw bug reports, packets, selected hardware addresses,
APKs, and decompiled source stay outside the tracked repository.

Relevant static observations are in these classes and methods, without copying
their implementation here:

- `centurion.cpp.feature.Features`: feature constructors and function enums.
- `centurion.cpp.device.CPPDevice`: volume, EQ, name, battery, outdoor, sleep,
  remote power, AVRCP, sticky, and receiver identification request builders.
- `centurion.cpp.utils.CPPDataPacker` / `CPPDataUnpacker`: UTF-8 string framing.
- `centurion.cpp.utils.UtilsKt`: CPP EQ preset conversion.
- `centurion.eq.EQProfile`: five signed band bytes and protocol limits.
- `howhigh.presenters.VolumeControlPresenter`: all CPP speakers use 32 volume
  steps (0–31); old models select their own 16/32-step branch.
- `howhigh.model.AutoSleepValue`: current app's minutes and Never presets.
- `centurion.avrcp.AVRCPCommand` and `centurion.xup` identification enums.

Unit tests cover runtime feature indices, source-matching payloads, UTF-8 limits,
signed EQ boundaries, advertised preset subsets, unknown battery / feature states,
inverse outdoor mode, sleep presets, MAC byte order, and setter acknowledgement
handling. Fake-session tests never send Bluetooth commands. Physical acceptance
results belong in `TESTING.md`; a test suite pass is not a device compatibility
claim.

## v0.3.0 additions / corrections

- PC-local named EQ memories are implemented (up to 20). These do not claim to write a speaker-side custom-EQ name. Loading stages sliders; Apply EQ writes.
- Source-backed modern BLE wake is now implemented behind explicit preview opt-in. The characteristic and default payload were independently reconstructed from CPPDevice/BLEUtilsKt/BLEPowerCommand/BLECharacteristics. GATT acknowledgement is not power-state confirmation; physical wake acceptance is outstanding. Legacy wake remains unimplemented.
- XUp guest channel assignment exists through GroupManager.set_channel and the Group UI; this supersedes the older inventory's pending implementation row. Physical stereo separation still needs acceptance.
- Group volume sync has a direct main-targeted UI shortcut. Its purpose is volume alignment, not audio/video timing.
- APP-PARITY.md records the broader researched flow and outstanding alarms, service playlists, Megaphone and firmware work.

## Playback protections — 0.7.1
Live tests found audio interruptions during a direct guest snapshot and a persistent-group toggle while playing. Root causes remain unresolved. All UI guest settings/read/EQ paths now query the selected main first and refuse to open a guest control transport while the main reports broadcasting; missing/malformed/failed state reads also prevent guest access. Main settings remain available. Guest controls require explicitly stopping PartyUp first; the app never stops the group automatically for a read. Changing Remember PartyUp group now queries broadcaster state before its setter and refuses active/unknown state. These are protective restrictions, not a claim of uninterrupted direct guest controls. Another application or external device can change group state after the check, so this is not a cross-device lock.
