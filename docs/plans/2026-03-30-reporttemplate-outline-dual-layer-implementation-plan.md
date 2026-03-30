# ReportTemplate Outline Dual-Layer Alignment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Align template editing and chat outline review with the latest `ReportTemplate` dual-layer model where section-level outline blueprints coexist with executable content chains.

**Architecture:** Extend the template schema and workbench first, then add instance-level blueprint materialization for chat outline review. Keep execution-chain generation compatible and only introduce blueprint-driven materialization before changing report runtime baselines.

**Tech Stack:** FastAPI, SQLAlchemy, React, TypeScript, TanStack Query, unittest, vitest.

---

### Task 1: Add section outline blueprint types and schema support

**Files:**
- Modify: `src/backend/report_template_schema_v2.json`
- Modify: `src/backend/template_schema_service.py`
- Modify: `src/frontend/src/entities/templates/types.ts`
- Modify: `src/frontend/src/features/template-workbench/state.ts`
- Test: `src/backend/tests/test_template_schema_service.py`
- Test: `src/frontend/src/features/template-workbench/state.test.ts`

**Step 1: Write the failing tests**
- Add backend test asserting `sections[].outline.document/blocks` passes validation.
- Add frontend state test asserting template details with `outline` round-trip through workbench state.

**Step 2: Run tests to verify they fail**
- Run: `python -m unittest backend.tests.test_template_schema_service -v`
- Run: `npm test -- src/features/template-workbench/state.test.ts`

**Step 3: Write minimal implementation**
- Extend backend JSON schema with `OutlineBlueprint` and `OutlineBlock`.
- Extend template types and workbench state serialization.

**Step 4: Run tests to verify they pass**
- Re-run the same test commands.

**Step 5: Commit**
- `git add ...`
- `git commit -m "feat: add outline blueprint template schema support"`

### Task 2: Add blueprint editing UI to template workbench

**Files:**
- Modify: `src/frontend/src/features/template-workbench/TemplateWorkbench.tsx`
- Modify: `src/frontend/src/features/template-workbench/validation.ts`
- Modify: `src/frontend/src/features/template-workbench/preview.tsx` or related preview helpers
- Test: `src/frontend/src/features/template-workbench/validation.test.ts`
- Test: `src/frontend/src/pages/TemplateDetailPage.test.tsx`

**Step 1: Write the failing tests**
- Add validation test for missing block references / duplicate block ids / invalid `param_ref`.
- Add UI test for blueprint editor controls and save payload.

**Step 2: Run tests to verify they fail**
- Run: `npm test -- src/features/template-workbench/validation.test.ts src/pages/TemplateDetailPage.test.tsx`

**Step 3: Write minimal implementation**
- Add `蓝图 / 执行链路 / 同步状态` tabs in section detail.
- Add `document` editor and `blocks[]` editor.
- Add validation and preview support.

**Step 4: Run tests to verify they pass**
- Re-run the same test command.

**Step 5: Commit**
- `git add ...`
- `git commit -m "feat: add outline blueprint workbench editor"`

### Task 3: Materialize outline blueprint for chat outline review

**Files:**
- Create: `src/backend/outline_blueprint_service.py`
- Modify: `src/backend/outline_review_service.py`
- Modify: `src/backend/chat_flow_service.py`
- Modify: `src/frontend/src/entities/chat/types.ts`
- Modify: `src/frontend/src/features/chat-report-flow/components/OutlineTree.tsx`
- Test: `src/backend/tests/test_outline_blueprint_service.py`
- Test: `src/backend/tests/test_outline_review_service.py`
- Test: `src/frontend/src/features/chat-report-flow/components/OutlineTree.test.tsx`

**Step 1: Write the failing tests**
- Add backend test that sections with `outline.document/blocks` materialize into review nodes with `outline_instance` and rendered `display_text`.
- Add frontend readonly/edit rendering test for blueprint-derived node payload.

**Step 2: Run tests to verify they fail**
- Run: `python -m unittest backend.tests.test_outline_blueprint_service backend.tests.test_outline_review_service -v`
- Run: `npm test -- src/features/chat-report-flow/components/OutlineTree.test.tsx`

**Step 3: Write minimal implementation**
- Build instance-level blueprint nodes.
- Make `build_pending_outline_review` prefer blueprint materialization when `section.outline` exists.
- Extend chat types with `outline_instance` metadata.

**Step 4: Run tests to verify they pass**
- Re-run the same commands.

**Step 5: Commit**
- `git add ...`
- `git commit -m "feat: materialize outline blueprints for chat review"`

### Task 4: Wire blueprint-aware outline review through chat page

**Files:**
- Modify: `src/frontend/src/features/chat-report-flow/components/ChatActionPanel.tsx`
- Modify: `src/frontend/src/pages/ChatPage.tsx`
- Test: `src/frontend/src/pages/ChatPage.test.tsx`
- Test: `src/backend/tests/test_chat_router.py`

**Step 1: Write the failing tests**
- Add chat router test verifying blueprint-backed review outline is returned.
- Add chat page test verifying review outline renders blueprint-derived sentence tree.

**Step 2: Run tests to verify they fail**
- Run: `python -m unittest backend.tests.test_chat_router -v`
- Run: `npm test -- src/pages/ChatPage.test.tsx`

**Step 3: Write minimal implementation**
- Keep current review flow, but consume new blueprint node payload.
- Preserve existing outline edit actions.

**Step 4: Run tests to verify they pass**
- Re-run the same commands.

**Step 5: Commit**
- `git add ...`
- `git commit -m "feat: wire blueprint review into chat flow"`

### Task 5: Full verification and docs sync

**Files:**
- Modify: `design/design.md`
- Modify: `design/design_api.md`
- Modify: `design/design_instance.md`
- Test: `src/backend/tests/test_frontend_chat_render.py`

**Step 1: Update docs**
- Add dual-layer section model and blueprint-aware chat review flow.

**Step 2: Run verification**
- `python -m unittest backend.tests.test_template_schema_service backend.tests.test_outline_blueprint_service backend.tests.test_outline_review_service backend.tests.test_chat_router backend.tests.test_frontend_chat_render -v`
- `npm test -- src/features/template-workbench/state.test.ts src/features/template-workbench/validation.test.ts src/pages/TemplateDetailPage.test.tsx src/features/chat-report-flow/components/OutlineTree.test.tsx src/pages/ChatPage.test.tsx`
- `npm run build`

**Step 3: Commit**
- `git add ...`
- `git commit -m "docs: align blueprint dual-layer template flow"`
