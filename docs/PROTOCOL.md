# Observed EVERBOOM protocol

Independent implementation derived from an owner-supplied Android HCI capture of a successful official-app PartyUp session. Raw captures are private and excluded.

Frame: `13`, then `A0 | length_high_nibble`, then `length_low_byte`, followed by the CPP message and 16-bit checksum. The CPP message begins with device ID, category, and operation/request-ID bytes. Total size is length + 5. Operation is the upper nibble; request ID is the lower nibble. IDs advance 1 through 15 and wrap to 1; zero is reserved for unsolicited events. A nonzero device ID must never be interpreted as a length byte.

Outgoing CRC uses reflected polynomial 0x8408, initial 0xFFFF, no final XOR; emitted little-endian over all preceding bytes. All 62 complete recovered outgoing modern messages matched. Observed reply trailers are zero; reply checksum validation is not asserted.

## Current APK validation with REA

The owner's installed APK was copied over authorized USB debugging, SHA-256 `018e9d6159311034327780480ee3798a7cdf31c5e7d174b6c496bf2254410e76`. REA 6.5.0 with pinned JADX 0.7.1 inspected it statically. No app code or APK is distributed in this repository.

`CLPSPPWrapperConnection.wrapPayload` and `extractPayloadSize` establish the three-byte length framing above. `CPPConductor.generateSWId` and `execute$lambda$1` establish per-command IDs and 1–15 rollover; `checkExpectedMessage` correlates replies by request ID. This corrects the initial capture interpretation. The legacy two-byte-length parser could stall when message device ID was nonzero.

`XupBroadcastModeCommand` distinguishes mode/audio changes and waits for a mode-change event. `XupReceiverController.removeFromGroup` invokes the guest's leave operation. The independent controller retains captured start/clear writes and verifies host off-state separately.

| Operation | Category | Operation nibble | Payload |
|---|---|---|---|
| Initialize | 0 | 0 | `00 01` |
| Query name | 5 | 0 | none |
| Query broadcast state | 11 | 1 | none |
| Set broadcast state | 11 | 0 | state, audio option |

Observed start state/audio: `03 00`. Observed disabled state/audio: `00 00`. These values were replayed for start and read back in the original test. Stop hardware verification remains pending.

Guest control BLE characteristic: `69c0f621-1354-4cf8-98a6-328b8faa1897`. Join write: selected host's six address bytes in displayed order followed by `01 02`. Observed clear write: eight zero bytes. Characteristic resolved by UUID; never assume an ATT handle on another device/firmware.

Observed receiver notification category11/operation0/sequence0 contains count followed by receiver address/status fields. The original test matched the guest address, then audible playback was confirmed by the owner. Do not generalize exact status-bit meaning from older app code.

Older UE app commands from https://github.com/countableSet/ue-boom-re were useful historical reference, but their framing failed on EVERBOOM. No decompiled app code or binaries are distributed here.
