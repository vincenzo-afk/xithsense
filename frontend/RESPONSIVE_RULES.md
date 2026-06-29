# Responsive Design Rules

## Breakpoints

| Name | Min Width | Tailwind prefix |
|------|-----------|----------------|
| Mobile | 0px | (default) |
| Tablet | 640px | `sm:` |
| Desktop | 1024px | `lg:` |
| Wide | 1280px | `xl:` |

## Layout Grid

- Mobile: 4-column grid, 16px gutter
- Tablet: 8-column grid, 24px gutter
- Desktop: 12-column grid, 32px gutter

## Component Responsive Behaviour

| Component | Mobile | Tablet | Desktop |
|-----------|--------|--------|---------|
| Navigation | Bottom tab bar | Top navbar + sidebar | Full sidebar |
| Team Display | Vertical list | 2-column grid | Pitch layout (visual positions) |
| Player Card | Full width, compact | Half width | 1/3 width, expanded |
| Match Header | Stacked | Side-by-side teams | Side-by-side + full details |
| Chart | 100% width, reduced height | 100% width | 60% width |
| Captain Cards | Vertically stacked | Row of 3 | Row of 3 |

## Touch Targets

Minimum 44×44px for all interactive elements on mobile.

## Font Scaling

- Mobile: base 14px
- Tablet+: base 15px
- Desktop: base 16px

Use `text-sm` (14px) as default in components; override per breakpoint if needed.
