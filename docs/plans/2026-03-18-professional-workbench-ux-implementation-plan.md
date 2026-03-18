# Professional Workbench UX Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the React frontend into a more polished professional workbench UX by removing duplicate titles, splitting template and instance list/detail flows, and rebalancing the chat workspace.

**Architecture:** Keep the existing React + Vite app and API contracts, but introduce shared layout primitives and route-level page separation. Implement the redesign incrementally with TDD so layout changes are locked in by route/component tests before visual refactors land.

**Tech Stack:** React, TypeScript, React Router, TanStack Query, Vitest, FastAPI static hosting.

---

### Task 1: Lock in shell hierarchy and route structure

**Files:**
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/app/App.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/app/shell/AppShell.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/shared/navigation.ts`
- Test: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/app/App.test.tsx`

**Step 1: Write the failing test**
- Extend the app shell test so it asserts the route title appears once at the page level.
- Add route assertions for `/templates/:templateId`, `/templates/new`, and `/instances/:instanceId`.

**Step 2: Run test to verify it fails**

Run: `npm test -- src/app/App.test.tsx`
Expected: FAIL because the new routes and title contract do not exist yet.

**Step 3: Write minimal implementation**
- Update routing to include list/detail routes for templates and instances.
- Shrink the shell so it owns the page title while page components can render intro copy without duplicating it.
- Adjust navigation metadata helpers if route lookup needs prefix handling.

**Step 4: Run test to verify it passes**

Run: `npm test -- src/app/App.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/frontend/src/app/App.tsx src/frontend/src/app/shell/AppShell.tsx src/frontend/src/shared/navigation.ts src/frontend/src/app/App.test.tsx
git commit -m "refactor: stabilize shell titles and page routes"
```

### Task 2: Introduce shared page layout primitives

**Files:**
- Create: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/shared/layouts/PageIntroBar.tsx`
- Create: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/shared/layouts/ConversationLayout.tsx`
- Create: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/shared/layouts/ListPageLayout.tsx`
- Create: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/shared/layouts/DetailPageLayout.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/shared/ui/PageSection.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/styles/layout.css`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/styles/components.css`

**Step 1: Write the failing test**
- Add a small render test that expects intro bars to render description/actions without forcing a duplicate heading.

**Step 2: Run test to verify it fails**

Run: `npm test -- src/app/App.test.tsx`
Expected: FAIL or missing component assertions.

**Step 3: Write minimal implementation**
- Add the shared layout primitives.
- Reduce `PageSection` to a neutral content wrapper or stop using it where it creates heading duplication.
- Add layout CSS tokens for content widths, list/detail frames, and conversation widths.

**Step 4: Run test to verify it passes**

Run: `npm test -- src/app/App.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/frontend/src/shared/layouts src/frontend/src/shared/ui/PageSection.tsx src/frontend/src/styles/layout.css src/frontend/src/styles/components.css src/frontend/src/app/App.test.tsx
git commit -m "refactor: add shared professional workbench layouts"
```

### Task 3: Rebuild the chat page as a single-column workspace

**Files:**
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/pages/ChatPage.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/pages/ChatPage.test.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/features/chat-report-flow/components/ChatActionPanel.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/features/chat-report-flow/components/ChatActionPanel.test.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/styles/pages.css`

**Step 1: Write the failing test**
- Add assertions that the page renders a compact workflow strip instead of the large hero card.
- Assert the body no longer repeats the `对话助手` heading.
- Assert the composer uses the refined conversation layout container.

**Step 2: Run test to verify it fails**

Run: `npm test -- src/pages/ChatPage.test.tsx src/features/chat-report-flow/components/ChatActionPanel.test.tsx`
Expected: FAIL because the old structure is still rendered.

**Step 3: Write minimal implementation**
- Replace the hero card with a lighter flow strip.
- Recompose the page around the conversation layout.
- Reduce composer default height and rebalance spacing.
- Keep action panels embedded in the message flow but visually lighter.

**Step 4: Run test to verify it passes**

Run: `npm test -- src/pages/ChatPage.test.tsx src/features/chat-report-flow/components/ChatActionPanel.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/frontend/src/pages/ChatPage.tsx src/frontend/src/pages/ChatPage.test.tsx src/frontend/src/features/chat-report-flow/components/ChatActionPanel.tsx src/frontend/src/features/chat-report-flow/components/ChatActionPanel.test.tsx src/frontend/src/styles/pages.css
git commit -m "feat: rebuild chat page as single-column workspace"
```

### Task 4: Split templates into list and detail pages

