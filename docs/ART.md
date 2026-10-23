# Pixel Party artwork

Original static project asset: `ue_partyup/assets/pixel-party-house.png`.

Generated with the built-in image-generation tool using the user's requested awesome-gpt-image-2 style library. Selected template: **UI Screenshot System**, `ui-screenshot-system`, cases 17, 2, 4. The template informed a decorative asset rather than a flattened UI. All actual controls remain native widgets. No paid API or new runtime dependency was introduced. The original generated PNG is bundled unchanged; Tk displays an integer subsample.

## Generation prompt

Create an original production UI illustration asset for a Windows multi-speaker music controller. Using the awesome-gpt-image-2 UI Screenshot System template (ui-screenshot-system; cases 17, 2, 4) adapted to a decorative header asset, not a whole screenshot.
Subject: a joyful tiny pixel-art house party seen as a side-on dollhouse cross section, three cozy rooms with small portable oval speakers sharing music, a tiny PC in one room, little musical notes and plants. No people needed. Original speaker designs, no logos or branding.
Composition: very wide horizontal banner, 3:1 aspect ratio. Illustrated rooms across the full width, no text, no UI controls, no labels. Perfectly flat dark aubergine background #171426. Warm cream, lavender, mint, peach and amber limited palette. Chunky 16-bit pixel art, hard square pixel edges, small dither shading, handheld-console game charm, crisp silhouettes, readable at 640 by 210 pixels. Pixel-grid alignment, no blur, no gradients, no glossy 3D, no photographic elements, no watermarks. This will be displayed as a static header in a real app with live controls coded separately.


## House Party v0.4.0 assets (2026-10-20)

The owner approved the detailed House Party / Pocket Party mockup and explicitly requested generated assets rather than a simplified implementation. New original assets generated with the built-in image tool, informed by the awesome-gpt-image-2 UI Screenshot System style template (cases 17/2/4):

- ue_partyup/assets/house-party-background.png: wide nighttime dollhouse cross-section, four richly furnished rooms, pixel texture, warm lamps, plum sky, cream/mint/lavender accents. No baked controls or device status. The final wide version supersedes an initial taller background.
- ue_partyup/assets/speaker-peach.png: original portable speaker sprite with transparent background and pixel details.
- ue_partyup/assets/speaker-lavender.png: matching transparent guest-color variation of the peach sprite.

The original generated PNGs are bundled. Rendering trims transparent sprite margins, scales the house with nearest-neighbor sampling, and uses a small bounded image cache. Small sprites use Lanczos to avoid grille aliasing. The illustration is static; all room labels, badges, selection corners and interactive controls are drawn by the application. Pillow 13.0.0 is now a pinned runtime dependency; the earlier no-additional-dependency statement above describes v0.3.0 only.

Silkscreen-Regular.ttf is bundled from the official Google Fonts repository (https://github.com/google/fonts/tree/main/ofl/silkscreen). Its SIL Open Font License is retained alongside it in assets/fonts/OFL-Silkscreen.txt. Windows loads it with FR_PRIVATE for this process, without installing a system font. Artwork and fonts require no runtime network service, account or image generation.

Approved mockup and its saved prompt are local outside the repo: outputs/design-mockups/house-party-pocket-buttons-v1.png and house-party-pocket-buttons-v1-prompt.txt in the chat workspace. Built application fixture previews: house-party-built-v0.4.png and house-party-ten-speakers-v0.4.png in that same folder. Their battery/status values are synthetic. Assets are local/private; nothing was published.

## Music classroom asset — 0.7.0
Built-in image-generation tool; UI Screenshot System style-library reference. Exact prompt: design/classroom-background-v1-prompt.txt. Bundled asset: ue_partyup/assets/classroom-background-v1.png. Static artwork contains ten chairs and music-room props; speaker sprites, selection, status and controls are live application overlays. No generation or network connection is needed at runtime.
