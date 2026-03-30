# ReportTemplate Outline Blueprint Dual-Layer Design

> Date: 2026-03-30
> Scope: Align `ReportSystemV2` with latest `ReportTemplate` dual-layer template definition

## Summary

The latest `ReportTemplate` definition introduces a user-facing `outline` blueprint (`document + blocks[]`) at section level, while keeping the system-facing execution chain (`content / datasets / presentation / subsections`). In `ReportSystemV2`, these two layers must coexist in the same section node and maintain explicit correspondence.

## Core Principles

1. A template section owns both layers at the same time.
2. `outline` is the user-facing intent blueprint.
3. `content/datasets/presentation` is the internal executable chain.
4. They are bound explicitly through section identity and `{@block_id}` references.
5. Instance generation first materializes blueprint values, then resolves the execution chain.

## Template-Level Model

Each section keeps:
- `title`
- `description`
- `foreach`
- `outline`
- `content`
- `subsections`

`outline` contains:
- `document`
- `blocks[]`

System-internal block extensions are allowed in `ReportSystemV2` to support UI and structured chat collection:
- `options`
- `source`
- `param_id`
- `multi`
- `widget`

## Mapping Rules

### Section-Level Mapping

Blueprint and execution chain are attached to the same section node. We do not maintain separate blueprint and execution trees.

### Token Namespaces

- `{param_id}`: global template parameter
- `{$varname}`: foreach iteration variable
- `{@block_id}`: current section blueprint block

`{@block_id}` may be referenced in:
- `section.title`
- `section.description`
- `datasets[].source.query`
- `datasets[].source.description`
- `datasets[].source.prompt`
- `presentation.template`
- `presentation.anchor`
- `ai_synthesis.knowledge.*`

### Scope Rules

- `{param_id}`: visible to the whole template
- `{$varname}`: visible to current foreach node and descendants
- `{@block_id}`: visible to current section and descendants
- Block ids may not be redefined in the same visible path

## Runtime Model

During outline review, we materialize an instance-level blueprint tree rather than a plain text outline.

Each node carries:
- `node_id`
- `section_ref`
- `display_text`
- `outline_instance`
- `execution_bindings`
- `dynamic_meta`
- `children`

`outline_instance` contains:
- `document_template`
- `rendered_document`
- `segments`
- `blocks`

`execution_bindings` record where each block is referenced in the execution layer.

## Chat Flow

Report generation becomes:
1. template matching
2. required global parameter collection
3. outline materialization
4. outline enrichment
5. outline review
6. generation

Block collection is primarily handled during outline review, not during the initial global parameter form.

## Template Workbench

Section detail uses three tabs:
- `蓝图`
- `执行链路`
- `同步状态`

Preview supports:
- `蓝图预览`
- `执行预览`
- `JSON`

## Implementation Phases

### Phase 1
- Add section `outline` to backend schema and frontend types
- Add outline blueprint editor to template workbench
- Add validation for blueprint blocks and references

### Phase 2
- Add blueprint materialization service for chat outline review
- Make outline review prefer blueprint-derived nodes

### Phase 3
- Add execution binding graph and structured outline editing payload

### Phase 4
- Resolve confirmed blueprint into report instance execution baseline

## Compatibility

- Existing legacy templates remain readable
- Existing v2 sections without `outline` continue to work
- `date` parameter input type remains as a `ReportSystemV2` compatibility extension
