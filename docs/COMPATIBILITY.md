# Speaker compatibility

This repository remains a private preview. Its target is one main speaker and
up to nine guests. A ten-speaker software limit does not establish ten-speaker
hardware playback, and a command acknowledgement does not establish audible
playback or synchronization.

## Evidence and current support

| Model | Manufacturer PartyUp evidence | Protocol evidence in the current Android app | This PC project's hardware result |
| --- | --- | --- | --- |
| EVERBOOM | Current EVERBOOM guide | CPP / Chopin | Two EVERBOOMs: Start, Stop state, restart and audible playback verified in the earlier controller; expanded controls need their own acceptance checks |
| Original BOOM | Official PartyUp launch explicitly included BOOM | Legacy / Kora, device code 1 | Experimental probe and source-backed commands implemented; no hardware test |
| BOOM 2 | Official PartyUp launch explicitly included BOOM 2 | Legacy / Maximus, device code 4 | Experimental; no hardware test |
| Original MEGABOOM | Official PartyUp launch explicitly included MEGABOOM | Legacy / Titus, device code 3 | Experimental; no hardware test |
| BOOM 3 | Current manufacturer family compatibility statement | Legacy / Mendocino, code 8; a separate CPP MendocinoCR entry, code 11, also identifies BOOM 3 | Experimental; protocol must be queried; no hardware test |
| MEGABOOM 3 | Current manufacturer family compatibility statement | Legacy / Humboldt, code 9 | Experimental; no hardware test |
| BOOM 4 / MEGABOOM 4 | Current manufacturer product pages | CPP entries MendocinoPlus / HumboldtPlus | Source investigation; no hardware test |
| EPICBOOM / HYPERBOOM | Current EVERBOOM guide and BOOM 4 family statement | CPP entries Puccini / MotorCity | Source investigation; no hardware test |

