# Template Requirement UX Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Preserve `outline` as the chapter-level container, introduce `requirement + slot` as the sentence-level model, and rebuild the template editor into a compact inspector-style workspace.

**Architecture:** Keep the outline flow and API lifecycle intact, but change the inner sentence model from `document + blocks` to `requirement + slots`. Implement the UX refactor in stages: first rename and map the data model, then rebuild the TemplateWorkbench layout, then replace the proposition-element editor with a list-plus-inspector pattern.

**Tech Stack:** FastAPI, Python unittest, React, TypeScript, TanStack Query, Vite, CSS modules via existing page/workbench styles.

---

### Task 1: Freeze naming-sensitive behavior with failing tests

**Files:**
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\pages\TemplateDetailPage.test.tsx`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\features\chat-report-flow\components\OutlineTree.test.tsx`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\backend\tests\test_templates_router.py`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\backend\tests\test_chat_router.py`

**Step 1: Write the failing tests**

Add assertions that new payloads and UI use:
- `outline.requirement`
- `outline.slots`
- `requirement_instance`
- `slot_id / slot_type`

Add assertions that these are still preserved:
- `review_outline`
- `outline_override`
- outline review flow container naming

**Step 2: Run tests to verify they fail**

Run:
```powershell
npm test -- src/pages/TemplateDetailPage.test.tsx src/features/chat-report-flow/components/OutlineTree.test.tsx
$env:PYTHONPATH='src'; python -m unittest src.backend.tests.test_templates_router src.backend.tests.test_chat_router -v
```

Expected: FAIL because code still emits `document / blocks / outline_instance / block_id`.

**Step 3: Commit**

```powershell
git add src/frontend/src/pages/TemplateDetailPage.test.tsx src/frontend/src/features/chat-report-flow/components/OutlineTree.test.tsx src/backend/tests/test_templates_router.py src/backend/tests/test_chat_router.py
git commit -m "test: freeze requirement naming behavior"
```

### Task 2: Rename template workbench state from document/blocks to requirement/slots

**Files:**
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\features\template-workbench\state.ts`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\entities\templates\types.ts`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\features\template-workbench\validation.ts`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\features\template-workbench\preview.ts`

**Step 1: Write minimal type changes**

Change the workbench state to:
- `outline.requirement`
- `outline.slots`

Change slot structures to use:
- `slot_id`
- `slot_type`

Keep `outline` itself intact.

**Step 2: Update normalization and serialization**

Implement mapping rules:
- old input `document -> requirement`
- old input `blocks -> slots`
- outgoing payload only emits new names

**Step 3: Run targeted tests**

Run:
```powershell
npm test -- src/pages/TemplateDetailPage.test.tsx src/features/template-workbench/validation.test.ts src/features/template-workbench/preview.test.ts
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add src/frontend/src/features/template-workbench/state.ts src/frontend/src/entities/templates/types.ts src/frontend/src/features/template-workbench/validation.ts src/frontend/src/features/template-workbench/preview.ts
git commit -m "refactor: rename requirement slots in template workbench"
```

### Task 3: Rename outline instance internals to requirement instance + slots

**Files:**
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\entities\chat\types.ts`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\entities\instances\types.ts`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\features\chat-report-flow\components\OutlineTree.tsx`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\pages\InstanceDetailPage.tsx`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\backend\routers\chat.py`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\backend\routers\instances.py`

**Step 1: Update frontend types**

Change node sentence internals to:
- `requirement_instance.requirement_template`
- `requirement_instance.rendered_requirement`
- `requirement_instance.slots`
- `segments.kind = "slot"`
- `slot_id / slot_type`

**Step 2: Update backend DTO serialization**

Keep `review_outline` as action type, but emit the inner sentence structure with new field names.

**Step 3: Run tests**

Run:
```powershell
npm test -- src/features/chat-report-flow/components/OutlineTree.test.tsx src/pages/InstanceDetailPage.test.tsx src/pages/ChatPage.test.tsx
$env:PYTHONPATH='src'; python -m unittest src.backend.tests.test_chat_router src.backend.tests.test_instances_router -v
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add src/frontend/src/entities/chat/types.ts src/frontend/src/entities/instances/types.ts src/frontend/src/features/chat-report-flow/components/OutlineTree.tsx src/frontend/src/pages/InstanceDetailPage.tsx src/backend/routers/chat.py src/backend/routers/instances.py
git commit -m "refactor: rename outline sentence internals to requirement slots"
```

### Task 4: Cut backend template catalog and runtime serializers to requirement/slot payloads

**Files:**
- Modify: `E:\code\codex_projects\ReportSystemV2\src\backend\contexts\template_catalog\application\services.py`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\backend\contexts\report_runtime\application\services.py`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\backend\contexts\report_runtime\infrastructure\outline.py`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\backend\tests\test_templates_router.py`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\backend\tests\test_outline_review_service.py`

**Step 1: Update serializer boundaries**

At the API boundary, emit and consume:
- `outline.requirement`
- `outline.slots`
- `requirement_instance`
- `slot_id / slot_type`

Keep `review_outline` and `outline_override` names unchanged.

**Step 2: Add or update migration helpers**

Where old stored data still contains `document / blocks`, normalize them into new field names before use.

**Step 3: Run tests**

