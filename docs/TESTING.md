# Alpha candidate validation — 0.7.1

## Automated checks
199 unit/integration tests passed on Windows in the pinned Python 3.13 build environment. Speaker responses are mocked in automated tests; native Windows mutex and isolated Tk widget checks exercise local behavior. Packaged asset check and UI smoke passed. These are not physical ten-speaker compatibility tests.

## Hardware acceptance
Tested pair: two EVERBOOMs, laptop Bluetooth audio through the selected main.

| Check | Result |
|---|---|
| Music-classroom appearance and teacher/student selection | Owner passed; both continued playing |
| Main settings read | Battery/volume/EQ returned; playback continued |
| Main volume down one and restore | Exact readback, owner heard dip/return; both continued |
| Main sleep setting 15/30/15 minutes | Exact readback; playback continued; actual sleep not tested |
| Main remote activation On/Off/On | Exact readback; playback continued; actual wake not tested |
| Direct guest snapshot during PartyUp | Failed and audio interrupted; restricted in 0.7.1 |
| Live persistent-group toggle | Readback matched but audio interrupted; restricted in 0.7.1 |
| Recovery Stop/Start | Host off/on and guest leave/join accepted; owner confirmed both playing |
| Main group status | Enabled; receiver report absent; membership unknown |
| Persistent-group guard on active hardware | Blocked; zero setter attempts; owner confirmed normal playback |
| Guest guard on active hardware | Blocked; zero guest connection attempts; owner confirmed normal playback |
| Open installed 0.7.1 | Owner approved appearance; both playing |

Visible button error/status handling for the guards remains pending. Automated controller checks do not establish visible UI acceptance. Additional test results are recorded in RELEASE-AUDIT.md.

## Not established
Fresh installation on a second machine; physical ten-speaker groups; older models; actual auto-sleep/wake/power-cycle persistence; acoustic stereo/channel behavior; all preview controls; measured lip-sync correction. External controllers can change group state after a guard's check.

## Reproduce
Run `python -m unittest discover -s tests -v`, then build with `Build Private.ps1`. `PartyUpPC.exe --self-check --report <file>` checks bundled dependencies/assets; `--smoke` constructs and closes the UI without discovery or speaker commands. Never label a successful command acknowledgement as audible acceptance.

0.7.2 alpha preparation: 201 tests passed, including restoration of a staged persistent-group checkbox after a guard refusal. Isolated empty-app-data self-check/install/installed-smoke all passed. Owner passed visible guest safeguard in 0.7.1: message displayed, main selectable, both playing. Updated 0.7.2 opened/responding; visible persistence safeguard/checkbox test pending. No speaker commands were sent for controller replacement.
