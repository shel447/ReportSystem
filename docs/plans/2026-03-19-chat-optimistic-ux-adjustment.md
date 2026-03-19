# 2026-03-19 Chat Optimistic UX Adjustment

## Scope
- Chat page only.
- No backend API change.
- Keep current chat action protocol.

## Goals
- User text enters message stream immediately after submit.
- Composer clears immediately and becomes non-editable while request is pending.
- Pending state uses icon button, not `发送中...` text.
- Structured parameter submission follows the same optimistic behavior.
- Remove verbose helper copy under the composer.
- Keep welcome message on initial load.
- Remove the large bounded white base from the message stream area.

## TDD Notes
- Add React tests for optimistic message insertion and pending disable state.
- Add static frontend render assertions for removed hint text and new pending button styling hooks.
- Then update ChatPage, ChatActionPanel, and chat page CSS.