Run:
```powershell
$env:PYTHONPATH='src'; python -m unittest src.backend.tests.test_templates_router src.backend.tests.test_outline_review_service src.backend.tests.test_chat_router src.backend.tests.test_instances_router -v
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add src/backend/contexts/template_catalog/application/services.py src/backend/contexts/report_runtime/application/services.py src/backend/contexts/report_runtime/infrastructure/outline.py src/backend/tests/test_templates_router.py src/backend/tests/test_outline_review_service.py
git commit -m "refactor: expose requirement and slot fields at api boundaries"
```

### Task 5: Rebuild the TemplateWorkbench layout into three columns

**Files:**
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\features\template-workbench\TemplateWorkbench.tsx`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\features\template-workbench\templateWorkbench.css`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\pages\TemplateDetailPage.tsx`

**Step 1: Write failing UI tests**

Add assertions for:
- left navigation rail
- main editor column
- right inspector column
- compact field grouping for short parameter fields

**Step 2: Implement minimal layout shift**

Change layout to:
- left: parameter/section navigator
- center: main editor
- right: inspector

Do not yet rebuild slot editing; only move the shell.

**Step 3: Run tests**

Run:
```powershell
npm test -- src/pages/TemplateDetailPage.test.tsx
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add src/frontend/src/features/template-workbench/TemplateWorkbench.tsx src/frontend/src/features/template-workbench/templateWorkbench.css src/frontend/src/pages/TemplateDetailPage.tsx
git commit -m "feat: rebuild template editor into compact three-column shell"
```

### Task 6: Replace large proposition-element cards with list + inspector editing

**Files:**
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\features\template-workbench\TemplateWorkbench.tsx`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\features\template-workbench\templateWorkbench.css`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\pages\TemplateDetailPage.test.tsx`

**Step 1: Write failing tests**

Add coverage for:
- slot list rows show `ID / 类型 / 提示 / 来源摘要`
- selecting a row opens the inspector editor
- all slot types remain editable from the inspector

**Step 2: Implement minimal slot list**

Replace large repeated cards with:
- compact list in center column
- slot detail editor in right inspector column

**Step 3: Run tests**

Run:
```powershell
npm test -- src/pages/TemplateDetailPage.test.tsx src/features/template-workbench/validation.test.ts src/features/template-workbench/preview.test.ts
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add src/frontend/src/features/template-workbench/TemplateWorkbench.tsx src/frontend/src/features/template-workbench/templateWorkbench.css src/frontend/src/pages/TemplateDetailPage.test.tsx
git commit -m "feat: move proposition slot editing into inspector"
```

### Task 7: Tighten visual density and action hierarchy

**Files:**
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\features\template-workbench\templateWorkbench.css`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\styles\components.css`
- Modify: `E:\code\codex_projects\ReportSystemV2\src\frontend\src\styles\layout.css`

**Step 1: Implement density pass**

Adjust:
- tighter paddings
- slimmer list rows
- lighter segmented controls
- compact short-field grids
- lower visual prominence for local actions

**Step 2: Run visual regression-friendly tests**

Run:
```powershell
npm test -- src/pages/TemplateDetailPage.test.tsx src/pages/TemplatesPage.test.tsx
npm run build
```

Expected: PASS and build success.

**Step 3: Commit**

```powershell
git add src/frontend/src/features/template-workbench/templateWorkbench.css src/frontend/src/styles/components.css src/frontend/src/styles/layout.css
git commit -m "style: tighten template editor density and controls"
```

### Task 8: Update docs and remove stale terminology

**Files:**
- Modify: `E:\code\codex_projects\ReportSystemV2\README.md`
- Modify: `E:\code\codex_projects\ReportSystemV2\design\design_template.md`
- Modify: `E:\code\codex_projects\ReportSystemV2\design\implementation\template_catalog.md`
- Modify: `E:\code\codex_projects\ReportSystemV2\design\implementation\report_runtime.md`
- Modify: `E:\code\codex_projects\ReportSystemV2\design\implementation\runtime_sequences.md`

**Step 1: Update terminology**

Document that:
- `outline` is the chapter-level container
- `requirement` is the sentence-level proposition
- `slot` is the technical implementation for a proposition variable position
- UI wording stays `诉求 / 诉求要素`

**Step 2: Run search to confirm stale terms are gone from production naming**

Run:
```powershell
rg -n "\bblock(s)?\b|blueprint|rendered_document|document_template" src design README.md
```

Expected: only intentional historical references remain.

**Step 3: Commit**

```powershell
git add README.md design/design_template.md design/implementation/template_catalog.md design/implementation/report_runtime.md design/implementation/runtime_sequences.md
git commit -m "docs: align requirement and slot terminology"
```

### Task 9: Final regression and integration verification

**Files:**
- No new files required

**Step 1: Run backend regression**

Run:
```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s src/backend/tests -p "test_*.py" -t .
```

Expected: all backend tests pass.

**Step 2: Run frontend regression**

Run:
```powershell
npm test -- src/pages/TemplateDetailPage.test.tsx src/pages/TemplatesPage.test.tsx src/pages/ChatPage.test.tsx src/pages/InstanceDetailPage.test.tsx
npm run build
```

Expected: tests pass and Vite build succeeds.

**Step 3: Manual smoke**

Check:
- template detail page loads and saves
- requirement slot list opens and edits
- outline review still works
- instance detail still shows requirement sentence values

**Step 4: Commit**

```powershell
git add -A
git commit -m "test: verify requirement naming and compact editor refactor"
```
