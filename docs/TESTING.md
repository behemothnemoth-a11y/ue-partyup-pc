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
