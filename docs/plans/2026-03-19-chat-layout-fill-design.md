# Chat Layout Fill Design

## Background

The recent professional workbench redesign fixed the previous dark and heavy UI, but it left two layout problems unresolved:

- the chat page still spends too much vertical space on non-essential framing, including a top description block and a workflow strip
- the shared list, detail, and conversation layouts still cap content width too aggressively, so most pages leave a large blank area on the right side

The result is a UI that feels cleaner than before, but still undersized and spatially inefficient. The most visible symptom is the chat page, where the conversation area does not use the available workspace and the top support content dilutes the main task.

## Goals

1. Make the chat conversation surface occupy most of the available main content width.
2. Remove all non-essential top framing from the chat page.
3. Reduce the visual weight of warning and status messaging on the chat page.
4. Eliminate the shared width caps that create large right-side blank space across pages.

## Non-goals

- No backend API changes.
- No chat workflow behavior changes.
- No new page-level information architecture changes beyond width and top-framing cleanup.

## Approved Product Decisions

- Remove the chat page top explanation entirely.
- Remove the numbered workflow strip entirely.
- Keep only necessary alerts on the chat page, and make them thinner than the main conversation surfaces.
- Widen the chat workspace close to the available shell width.
- Apply the same width relaxation to all shared page layouts so the right-side blank area disappears application-wide.

## Design

### Chat page

The chat page should render only the actual work surface:

- warning banners when needed
- the conversation stream
- the composer

The page body should no longer render:

- route-level duplicate explanation text
- workflow overview copy
- the `1 2 3 4 5` step strip

The conversation surface remains a single-column layout, but it should span the main workspace instead of stopping at a narrow fixed maximum width.

### Shared layout widths

The current `list`, `detail`, and `conversation` layout primitives all apply page-width caps. Those caps made sense when the shell and cards were first introduced, but they now create persistent right-side dead space. The new rule is:

- page layouts should use the full available width of the main content column
- local components can still constrain specific content blocks for readability, but top-level page layouts should not do so

This keeps wide workspaces wide while still allowing individual message bubbles, forms, and tables to define their own readable widths.

### Status messaging

Chat warnings should remain visible, but they should not visually compete with the message stream. The current status banner treatment is too tall for this page. The replacement is a slimmer inline banner with tighter padding and lower emphasis.

## Testing

- Frontend test: the chat page no longer renders the workflow strip or top workflow copy.
- Frontend test: the chat page still renders the welcome message and can send a message through the chat API.
- Backend regression test: shared layout CSS no longer contains the old narrow `max-width` rules for list/detail/conversation layouts.
