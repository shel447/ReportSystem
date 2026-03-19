# Shell Feedback Placement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep the settings entry fixed in the desktop sidebar and move the feedback trigger into the header as a borderless text action.

**Architecture:** Update the shell structure in `AppShell.tsx`, then adjust `layout.css` so the sidebar is sticky and the header owns a lightweight action cluster. Lock the behavior with one React DOM test and one static CSS/render regression test before implementation.

**Tech Stack:** React, React Router, Vitest, Python unittest, CSS

---

### Task 1: Lock the shell structure with tests

**Files:**
- Modify: `E:/code/codex_projects/ReportSystemV2/src/frontend/src/app/App.test.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/src/backend/tests/test_frontend_chat_render.py`

**Step 1: Write the failing tests**
- Assert `提意见` renders inside a header actions container, not inside `.sidebar-footer`.
- Assert layout CSS includes sticky desktop sidebar and a borderless header feedback action class.

**Step 2: Run targeted tests to verify they fail**
Run: `npm test -- src/app/App.test.tsx`
Run: `$env:PYTHONPATH='src'; python -m unittest src/backend/tests/test_frontend_chat_render.py -v`
Expected: failures about missing header feedback action and missing sticky/header style hooks.

### Task 2: Move feedback trigger and keep settings in sticky sidebar

**Files:**
- Modify: `E:/code/codex_projects/ReportSystemV2/src/frontend/src/app/shell/AppShell.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/src/frontend/src/styles/layout.css`

**Step 1: Write minimal implementation**
- Remove the feedback button from `.sidebar-footer`.
- Add a header actions wrapper that contains a new feedback trigger and the existing workspace pill.
- Make desktop `.app-sidebar` sticky with viewport height and overflow handling.
- Add a `header-feedback-link` style with no border/background chrome.

**Step 2: Run targeted tests to verify they pass**
Run: `npm test -- src/app/App.test.tsx`
Run: `$env:PYTHONPATH='src'; python -m unittest src/backend/tests/test_frontend_chat_render.py -v`
Expected: PASS.

### Task 3: Full verification and integration

**Files:**
- No new files

**Step 1: Run full verification**
Run: `npm test`
Run: `npm run build`
Run: `$env:PYTHONPATH='src'; python -m unittest discover src/backend/tests -v`
Expected: all green.

**Step 2: Commit and push**
Run:
`git add E:/code/codex_projects/ReportSystemV2/src/frontend/src/app/App.test.tsx E:/code/codex_projects/ReportSystemV2/src/backend/tests/test_frontend_chat_render.py E:/code/codex_projects/ReportSystemV2/src/frontend/src/app/shell/AppShell.tsx E:/code/codex_projects/ReportSystemV2/src/frontend/src/styles/layout.css E:/code/codex_projects/ReportSystemV2/docs/plans/2026-03-19-shell-feedback-placement-design.md E:/code/codex_projects/ReportSystemV2/docs/plans/2026-03-19-shell-feedback-placement-implementation-plan.md`
`git commit -m "fix: reposition shell feedback action"`
`git push origin master`
