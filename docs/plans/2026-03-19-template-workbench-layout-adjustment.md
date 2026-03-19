# Template Workbench Layout Adjustment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Adjust the template workbench so the parameter workbench spans the full page width and legacy compatibility/json inspection moves into the structural preview card as a tab.

**Architecture:** Keep the existing template workbench state model and only change layout composition and preview-card interaction. Remove the standalone compatibility card, add preview tabs, and move save actions into a dedicated footer so layout concerns stay separate from editor state.

**Tech Stack:** React, TypeScript, Vitest, CSS modules-by-feature, FastAPI static serving.

---

### Task 1: Lock the new UI behavior with tests

**Files:**
- Modify: `src/frontend/src/pages/TemplateDetailPage.test.tsx`
- Modify: `src/backend/tests/test_frontend_chat_render.py`

**Step 1: Write the failing test**
- Assert the template detail page shows preview tabs.
- Assert the old standalone `兼容迁移` card title is gone.
- Assert switching to `模板 JSON` reveals compatibility copy and read-only JSON.
- Assert the parameter workbench root carries the full-width layout class.

**Step 2: Run test to verify it fails**

Run: `npm test -- src/pages/TemplateDetailPage.test.tsx`
Expected: FAIL because tabs/full-width class do not exist yet.

**Step 3: Update lightweight static render checks**
- Adjust `test_frontend_chat_render.py` so it verifies the new tab labels and the removed standalone compatibility heading pattern.

**Step 4: Run targeted tests**

Run: `python -m unittest src/backend/tests/test_frontend_chat_render.py -v`
Expected: FAIL or PASS aligned with new assertions after UI implementation.

**Step 5: Commit**

```bash
git add src/frontend/src/pages/TemplateDetailPage.test.tsx src/backend/tests/test_frontend_chat_render.py
git commit -m "test: cover template workbench preview tabs"
```

### Task 2: Implement the layout and preview tab changes

**Files:**
- Modify: `src/frontend/src/features/template-workbench/TemplateWorkbench.tsx`
- Modify: `src/frontend/src/features/template-workbench/templateWorkbench.css`

**Step 1: Add preview tab state**
- Introduce local tab state for `structure` and `json`.
- Default to `structure`.

**Step 2: Remove the standalone compatibility card**
- Move compatibility copy, validation list, and JSON viewer into the preview card under the `模板 JSON` tab.

**Step 3: Make parameters full width**
- Mark the parameter workbench card with a dedicated class.
- Update grid CSS so it spans the full row.

**Step 4: Add a footer save action**
- Keep save semantics unchanged but move the action row out of the removed compatibility card into a dedicated footer row.

**Step 5: Run targeted tests**

Run: `npm test -- src/pages/TemplateDetailPage.test.tsx`
Expected: PASS.

**Step 6: Commit**

```bash
git add src/frontend/src/features/template-workbench/TemplateWorkbench.tsx src/frontend/src/features/template-workbench/templateWorkbench.css
git commit -m "feat: simplify template workbench preview layout"
```

### Task 3: Verify the full stack

**Files:**
- Verify only

**Step 1: Run frontend tests**

Run: `npm test`
Expected: PASS.

**Step 2: Run frontend build**

Run: `npm run build`
Expected: PASS.

**Step 3: Run backend regression tests**

Run: `$env:PYTHONPATH='src'; python -m unittest discover src/backend/tests -v`
Expected: PASS.

**Step 4: Commit verification-safe final state**

```bash
git status --short
```
Expected: only runtime artifacts or a clean tree.
