"""User-facing control inventory, separate from device capability detection."""
from dataclasses import dataclass

UE_GUIDE = 'https://support.logi.com/hc/en-us/articles/22067951753751-Getting-Started-UE-EVERBOOM'


@dataclass(frozen=True)
class GuideEntry:
    name: str
    status: str
    page: str | None
    detail: str


FEATURE_GUIDE = (
    GuideEntry('PartyUp / add and remove speakers', 'Available', 'Group',
               'Choose the main speaker receiving Windows audio, then up to nine guests. '
               'Drag a speaker from the drawer into Your group to join, or drag a guest back to remove it. '
               'Buttons provide the same actions. Only the two EVERBOOMs have hardware acceptance; ten-speaker groups remain untested.'),
    GuideEntry('Group volume sync', 'Available; listening check needed', 'Group',
               'UE says guests initially follow host volume and can then be adjusted individually. '
               'Sync group volume sends the recovered synchronization command to the main speaker. It is not audio/video timing correction.'),
    GuideEntry('Volume / EQ / custom memories', 'Available when readback succeeds', 'Sound',
               'Controls become available when the selected speaker responds. Volume and EQ apply on slider release. '
               'Only advertised EQ presets are offered. Save up to 20 named EQ memories on this PC; loading a memory changes sliders only. '
               'Press Apply EQ to send it. Band values are protocol levels, not dB.'),
    GuideEntry('Name / battery / power off', 'Available when supported', 'Speaker',
               'Read controls loads the selected speaker’s name and battery. Rename changes its Bluetooth name. '
               'Power off affects that speaker immediately; Silent suppresses its shutdown sound.'),
    GuideEntry('Outdoor Boost', 'Readback unresolved on this pair', 'Sound',
               'The official EVERBOOM app offers Outdoor Boost. Our source-backed setter exists, but the tested speaker has not returned '
               'a usable value. The switch stays disabled rather than showing an invented state.'),
    GuideEntry('Remote activation / sleep timer', 'Available when supported', 'Speaker',
               'Remote activation allows remote functions while the speaker is in standby, at a battery cost. '
               'Changing that setting does not itself wake a powered-off speaker. Sleep choices are 15, 30, 60, 180 minutes or Never.'),
    GuideEntry('Playback / skip', 'Available; player support varies', 'Speaker',
               'Controls relay Bluetooth media commands through the selected speaker to the chosen PC Bluetooth source. '
               'A command acknowledgement is not proof the media player acted on it.'),
    GuideEntry('Public / private / persistent group', 'Available when supported', 'PartyUp settings',
               'Public visibility lets a speaker be invited to a party. UE documents double-pressing a private guest’s Bluetooth button '
               'to authorize an invitation. Remote activation must be on for its official PartyUp discovery. '
               'Persistent group stores grouping behavior; power-cycle acceptance remains outstanding.'),
    GuideEntry('Identify / left, right, center', 'Source-backed; acceptance pending', 'Group',
               'Select a guest row to control that speaker or assign Left, Right or Center. Channel command acceptance does not prove stereo '
               'separation. Identify in PartyUp settings sends an LED signal. Apollo balance is a separate experimental control.'),
    GuideEntry('Power on from standby', 'Opt-in preview; hardware test pending', 'Speaker',
               'Enable preview BLE wake, then press Wake speaker. The recovered modern EVERBOOM request requires remote activation '
               'and an acknowledged-write characteristic. An acknowledged BLE write does not independently confirm power-on. '
               'Older-model wake paths remain unimplemented.'),
    GuideEntry('Magic Button / playlists', 'Research needed', None,
               'UE maps a hardware button to playlists with platform-specific music-service integration. '
               'The official guide lists Amazon Music, Apple Music on iOS and Spotify on Android. '
               'No Windows account or playlist integration is currently implemented.'),
    GuideEntry('Alarms', 'Research needed', None,
               'UE’s musical alarm includes speaker time, music selection and persistent configuration. '
               'A PC timer is not equivalent. No alarm writes are currently sent.'),
    GuideEntry('Megaphone', 'Research needed', None,
               'UE broadcasts the phone microphone while music plays. Windows needs a separate microphone/audio routing path. '
               'This app does not open a microphone or create a live monitoring loop.'),
    GuideEntry('Firmware updates', 'Official app required', None,
               'Use the official app for speaker firmware updates. This controller does not download or write firmware.'),
    GuideEntry('Video / YouTube lip sync', 'Player-side adjustment', None,
               'Audio/video offset differs from cutting or echo between speakers. Bluetooth and grouping can add playback delay; '
               'we have not measured it or established a PartyUp delay command. Sync group volume does not fix this. '
               'First check that Windows audio targets the selected main speaker, then compare the same video with one speaker and the group. '
               'Players such as VLC offer audio-track synchronization; no global delay slider is applied here.'),
)
