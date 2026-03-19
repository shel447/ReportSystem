# 2026-03-19 Chat Pending Indicator Adjustment

## Scope
- Chat page only.
- No backend API change.

## Goals
- Remove residual hover highlight from the chat stream surface.
- Show a subtle assistant pending indicator inside the message stream while a response is in flight.
- Keep optimistic user message insertion and disabled composer/action controls.

## TDD Focus
- Add frontend tests for pending indicator appearance/disappearance.
- Add static CSS/render assertions for hover override and pending indicator classes.
- Then update chat page rendering and styles.
