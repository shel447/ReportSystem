# Inline Outline Block Editing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade report outline review from whole-sentence editing to true inline block editing so block values remain structured and drive resolved execution baselines.

**Architecture:** Keep the existing dual-layer template model. Frontend renders `outline_instance.segments` as inline text and block chips/controls, submits structured `outline_instance` changes through `outline_override`, and backend merges those edits without losing `content` / `resolved_content` generation. Generation continues to resolve execution from confirmed block values.

**Tech Stack:** FastAPI, Python unittest, React, TypeScript, Vitest, existing chat outline review flow.

---

### Task 1: Lock the contract in tests

**Files:**
- Modify: `E:\code\codex_projects\ReportSystemV2\src\backend\tests\test_outline_review_service.py`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\backend\tests\test_chat_router.py`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\features\chat-report-flow\components\OutlineTree.test.tsx`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\features\chat-report-flow\components\ChatActionPanel.test.tsx`

**Step 1: Write the failing backend tests**
- Add a test proving `merge_outline_override()` preserves edited `outline_instance.blocks[].value` and recomputed `display_text`.
- Add a chat-router test proving `confirm_outline_generation` uses edited block values to produce `resolved_content`.

**Step 2: Run backend tests to verify failure**

Run:
```powershell
python -m unittest src.backend.tests.test_outline_review_service src.backend.tests.test_chat_router -v
```

Expected: FAIL because override merging currently drops or ignores structured block edits.

**Step 3: Write the failing frontend tests**
- Add a tree test proving editable mode renders inline block chips, not just a single input.
- Add an action-panel test proving block edits submit structured `outline_instance` values instead of only rewritten `title/description`.

**Step 4: Run frontend tests to verify failure**

Run:
```powershell
npm test -- src/features/chat-report-flow/components/OutlineTree.test.tsx src/features/chat-report-flow/components/ChatActionPanel.test.tsx
```

Expected: FAIL because current UI only supports whole-line text editing.

### Task 2: Implement backend structured outline merge

**Files:**
- Modify: `E:\code\codex_projects\ReportSystemV2\src\backend\outline_review_service.py`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\backend\chat_flow_service.py`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\backend\routers\chat.py` (only if payload plumbing needs adjustment)

**Step 1: Minimal merge support**
- Allow `merge_outline_override()` to preserve and normalize `outline_instance` when the override contains structured segments / block values.
- Recompute `display_text` from `outline_instance.rendered_document` when present instead of only `title/description`.
- Preserve `content`, `execution_bindings`, `section_kind`, and source metadata for existing structured nodes.

**Step 2: Resolve edited block values into execution baseline**
- Update outline resolution so `resolved_content` uses overridden block values from `outline_instance.blocks`.
- Keep behavior unchanged for legacy / freeform nodes.

**Step 3: Run backend tests to go green**

Run:
```powershell
python -m unittest src.backend.tests.test_outline_review_service src.backend.tests.test_chat_router -v
```

Expected: PASS.

### Task 3: Implement frontend inline block editor

**Files:**
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\entities\chat\types.ts`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\features\chat-report-flow\components\OutlineTree.tsx`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\features\chat-report-flow\components\ChatActionPanel.tsx`

**Step 1: Extend UI draft types**
- Add structured editable segment / block value support to outline draft nodes.
- Keep readonly mode unchanged.

**Step 2: Render inline block editing**
- Replace whole-line input editing for blueprint-backed nodes with inline rendering:
  - text segments editable in-place
  - block segments rendered as compact chips / controls
- Keep freeform/manual nodes on the simpler whole-line input path.

**Step 3: Submit structured override**
- Serialize edited `outline_instance` back into `outline_override`.
- Keep existing structural operations (add/move/delete/promote/demote) working.

**Step 4: Run frontend tests to go green**

Run:
```powershell
npm test -- src/features/chat-report-flow/components/OutlineTree.test.tsx src/features/chat-report-flow/components/ChatActionPanel.test.tsx
```

Expected: PASS.

### Task 4: Verify full chat flow and build

**Files:**
- Verify only.

**Step 1: Run focused backend regression**

Run:
```powershell
python -m unittest src.backend.tests.test_outline_review_service src.backend.tests.test_chat_router src.backend.tests.test_chat_flow_service src.backend.tests.test_instances_router -v
```

Expected: PASS.

**Step 2: Run focused frontend regression**

Run:
```powershell
npm test -- src/features/chat-report-flow/components/OutlineTree.test.tsx src/features/chat-report-flow/components/ChatActionPanel.test.tsx src/pages/ChatPage.test.tsx src/pages/InstanceDetailPage.test.tsx
```

Expected: PASS.

**Step 3: Run production build**

Run:
```powershell
cd E:\code\codex_projects\ReportSystemV2\src\frontend
npm run build
```

Expected: build succeeds.

**Step 4: Commit**

```powershell
git add docs/plans/2026-03-30-inline-outline-block-editing-implementation-plan.md src/backend/outline_review_service.py src/backend/tests/test_outline_review_service.py src/backend/tests/test_chat_router.py src/frontend/src/entities/chat/types.ts src/frontend/src/features/chat-report-flow/components/OutlineTree.tsx src/frontend/src/features/chat-report-flow/components/OutlineTree.test.tsx src/frontend/src/features/chat-report-flow/components/ChatActionPanel.tsx src/frontend/src/features/chat-report-flow/components/ChatActionPanel.test.tsx
git commit -m "feat: add inline outline block editing"
```
