# Remaining Outline Block Types Typed Config Design

## Summary
- Goal: continue the typed block config work in the template workbench by covering the remaining commonly used block types: `number`, `threshold`, `boolean`, and `operator`.
- Scope: template workbench only. No backend contract changes.
- Principle: keep configuration structured and constrained where the runtime semantics are already known, but avoid inventing new schema fields.

## Decision
- `number`
  - Use a numeric input for default value.
  - Keep value stored as string in state/payload for backward compatibility.
  - Hide free-form widget configuration.
- `threshold`
  - Same as `number` for now: numeric default input.
  - Treat threshold as a specialized numeric semantic, not a separate transport shape.
- `boolean`
  - Replace text default input with a true/false selector.
  - Hide multi-value and generic widget config.
- `operator`
  - Use a constrained select of common operators.
  - Persist the chosen operator into `defaultValue`.
  - Keep `options`/`source` hidden; this type is not a dynamic option set.
- `free_text`
  - Keep the current lightweight text-oriented configuration.

## Compatibility
- No schema changes.
- Still serialize into the current `default/options/source/param_id/widget/multi` shape.
- UI becomes stricter, saved payload remains backward compatible.

## Test Focus
- Template workbench page test should verify:
  - `number` and `threshold` use numeric default inputs
  - `boolean` uses a boolean selector
  - `operator` uses a constrained operator selector
  - unrelated fields are hidden for these types
- Existing save and preview behavior must stay green.
