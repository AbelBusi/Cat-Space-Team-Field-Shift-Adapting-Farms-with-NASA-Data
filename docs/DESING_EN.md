# Design and Frontend Guidelines --- NASA Space Apps Agricultural Project

> **Mandatory compliance document for every AI agent or developer who
> designs, generates, or modifies the interface.**\
> This document defines the visual language, approved color palette,
> animation behavior, and implementation boundaries. If a decision is
> not specified here, do not invent it as if it were a requirement:
> preserve the existing pattern or ask for clarification.

------------------------------------------------------------------------

## 1. Visual Objective

Build a web interface for a project related to agriculture, Earth
observation, and geospatial data. The experience should feel:

-   **Exploratory and contemplative**, taking inspiration from the sense
    of discovery, navigation, and observation found in *Outer Wilds*.
-   **Warm, rural, and approachable**, taking inspiration from
    agriculture, natural cycles, and the visual clarity of *Stardew
    Valley*.
-   **Scientific and functional**, because the interface will display
    data, maps, indicators, anomalies, and results that users must be
    able to interpret accurately.
-   **Handcrafted, not prefab**: it should look like an interface
    designed specifically for this project, not a generic AI-generated
    template.

These references define the **art direction and overall feel**. They do
not authorize copying interfaces, illustrations, characters, logos,
music, maps, distinctive iconography, or copyrighted assets from either
game.

### Guiding Principle

The interface must combine **exploration + nature + scientific data
interpretation**. Atmosphere must never compromise readability, data
accuracy, or usability.

------------------------------------------------------------------------

## 2. Approved Color Palette

### 2.1 Core Colors

These seven colors are the main palette established by the team. They
must be centralized as design tokens and reused. **Do not create
additional base colors or replace these colors with trendy colors,
framework defaults, or AI-generated palettes.**

  -----------------------------------------------------------------------
  Token                   Color                   Usage
  ----------------------- ----------------------- -----------------------
  `--color-background`    `#0B1026`               Main application
                                                  background and deepest
                                                  interface areas.

  `--color-panel`         `#121A3A`               Panels, surfaces,
                                                  navigation, and primary
                                                  containers.

  `--color-border`        `#1E2A52`               Borders, dividers,
                                                  panel boundaries, and
                                                  subtle separation.

  `--color-text-muted`    `#8C9BC4`               Secondary text, labels,
                                                  hints, metadata, and
                                                  low-priority states.

  `--color-text`          `#F2E8D5`               Primary text, headings,
                                                  important values, and
                                                  readable content.

  `--color-turquoise`     `#4FC1B6`               Environmental data such
                                                  as water, humidity,
                                                  quantity, and
                                                  vegetation, or
                                                  positive/neutral
                                                  environmental signals
                                                  depending on context.

  `--color-fire`          `#F2A541`               Warm accent for
                                                  anomalies, selection,
                                                  occasional emphasis,
                                                  and a highlighted data
                                                  series.
  -----------------------------------------------------------------------

### 2.2 Required CSS Tokens

Define the colors in one central location. Do not repeat hexadecimal
values arbitrarily throughout individual components.

``` css
:root {
  --color-background: #0B1026;
  --color-panel: #121A3A;
  --color-border: #1E2A52;
  --color-text-muted: #8C9BC4;
  --color-text: #F2E8D5;
  --color-turquoise: #4FC1B6;
  --color-fire: #F2A541;
}
```

If the project already has a variable or token system, adapt these names
to its conventions without duplicating tokens or creating a second
palette.

### 2.3 Semantic Colors Already Present in the Reference

The reference image also shows specific colors for risk levels and a
fourth category. These are considered **predefined semantic colors for
that visualization**, not permission to expand the general palette.

  ------------------------------------------------------------------------
  Suggested token          Reference sample        Exclusive usage
  ------------------------ ----------------------- -----------------------
  `--risk-low`             `#D7BF8D`               Low risk.

  `--risk-medium`          `#F2A541`               Medium risk.

  `--risk-high`            `#DF6F3D`               High risk.

  `--risk-category-four`   `#A89AE7`               Fourth category, only
                                                   if the domain actually
                                                   requires it.
  ------------------------------------------------------------------------

The values above are visual estimates based on the supplied screenshot.
If the team has the original design values, those original values take
precedence.

**Do not use these semantic colors to decorate buttons, general
backgrounds, cards, text, or elements that do not represent those
states.** Do not create additional risk colors without explicit team
approval.

### 2.4 Permitted Data Gradients

The reference uses gradients only to communicate a continuous scale.
Data gradients derived from the existing palette are allowed:

-   **Quantity (rainfall/humidity):** progression from low to high
    values using shades derived from dark blue and turquoise.
