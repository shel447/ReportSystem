# Professional Workbench UX Redesign

## Background

The current React frontend fixed the previous dark and cluttered visual style, but it still behaves like a direct translation of the earlier single-file UI. The result is visually brighter but structurally rough:

- the shell and page body both render the same page title, creating duplicate headings on core pages
- content proportions are unstable, especially on the chat page where the conversation area is too small while the composer is oversized
- list-and-detail flows are forced into the same screen for templates and instances, so the left rail is cramped and the detail area feels like a field wall
- cards, banners, list items, and detail blocks use similar visual weight, so primary and secondary information are hard to distinguish
- new pages can easily drift because page-level layout, width rules, and local headings are not constrained by shared layout primitives

This redesign targets a professional workbench UX: restrained, precise, and task-oriented. It keeps the persistent sidebar, preserves the existing `/api/*` contracts, and reuses the current React + Vite frontend.

## Goals

1. Make the application feel like a coherent professional data product instead of a stitched set of cards.
2. Remove duplicate titles and stabilize hierarchy across all pages.
3. Give the chat flow a dominant single-column workspace suited for long-form interaction.
4. Split browsing and editing/detail work into separate pages for templates and instances.
5. Refactor the frontend so future pages inherit the same structure instead of reinventing local layout rules.

## Non-goals

- No backend business logic changes.
- No API contract redesign.
- No visual template builder or charting upgrade.
- No PDF work in this round.

## Approved Product Decisions

### Overall direction

- Visual direction: professional workbench.
- Sidebar: persistent.
- Chat page: message flow takes the main width.
- Template management: list page first, then navigate into a dedicated detail page.
- Instance management: follow the same list -> detail model.

## Information Architecture

### Shell responsibilities

The shell owns the single page-level title. It should not force downstream pages to repeat that title inside the page body.

The shell continues to provide:

- persistent sidebar navigation
- top header with page title and workspace chip
- bottom-left feedback and settings entry

The shell should become visually lighter and more infrastructural. It frames the workspace but should not compete with the content.

### Page families

The frontend should standardize on three page families:

1. Conversation pages
- single dominant content column
- persistent action/composer region inside the primary surface
- lightweight support banners and flow indicators

2. List pages
- browsing-focused, card or row list layout
- summary metadata visible before navigation
- no heavy detail editors embedded in the list page

3. Detail pages
- summary header
- operation bar
- grouped detail sections with clear primary/secondary emphasis

Each page chooses exactly one family. Local pages should not compose their own high-level layout from scratch.

## Core Page Designs

### Chat page

The chat page becomes a single-column workspace.

#### Structure

- shell title only: `对话助手`
- page intro bar with a short description and a compact flow strip:
  - `模板匹配 -> 补参 -> 确认 -> 生成 -> 下载`
- narrow warning banners for settings and request errors
- one primary conversation surface containing:
  - message stream
  - embedded action panels for `ask_param`, `review_params`, `download_document`
  - bottom composer

#### UX rules

- remove the current hero card; it duplicates explanation without helping the task
- message stream gets the widest readable width on the page
- composer height is reduced substantially and should auto-expand within a bounded range rather than starting as a large text block
- assistant action panels remain in-stream so the workflow stays conversational
- support copy and status banners are visually quieter than the conversation itself

### Templates

Templates move from a cramped split editor to two pages.

#### `/templates`

Purpose: browse and enter.

Displays:

- page intro
- `新建模板` primary action
- list/grid of template summary cards
- each card shows name, type/scene, and structural summary such as parameter count and section count

This page should not display the full editor.

#### `/templates/new` and `/templates/:templateId`

Purpose: create or edit one template.

Displays:

- summary header with template name, key metadata, and top-level actions
- grouped sections:
  - basic information
  - parameter summary / parameter JSON
  - section summary / section JSON
  - legacy compatibility fields
- actions are aligned in a stable top bar, not floating in card corners

The detail page should read like a focused editing workspace, not a generic admin form.

### Instances

Instances adopt the same list -> detail separation.

#### `/instances`

Purpose: browse and choose an instance.

Displays:

- list of instances with template name, status, update time, and concise state markers
- no embedded chapter detail on this page

#### `/instances/:instanceId`

Purpose: inspect and operate on one instance.

Displays:

- instance summary header
- metadata panel
- input parameter panel
- document operations
- chapter accordion list

#### Section panel behavior

Chapters remain accordion-based, but the information hierarchy changes:

- top level: chapter title, description, status chips
- body: main markdown content first
- debug information collapses into a secondary nested section so it does not visually compete with the chapter narrative

## Layout System

### Title hierarchy

- shell renders the only page-level heading
- page bodies use intro text and section titles, not repeated page names
- section titles are local only and must describe the contained block, not restate the route title

### Shared layouts

Introduce explicit layout primitives:

- `PageIntroBar`: intro description plus optional actions
- `ContentFrame`: central width control and spacing contract
- `ConversationLayout`: single-column conversation skeleton
- `ListPageLayout`: list-page skeleton
- `DetailPageLayout`: detail-page skeleton

These primitives replace page-specific top-level layout assembly.

### Width strategy

Different content types need different width rules:

- conversation width: wide but readable
- form width: moderate, optimized for scanning fields
- list width: stable card/row width for browsing
- data width: allows wider tables and debug content without shrinking the whole page

These should be promoted into shared tokens/utilities instead of repeated local `max-width` decisions.

## Visual System

### Tone

The new look should be lighter and more controlled, but not decorative. It should resemble a serious operations or analysis workbench.

### Components by weight

Use three visual weights:

1. primary workspace surface
- for conversation body, major detail blocks, main edit surfaces

2. secondary grouped surfaces
- for metadata groups, summary groups, nested content sections

3. tertiary utility surfaces
- for inline actions, debug blocks, filters, hints

This prevents every card from looking equally important.

### Inputs and lists

- inputs must share consistent label spacing, control height, and helper text rhythm
- JSON editors should be isolated in their own grouped area, not mixed into basic metadata rows
- list cards need a fixed information pattern so browsing is predictable
- active states should be clear but not loud

## Routing and State

Frontend routes expand to:

- `/chat`
- `/templates`
- `/templates/new`
- `/templates/:templateId`
- `/instances`
- `/instances/:instanceId`
- existing `/documents`, `/tasks`, `/settings`

No backend routing changes are required.

Template and instance data fetching can continue to use TanStack Query, but list and detail concerns should be separated by route instead of combined inside a single page component.

## Testing Strategy

This work should be implemented with TDD.

Key regression expectations:

- app shell renders one page-level heading per route
- chat page no longer renders duplicate route title inside the page body
- template list page does not embed the full editor
- template detail page handles create and edit flows by route
- instance list page does not embed chapter detail
- instance detail page renders chapter content and nested debug disclosure
- existing chat flow behavior remains available

Verification should include:

- targeted Vitest route/component tests
- full `npm test`
- `npm run build`
- backend regression tests to ensure static serving remains intact

## Implementation Notes

- keep the current React architecture and improve it instead of rewriting again
- prefer extracting shared layout and composition components before doing broad visual changes
- move pages away from generic `PageSection` title duplication by shrinking `PageSection` responsibilities or replacing it where necessary
- keep the sidebar persistent and visually lighter than the main workspace
- favor editing the core pages first, then unify `documents`, `tasks`, and `settings` with the new shell/layout rules
