# Chat Fixed Composer Design

## Background

The current chat page widened the main workspace and removed redundant top framing, but the composer still lives in the normal document flow. As a result, it scrolls away with the page, which breaks the expected chat interaction model. The user wants the input area to remain visible at the bottom of the viewport at all times.

## Goals

1. Keep the chat composer visible at the bottom of the browser viewport while the user scrolls.
2. Keep the composer aligned with the main content column instead of covering the sidebar.
3. Prevent the fixed composer from obscuring the latest messages.
4. Limit the change to the chat page so other pages keep their current layout behavior.

## Non-goals

- No backend changes.
- No changes to chat workflow or message semantics.
- No cross-page sticky/fixed footer system.

## Approved Decisions

- The composer should be fixed to the viewport, not just sticky within the chat panel.
- The fixed composer should align with the chat content width and sidebar offset.
- The message stream should reserve bottom space equal to the composer height.
- Only the chat page should adopt this behavior.

## Design

### Layout behavior

The chat page will keep the current `ConversationLayout`, but the composer region will render inside a viewport-fixed shell:

- `position: fixed`
- bottom-aligned to the viewport
- horizontally aligned to the main content column
- constrained by the chat content width, not the full window

The notices and message stream remain in the normal page flow.

### Width and offset strategy

The fixed composer must not overlap the sidebar. The chat page therefore needs the current content column geometry:

- left offset
- width

Those values should be derived from the actual `.page-body` element at runtime rather than hard-coded. This keeps the composer aligned even if shell padding changes.

### Bottom reservation

Because the composer is fixed, the message stream needs bottom padding equal to the rendered composer height plus a small gap. That padding should be driven by measured DOM height, not a guessed constant, so the layout stays correct when the composer wraps or the viewport changes.

### Responsive behavior

On narrow screens, the fixed composer still stays visible, but it should use the available content width without assuming a desktop sidebar offset. The same measurement approach should handle this automatically.

## Testing

- Frontend test: chat page renders a dedicated fixed-composer container.
- Frontend test: chat page exposes a reserved bottom offset for the stream wrapper.
- Backend text regression: chat styles contain fixed composer rules and a stream spacer rule.
- Browser verification:
  - composer remains visible while scrolling
  - latest messages are not obscured
  - sidebar stays uncovered
