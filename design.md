# Design: Doc2Data

The locked system. Every Hallmark run reads this first and pages share it. Change it on purpose; the file is the rule.

## System
- Genre: modern-minimal
- Shape of the first page: app screen, a workbench: setup rail beside the review stage
- Theme: Terrazzo, light colourway (the white specimen sheet)
- Axes: light paper / geometric sans / warm rust · posture: restrained

## Tokens
`frontend/app/tokens.css` is the source of truth. The roles:

```css
:root {
  --color-paper: oklch(96% 0.009 82);  --color-paper-2: oklch(92% 0.012 82);  --color-paper-3: oklch(87.5% 0.014 80);
  --color-plate: oklch(99.5% 0.003 82);
  --color-ink: oklch(16% 0.006 60);  --color-ink-2: oklch(27% 0.006 60);  --color-muted: oklch(46% 0.01 60);
  --color-rule: oklch(81% 0.012 80);
  --color-accent: oklch(53% 0.15 38);  --color-accent-soft: oklch(91% 0.035 45);  --color-accent-ink: oklch(99.5% 0.003 82);
  --color-signal: oklch(45% 0.14 38);  --color-focus: oklch(50% 0.16 38);
  --color-error-ink: oklch(44% 0.16 27);  --color-error-soft: oklch(94% 0.025 30);
  --color-warn-ink: oklch(42% 0.075 75);  --color-warn-soft: oklch(94% 0.03 78);
  --color-ok-ink: oklch(40% 0.08 150);  --color-ok-soft: oklch(94% 0.025 150);
  --font-display: "Syne", ui-sans-serif, sans-serif;  --font-body: "Onest", ui-sans-serif, sans-serif;
  --font-outlier: "JetBrains Mono", ui-monospace, monospace;
  --radius-card: 0;  --radius-pill: 0;  --rule-hair: 1px;  --rule-bar: 2px;
  --shadow-card: 14px 14px 0 var(--color-paper-3);  --shadow-app: 10px 10px 0 var(--color-paper-3);
  --container: 1440px;  --gutter: 64px;  --gap-columns: 32px;
}
```

The spacing scale, easings and durations are the scaffold's and live in `tokens.css`. Type is the app scale, a 1.2 ratio from 16px: 12, 14, 16, 19, 23, 28, 33px, with no fluid display heads.

## Controls
- Primary: ink fill, square, 36px tall with a 44px hit target, paper text. One primary per mode.
- Secondary: 2px ink or muted outline, same square and height; hover is one background step.
- Labels: sentence case in Onest 500, untracked, never uppercase; mono only for codes, filenames, figures and measures.
- Focus: 2px rust outline, instant, offset 2px (inset on inputs). Every interactive element has one.
- States: default, hover, focus-visible, active, disabled (opacity .55 and not-allowed), loading, error (the soft state pair), success from the server only.

## Surfaces
- Paper at 96% under white plates at 99.5%, parted by 2px ink rules; a card carries the hard 10px offset and nothing else casts a shadow.
- One radius: 0 everywhere. No tinted panels, no glass, no gradient washes, no drawn illustration.
- Tables: 2px ink top rule, hairline rows, a pinned key column, a themed thin scrollbar and a 24px right-edge fade.

## Motion
- Character: still. `--dur-micro` on background, border, colour and one 1px press; no reveal, no loop except a button spinner; reduced motion ends everything at once.

## Exports
`frontend/app/tokens.css` in this project; the same file is the Tailwind `@theme static` block. DTCG or shadcn blocks are added here on request, per `export-formats.md`.
