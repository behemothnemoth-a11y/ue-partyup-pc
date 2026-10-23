# UE app comparison and PC implementation

Reviewed 2026-10-19 against the official [EVERBOOM guide](https://support.logi.com/hc/en-us/articles/22067951753751-Getting-Started-UE-EVERBOOM), [BOOM app listing](https://play.google.com/store/apps/details?hl=en&id=com.logitech.ueboom), and the owner's locally cached APK using REA 6.5.0 / JADX 0.7.1. This is an independent implementation, not a redistribution of the Android app.

## Official interaction model

The guide describes a home screen with speaker identity and available controls, a PartyUp drawer with drag-to-join/remove, and customizable EQ. Guests initially follow host volume; volume sync restores shared levels after individual adjustments. Privacy and remote activation affect invitations/discovery. The app also offers model-dependent remote power, musical alarms, playlist shortcuts, Megaphone and updates. These descriptions do not establish that every model or Windows supports every function.

## PC coverage after this pass

| Area | Current PC behavior | Evidence / remaining work |
|---|---|---|
| Group setup | Main + up to nine selected guests, Start/Add/Remove/Stop/Check | Two EVERBOOMs tested. Ten physical speakers and older models unaccepted. |
| Drawer interaction | Drag a paired guest into group to join; drag a guest row back to remove; buttons retained | Regression tested routing and harmless clicks; physical drag acceptance still needed. |
| Member control | Selected group row opens that speaker's Sound tab | Same capability/readback gates as normal device selection. |
| Volume sync | Explicit group button always targets main, independent of control dropdown | Source-backed command; not timing correction. Listening acceptance pending. |
| EQ | Advertised presets, five signed bands, 20 PC-local named memories | Save/load/delete validated; loading never writes; Apply EQ sends. Does not alter the speaker's custom-EQ naming format. |
| Battery/name/power off | Existing readback and setters retained | Model-specific acceptance remains in CONTROLS.md. |
| Remote activation/sleep | Existing settings and source-backed choices retained | Setting enabled is distinct from wake success. |
| Wake | Modern BLE request behind explicit preview opt-in | New source-backed implementation, mocked payload/cleanup checks. No hardware wake test. |
| Privacy/persistence/identify/channel | Existing controls retained with feature gates and experimental labels | Channel command acceptance is not proof of stereo acoustics. |
| Windows output | On-demand default multimedia endpoint/container comparison | Read-only live result matched saved main on 2026-10-19. Per-app routing unknown. |
| Lip sync | Guide explains distinction and checks | User reports slight YouTube audio/video offset. No verified speaker-delay setter or global compensation implemented. |
| Alarms | Not implemented | Speaker time, persistence, snooze and music semantics still need independent implementation/testing. |
| Magic Button/playlists | Not implemented | Windows music-service integration is separate from speaker commands. |
| Megaphone | Not implemented | REA initStreams confirms microphone capture, echo/noise processing and audio playback on Android; Windows audio path still needed. |
| Updates | Official app required | No independent verified updater or firmware recovery flow. |

## New REA observations

`CPPDevice.powerOn` dispatches to the BLE flow. `BLEUtilsKt.powerOnCPPDevice` writes AUID followed by the power-on code to the authorize/remote-power characteristic. Its default uses six 02 bytes; `BLEPowerCommand` defines POWER_ON as FF. `BLECharacteristics` identifies the target UUID `5e9bf2a8-f93f-4481-a67e-3b2f4a07891a`. `BLEConnection.sendData` delegates to characteristic write. The independent wake implementation requires acknowledged-write capability and leaves power-on confirmation explicitly unknown.

`MegaphoneManager.initStreams` creates microphone capture, optional echo/noise processing, and a media AudioTrack. This supports treating Megaphone as a Windows audio-routing feature, not adding a guessed Bluetooth opcode.

No APK, raw capture, decompiled method body, or real device identifier belongs in this repo. Method evidence files remain in the private work area. Research did not establish an exhaustive API inventory or prove there is no undiscovered timing control.
