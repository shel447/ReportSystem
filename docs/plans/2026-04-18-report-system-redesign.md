# Report System Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild the report system to match `design/report_system` exactly, with a single template model, a TemplateInstance-centered runtime, and a public API limited to templates, chat, reports, and parameter-option resolution.

**Architecture:** Replace the existing report implementation with a new DDD-aligned backend and frontend projection. Recreate the database schema from scratch, validate all formal models against `design/report_system/schemas/*`, and remove every compatibility path and deprecated public surface.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, React, TypeScript, Vitest, pytest

---

### Task 1: Freeze target design and implementation docs

**Files:**
- Create: `design/report_system/implementation/README.md`
- Create: `design/report_system/implementation/总体实现架构.md`
- Create: `design/report_system/implementation/模板目录实现.md`
- Create: `design/report_system/implementation/统一对话实现.md`
- Create: `design/report_system/implementation/报告运行时实现.md`
- Create: `design/report_system/implementation/持久化与表结构实现.md`
- Create: `design/report_system/implementation/前端实现.md`
- Create: `design/report_system/implementation/外部集成与导出实现.md`

**Step 1: Verify target design inputs**

Run: `Get-ChildItem design/report_system -Recurse`
Expected: design package and schemas are present.

**Step 2: Write implementation docs**

Write the target-state implementation mapping and keep it aligned with the design package.

**Step 3: Verify docs exist**

Run: `Get-ChildItem design/report_system/implementation`
Expected: the new implementation docs exist.

### Task 2: Rebuild backend persistence and domain models

**Files:**
- Modify: `src/backend/infrastructure/persistence/models.py`
- Modify: `src/backend/infrastructure/persistence/database.py`
- Modify: `src/backend/contexts/template_catalog/**`
- Modify: `src/backend/contexts/conversation/**`
- Modify: `src/backend/contexts/report_runtime/**`
- Delete: `src/backend/contexts/scheduling/**`

**Step 1: Write failing backend tests for the new contracts**

Add tests for:
- template schema root uses `catalogs`
- chat ask/answer returns `templateInstance`
- report view matches chat report answer
- no `/instances` or `/scheduled-tasks`

**Step 2: Run failing tests**

Run: `python -m pytest src/backend/tests -q`
Expected: failures on old models/contracts.

**Step 3: Replace persistence schema and services**

Implement new ORM tables, repositories, and application services around `ReportTemplate`, `TemplateInstance`, and `Report DSL`.

**Step 4: Re-run backend tests**

Run: `python -m pytest src/backend/tests -q`
Expected: passing tests.

### Task 3: Rebuild public routers and dependency assembly

**Files:**
- Modify: `src/backend/main.py`
- Modify: `src/backend/infrastructure/dependencies.py`
- Modify: `src/backend/routers/chat.py`
- Modify: `src/backend/routers/templates.py`
- Modify: `src/backend/routers/reports.py`
- Modify: `src/backend/routers/parameter_options.py`
- Delete: removed router files and references for deprecated resources

**Step 1: Write failing API tests for removed routes and new payloads**

**Step 2: Implement the new route layer**

Keep only:
- `/templates`
- `/chat`
- `/reports`
- `/parameter-options/resolve`

**Step 3: Verify with pytest**

Run: `python -m pytest src/backend/tests -q`
Expected: public API tests pass.

### Task 4: Rebuild frontend types, API clients, and pages

**Files:**
- Modify: `src/frontend/src/entities/**`
- Modify: `src/frontend/src/features/**`
- Modify: `src/frontend/src/pages/**`
- Modify: `src/frontend/src/app/App.tsx`

**Step 1: Write failing frontend tests for the new contracts**

**Step 2: Replace old instance/task/report compatibility state**

Rebuild the UI to consume only the new template/chat/report payloads.

**Step 3: Re-run frontend tests**

Run: `npm test`
Expected: all tests pass.

### Task 5: Validate end-to-end flow and clean removed code

**Files:**
- Modify: `design/openapi/*`
- Delete: legacy files, old schemas, obsolete services, deprecated tests

**Step 1: Run backend and frontend test suites**

Run: `python -m pytest src/backend/tests -q`
Expected: pass.

Run: `npm test`
Expected: pass.

**Step 2: Run frontend build**

Run: `npm run build`
Expected: build succeeds.

**Step 3: Run smoke checks**

Verify:
- template CRUD
- chat template matching and parameter ask
- confirm params and report generation
- report detail
- document generation/download

**Step 4: Commit**

```bash
git add .
git commit -m "feat: rebuild report system on new report_system design"
```
