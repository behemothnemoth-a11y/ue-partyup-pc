# PartyUp PC 0.7.5 — experimental Windows alpha



Public experimental prerelease approved by the owner.



Independent UE speaker music-group controller with a pixel-art music classroom, one main teacher and nine guest seats, volume/EQ tools and local preset memories. Tested with two EVERBOOMs only. Older models and larger groups are experimental/unverified.



Playback safeguards block guest control connections and persistent-group changes during active PartyUp. This restricts affected features; it does not resolve the underlying interruptions. Stop PartyUp explicitly before guest controls. Missing membership reports remain unknown. See README for all limits.



Windows x64 folder bundle; extract the whole archive, run Install Private.cmd, then open PartyUp PC from Start. No Python or admin rights required. Unsigned. No account, telemetry or automatic updates. Close the old controller before opening an update. User settings persist separately. Keep the prior version for manual rollback.



Affected controls are disabled while PartyUp is active or group state is unchecked. Inline text explains the restriction; stop and Check group to unlock. Main controls remain available. No safeguard popup is required. Backend state checks remain in place.


## Known limitations

- Tested with two EVERBOOMs only; ten physical speakers and older models are unverified.
- Guest controls and Remember group are disabled during active or unchecked PartyUp. Stop then Check group to unlock. Underlying audio-interruption causes remain unresolved.
- Missing receiver reports mean unknown membership. Listen to confirm audio.
- Outdoor lookup may time out; stereo-balance readback is undecoded. Actual wake/sleep timing, power-cycle persistence and acoustic channel behavior lack complete acceptance.
- No measured lip-sync correction; grouped music is not discrete surround sound.
- Unsigned Windows x64 app. Installation was tested on the development host with isolated app data, not a second machine. No automatic updater.
- Firmware/reset, alarms, mobile streaming integrations and megaphone are not implemented.

202 automated tests passed. Owner confirmed disabled controls and both EVERBOOMs playing. No account, telemetry or automatic diagnostic upload. Source is MIT licensed; retained dependency/font notices included. Independent project, not affiliated with Logitech or Ultimate Ears.

Download PartyUpPC-0.7.5-alpha-win64.zip and its checksum. Extract everything, run Install Private.cmd (the installer retains its development filename), then open PartyUp PC from Start. No Python/admin rights required. Close the previous controller before updating. Retain the prior version for manual rollback. Review unsigned-app security prompts deliberately. Do not share raw captures, APKs, device addresses or credentials in issues.
