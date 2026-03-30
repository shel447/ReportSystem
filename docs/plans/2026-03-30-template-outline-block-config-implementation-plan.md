# Template Outline Block Config Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** make template workbench `outline.blocks` configuration typed and aligned with chat outline block controls.

**Architecture:** keep the existing section-level blueprint editor, but replace generic block row inputs with a type-aware config form. Normalize block fields on type changes so saved payloads stay coherent and current validation rules become easier to satisfy.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Write failing workbench UI tests

**Files:**
- Modify: `src/frontend/src/pages/TemplateDetailPage.test.tsx`

**Step 1: Write the failing test**
- Add a test covering `time_range`, `indicator`, and `param_ref` block config UI.
- Assert:
  - `time_range` shows a widget selector with `date_range`
  - `param_ref` shows parameter binding but not dynamic source/options input
  - `indicator` can switch between fixed options and dynamic source modes

**Step 2: Run test to verify it fails**

Run: `npm test -- src/pages/TemplateDetailPage.test.tsx`
Expected: FAIL because the current workbench still renders generic block inputs.

### Task 2: Implement typed block config UI

**Files:**
- Modify: `src/frontend/src/features/template-workbench/TemplateWorkbench.tsx`
- Modify: `src/frontend/src/styles/pages.css`

**Step 1: Implement minimal code**
- Add block type helpers.
- Replace generic row form with typed config sections.
- Add block type normalization on type changes.
- Keep serialization compatible with existing state.

**Step 2: Run page test to verify it passes**

Run: `npm test -- src/pages/TemplateDetailPage.test.tsx`
Expected: PASS

### Task 3: Add normalization regression tests

**Files:**
- Modify: `src/frontend/src/features/template-workbench/validation.test.ts`

**Step 1: Write failing test**
- Cover the normalized save shape for a typed block after editing.

**Step 2: Run test to verify it fails**

Run: `npm test -- src/features/template-workbench/validation.test.ts`
Expected: FAIL if normalization is missing or inconsistent.

**Step 3: Implement minimal code**
- Add any missing normalization helpers in `TemplateWorkbench.tsx` or `state.ts` only if required.

**Step 4: Re-run test**

Run: `npm test -- src/features/template-workbench/validation.test.ts`
Expected: PASS

### Task 4: Full verification and commit

**Files:**
- Verify only relevant frontend files and docs.

**Step 1: Run focused frontend verification**

Run: `npm test -- src/pages/TemplateDetailPage.test.tsx src/features/template-workbench/validation.test.ts src/features/template-workbench/preview.test.ts`
Expected: PASS

**Step 2: Run build**

Run: `npm run build`
Expected: PASS

**Step 3: Commit**

```bash
git add docs/plans/2026-03-30-template-outline-block-config-design.md docs/plans/2026-03-30-template-outline-block-config-implementation-plan.md src/frontend/src/pages/TemplateDetailPage.test.tsx src/frontend/src/features/template-workbench/TemplateWorkbench.tsx src/frontend/src/features/template-workbench/validation.test.ts src/frontend/src/styles/pages.css
git commit -m "feat: add typed template outline block config"
git push origin master
```
