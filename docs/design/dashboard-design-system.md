# LogSentinel Dashboard Design System

The implementation reference is `docs/design/logsentinel-dashboard-concept.png` at 1586×992.

## Visual tokens

- Main canvas: cool near-white `#F7F9FC`; surfaces: true white `#FFFFFF`.
- Navigation: graphite navy `#0B1728`; primary accent: electric blue `#0B6CFB`.
- Text: ink `#142033`; muted text `#637083`; border `#DCE3EC`.
- Semantic colors: anomaly red `#E3242B`, warning orange `#FF8A00`, low amber `#F4BF24`, ready green `#10A66A`.
- Radius: 8–10px; shadows are minimal; structure comes from 1px borders.
- Spacing follows an 8px base scale with compact, breathable operational density.
- Typography uses a Swiss-style sans-serif stack; dashboard chrome is 12–14px, body 14–16px, section headings 16–18px.

## Component and container rules

- One dark left navigation rail and one open main canvas; no marketing hero.
- Timeline and incident table share the primary wide work surface.
- Selected incident uses a persistent right detail panel.
- Benchmark, threshold, drift, and onboarding regions are restrained bordered surfaces, not decorative cards.
- Tables, controls, labels, metrics, and chart text remain code-native.
- Active navigation and selected rows use a pale-blue field with blue emphasis.
- Icons are simple consistent line icons; Streamlit text symbols are avoided where a native control exists.

## Visible-copy lock

Above the fold: `LogSentinel`, `Environment`, `Model version`, `Model status`, `Overview`, `Incidents`, `Benchmarks`, `Drift`, `Onboarding`, `Anomaly timeline`, `Replay`, `Upload logs`, `Severity filter`, `Top incidents`, and `Selected incident`.

