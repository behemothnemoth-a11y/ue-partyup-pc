# Local-video timing experiment, 2026-10-19

Owner requested single-speaker versus PartyUp testing before choosing a YouTube-specific fix. No compensation feature was implemented or applied. Repository visibility was verified PRIVATE; no push or publication.

## Method

- Generated an eight-second local H.264/AAC MP4 containing four white flashes and matching synthetic frequency-sweep pulses at 1.0, 2.4, 4.1 and 6.2 seconds. Decoded video confirmed the authored flash onsets. Audio/video stream starts both reported zero.
- Used an isolated headless Chrome profile, with audio enabled, to play the same file. It did not access the owner's browser tabs/profile or YouTube. Video measurements refer to `requestVideoFrameCallback.expectedDisplayTime`, a virtual scheduled presentation, **not a physical screen flash**.
- Verified Windows default multimedia output matched the saved main. Windows/speaker volume and output selection were unchanged. Background workload was not frozen; measured CPU use varied.
- Explicit GroupManager Stop confirmed main broadcasting off for single-speaker passes. Start enabled PartyUp and obtained the guest join acknowledgement for grouped passes. No fresh receiver-list event was observed, and the microphone cannot identify which speaker produced each sound.
- Captured the laptop microphone briefly into RAM. Initial WinMM/direct waveform tests failed detection confidence checks. A per-stream WASAPI RAW path then used packet QPC timestamps without changing global microphone settings. No microphone recording was saved.
- A frequency-pattern detector was checked against three known-delay/reverberation examples and 30 noise-only controls. It has a 2 ms analysis grid; that is **not** a claim of 2 ms end-to-end accuracy. Confidence thresholds were retained even when hardware passes failed.
- After an initial low-confidence A/A/B/B pass, a final A/A/B/B pass used clearer 120 ms pulses at peak amplitude 0.32; this changed the synthetic source, not speaker/Windows volume. Final conditions used the same revised clip.

## Final pass

| Condition | Passes | Accepted pulse detections | Estimated accepted offsets | CPU averages | Video dropped frames |
|---|---:|---:|---|---|---|
| Single main; broadcasting off | 2 | 0 of 8 | No trustworthy estimate | 26.56%, 29.81% | 0, 0 |
| PartyUp enabled; guest join accepted | 2 | 8 of 8 | 640–660 ms after scheduled virtual frames; median 656 ms | 10.69%, 12.13% | 0, 0 |

The grouped local clip produced repeatable detected acoustic arrivals after the scheduled frames. This observation does not depend on YouTube, but it **does not isolate the delay's cause**. It includes player/audio transport, speaker/acoustic path and capture timing; the virtual presentation reference is not the owner's physical display. It must not be used as a YouTube correction value.

The single-speaker recordings did not pass the same confidence gate. Their candidate offsets are deliberately excluded, so no reliable PartyUp-added delta can be claimed. CPU load differed across conditions; these passes do not prove or disprove PC-load causation. Zero dropped frames is a player result, not an audio-glitch or lip-sync certification.

## Final state and limits

PartyUp was left enabled after an acknowledged guest join. Test-player processes and microphone streams were closed. No mouse/keyboard automation, Windows output change, firmware operation, audio-delay setting or browser extension was used. Existing project changes were preserved.

The next discriminating measurement would require a clearer single-main acoustic signal under comparable workload, followed by the same local A/B test. A physical screen-to-sound measurement would additionally need a common recording of the screen and speaker sound. These are measurement requirements, not evidence that YouTube, Windows, the controller, Bluetooth or PartyUp alone caused the reported issue.

Private source clip, instrumentation and numeric reports remain in the owner's `work/` directory, outside this repository. Raw room/microphone audio was not persisted.
