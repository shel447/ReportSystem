# Chat Layout Fill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove redundant top framing from the chat page and relax shared page-width caps so the main workspace fills the shell more effectively.

**Architecture:** Keep the current React route and component structure, but tighten the chat page composition and move width control from top-level page layouts down to local content elements. Use TDD to lock in the removal of workflow chrome and the widening of the shared layouts.

**Tech Stack:** React, TypeScript, Vitest, FastAPI static hosting, Python unittest regression checks.

---

### Task 1: Lock in the new chat page frame

**Files:**
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/chat-layout-fill/src/frontend/src/pages/ChatPage.test.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/chat-layout-fill/src/frontend/src/pages/ChatPage.tsx`

**Step 1: Write the failing test**
- Update the chat page test so it asserts the page no longer renders:
  - `Conversation Workflow`
  - `模板匹配`
  - `补参`
  - `确认`
  - `生成`
  - `下载`
  - the old top description copy

**Step 2: Run test to verify it fails**

Run: `npm test -- src/pages/ChatPage.test.tsx`
Expected: FAIL because the current page still renders the workflow strip and intro copy.

**Step 3: Write minimal implementation**
- Remove the top description and workflow strip from `ChatPage.tsx`.
- Keep only notices, stream, and composer inside the conversation layout.

**Step 4: Run test to verify it passes**

Run: `npm test -- src/pages/ChatPage.test.tsx`
Expected: PASS.

### Task 2: Relax shared layout widths and slim the chat banners

**Files:**
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/chat-layout-fill/src/backend/tests/test_frontend_chat_render.py`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/chat-layout-fill/src/frontend/src/styles/layout.css`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/chat-layout-fill/src/frontend/src/styles/pages.css`

**Step 1: Write the failing test**
- Add a regression assertion that the old `max-width: 1180px`, `1220px`, and `1040px` layout caps are gone.

**Step 2: Run test to verify it fails**

Run: `$env:PYTHONPATH='src'; python -m unittest src.backend.tests.test_frontend_chat_render -v`
Expected: FAIL because those width caps still exist.

**Step 3: Write minimal implementation**
- Remove the shared top-level width caps from `layout.css`.
- Remove the local chat page max-width from `pages.css`.
- Add a compact inline banner style for chat notices.

**Step 4: Run test to verify it passes**

Run: `$env:PYTHONPATH='src'; python -m unittest src.backend.tests.test_frontend_chat_render -v`
Expected: PASS.

### Task 3: Full verification and rollout

**Files:**
- Verify only

**Step 1: Run focused frontend tests**

Run: `npm test -- src/pages/ChatPage.test.tsx`

**Step 2: Run full frontend validation**

Run:
- `npm test`
- `npm run build`

**Step 3: Run backend regression validation**

Run:
- `$env:PYTHONPATH='src'; python -m unittest discover src/backend/tests -v`

**Step 4: Manual browser verification**

Check:
- `/chat` no longer shows the top explanation or workflow strip
- message stream uses most of the main workspace width
- notices are visibly slimmer
- `/templates`, `/instances`, `/documents`, `/tasks`, `/settings` no longer show large right-side blank space

**Step 5: Commit and integrate**

```bash
git add docs/plans src/frontend/src/pages/ChatPage.tsx src/frontend/src/pages/ChatPage.test.tsx src/frontend/src/styles/layout.css src/frontend/src/styles/pages.css src/backend/tests/test_frontend_chat_render.py
git commit -m "fix: widen layouts and simplify chat framing"
```
