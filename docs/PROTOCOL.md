# Observed EVERBOOM protocol

Independent implementation derived from an owner-supplied Android HCI capture of a successful official-app PartyUp session. Raw captures are private and excluded.

Frame: `13 A0`, 16-bit little-endian length, category byte, operation/sequence byte, payload, 16-bit checksum. Total size is length + 5. Operation is the upper nibble; sequence is the lower nibble.

Outgoing CRC uses reflected polynomial 0x8408, initial 0xFFFF, no final XOR; emitted little-endian over all preceding bytes. All 62 complete recovered outgoing modern messages matched. Observed reply trailers are zero; reply checksum validation is not asserted.

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
