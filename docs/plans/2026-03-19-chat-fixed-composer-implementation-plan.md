# Chat Fixed Composer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep the chat input composer fixed to the viewport bottom while preserving content alignment and message readability.

**Architecture:** Leave the current chat page composition intact, but wrap the composer in a chat-page-specific fixed shell that measures the content column and composer height at runtime. Use those measurements to position the fixed shell and reserve equivalent bottom space under the message stream.

**Tech Stack:** React, TypeScript, Vitest, Python unittest, FastAPI static hosting.

---

### Task 1: Lock in the fixed-composer contract

**Files:**
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/chat-fixed-composer/src/frontend/src/pages/ChatPage.test.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/chat-fixed-composer/src/backend/tests/test_frontend_chat_render.py`

**Step 1: Write the failing test**
- Extend the chat page test to assert a dedicated fixed composer container is rendered.
- Extend the backend CSS regression test to assert the stylesheet contains fixed composer and bottom-reservation hooks.

**Step 2: Run test to verify it fails**

Run:
- `npm test -- src/pages/ChatPage.test.tsx`
- `$env:PYTHONPATH='src'; python -m unittest src.backend.tests.test_frontend_chat_render -v`

Expected: FAIL because the current chat page keeps the composer in normal flow and does not expose the new CSS hooks.

**Step 3: Write minimal implementation**
- None in this task.

**Step 4: Run test to verify it still fails**

Run the same commands above.
Expected: FAIL.

### Task 2: Implement the fixed composer and stream spacer

**Files:**
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/chat-fixed-composer/src/frontend/src/pages/ChatPage.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/chat-fixed-composer/src/frontend/src/styles/pages.css`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/chat-fixed-composer/src/frontend/src/styles/layout.css`

**Step 1: Write the minimal implementation**
- Measure `.page-body` width and left offset.
- Measure composer height.
- Render the composer inside a fixed container aligned to the measured content column.
- Apply stream bottom padding based on measured composer height.

**Step 2: Run focused tests to verify it passes**

Run:
- `npm test -- src/pages/ChatPage.test.tsx`
- `$env:PYTHONPATH='src'; python -m unittest src.backend.tests.test_frontend_chat_render -v`

Expected: PASS.

### Task 3: Full verification and rollout

**Files:**
- Verify only

**Step 1: Run full frontend validation**

Run:
- `npm test`
- `npm run build`

**Step 2: Run backend regression validation**

Run:
- `$env:PYTHONPATH='src'; python -m unittest discover src/backend/tests -v`

**Step 3: Browser verification**

Check:
- `/chat` composer stays visible during page scroll
- latest message remains fully visible above the composer
- composer aligns with the main content column and does not cover the sidebar

**Step 4: Commit**

```bash
git add docs/plans src/frontend/src/pages/ChatPage.tsx src/frontend/src/pages/ChatPage.test.tsx src/frontend/src/styles/pages.css src/frontend/src/styles/layout.css src/backend/tests/test_frontend_chat_render.py
git commit -m "fix: pin chat composer to viewport"
```
