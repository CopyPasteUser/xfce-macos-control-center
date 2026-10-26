# Design system

## Product

A compact GTK3 Control Center for XFCE, inspired by the focus and hierarchy of modern macOS Control Center. The panel should feel like one quiet, cohesive surface and remain quick to scan and operate.

## Visual direction

- Dark, opaque window with calm elevated cards and one blue accent.
- Connectivity is grouped in one compact card; state and network name lead, technical values live on detail pages.
- Main controls stay short. Detail pages use the same card, label, icon, and spacing language with a persistent Back action.
- Brightness and volume share one card; audio device and microphone state use compact labeled rows on the Sound page.
- Network diagnostics use fixed label/value rows so addresses scan cleanly and remain selectable.
- Media gives artwork and playback controls priority; the idle state remains a deliberate card.
- Use GTK symbolic icons and the system sans-serif fallback. Avoid decorative symbols and excess labels.

## Runtime tokens

`UI_TOKENS` in `macos-control-center` is the source for the shared GTK CSS values.

| Token | Runtime value |
| --- | --- |
| Background | `#0e1118` |
| Elevated surface | `#1a1f29` |
| Secondary surface | `#242a35` |
| Active surface | `#0d2d4f` |
| Primary text | `#ffffff` |
| Secondary text | `#a7afbf` |
| Accent | `#0a84ff` |
| Warning / error | `#ff453a` |
| Card radius | `16px` |
| Control radius | `12px` |
| Card padding | `12px` |
| Section gap | `10px` |
| Control height | `36px` |
| Small / action / brand icons | `16 / 18 / 24px` |

Theme adaptation stays in `_theme_css`; do not change the opaque GTK window model or apply global desktop theme changes.

## Interaction contract

- Detail navigation is owned by `_navigate_page`. UI actions request navigation; background workers only deliver data to the active page model.
- Every detail page has a Back action that returns to Main. GTK stack transitions are short and respect Reduce Motion.
- Main keeps connectivity, brightness, volume, media, and quick actions compact. Network diagnostics and device lists belong in detail views.
- Disabled controls explain unavailability; hover never carries the only indication of an action.

## Motion

Use brief GTK stack transitions and restrained hover/active feedback. Reduce Motion and animation speed settings remain authoritative.

## Appearance themes

The theme palette is defined by `THEME_TOKENS` and applied by `_theme_css`. Graphite, Midnight,
Frosted Dark, and Light share the same geometry. Every palette supplies an opaque window background,
card/elevated/secondary surfaces, separators, primary/secondary/disabled text, hover and pressed
surfaces, active surface, slider background, accent treatment, and focus treatment. Frosted Dark
uses solid layered colors; the window remains opaque. Accent colors are Blue, Purple, Teal, Pink,
Red, Orange, Yellow, Green, and Graphite.

Settings use compact grouped rows that configure the Control Center itself. Only options backed by
persisted behavior are exposed: appearance and language, quick-action visibility/density, media card
and artwork, motion/focus behavior, and the existing resource/refresh presets. Theme and accent
selection use small color previews. Config values are validated when loaded and saved, and the
config file remains atomically replaced with owner-only permissions.

## Runtime hardening (2026-10-26)

Keep the existing Main composition and Stack routes. Settings currently belongs to the
Main action revealer, not to a separate Stack child; its Back action closes that revealer.
Preview callers must specify `theme:<id>` or `accent:<id>`. Constructor failures produce
a traceback and a translated error toast, and leave the action area reopenable.

Media progress and hiding an idle card are explicit persisted options. Success feedback
can be disabled; error feedback remains visible. All defaults preserve the prior appearance.
Theme palettes also own destructive/warning colors, including readable Light variants.

Backend completions must validate window lifetime and, where requests overlap, request
generation. Polling must not overwrite a pending or newly completed Bluetooth action.
Read-only CLI diagnostics do not create a window, change hardware, signal a resident,
or write persistent application/PulseAudio configuration.