-   **Vegetation (NDVI):** progression from bare soil to dense
    vegetation using shades derived from warm text, turquoise, and
    blue-green.
-   **Anomaly:** progression from cooler/wetter to normal and
    hotter/drier conditions, using shades derived from the base colors
    and warm accent.

Rules:

1.  A gradient must represent a real scale and have identifiable
    endpoints and meaning.
2.  Do not use gradients as decorative backgrounds, headers, buttons, or
    cards.
3.  Do not introduce new saturated colors to make a gradient more
    eye-catching.
4.  The legend must explain what each endpoint represents and, when
    applicable, what the midpoint means.
5.  Do not reverse a scale's meaning without updating its legend.
6.  Values and colors must maintain a consistent relationship across all
    screens.

------------------------------------------------------------------------

## 3. Strict Color Rules

-   The main background must remain dark: `#0B1026`.
-   Main surfaces must use `#121A3A`.
-   Borders must be subtle and use `#1E2A52`.
-   Primary text must use `#F2E8D5`.
-   Secondary text must use `#8C9BC4`.
-   Turquoise must communicate relevant environmental information or
    interaction. It must not become the color of every interface
    element.
-   Orange must be reserved for emphasis, anomalies, and highlighted
    elements. Do not paint the entire interface orange.
-   Do not use pure white (`#FFFFFF`) or pure black (`#000000`) as
    substitutes for the established colors.
-   Do not introduce purple, pink, electric blue, lime green, pure red,
    or other colors on your own initiative.
-   Do not add colors because a library, template, or component includes
    them by default.
-   Do not change the palette to "modernize" it, "improve its visual
    appeal," or make it "more attractive" without authorization.
-   States must also be identified through text, icons, or patterns.
    Color must never be the only signal.

------------------------------------------------------------------------

## 4. Visual Language and Composition

### 4.1 Overall Appearance

-   Dark, restrained, atmospheric interface.
-   A scientific exploration tool in a natural environment.
-   Clean composition with a clear visual hierarchy.
-   Enough spacing to distinguish controls, maps, legends, and data.
-   Square corners or moderate, consistent corner radii.
-   Thin borders, visible only when they help separate areas.
-   Every panel must serve a real purpose; do not wrap every text
    element in a card.
-   Important elements should stand out through position, hierarchy,
    contrast, and context---not exaggerated shadows.

### 4.2 Outer Wilds Inspiration

Use these concepts as inspiration:

-   Exploring an unknown territory.
-   Curiosity and gradual discovery.
-   A sense of scale, orientation, and observation.
-   Restrained cartographic or astronomical details when relevant to the
    project.
-   Transitions that support navigation or the discovery of information.

Do not turn the website into a generic space-themed interface. This is
an agricultural and Earth-focused project: navigation, soil, water,
crops, weather, and satellite observation must remain central.

### 4.3 Stardew Valley Inspiration

Use these concepts as inspiration:

-   Visual warmth and closeness to the agricultural world.
-   A connection to seasons, crops, weather, and natural cycles.
-   Small, deliberate graphic details.
-   The feeling of a tool made for a community rather than a fictional
    corporation.
-   Occasional pixel-art accents in secondary elements, provided they do
    not harm readability.

Do not turn the entire application into pixel art. Do not use pixelated
typefaces for paragraphs, tables, forms, or scientific values. Do not
copy original sprites, characters, icons, scenes, or other game assets.

### 4.4 Required Balance

The influence of both references must remain subtle. Do not mix visual
elements arbitrarily. Priorities are:

1.  Understanding agricultural information.
2.  Usability and accessibility.
3.  Visual identity consistency.
4.  Atmosphere and decorative details.

------------------------------------------------------------------------

## 5. Interface Components and Patterns

### 5.1 Panels and Surfaces

-   Use `--color-panel` for surfaces that need to be distinguished from
    the background.
-   Use `--color-border` for outlines and dividers.
-   Avoid unnecessary nested cards.
-   Do not create a separate card for every data point when the
    information can belong in a section, table, list, or panel.
-   Do not use large shadows or elevation effects as a hierarchy
    mechanism.
-   Do not use blurred transparency to imitate glass.

### 5.2 Buttons

-   Every button must have a clear purpose and action.
-   Maintain a consistent hierarchy between primary, secondary, and
    destructive actions.
-   Use turquoise or orange only when the meaning of the action
    justifies it.
-   Do not turn every button into an accent-colored button.
-   `hover`, `focus`, `active`, and `disabled` states must be visible,
    restrained, and consistent with the palette.
-   Do not use shine, decorative gradients, glowing borders, or bounce
    animations.

### 5.3 Forms and Filters

-   Use visible, understandable labels.
-   Controls must have comfortable dimensions and clearly differentiated
    states.
