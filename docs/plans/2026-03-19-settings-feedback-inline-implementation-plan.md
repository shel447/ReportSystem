# Settings Feedback Inline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move system settings operation feedback below the action buttons, summarize it, and dismiss it automatically.

**Architecture:** Keep all behavior inside `SettingsPage`. Replace the page-level message string with a structured local feedback model, add a short-lived timer for dismissal, and render a lightweight inline feedback row inside the operations card.

**Tech Stack:** React, TypeScript, Vitest, Python unittest.

---

### Task 1: Lock in the new feedback behavior

**Files:**
- Create: `E:/code/codex_projects/ReportSystemV2/.worktrees/settings-feedback-inline/src/frontend/src/pages/SettingsPage.test.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/settings-feedback-inline/src/backend/tests/test_frontend_chat_render.py`

**Step 1: Write the failing test**
- Add a settings page test that:
  - loads the page
  - triggers `测试连接`
  - expects inline summary feedback below the action buttons
  - expects no top `操作反馈` banner
  - advances fake timers and expects the feedback to disappear
- Extend backend text regression to assert the new inline feedback hook classes exist.

**Step 2: Run test to verify it fails**

Run:
- `npm test -- src/pages/SettingsPage.test.tsx`
- `$env:PYTHONPATH='src'; python -m unittest src.backend.tests.test_frontend_chat_render -v`

Expected: FAIL because the current page still renders a top banner and does not auto-dismiss.

### Task 2: Implement inline summarized feedback

**Files:**
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/settings-feedback-inline/src/frontend/src/pages/SettingsPage.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/settings-feedback-inline/src/frontend/src/styles/pages.css`

**Step 1: Write minimal implementation**
- Replace `message: string` with structured feedback state.
- Add helper functions to summarize connection test success and failure results.
- Move feedback rendering under the action row.
- Add three-second auto-dismiss with cleanup.

**Step 2: Run focused tests to verify it passes**

Run:
- `npm test -- src/pages/SettingsPage.test.tsx`
- `$env:PYTHONPATH='src'; python -m unittest src.backend.tests.test_frontend_chat_render -v`

Expected: PASS.

### Task 3: Full verification and rollout

**Files:**
- Verify only

**Step 1: Run frontend validation**

Run:
- `npm test`
- `npm run build`

**Step 2: Run backend validation**

Run:
- `$env:PYTHONPATH='src'; python -m unittest discover src/backend/tests -v`

**Step 3: Commit**

```bash
git add docs/plans src/frontend/src/pages/SettingsPage.tsx src/frontend/src/pages/SettingsPage.test.tsx src/frontend/src/styles/pages.css src/backend/tests/test_frontend_chat_render.py
git commit -m "fix: move settings feedback under actions"
```
