# Canvas App Plan

## Mode
CREATE

## App Requirements
Build a single screen "Mes demandes" for a Takaful insurance company canvas app
("Assurances At-Takafulia"). The app is connected live via the canvas-authoring MCP
coauthoring session (already connected). The app is currently blank (one empty
`Screen1` with 3 empty containers). The screen shows the connected agent's own
requests (`Demandes`), sorted by submission date descending, with status badges,
urgency indicator, type/service metadata, and a relative "time ago" label. No
navigation to a Detail screen exists yet — cards are not clickable.

## Working Directory
`C:\Windows\System32\mes-demandes`

## Discovery Summary
- Controls used: `GroupContainer` (Variant: `AutoLayout`) for all layout containers,
  `Gallery` (Family: Classic, Variant: `Vertical`) for the list of requests, `Badge`
  (status pill), `ModernText` (all text), `Rectangle` (accent bar + left urgency stripe).
- `ModernCard` was evaluated and rejected for the request card — it does not expose an
  arbitrary `Children` slot needed to compose the multi-field card (urgency stripe +
  title + badge + type + service + relative date). A `GroupContainer` (AutoLayout,
  Horizontal) is used instead as the card root; since the card is not clickable
  (no Detail screen exists), `GroupContainer`'s lack of `OnSelect` is not a blocker.
- Data sources: `Demandes` (primary, queried directly with `Filter`/`SortByColumns`),
  `Types_Demandes` and `Services_Siege` are connected but **not** queried directly by
  this screen — `Demandes.Type_Demande_ID.Value` and `Demandes.Service_Actuel_ID.Value`
  already resolve the lookup display value.
- Connectors: none used by this screen.
- No mock data / local collections are used — `Demandes` is queried live.

## Data Source Schemas

### Demandes
Live SharePoint list, queried directly by the screen. Relevant columns (as confirmed
in the approved plan):

| Column | Type | Notes |
|--------|------|-------|
| `Title` | String | Request title, shown as card title |
| `Date_Soumission` | DateTime | Submission date; used for sort and relative date |
| `Statut_Actuel` | Record (Choice) | Use `.Value` for the status text (`Soumis`, `En cours`, `Validé`, `Rejeté`, `Clôturé`) |
| `Niveau_Urgence` | Record (Choice) | Use `.Value`; real choices are `Faible`/`Normal`/`Urgent`/`Critique` — `"Urgent"` or `"Critique"` drives the red urgency stripe (`"Élevé"` does NOT exist) |
| `Type_Demande_ID` | Record (Lookup) | Use `.Value` for the display text |
| `Service_Actuel_ID` | Record (Lookup) | Use `.Value` for the display text |
| `Agent_Demandeur` | Record (Person) | Use `.Email` to filter to the connected user (`User().Email`) |

### Types_Demandes
Connected data source. Not queried directly on this screen (referenced only through
`Demandes.Type_Demande_ID.Value`).

### Services_Siege
Connected data source. Not queried directly on this screen (referenced only through
`Demandes.Service_Actuel_ID.Value`).

## API Details
None — no connectors are used on this screen.

## Screens
| Screen | File | Purpose | Key Controls |
|--------|------|---------|--------------|
| MesDemandes | MesDemandes.pa.yaml | Personal view of the connected agent's requests, sorted by date | GroupContainer (AutoLayout), Gallery (Vertical), Badge, ModernText, Rectangle |

This screen replaces/renames the existing empty `Screen1`. `App.pa.yaml` has already
been updated with `StartScreen: =MesDemandes`.

## Aesthetic Direction
- Palette: Clean & Professional — sober corporate insurance (Takaful) look. Emerald
  green is the single accent/brand color; white/very light gray backgrounds; white
  cards with light shadow and 12px rounded corners; generous padding; restrained
  typography hierarchy.
