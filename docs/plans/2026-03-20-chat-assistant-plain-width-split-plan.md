# Chat Assistant Plain Text Width Split Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让助手纯文本消息按内容收缩、最大 40%，同时保持助手面板消息当前宽度不变。

**Architecture:** 通过在聊天页为纯文本助手消息添加轻量样式类，局部切换消息主体宽度策略。CSS 继续保留助手面板消息的固定宽度轨道。

**Tech Stack:** React, CSS, Python unittest, Vitest, Vite

---

### Task 1: Lock the compact assistant-text rule in tests

**Files:**
- Modify: `src/backend/tests/test_frontend_chat_render.py`

**Step 1: Write the failing test**
- 断言 ChatPage 中出现纯文本助手消息的紧凑类名。
- 断言 CSS 中存在该类对应的 `fit-content + 40%` 规则。

**Step 2: Run test to verify it fails**
- Run: `python -m unittest src.backend.tests.test_frontend_chat_render -v`
- Expected: FAIL on missing compact assistant-text rule.

### Task 2: Implement the split styling

**Files:**
- Modify: `src/frontend/src/pages/ChatPage.tsx`
- Modify: `src/frontend/src/styles/pages.css`

**Step 1: Write minimal implementation**
- 为无 action 的助手消息添加紧凑 body class。
- 在 CSS 中为该 class 设置 `fit-content` 和 `40%` 上限。
- 保留带 action 的助手消息和 pending 消息当前样式。

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
