# Template Workbench Divider Adjustment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add clear vertical dividers between list panes and detail panes inside the template parameter and section workbenches.

**Architecture:** Keep the current template workbench component structure and solve this with layout-level styling only. Desktop layouts gain a dedicated divider track between the list pane and detail pane, while the divider collapses automatically on narrow screens.

**Tech Stack:** React, TypeScript, Vitest, CSS.

---

### Task 1: Lock the divider behavior with tests

**Files:**
- Modify: `src/backend/tests/test_frontend_chat_render.py`

**Step 1: Write the failing test**
- Assert the workbench stylesheet contains the dedicated divider rules for the split layouts.

**Step 2: Run test to verify it fails**

Run: `$env:PYTHONPATH='src'; python -m unittest src/backend/tests/test_frontend_chat_render.py -v`
Expected: FAIL because the divider rule does not exist yet.

**Step 3: Implement the minimal assertions**
- Keep the assertion scoped to the feature stylesheet, not general layout CSS.

**Step 4: Run the targeted test**

Run: `$env:PYTHONPATH='src'; python -m unittest src/backend/tests/test_frontend_chat_render.py -v`
Expected: PASS.

### Task 2: Add the divider styling

**Files:**
- Modify: `src/frontend/src/features/template-workbench/templateWorkbench.css`

**Step 1: Update split layout grid**
- Add a narrow middle track to `.workbench-split`.

**Step 2: Render the divider visually via CSS**
- Use a pseudo element or background on the middle track so parameters and sections both gain the same separation.

**Step 3: Preserve responsive behavior**
- Remove the divider when the layout collapses to one column under the mobile breakpoint.

**Step 4: Run frontend regression tests**

Run: `npm test -- src/pages/TemplateDetailPage.test.tsx`
Expected: PASS.

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
