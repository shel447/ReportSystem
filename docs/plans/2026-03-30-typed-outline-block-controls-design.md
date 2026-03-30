# Typed Outline Block Controls Design

## Goal

Refine inline outline editing so block-backed blueprint nodes use lightweight typed controls instead of falling back to generic text editing. The objective is to preserve the dual-layer mapping while improving correctness for time, enum-like, and parameter-reference blocks.

## Scope

This round only changes the outline review editor in chat. Template schema, report generation, and saved instance baseline contracts remain unchanged.

Included:
- `time_range` inline date/date-range control
- `enum_select` / `indicator` / `scope` select-first behavior when options exist
- `param_ref` readonly inline chip with guidance to edit the linked global parameter
- text fallback for all other blocks

Excluded:
- modal editors
- dynamic source loading during outline review
- backend storage shape changes beyond existing string block values
- template workbench redesign

## Approaches

### Option 1: Keep all block edits as free text
- Smallest change
- Fails the product goal because typed blocks still lose structure at the point of user interaction

### Option 2: Full custom editor per block type
- Best UX in theory
- Too heavy for this increment and would duplicate parameter-form complexity inside outline review

### Option 3: Lightweight typed inline controls with text fallback
- Recommended
- Preserves current inline editing model
- Uses existing block metadata (`type`, `widget`, `options`, `param_id`)
- Keeps implementation local to `OutlineTree`

## Design

### Rendering rules
- `param_ref`
  - Render as readonly chip
  - No inline editing
  - Tooltip/text indicates the value comes from a global parameter and should be changed via “返回改参数”
- `time_range`
  - Render as editable chip
  - When editing, show compact date inputs
  - If the block value already looks like a range, split it into `start` / `end`
  - Commit back to the existing string field so backend contracts stay stable
- `enum_select` / `indicator` / `scope`
  - If `options` exists and is non-empty, render a select editor
  - Otherwise fall back to text input
- Everything else
  - Use current text input fallback

### Data flow
- Frontend keeps editing state only in the outline review panel
- Committed block values still update:
  - `outline_instance.blocks[].value`
  - matching `outline_instance.segments[].value`
  - derived `outline_instance.rendered_document`
  - node `display_text`
- Backend remains unchanged in contract terms and continues resolving execution baseline from the edited block values

### Error handling
- Empty dates or half-filled ranges are allowed during editing but committed as the best-effort string
- Select blocks without options degrade to text input instead of failing
- `param_ref` cannot be edited inline, preventing drift from the linked parameter value

### Testing
- Frontend tests must prove each typed behavior renders the right control
- Existing backend tests already prove edited block values flow into `resolved_content`; they should continue to pass unchanged
