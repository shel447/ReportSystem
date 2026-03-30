# Outline Blocks Typed Config Design

## Summary
- Goal: align template workbench `outline.blocks` configuration with the typed controls already used in chat outline review.
- Scope: template workbench only. No runtime query execution changes.
- Principle: the workbench configures control semantics; chat consumes them. The workbench does not try to reproduce runtime interaction.

## Decision
- Keep `outline.blocks` in the same section-level `蓝图` tab.
- Replace the current generic row inputs with type-aware configuration groups.
- First-class typed config in this increment:
  - `time_range`
  - `indicator`
  - `scope`
  - `enum_select`
  - `param_ref`
- Other types (`threshold`, `operator`, `number`, `boolean`, `free_text`) keep a lightweight generic form.

## Mapping Rules
- `time_range`
  - Use a constrained widget selector instead of free-text `widget`.
  - Supported widgets in workbench: `date`, `date_range`, `relative_range`.
  - Keep `defaultValue` as a string because runtime storage is still string-based.
- `indicator | scope | enum_select`
  - Explicitly choose between `固定选项` and `动态来源`.
  - `固定选项` drives `options[]`.
  - `动态来源` drives `source`.
  - `widget` is derived or constrained; it is no longer a generic free-text field here.
- `param_ref`
  - Only expose the bound global parameter selector.
  - Hide `options`, `source`, and generic widget config.
  - Preserve `defaultValue` as an optional fallback display value, but the primary source is `paramId`.

## Normalization Rules
- When block type changes, clear irrelevant fields immediately.
- Examples:
  - switching to `param_ref` clears `options`, `source`, `widget`
  - switching to `time_range` clears `options`, `source`, sets default widget to `date_range` when empty
  - switching to `indicator | scope | enum_select` keeps either `options` or `source`, never both after save
- Serialization should remain backward compatible with the current template payload shape.

## Validation
- Existing validation remains, but typed UI should make invalid states harder to enter.
- Keep current rules:
  - `param_ref` must bind an existing parameter
  - `indicator | scope | enum_select` require `options` or `source`
- Add UI normalization so users do not need to hand-edit these combinations.

## Test Focus
- Page-level test that `time_range` shows a constrained widget selector and no generic options/source field.
- Page-level test that `param_ref` only shows parameter binding.
- Page-level test that `indicator` can switch between fixed options and dynamic source.
- State serialization/regression must remain compatible.
