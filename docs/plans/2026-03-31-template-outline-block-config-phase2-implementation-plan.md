# Template Outline Block Config Phase 2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** extend template workbench typed block config to `number`, `threshold`, `boolean`, and `operator`.

**Architecture:** build on the existing typed block editor in `TemplateWorkbench.tsx`, adding block-type-specific controls while keeping serialization backward compatible. Use TDD with page-level tests to drive the exact UI.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Add failing page-level tests

**Files:**
- Modify: `src/frontend/src/pages/TemplateDetailPage.test.tsx`

**Step 1: Write the failing test**
- Extend the fixture template with `number`, `threshold`, `boolean`, and `operator` blocks.
- Add assertions that these render type-specific controls instead of generic text fields.

**Step 2: Run test to verify it fails**

Run: `npm test -- src/pages/TemplateDetailPage.test.tsx`
Expected: FAIL because the current typed editor does not yet render all of those specialized controls.

### Task 2: Implement specialized controls

**Files:**
- Modify: `src/frontend/src/features/template-workbench/TemplateWorkbench.tsx`

**Step 1: Implement minimal code**
- Add specialized UI branches for:
  - `number`
  - `threshold`
  - `boolean`
  - `operator`
- Constrain values without changing the saved payload shape.

**Step 2: Re-run page test**

Run: `npm test -- src/pages/TemplateDetailPage.test.tsx`
Expected: PASS

### Task 3: Regression verification

**Files:**
- Verify existing template workbench tests only.

**Step 1: Run focused tests**

Run: `npm test -- src/pages/TemplateDetailPage.test.tsx src/features/template-workbench/validation.test.ts src/features/template-workbench/preview.test.ts src/features/template-workbench/state.test.ts`
Expected: PASS

**Step 2: Run build**

Run: `npm run build`
Expected: PASS

### Task 4: Commit and push

**Step 1: Commit**

```bash
git add docs/plans/2026-03-31-template-outline-block-config-phase2-design.md docs/plans/2026-03-31-template-outline-block-config-phase2-implementation-plan.md src/frontend/src/pages/TemplateDetailPage.test.tsx src/frontend/src/features/template-workbench/TemplateWorkbench.tsx
git commit -m "feat: add specialized outline block controls"
git push origin master
```