**Files:**
- Create: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/pages/TemplateListPage.tsx`
- Create: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/pages/TemplateDetailPage.tsx`
- Create: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/pages/TemplateDetailPage.test.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/pages/TemplatesPage.test.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/entities/templates/api.ts`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/styles/pages.css`
- Remove or repurpose: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/pages/TemplatesPage.tsx`

**Step 1: Write the failing test**
- Replace the current combined-page test with:
  - list page shows template cards without the full editor
  - detail page loads a single template and renders edit sections
  - navigation into the detail page works for an existing template and for `/templates/new`

**Step 2: Run test to verify it fails**

Run: `npm test -- src/pages/TemplatesPage.test.tsx src/pages/TemplateDetailPage.test.tsx`
Expected: FAIL because the new pages/routes do not exist.

**Step 3: Write minimal implementation**
- Split list and detail responsibilities into separate route components.
- Move the existing editor state into the detail page.
- Add compact summary cards for the list page.
- Group the detail form into clearer sections and isolate advanced JSON areas.

**Step 4: Run test to verify it passes**

Run: `npm test -- src/pages/TemplatesPage.test.tsx src/pages/TemplateDetailPage.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/frontend/src/pages/TemplateListPage.tsx src/frontend/src/pages/TemplateDetailPage.tsx src/frontend/src/pages/TemplateDetailPage.test.tsx src/frontend/src/pages/TemplatesPage.test.tsx src/frontend/src/styles/pages.css src/frontend/src/app/App.tsx
git commit -m "feat: split template list and detail workspaces"
```

### Task 5: Split instances into list and detail pages

**Files:**
- Create: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/pages/InstanceListPage.tsx`
- Create: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/pages/InstanceDetailPage.tsx`
- Create: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/pages/InstanceDetailPage.test.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/pages/InstancesPage.test.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/styles/pages.css`
- Remove or repurpose: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/pages/InstancesPage.tsx`

**Step 1: Write the failing test**
- Replace the combined instance page test with:
  - list page shows instance summaries only
  - detail page loads one instance and shows metadata + chapters
  - debug information is rendered inside a secondary disclosure block

**Step 2: Run test to verify it fails**

Run: `npm test -- src/pages/InstancesPage.test.tsx src/pages/InstanceDetailPage.test.tsx`
Expected: FAIL because the new page split is not implemented.

**Step 3: Write minimal implementation**
- Split instance browsing and detail inspection into separate pages.
- Preserve document creation and section regeneration actions in the detail page.
- Make chapter content primary and debug content secondary.

**Step 4: Run test to verify it passes**

Run: `npm test -- src/pages/InstancesPage.test.tsx src/pages/InstanceDetailPage.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/frontend/src/pages/InstanceListPage.tsx src/frontend/src/pages/InstanceDetailPage.tsx src/frontend/src/pages/InstanceDetailPage.test.tsx src/frontend/src/pages/InstancesPage.test.tsx src/frontend/src/styles/pages.css src/frontend/src/app/App.tsx
git commit -m "feat: split instance list and detail workspaces"
```

### Task 6: Polish secondary pages and unify visual rhythm

**Files:**
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/pages/DocumentsPage.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/pages/TasksPage.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/pages/SettingsPage.tsx`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/styles/layout.css`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/styles/components.css`
- Modify: `E:/code/codex_projects/ReportSystemV2/.worktrees/ux-workbench-polish/src/frontend/src/styles/pages.css`

**Step 1: Write the failing test**
- Add or extend route-level tests to ensure secondary pages render without duplicate page titles and use consistent page intro/layout structure.

**Step 2: Run test to verify it fails**

Run: `npm test -- src/app/App.test.tsx`
Expected: FAIL because the remaining pages still use the old page structure.

**Step 3: Write minimal implementation**
- Recompose the remaining pages with the shared intro/layout primitives.
- Tighten spacing, hierarchy, and panel weight across the app.
- Ensure no route falls back to the old duplicated section-heading pattern.

**Step 4: Run test to verify it passes**

Run: `npm test -- src/app/App.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/frontend/src/pages/DocumentsPage.tsx src/frontend/src/pages/TasksPage.tsx src/frontend/src/pages/SettingsPage.tsx src/frontend/src/styles/layout.css src/frontend/src/styles/components.css src/frontend/src/styles/pages.css src/frontend/src/app/App.test.tsx
git commit -m "refactor: unify secondary pages with shared workbench rhythm"
```

### Task 7: Final verification and manual UX pass

**Files:**
- Verify only

**Step 1: Run frontend tests**

Run: `npm test`
Expected: PASS with all Vitest suites green.

**Step 2: Run frontend build**

Run: `npm run build`
Expected: PASS with Vite production build output.

**Step 3: Run backend regression tests**

Run: `python -m unittest discover backend.tests -v`
Expected: PASS.

**Step 4: Run browser validation on core pages**
- Check `/chat`, `/templates`, `/templates/new`, `/templates/:id`, `/instances`, `/instances/:id`, `/settings`.
- Confirm no duplicate route title, stable spacing, and correct list/detail navigation.

**Step 5: Commit final polish if needed**

```bash
git add -A
git commit -m "refactor: polish professional workbench ux"
```