-   Keep equivalent filters visually consistent.
-   Do not replace labels with ambiguous icons.
-   Do not hide essential information inside tooltips.
-   Geographic and time filters should retain their context when results
    are updated, as long as the existing functional behavior allows it.

### 5.4 Maps and Geographic Visualizations

-   The map is a primary workspace, not a decorative image.
-   Controls must remain grouped and must not cover important geographic
    information.
-   The legend must explain layers, units, ranges, and color meanings.
-   Markers must have consistent semantics.
-   Do not add markers, layers, fictional data, grids, or controls that
    were not requested.
-   Do not use a gradient without a scale and legend.
-   Avoid continuously animating the map or its markers.
-   Layer transitions must be brief and must not block interaction.
-   Do not sacrifice map performance for visual effects.

### 5.5 Charts and Data

-   Each chart must communicate one main idea.
-   Avoid highlighting multiple series simultaneously when one
    highlighted story is sufficient.
-   Use turquoise for environmental series or reference values when
    appropriate.
-   Reserve orange for the specific data point, period, or anomaly being
    highlighted.
-   Axes, units, dates, and legends must be readable.
-   Do not hide important values to achieve a minimalist composition.
-   Do not add 3D effects, shine, decorative gradients, or continuous
    animations.
-   Chart entrance animations must be brief and must not delay reading.

------------------------------------------------------------------------

## 6. Animations and Microinteractions

Animations should reinforce exploration and the feeling of a natural
world. They must not look like effects from an AI-generated landing-page
template.

### 6.1 Permitted Animations

-   Brief panel appearance when a section opens.
-   Smooth transitions when changing tabs or filters.
-   Subtle highlighting of a selected point or data value.
-   Controlled progression when loading a visualization.
-   Subtle movement of environmental decorative elements, only if they
    are already part of the approved design.
-   Map or layer transitions when they help users understand a change.
-   Button and control microinteractions that confirm user input.

### 6.2 Motion Rules

-   Prefer short transitions, generally between 120 and 250 ms for
    controls.
-   Use longer durations only for context transitions that justify them.
-   Prefer natural easing curves (`ease-out`, `ease-in-out`).
-   Avoid bouncing, excessive elasticity, and abrupt movement.
-   Do not animate every element when a page loads.
-   Do not make elements float continuously.
-   Do not use intense parallax or motion that distracts from maps or
    charts.
-   Do not introduce animations that delay access to an action.
-   Respect `prefers-reduced-motion` and provide an equivalent
    experience without non-essential motion.

### 6.3 Animation Prohibitions

Do not implement any of the following on your own initiative:

-   Floating particles across the entire screen.
-   Permanently animated star backgrounds.
-   Decorative nebulae, waves, or glowing color blobs.
-   Custom cursors with effects.
-   Typewriter effects for headings or content.
-   Staggered entrance animations for every item in a list.
-   Buttons that continuously pulse, breathe, or glow.
-   Cards that flip, jump, or rise excessively.
-   Continuously moving backgrounds.
-   Loading animations that imply an operation when no real operation is
    taking place.

------------------------------------------------------------------------

## 7. Explicitly Prohibited Visual Effects

Do not use the following unless the team explicitly authorizes them:

-   Glassmorphism or frosted-glass panels.
-   Neumorphism.
-   Decorative gradients on backgrounds or buttons.
-   Glow, neon, shine, or luminous borders.
-   Large, diffuse, or multiple shadows.
-   Abstract colored spheres, blobs, or stains.
-   Mesh, noise, or generated patterns used only to fill empty space.
-   Generic AI-style purple-to-blue gradients.
-   Excessive transparency and blur.
-   Repeated rounded cards for absolutely everything.
-   Emoji icons as replacements for interface iconography.
-   Stock illustrations that provide no information.
-   Oversized hero sections with generic marketing slogans.
-   Invented counters, metrics, or charts used as decoration.
-   Scroll effects that hijack or hinder navigation.

------------------------------------------------------------------------

## 8. Typography and Iconography

-   Prioritize readability on desktop and mobile screens.
-   Use a consistent type family throughout the interface.
-   Reserve pixel-art-style fonts for very specific details, never for
    long-form content or data.
-   Maintain a clear hierarchy between headings, subtitles, labels,
    values, and helper text.
-   Avoid tiny text in legends, scales, and map controls.
-   Use consistent iconography from a single visual style.
-   Do not arbitrarily mix outline icons, solid icons, emoji, and
    decorative symbols.
-   Icons must communicate a recognizable action or category.
-   Do not replace important text with an icon unless an accessible
    label or alternative is provided.

Do not introduce a new typeface or icon library without first reviewing
the project's existing dependencies and conventions.

