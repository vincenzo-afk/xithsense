# UI/UX Guidelines

## Design Principles

1. **Clarity over density** — Show the most important pick and reason first. Bury supporting data in an expandable panel.
2. **Confidence signals** — Every recommendation shows a confidence badge. Users must always know how certain we are.
3. **Action-first** — Primary CTA (Generate Team / Lock Captain) is always visible without scrolling.
4. **Speed** — Loading states visible within 100ms. Skeleton loaders for player cards.
5. **Trust** — Show data sources and rule triggers. Never hide why a player was picked.

## Colour Palette (from `frontend/DESIGN_TOKENS.json`)

| Token | Hex | Usage |
|-------|-----|-------|
| `color-primary` | `#6366F1` | Primary actions, active states |
| `color-secondary` | `#F59E0B` | Accents, captain badge |
| `color-success` | `#10B981` | High confidence, good form |
| `color-warning` | `#F59E0B` | Medium confidence, caution |
| `color-danger` | `#EF4444` | Low confidence, poor form |
| `color-bg-base` | `#0F172A` | Dark background |
| `color-bg-surface` | `#1E293B` | Card backgrounds |
| `color-bg-elevated` | `#334155` | Elevated panels |
| `color-text-primary` | `#F8FAFC` | Primary text |
| `color-text-secondary` | `#94A3B8` | Labels, captions |

## Typography

| Scale | Size | Weight | Usage |
|-------|------|--------|-------|
| `text-display` | 36px | 700 | Page titles |
| `text-heading-1` | 24px | 600 | Section headers |
| `text-heading-2` | 18px | 600 | Card titles |
| `text-body` | 14px | 400 | Body content |
| `text-caption` | 12px | 400 | Labels, metadata |
| `text-badge` | 11px | 600 | Confidence badges |

Font: **Inter** (Google Fonts)

## Component States

Every interactive component must have: Default, Hover, Active, Disabled, Loading, Error states.

## Confidence Badge Colours

| Confidence | Label | Colour |
|---|---|---|
| 80–100 | High | `color-success` (#10B981) |
| 60–79 | Medium | `color-warning` (#F59E0B) |
| 40–59 | Low | `color-danger` (#EF4444) |
| 0–39 | Very Low | `#6B7280` (gray) |

## Icon System

Use **Lucide React** for all icons. Size: 16px (inline), 20px (action), 24px (standalone).

## Spacing

4px base unit. Use multiples: 4, 8, 12, 16, 24, 32, 48, 64px.  
Defined in Tailwind config as `space-1` through `space-16`.

## Animation

- Micro-interactions: 150ms ease-out
- Page transitions: 250ms ease-in-out
- Skeleton loaders: pulse animation 1.5s
- Never animate data-heavy components (charts)
