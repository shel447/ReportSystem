# Outline Confirmation Structured-Edit Downgrade Design

## Summary
- Goal: in outline confirmation, users can edit both structured variable segments and surrounding free text.
- Rule: if the edit only changes structured segment values, the blueprint stays intact; if the edit changes static text, the node degrades into a plain freeform sentence.
- UX: structured variable segments remain visually distinct, but source hints move to hover tooltips instead of always-visible helper text.

## Behavior
- Structured node, edit variable only:
  - preserve `outline_instance`
  - update segment/block values
  - keep structured generation path
- Structured node, edit static text:
  - clear `outline_instance`
  - mark node as freeform override
  - drop execution bindings / structured content on merge
  - generation falls back to freeform leaf behavior
- Parameter-sourced segments are still editable in outline confirmation.

## UI
- Block chips stay visually distinct from plain text.
- `param_ref` chips use a hover tooltip for source information instead of visible `来自参数 ...` text.
- Clicking non-block text in a structured sentence enters whole-sentence edit mode.

## Backend
- Add an explicit node-level marker for degraded freeform overrides.
- Merge logic must clear structured execution data when that marker is present.