Manufacturer capability is separate from this application's capability. The
2016 announcement names original BOOM and MEGABOOM, so original generations
should not be rejected merely because a newer setup page lists newer examples.
The current BOOM 4 page states compatibility with all BOOM, MEGABOOM, EVERBOOM,
EPICBOOM and HYPERBOOM speakers. The EVERBOOM guide requires current speaker
firmware for its PartyUp setup. These statements support investigation; they do
not prove our PC adapter works with every generation.
[Official PartyUp announcement](https://news.logitech.com/press-releases/news-details/2016/Ultimate-Ears-Turns-the-Party-Up-with-PartyUp/default.aspx),
[official BOOM 4 compatibility](https://www.ultimateears.com/en-gb/shop/p/boom-4.984-001969),
[official EVERBOOM guide](https://support.logi.com/hc/en-gb/articles/22067951753751-Getting-Started-UE-EVERBOOM).

WONDERBOOM, ROLL, BLAST and MEGABLAST are outside this adapter's supported test
scope. Their appearance in an app's device inventory does not establish PartyUp
compatibility. No firmware updater, reset or flash commands are implemented.

## Why older models need a separate adapter

The copied current UE Android APK still contains `LegacySPPDevice`,
`CenturionCommand` and the legacy PartyUp operations. REA/JADX static inspection
verified that its broadcast-state, add-receiver, remove-receiver and volume-sync
commands agree with the historical UE app evidence. The independent PC adapter
uses only recovered command values and payload layouts. The APK, packet captures
and decompiled source remain local and are excluded from the repository.
[Historical UE protocol research](https://github.com/countableSet/ue-boom-re),
[REA's Android analysis workflow](https://github.com/morluto/rea/blob/main/docs/android-analysis.md).

The current APK model table assigns original BOOM, MEGABOOM, BOOM 2, BOOM 3 and
MEGABOOM 3 entries to the legacy protocol. It also contains a CPP revision with
the BOOM 3 marketing name. Display names are therefore only discovery hints;
a successful protocol query selects the adapter. A working CPP reply must never
trigger speculative legacy fallback.

Its `PartyUpModelGroup` table puts Kora, Maximus and Mendocino in `SMALL`, and
Titus and Humboldt in `BIG`. These are app classifications, not prohibitions on
mixed groups and not proof of stereo capability. Stereo/channel choices still
need model-specific verification.

### Current PartyUp channel and visibility findings

The current APK translates channel choices differently for the host's serial
command and the guest's BLE join. The enum's ordinal is not a wire code.

| Channel | Host AddReceiver command byte | Guest BLE join audio byte |
| --- | --- | --- |
| Center / all audio | 3 | 0 |
| Left | 1 | 1 |
| Right | 2 | 2 |

Both current `BaseXupBLEController` and `XupReceiverController` call the BLE
conversion function when joining a guest. The BLE payload is the main speaker's
six address bytes, JOIN code 1, and the BLE audio byte above; leave clears the
address and writes LEAVE code 0 and audio 0. The earlier capture's trailing
`01 02` therefore demonstrates a join using the right-channel value under this
current source mapping. The earlier listening result established audible
playback, and did not establish the exact channel assignment. Center/left/right
behavior needs its own listening test before claiming stereo fidelity.

Current host audio options include `DOUBLE_UP` 0, stereo left/right/center
`0x50/0x60/0x70`, and reverse stereo right/left/center `0x90/0xA0/0xB0`.
The reverse labels differ from the historical app and must follow current
source for current commands. The adapter accepts the additional center options;
this validation does not establish which older firmware implements them.

The modern public/private setting belongs to CPP XUpReceiver feature `0x0205`:
function 0 reads the promiscuous-mode boolean, and function 1 writes it. Its
numeric feature ID was checked against the copied APK's DEX constants rather
than relying on a similarly named constant in a newer external library. Legacy
query/set counterparts remain `0x042A/0x0426`.

### Individual guest volume and main-speaker transfer limits

The modern `SendDataOverBroadcast` function 11 writes a one-byte packet ID
followed by opaque package data. This alone does not define a directed guest
volume packet. Current generic `getReceiverOneAttribute` and
`setReceiverOneAttribute` methods return unsupported on CPP, so legacy guest
attribute framing must not be sent to a modern host speculatively.

The legacy guest attribute setter is source-backed at `0x0422`, with guest
address, attribute byte and data; its volume attribute number is `0x1E`.
Complete value semantics and result handling still need verification before
exposing a new relayed volume setter. The current legacy BLE command inventory
has no volume characteristic, and inspection did not identify an equivalent
modern relay route used by the app. Direct control sessions to a guest may
behave differently while the guest is receiving PartyUp audio; that remains a
hardware acceptance case.

The inspected grouping manager creates and removes controllers keyed by
speaker address, and the inspected XUp controllers bind to a main device. No
atomic main-speaker transfer command was established. Selecting a different
main speaker is therefore a separate configuration/test case; a seamless
transfer claim would require a verified leave/rejoin and audio-source flow.

## Experimental legacy behavior

`LegacySession` defaults to read-only. `probe()` reads the protocol, queried
device ID, name and broadcast configuration. It reports the app-derived model
and profile and always reports `hardware_verified=False`. An explicit
unrecognized-command reply marks broadcast capability unavailable; a timeout
remains unknown and is surfaced as an error.

Legacy writes require an explicit experimental option plus successful protocol
and broadcast queries and a known queried BOOM/MEGABOOM identity on the active
connection. The implemented host operations
are broadcast configuration, add a guest, remove a guest and synchronize volume.
Basic operations include name, 16/32-step volume, sticky/public PartyUp settings,
battery announcement and remote power off. Each waits for a successful ACK that
echoes the command, and ambiguous mutations are never blindly retried. Receiving
an ACK alone does not count as successful guest audio or group membership.

The legacy frame uses a one-byte length followed by a two-byte big-endian
command. Information responses and notifications receive receipt ACKs; these do
not change settings. A query's ACK cannot replace its expected information
response. No arbitrary command input is exposed.

No older speaker has been available for a PC hardware test yet. Mixed
EVERBOOM/legacy grouping and ten-speaker playback remain unverified, even though
the manufacturer describes the families as PartyUp compatible.

## Required hardware acceptance before expanding claims

1. Query an original BOOM and original MEGABOOM; record only nonidentifying model,
   protocol and capability results in the repository.
2. Verify each legacy model as both host and guest, including connection cleanup
   and explicit unsupported-command handling.
3. Test a mixed legacy/CPP group and confirm join/remove notifications and
   actual audio, including whether the removed guest goes silent.
4. Test one main speaker plus nine guests, an unavailable guest, removal of a
   single guest, reconnection and per-speaker/group controls.
5. Verify stereo choices only for documented compatible model combinations.
6. Keep unknown values and missing replies visible; preserve the remaining
   group when one guest fails. Do not turn test fixtures into compatibility
   claims.

Sources checked on 2026-10-14. Current APK static evidence is local and tied to
SHA-256 `018e9d6159311034327780480ee3798a7cdf31c5e7d174b6c496bf2254410e76`.
