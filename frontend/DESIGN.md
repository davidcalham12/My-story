# The storyMaker panel, visually

The identity is **Qaracter's**. It was not invented here and it is not a matter
of taste on this screen: it is recorded below and held by
`src/shared/ui/tokens.css`, the only file in `src/` allowed to name a colour or
a typeface. `src/shared/ui/identity.test.ts` fails the build on the first one
that appears anywhere else.

That test exists because of a specific failure: the previous panel carried four
oranges, none of them the brand's. A hex code typed into a component is a colour
nobody decided — invisible to a grep for `--primary`, and immune to a redesign.

## Colour

| token | value | what it is for |
|---|---|---|
| `--qr-primary` | `#FF7932` | the one thing on a screen that needs attention: the primary action, a question the check is asking, the band on a new version |
| `--qr-primary-pressed` | `#F4631E` | that action while pressed, and text set in the accent (it carries more contrast on white) |
| `--qr-ink` | `#233441` | body text and titles |
| `--qr-deep` | `#1E2D3D` | dark panels and the active navigation item |
| `--qr-card` | `#F5F5F5` | cards and quiet surfaces on a white page |

Five supporting values are not brand colours and are named as such in
`tokens.css`: `--page`, `--muted`, `--line`, and the three state hues `--fail`,
`--pass`, `--halt`. They are the smallest set that keeps *rewritten*, *stopped*
and *passed* apart.

**Colour is never the only signal.** Every state also carries a word: a field
the check asked about has a left rule *and* the question printed under it; a
halted run says what stopped it in a sentence; a provenance mark carries its
meaning in its `title` and its grade in its class. Someone who sees none of the
colours loses nothing.

Dark is a re-mapping of the same roles, not a second palette. The brand orange
holds its contrast on a dark ground and the pressed orange does not, so on dark
`--primary-pressed` resolves to the brand orange rather than to an invented
value.

## Type

One family, **DM Sans**, loaded from Google Fonts by the single `@import` at the
top of `tokens.css` — the one place the face is named. The stack behind it
(`ui-sans-serif, system-ui, 'Segoe UI', Roboto, sans-serif`) carries the page on
a machine with no network, which the demo laptop may well be: a missing DM Sans
changes the texture and not the layout.

Seven sizes, each with one job. A size without a role is a size someone picks by
eye.

| token | px | role |
|---|---|---|
| `--text-eyebrow` | 12 | the label above a title; table headings |
| `--text-footnote` | 13 | hints, the meaning of a provenance mark |
| `--text-body` | 16 | everything the buyer reads |
| `--text-card-title` | 18 | a card's own heading |
| `--text-lead` | 20 | the one paragraph under a page title; `h2` |
| `--text-figure` | 24 | a number that is the point of its panel |
| `--text-title` | 32 | one per screen |

Line height is `1.2` for headings and `1.55` for everything else. Weights: 400
body, 500 labels, 700 headings and the primary action. No italics except the
word *none* where a value is absent.

## Space

**One step of 4px.** Nothing sits between its multiples:

`--s1 4` · `--s2 8` · `--s3 12` · `--s4 16` · `--s5 24` · `--s6 32` · `--s7 48`

The page gutter is `--s4` and never smaller: 375 − 2×16 is the phone column, and
that is the width every screen is built at first. Corners are `--radius` 10px
for cards and 6px for controls — softly rounded, as §7 of the spec asks.

## Layout

- One column, `--measure` 72ch, centred. The buyer's screens are a conversation,
  not a dashboard.
- **Read** is the exception: a grid that is one column by default and becomes
  `2fr / 1fr` — the book beside its index and character sheet — only above
  900px. The single column is the default and the two-column rule the exception
  precisely so that 375px cannot start scrolling sideways because someone forgot
  a breakpoint.
- Controls are at least 44px tall: a thumb on a phone, not a mouse on a desk.
- Long buyer text (memories, a pasted letter, a dedication) is `.verbatim`:
  wrapped, never truncated, shown exactly as typed.

## Accessibility floor

- `:focus-visible` is a 3px `--focus` outline with 2px offset. It is never
  removed, only replaced by a better one — a keyboard is the only way through
  the interview for some people.
- `prefers-reduced-motion: reduce` flattens every animation and transition.
  Nothing animates today; the rule is the floor, so the first transition anyone
  adds is already covered rather than needing to be remembered.
- Colour never carries meaning alone (above).
- Every screen is built at 375px with no horizontal scroll; tables and the PDF
  viewer are the only things allowed to scroll, each inside its own box.

## What is deliberately not here

No design system package, no icon library, no CSS framework — the panel has
**zero dependencies beyond React and Vite**, and a token file plus 180 lines of
CSS is cheaper than any of them. The PDF is shown by the browser's own viewer
for the same reason.
