# Design Tokens — extracted from iwarranty.ai

> **Source:** `https://iwarranty.ai/` and its stylesheet `/assets/index-CFk8L3NA.css`
> **Method:** headless Chromium (1440×900), `getComputedStyle` over visible elements,
> `document.getAnimations()`, `CSSKeyframesRule` inspection.
> **Date:** 2026-10-22. Raw capture: `e2e/iwarranty/tokens.json`.
> Values below are measurements, not guesses. iWarranty's copy, logo and imagery
> are **not** used anywhere in this app.

---

## 1. Type system

| Role | Family | Size / line-height | Weight | Tracking |
| --- | --- | --- | --- | --- |
| Display / hero | **DM Serif Display**, Georgia, serif | 56px / 1.05 | 400 | −0.02em |
| Section headline | DM Serif Display | 40–54px / 1.1 | 400 | −0.02em |
| Card title | DM Sans | 16px / 1.35 | 600 | normal |
| Body | **DM Sans**, system-ui, sans-serif | 17px / 1.7 | 400 | normal |
| Body small | DM Sans | 14px / 1.63 | 400 | normal |
| UI label / nav | DM Sans | 13px / 1.2 | 500 | normal |
| Eyebrow / micro-label | DM Sans (uppercase) | 11px / 1.2 | 500 | 0.12–0.18em |
| Data / IDs / stats | **JetBrains Mono**, monospace | 10–13px (IDs), 40px (figures) | 400–500 | normal |

Google Fonts: `DM Sans` 400/500/600/700, `DM Serif Display` 400, `JetBrains Mono` 400/500.

Type-scale steps measured on the page: `56 → 40 → 20 → 17 → 16 → 15 → 14 → 13 → 11 → 10.5`.

---

## 2. Colour

| Token | Value | Usage |
| --- | --- | --- |
| canvas | `#FAFAF8` | page background |
| canvas-alt | `#F4F2EE` | alternating sections |
| surface | `#FFFFFF` | cards, header, panels |
| ink | `#0C1A14` | headlines |
| ink-strong | `#0A0A0A` | body text |
| muted | `#5C6B62` | body copy, nav links |
| muted-light | `#8A9991` | captions, meta |
| brand | `#035948` | primary buttons, links, eyebrows |
| brand-hover | `#024438` | primary hover |
| accent | `#0CA789` | live indicators, focus, highlights |
| gold | `#B8965A` | sparing premium accent |
| border | `#E2DDD8` | card + nav borders |
| border-strong | `#D6DDD8` | section dividers |
| border-input | `#C8D4CF` | secondary button / field outline |
| tint | `rgba(3,89,72,0.07)` | active nav, soft chips |
| tint-accent | `rgba(12,167,137,0.08)` | success chips |

Status: success `#0F6B4F`, warning `#9A6B1F`, danger `#B42318`, info `#035948`.
Shadows are green-tinted, never neutral black: `rgba(3,89,72,0.06–0.08)`.

---

## 3. Shape, spacing, elevation

- Radii: **6px** buttons/inputs, **8px** icon tiles, **10px** selectable tiles,
  **12px** media, **16px** cards/panels, **3–4px** status chips.
- Borders: 1px; card `#E2DDD8`; divider `#D6DDD8`; secondary control `#C8D4CF`.
- Card shadow: `0 4px 32px rgba(3,89,72,0.08)`; buttons `0 1px 4px rgba(3,89,72,0.2)`.
- Section padding: 72–80px vertical (120px for hero-scale bands); inner hero
  container ≈1104px at 1440, nav container ≈1200px; nav height 64px.
- Spacing rhythm: 4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 / 64.
- Buttons: height 36–44px, 13px label, 6px radius, `px 18–26px`.
  Primary `#035948` + white; hover `#024438` + `translateY(-1px)`.
  Secondary transparent, `#C8D4CF` border, green text.

---

## 4. Motion language

| Interaction | Timing | Easing | Notes |
| --- | --- | --- | --- |
| Hover colour/border | 150/200/300ms | `cubic-bezier(0.4, 0, 0.2, 1)` | site's dominant curve |
| Button hover lift | 200ms | same | `translateY(-1px)` |
| Card hover | 300ms | same | border + shadow |
| Menu / enter | 200ms | same | `enter` / `exit` keyframes |
| Live dot | 1500ms | linear | `livePulse` opacity/scale loop |
| Status blink | 2000ms | linear | 90–95% keyframe, 400ms stagger |
| Progress loop | 3000ms | linear | 15% → 85% width |
| Claim row enter | 400ms | linear | `translateY(-6px)` → 0 |
| Orbit rings | 18s / 28s | linear | continuous rotation |
| Ambient glow | 4s | linear | opacity 0.18 ↔ 0.32, −2s offset |
| Shimmer | 2.5–3s | linear | background-position sweep |

No GSAP/Framer Motion; all CSS keyframes. Scroll reveals are not used —
entrance motion is short (≤400ms) and state-driven. This app mirrors that:
micro-interactions only, plus a 400ms page/card entrance and stat count-up.

`prefers-reduced-motion: reduce` disables all of it.

---

## 5. Mapping to this app

| App token | Value |
| --- | --- |
| `--color-background` | `#FAFAF8` |
| `--color-surface` | `#FFFFFF` |
| `--color-ink` | `#0C1A14` |
| `--color-muted` | `#5C6B62` |
| `--color-line` | `#E2DDD8` |
| `--color-brand-500` | `#035948` |
| `--color-brand-600` | `#024438` |
| `--color-brand-400` | `#0CA789` |
| `--font-sans` | `"DM Sans", system-ui, sans-serif` |
| `--font-display` | `"DM Serif Display", Georgia, serif` |
| `--font-mono` | `"JetBrains Mono", monospace` |
| `--radius-xl` | `6px` |
| `--shadow-card` | `0 4px 32px rgba(3,89,72,0.08)` |
