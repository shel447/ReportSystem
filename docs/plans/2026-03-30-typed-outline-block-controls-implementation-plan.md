# Typed Outline Block Controls Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add lightweight typed inline controls for key outline blueprint block types during chat outline review.

**Architecture:** Keep backend contracts stable and implement typed behavior primarily in the shared `OutlineTree` component. Block edits still write through the existing `outline_instance` structure, so report generation continues to resolve execution baselines without a new persistence shape.

**Tech Stack:** React, TypeScript, Vitest, existing chat outline review flow, existing backend outline baseline resolution.

---

### Task 1: Lock expected typed behaviors in tests

**Files:**
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\features\chat-report-flow\components\OutlineTree.test.tsx`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\features\chat-report-flow\components\ChatActionPanel.test.tsx`

**Step 1: Write failing tests for typed block rendering**
- Add a test for `time_range` block editing that expects date inputs instead of a plain text input.
- Add a test for `enum_select` / `indicator` select behavior when options are present.
- Add a test for `param_ref` readonly rendering that confirms no inline editor appears.

**Step 2: Run tests to verify failure**

Run:
```powershell
npm test -- src/features/chat-report-flow/components/OutlineTree.test.tsx src/features/chat-report-flow/components/ChatActionPanel.test.tsx
```

Expected: FAIL because current block editing still uses generic text/select logic and does not special-case readonly parameter references.

### Task 2: Implement typed inline controls in OutlineTree

**Files:**
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\features\chat-report-flow\components\OutlineTree.tsx`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\styles\pages.css`

**Step 1: Add block-type helpers**
- Add helpers that classify blocks into readonly param-ref, date-range, select, and text fallback.
- Parse and format range strings without changing the backend payload type.

**Step 2: Render typed editors**
- `param_ref`: readonly chip with hint text/title
- `time_range`: compact date inputs
- `enum_select` / `indicator` / `scope` with options: select
- fallback: existing text input

**Step 3: Keep current write-through behavior**
- Continue updating `outline_instance.blocks`, `segments`, `rendered_document`, and `display_text` on commit.

**Step 4: Run focused tests to green**

Run:
```powershell
npm test -- src/features/chat-report-flow/components/OutlineTree.test.tsx src/features/chat-report-flow/components/ChatActionPanel.test.tsx
```

Expected: PASS.

### Task 3: Verify adjacent flows and build

**Files:**
- Verify only.

**Step 1: Run page-level regression**

Run:
```powershell
npm test -- src/pages/ChatPage.test.tsx src/pages/InstanceDetailPage.test.tsx
```

Expected: PASS.

**Step 2: Run production build**

Run:
```powershell
cd E:\code\codex_projects\ReportSystemV2\src\frontend
npm run build
```

Expected: PASS.

**Step 3: Commit**

```powershell
git add docs/plans/2026-03-30-typed-outline-block-controls-design.md docs/plans/2026-03-30-typed-outline-block-controls-implementation-plan.md src/frontend/src/features/chat-report-flow/components/OutlineTree.tsx src/frontend/src/features/chat-report-flow/components/OutlineTree.test.tsx src/frontend/src/features/chat-report-flow/components/ChatActionPanel.test.tsx src/frontend/src/styles/pages.css
git commit -m "feat: add typed outline block controls"
```