- Primary background: `RGBA(249,250,251,1)` (very light gray) — screen background.
- Accent color: `RGBA(6,95,70,1)` (emerald green) — title text, accent bar.
- Card background: `RGBA(255,255,255,1)` (white).
- Text primary (title): `RGBA(6,95,70,1)` for the "Mes demandes" title; card titles
  use default dark text at `FontWeight.Bold`.
- Text secondary: `RGBA(107,114,128,1)` (gray) — small header line, meta text.
- Text tertiary: `RGBA(156,163,175,1)` (lighter gray) — relative date, empty state.
- Urgency accent: `RGBA(220,38,38,1)` (red) — left stripe on cards where
  `Niveau_Urgence.Value = "Urgent" || Niveau_Urgence.Value = "Critique"`
  (corrected 2026-07-04: the column's real choices are Faible/Normal/Urgent/Critique — "Élevé" never existed).
- Layout strategy: AutoLayout throughout (`GroupContainer`, Variant `AutoLayout`),
  Vertical direction for the screen/header/content stacks, Horizontal direction for
  the card root (stripe + content side by side). Responsive Tablet/Web format.
- Typography scale: header line 12px normal gray; title 28px bold emerald; card
  title 16px bold; body/meta text 12–14px normal; relative date 12px gray.

## Named Variables and Shared State
No local/global variables are required — the screen queries `Demandes` directly in
the Gallery's `Items` property and derives the empty-state condition from the
Gallery's own `AllItems` row count (`CountRows(GalleryDemandes.AllItems) = 0`). No
`OnVisible` state initialization is needed.

App-level named formulas (already written to `App.pa.yaml`, available to every
screen as global constants — reference these instead of re-typing raw `RGBA()`
values):
- `ColorAccent` = `RGBA(6,95,70,1)`
- `ColorBackground` = `RGBA(249,250,251,1)`
- `ColorTextSecondary` = `RGBA(107,114,128,1)`
- `ColorTextTertiary` = `RGBA(156,163,175,1)`
- `ColorCardWhite` = `RGBA(255,255,255,1)`
- `ColorUrgent` = `RGBA(220,38,38,1)`

Screen builders may use these named formulas directly (e.g. `Fill: =ColorAccent`) or
the literal `RGBA(...)` values — both are equivalent; use named formulas for
consistency where convenient.

## Control Definitions

> Note on sourcing: property names below are grounded in (a) the properties
> explicitly confirmed and specified in the approved plan (which was validated
> against the live MCP coauthoring session by the orchestrating skill prior to this
> planning pass — e.g. Gallery's Classic family / Vertical variant, Badge's
> `Content`/`Appearance`/`BasePaletteColor`/`FontColor` properties), and (b) the
> documented common/AutoLayout property patterns in `TechnicalGuide.md`. Do not add
> properties beyond what is listed here — if a property is not listed for a control
> below, treat it as unavailable and find an alternative approach within these
> definitions.

### GroupContainer (Variant: AutoLayout)
Used for: `ScreenContainer`, `HeaderContainer`, `GalleryContainer`, per-item
`CardContainer` (Horizontal), and the card's inner `ContentContainer` (Vertical),
and the thin urgency-stripe container.

Properties available for this control/variant:
- `X`, `Y` — position (not used under pure AutoLayout except at the root)
- `Width`, `Height` — size; required alongside `FillPortions: =0` for fixed-size
  containers (e.g. the 4px urgency stripe)
- `Fill` — background color
- `LayoutDirection` — `=LayoutDirection.Vertical` or `=LayoutDirection.Horizontal`
- `LayoutAlignItems` — `=LayoutAlignItems.Start` / `Center` / `End` / `Stretch`
- `LayoutJustifyContent` — `=LayoutJustifyContent.Start` / `Center` / `End` /
  `SpaceBetween` / `SpaceAround` / `SpaceEvenly`
- `LayoutGap` — spacing between children (numeric)
- `LayoutOverflowX`, `LayoutOverflowY` — `=LayoutOverflow.Hidden` / `Scroll` /
  `Visible`
- `PaddingTop`, `PaddingBottom`, `PaddingLeft`, `PaddingRight` — container padding
- `RadiusTopLeft`, `RadiusTopRight`, `RadiusBottomLeft`, `RadiusBottomRight` —
  corner radius (used on the card root and the accent bar's parent if needed)
- `BorderColor`, `BorderThickness`, `BorderStyle` — for subtle card border
- `DropShadow` — `=DropShadow.Semilight` / `Regular` / `Heavy` for card elevation
- `Visible` — boolean visibility
- `DisplayMode`
- Child-level layout properties (set on each child control inside an AutoLayout
  parent): `FillPortions` (proportional sizing; set `=0` for fixed-size children),
  `AlignInContainer`, `LayoutMinWidth`, `LayoutMinHeight`, `LayoutMaxWidth`,
  `LayoutMaxHeight`

### Gallery (Family: Classic, Variant: Vertical)
Used for: `GalleryDemandes`, the single list of request cards.

Properties available for this control/variant:
- `Items` — data source formula (`Filter`/`SortByColumns` over `Demandes`)
- `TemplateSize` — pixel height of one template unit (Gallery lays out multiples of
  this per item); not required when the card uses AutoLayout auto-sizing, but keep
  available if a fixed template height is needed
- `TemplatePadding` — spacing between gallery items
- `TemplateFill` — background of each template slot
- `Layout` — `=Layout.Vertical`
- `WrapCount` — `=1` for a single-column vertical list
- `Width`, `Height` — size; `Height` uses the dynamic pattern
  `=CountRows(Self.AllItems) * Self.TemplateHeight`
- `X`, `Y`
- `Fill` — background color of the gallery control itself
- `AllItems` — read-only; all rows currently in `Items` (used for the empty-state
  check and the dynamic height formula)
- `Visible`, `DisplayMode`
- `LoadingSpinner`, `LoadingSpinnerColor`
- `TransitionDuration`
- `DelayItemLoading`

No `OnSelect` navigation is used on this screen (cards are not clickable — no Detail
screen exists yet).

### ModernText
Used for: header line, title, card title, badge is a separate control (see Badge),
type line, service line, relative date line, empty-state message.

Properties available for this control:
- `Text` — the string/formula to display
- `Size` — font size (numeric)
- `FontWeight` — `=FontWeight.Bold` / `Semibold` / `Normal` / `Lighter`
- `FontColor` — `=RGBA(...)` or named formula
- `Align` — `=Align.Left` / `Center` / `Right` / `Justify`
- `VerticalAlign` — `=VerticalAlign.Top` / `Middle` / `Bottom`
- `AutoHeight` — `=true` so multi-line/meta text expands without a scrollbar
- `Width`, `Height`, `X`, `Y`
- `Visible`
- `FillPortions` — set on children of AutoLayout containers

### Rectangle
Used for: the emerald accent bar under the title, and the thin (4px) left urgency
stripe on each card.

Properties available for this control:
- `Fill` — `=RGBA(...)`; for the urgency stripe:
  `=If(ThisItem.Niveau_Urgence.Value = "Urgent" || ThisItem.Niveau_Urgence.Value = "Critique", ColorUrgent, RGBA(255,255,255,0))`
- `BorderColor`, `BorderThickness`, `BorderStyle`
- `RadiusTopLeft`, `RadiusTopRight`, `RadiusBottomLeft`, `RadiusBottomRight` —
  rounded corners on the accent bar
- `Width`, `Height`, `X`, `Y`
- `Visible`
- `FillPortions` — `=0` when given a fixed `Width`/`Height` inside an AutoLayout
  parent (required per TechnicalGuide, otherwise the container overrides the size)

### Badge
Used for: the status pill inside each card (`Statut_Actuel.Value`).

Properties available for this control (as specified and confirmed in the approved
plan):
- `Content` — the displayed text, e.g. `=ThisItem.Statut_Actuel.Value`
- `Appearance` — `='BadgeCanvas.Appearance'.Tint` if the enum name requires
  escaping, otherwise `=BadgeAppearance.Tint` — use `Tint` appearance so the
  explicit `BasePaletteColor`/`FontColor` pair below fully controls the look
- `BasePaletteColor` — the light background color per status (see mapping below)
- `FontColor` — the dark text color per status (see mapping below)
- `Size`
- `Visible`
- `Width`, `Height`, `X`, `Y`
- `FillPortions` — set on Badge as a child of an AutoLayout container

**Do not use the `ThemeColor`/semantic color enum on Badge** — set
`BasePaletteColor` and `FontColor` explicitly via `Switch()` to hit the exact
client-required RGBA values below (they do not correspond to a built-in theme
color).

## Per-Screen Specifications

### MesDemandes
- **File:** `MesDemandes.pa.yaml`
- **Purpose:** Personal, read-only view of the connected agent's own `Demandes`
  (requests), sorted newest first, with status badge, urgency indicator, type,
  service, and a relative submission date.
- **Layout:** Pure AutoLayout, no ManualLayout anywhere on the screen.
  - `ScreenContainer` (`GroupContainer`, Variant `AutoLayout`)
    - `LayoutDirection: =LayoutDirection.Vertical`
    - `Width: =Parent.Width`, `Height: =Parent.Height`
    - `LayoutOverflowY: =LayoutOverflow.Scroll`
    - `Fill: =ColorBackground` (`RGBA(249,250,251,1)`)
    - Children:
      1. `HeaderContainer` (`GroupContainer`, Variant `AutoLayout`, Vertical,
         generous `PaddingTop`/`PaddingBottom`/`PaddingLeft`/`PaddingRight`, e.g.
         24–32px)
         - `TxtBrand` (`ModernText`): `Text: ="Assurances At-Takafulia"`,
           `Size: =12`, `FontColor: =ColorTextSecondary`
           (`RGBA(107,114,128,1)`), `FontWeight: =FontWeight.Normal`,
           `AutoHeight: =true`
         - `TxtTitle` (`ModernText`): `Text: ="Mes demandes"`, `Size: =28`,
           `FontWeight: =FontWeight.Bold`, `FontColor: =ColorAccent`
           (`RGBA(6,95,70,1)`), `AutoHeight: =true`
         - `RectAccentBar` (`Rectangle`): `Width: =56`, `Height: =4`,
           `FillPortions: =0`, `Fill: =ColorAccent`, `RadiusTopLeft: =2`,
           `RadiusTopRight: =2`, `RadiusBottomLeft: =2`,
           `RadiusBottomRight: =2`
      2. `GalleryContainer` (`GroupContainer`, Variant `AutoLayout`, Vertical,
         `FillPortions: =1`, `LayoutOverflowY: =LayoutOverflow.Scroll`,
         `PaddingLeft`/`PaddingRight` matching header padding)
         - `GalleryDemandes` (`Gallery`, Family Classic, Variant `Vertical`)
           - `Items: |-`
             ```
             =SortByColumns(
               Filter(Demandes, Agent_Demandeur.Email = User().Email),
               "Date_Soumission",
               SortOrder.Descending
             )
             ```
           - `Height: =CountRows(Self.AllItems) * Self.TemplateHeight`
           - `Width: =Parent.Width`
           - `Layout: =Layout.Vertical`
           - `WrapCount: =1`
           - `TemplatePadding: =14` (gap between cards, 12–16px range)
           - `Fill: =RGBA(0,0,0,0)` (transparent — background shows through from
             `ScreenContainer`)
           - Template (card), per item:
             - `CardContainer` (`GroupContainer`, Variant `AutoLayout`,
               `LayoutDirection: =LayoutDirection.Horizontal`, `Width:
               =Parent.TemplateWidth` or `=Parent.Width`, `Fill: =ColorCardWhite`,
               `RadiusTopLeft: =12`, `RadiusTopRight: =12`,
               `RadiusBottomLeft: =12`, `RadiusBottomRight: =12`,
               `DropShadow: =DropShadow.Semilight`, `AutoHeight`-equivalent via
               AutoLayout content sizing)
               - `RectUrgencyStripe` (`Rectangle`): `Width: =4`,
                 `FillPortions: =0`,
                 `Fill: =If(ThisItem.Niveau_Urgence.Value = "Urgent" || ThisItem.Niveau_Urgence.Value = "Critique", ColorUrgent, RGBA(255,255,255,0))`,
                 `RadiusTopLeft: =12`, `RadiusBottomLeft: =12`,
                 `RadiusTopRight: =0`, `RadiusBottomRight: =0`
               - `ContentContainer` (`GroupContainer`, Variant `AutoLayout`,
                 `LayoutDirection: =LayoutDirection.Vertical`, `FillPortions: =1`,
                 generous `PaddingTop`/`PaddingBottom`/`PaddingLeft`/`PaddingRight`
                 (16–20px), `LayoutGap: =6`)
                 - `TxtCardTitle` (`ModernText`): `Text: =ThisItem.Title`,
                   `FontWeight: =FontWeight.Bold`, `Size: =16`,
                   `AutoHeight: =true`
                 - `BadgeStatut` (`Badge`):
                   - `Content: =ThisItem.Statut_Actuel.Value`
                   - `Appearance: =BadgeAppearance.Tint`
                   - `BasePaletteColor: |-`
                     ```
                     =Switch(
                       ThisItem.Statut_Actuel.Value,
                       "Soumis", RGBA(229,231,235,1),
                       "En cours", RGBA(219,234,254,1),
                       "Validé", RGBA(209,250,229,1),
                       "Rejeté", RGBA(254,226,226,1),
                       "Clôturé", RGBA(219,226,254,1),
                       RGBA(229,231,235,1)
                     )
                     ```
                   - `FontColor: |-`
                     ```
                     =Switch(
                       ThisItem.Statut_Actuel.Value,
                       "Soumis", RGBA(55,65,81,1),
                       "En cours", RGBA(30,64,175,1),
                       "Validé", RGBA(6,95,70,1),
                       "Rejeté", RGBA(153,27,27,1),
                       "Clôturé", RGBA(30,27,120,1),
                       RGBA(55,65,81,1)
                     )
                     ```
                 - `TxtType` (`ModernText`):
                   `Text: =\"Type : \" & ThisItem.Type_Demande_ID.Value`,
                   `Size: =13`, `AutoHeight: =true`
                 - `TxtService` (`ModernText`):
                   `Text: =\"Service : \" & ThisItem.Service_Actuel_ID.Value`,
                   `Size: =13`, `AutoHeight: =true`
                 - `TxtRelativeDate` (`ModernText`): `Size: =12`,
                   `FontColor: =ColorTextTertiary`, `AutoHeight: =true`,
                   `Text: |-`
                   ```
                   =With(
                     {
                       _hrs: DateDiff(ThisItem.Date_Soumission, Now(), TimeUnit.Hours)
                     },
                     If(
                       _hrs < 24,
                       "il y a " & _hrs & If(_hrs = 1, " heure", " heures"),
                       With(
                         {_days: RoundDown(_hrs / 24, 0)},
                         "il y a " & _days & If(_days = 1, " jour", " jours")
                       )
                     )
                   )
                   ```
         - `TxtEmptyState` (`ModernText`, sibling of `GalleryDemandes` inside
           `GalleryContainer`): `Text: ="Aucune demande pour le moment."`,
           `FontColor: =ColorTextTertiary`, `Size: =14`,
           `Align: =Align.Center`, `AutoHeight: =true`,
           `Visible: =CountRows(GalleryDemandes.AllItems) = 0`
- **Key Controls:** `ScreenContainer`, `HeaderContainer`, `TxtBrand`, `TxtTitle`,
  `RectAccentBar`, `GalleryContainer`, `GalleryDemandes`, `CardContainer`,
  `RectUrgencyStripe`, `ContentContainer`, `TxtCardTitle`, `BadgeStatut`,
  `TxtType`, `TxtService`, `TxtRelativeDate`, `TxtEmptyState`.
- **Data Binding:** `GalleryDemandes.Items` queries `Demandes` directly via
  `Filter(Demandes, Agent_Demandeur.Email = User().Email)` wrapped in
  `SortByColumns(..., "Date_Soumission", SortOrder.Descending)`. No collections,
  no context variables.
- **Navigation:** None. No `OnSelect` navigation on cards or elsewhere — there is
  no Detail screen to navigate to.
- **State:** None. No `OnVisible` initialization required; empty state is derived
  directly from `CountRows(GalleryDemandes.AllItems) = 0`.

## TechnicalGuide Key Conventions
- Every formula must start with `=`. Multi-line formulas use the `|-` block
  scalar with the `=` on the first content line (see `Items`, `BasePaletteColor`,
  `FontColor`, and `TxtRelativeDate.Text` above — all multi-line).
- Strings containing `: ` must be quoted as a full YAML string, e.g.
  `Text: ="Type : " & ThisItem.Type_Demande_ID.Value` — the `"Type : "` literal is
  already inside a quoted Power Fx string so it is safe; if a raw `Label: value`
  pattern were ever needed as a bare value it would need outer quoting.
- Power Fx record literals (e.g. `{Value: "x"}`) are **not** used anywhere in this
  screen — all choice/lookup fields are read via `.Value` on the field, not
  constructed as literals, so this pitfall does not apply here.
- Escape enum/option-set names containing spaces or special characters with `'`.
  `Statut_Actuel.Value`, `Niveau_Urgence.Value`, `Type_Demande_ID.Value`, and
  `Service_Actuel_ID.Value` are plain text comparisons (`=`), not option-set enum
  references, so no escaping is needed for the `Switch()`/`If()` comparisons above.
- AutoLayout rules (mandatory for this screen — pure AutoLayout, no ManualLayout
  anywhere):
  - Every fixed-size child of an AutoLayout container (the urgency stripe
    `Rectangle`, the accent bar `Rectangle`) must set `FillPortions: =0`, or the
    parent will silently override the fixed `Width`/`Height`.
  - Flexible children that should grow to fill space (`ContentContainer` inside
    the card, `GalleryContainer` inside `ScreenContainer`) use
    `FillPortions: =1`.
  - Set `LayoutOverflowY: =LayoutOverflow.Scroll` on `ScreenContainer` and/or
    `GalleryContainer` (choose one scroll owner — do not nest two scrollbars).
  - Dynamic Gallery height: `Height: =CountRows(Self.AllItems) * Self.TemplateHeight`.
  - Set `AutoHeight: =true` on every `ModernText` in this screen so multi-line/meta
    text expands without clipping or showing scrollbars.
  - Do not mix ManualLayout properties (`X`, `Y` as primary positioning) inside any
    AutoLayout container.
- Date formatting: format specifiers must be lower case (`mm` not `MM`) if `Text()`
  with a date format string is ever used; this screen uses `DateDiff`/`RoundDown`
  arithmetic instead of a formatted date string, per the approved plan.
- Named formulas: `App.pa.yaml` already defines `ColorAccent`, `ColorBackground`,
  `ColorTextSecondary`, `ColorTextTertiary`, `ColorCardWhite`, `ColorUrgent` in
  `App.Properties.Formulas` — reference these directly from the screen file
  (they are globally available, no import needed).
