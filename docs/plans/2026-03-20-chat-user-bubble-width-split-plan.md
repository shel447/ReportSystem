# Chat User Bubble Width Split Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让用户消息按内容收缩但不超过 40%，同时保持助手消息当前 75% 的稳定宽度。

**Architecture:** 只调整聊天页 CSS 和静态回归断言，不修改前端状态或后端接口。桌面端拆分用户与助手两套宽度规则，移动端继续统一 100%。

**Tech Stack:** React, CSS, Python unittest, Vitest, Vite

---

### Task 1: Lock the width split in regression tests

**Files:**
- Modify: `src/backend/tests/test_frontend_chat_render.py`

**Step 1: Write the failing test**
- 把静态断言改成：助手消息仍是 `75%`，用户消息是 `fit-content + 40%` 上限。

**Step 2: Run test to verify it fails**
- Run: `python -m unittest src.backend.tests.test_frontend_chat_render -v`
- Expected: FAIL on old shared-width rules.

### Task 2: Implement CSS split

**Files:**
- Modify: `src/frontend/src/styles/pages.css`

**Step 1: Write minimal implementation**
- 保留 `.message-entry__body` 为助手消息的 75% 宽度。
- 为 `.message-entry--user .message-entry__body` 增加 `fit-content` 和 `40%` 上限。
- 为 `.message-bubble--user` 增加 `inline-size: fit-content`，助手气泡维持 `100%`。
- 保持移动端 100% 宽度回退。

**Step 2: Run regression test**
- Run: `python -m unittest src.backend.tests.test_frontend_chat_render -v`
- Expected: PASS

### Task 3: Verify frontend integrity

**Files:**
- No source changes expected

**Step 1: Run frontend tests**
- Run: `npm test`
- Expected: PASS

**Step 2: Run production build**
- Run: `npm run build`
- Expected: PASS