------------------------------------------------------------------------

## 9. Responsive Design

The interface must work on desktop, tablet, and mobile devices.

-   Do not assume the user has a large screen.
-   On mobile, rearrange panels and controls without removing essential
    features.
-   Prevent legends, filters, or controls from covering the map's usable
    area.
-   Long tables must have a defined responsive strategy; do not compress
    them until they become unreadable.
-   Maintain comfortable touch targets.
-   Avoid horizontal scrolling across the entire page.
-   Keep the same visual identity across screen sizes.
-   Do not create a visually different mobile version unless there is a
    functional need.

------------------------------------------------------------------------

## 10. Accessibility and Data Readability

-   Maintain sufficient contrast between text and surfaces.
-   Do not rely exclusively on color to communicate risk, anomalies, or
    status.
-   Accompany important states with text, an icon, or a pattern.
-   Keep keyboard focus visible.
-   Controls must have accessible labels.
-   Non-essential animations must be reducible.
-   Legends must explain units and ranges.
-   Charts should provide equivalent information through text, a table,
    or a description when necessary.
-   Do not use `--color-text-muted` for critical information if its
    contrast is insufficient.
-   Do not reduce contrast to achieve a more atmospheric appearance.

------------------------------------------------------------------------

## 11. Implementation Rules for AI Agents

These rules take priority over aesthetic preferences inferred by the
agent.

### 11.1 Before Making Changes

1.  Inspect the current project structure.
2.  Identify the framework, libraries, styling system, reusable
    components, and existing conventions.
3.  Review components related to the task before creating new ones.
4.  Identify functional areas that must not be altered.
5.  Preserve the existing architecture and patterns unless the user
    explicitly requests a change.

### 11.2 While Implementing

-   Work only within the requested scope.
-   Reuse existing components and tokens.
-   Keep structure, styles, and logic separated according to the
    project's current organization.
-   Do not duplicate components that already perform the same function.
-   Do not add dependencies to solve something that can be handled with
    existing tools.
-   Do not change the framework, architecture, routes, or state
    management without authorization.
-   Do not replace real data with fictional data.
-   Do not invent endpoints, features, fields, states, or business
    rules.
-   Do not modify API contracts or data models for visual reasons.
-   Do not alter functional behavior while making a design change.
-   Do not add unnecessary comments or in-code documentation unless
    requested.
-   Do not rename files, change paths, or restructure files outside the
    requested scope.
-   Do not implement "extra" features because they seem useful.

### 11.3 When Information Is Missing

-   Do not assume a visual idea is a functional requirement.
-   Do not invent states or categories to complete a screen.
-   Do not invent colors.
-   Do not invent content, metrics, sample data, or results.
-   If an essential decision is missing, ask before implementing it.
-   If the missing detail does not prevent progress, preserve the
    existing pattern and state the decision made.

### 11.4 Before Finishing

Verify that:

-   Only the approved colors and permitted derivatives were used.
-   Components remain visually consistent.
-   No prohibited effects were added.
-   Animations are functional, brief, and reducible.
-   The interface is responsive and readable.
-   Existing logic was not altered.
-   No unrequested features, data, colors, or dependencies were added.
-   No temporary styles, arbitrary values, or fictional data remain.
-   The result matches the reference and the requested scope.

------------------------------------------------------------------------

## 12. Visual Acceptance Criteria

An implementation is considered aligned with this guide only if every
item below is satisfied:

-   [ ] It uses the seven established core colors.
-   [ ] Risk colors are used only for their semantic categories.
-   [ ] Gradients represent data scales only and are derived from the
    approved palette.
-   [ ] The interface retains the defined dark background and panel
    colors.
-   [ ] Text hierarchy is clear and readable.
-   [ ] The composition communicates exploration, nature, and
    agricultural analysis without literally imitating the reference
    games.
-   [ ] There is no glassmorphism, neon, glow, or decorative gradients.
-   [ ] Cards, shadows, and rounded borders are not overused.
-   [ ] Animations do not distract or block interaction.
-   [ ] Geographic and scientific information takes priority over
    decoration.
-   [ ] The interface adapts to different screen sizes.
-   [ ] No unrequested features, data, colors, or dependencies were
    added.

------------------------------------------------------------------------

## 13. Final Instruction for the Agent

**Do not freely redesign the product. Do not fill requirements with your
own visual trends. Do not add elements just because they "would look
good."**

Treat this guide as the visual contract. Respect the palette, hierarchy,
patterns, and restrictions. Creativity should be expressed through
composition, details, and microinteractions within these
boundaries---not by creating a new visual identity.

When a request conflicts with this guide, follow the user's most recent
explicit instruction for that specific task. Do not extend that
exception to other screens or components.
