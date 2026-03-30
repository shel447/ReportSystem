# Outline Confirmation Structured Edit Downgrade Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** allow whole-sentence editing in outline confirmation while preserving blueprint structure only when static text remains unchanged.

**Architecture:** detect whether a whole-sentence edit can still be expressed as the original segment template. If yes, keep `outline_instance` and update only block values. If no, mark the node as a freeform override and let backend merge downgrade it by clearing structured execution data.

**Tech Stack:** React, TypeScript, Python, unittest, Vitest.

---

### Task 1: Add failing frontend tests
- Modify `src/frontend/src/features/chat-report-flow/components/OutlineTree.test.tsx`
- Modify `src/frontend/src/features/chat-report-flow/components/ChatActionPanel.test.tsx`
- Cover:
  - `param_ref` chips are editable and use tooltip instead of visible helper text
  - whole-sentence edit that only changes block values preserves `outline_instance`
  - whole-sentence edit that changes static text degrades to freeform payload

### Task 2: Add failing backend merge test
- Modify `src/backend/tests/test_outline_review_service.py`
- Cover degraded override clearing `outline_instance`, `content`, and execution bindings.

### Task 3: Implement frontend behavior
- Modify `src/frontend/src/entities/chat/types.ts`
- Modify `src/frontend/src/features/chat-report-flow/components/OutlineTree.tsx`
- Modify `src/frontend/src/features/chat-report-flow/components/ChatActionPanel.tsx`
- Modify `src/frontend/src/styles/pages.css`
- Add explicit `outline_mode` marker, editable param chips, tooltip-only source hint, and structured-edit matching.

### Task 4: Implement backend downgrade merge
- Modify `src/backend/outline_review_service.py`
- Honor the freeform downgrade marker during merge.

### Task 5: Verify and commit
- Run:
  - `npm test -- src/features/chat-report-flow/components/OutlineTree.test.tsx src/features/chat-report-flow/components/ChatActionPanel.test.tsx`
  - `python -m unittest backend.tests.test_outline_review_service -v`
  - `npm run build`
- Then commit and push.
