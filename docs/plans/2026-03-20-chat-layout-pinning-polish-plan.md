# Chat Layout Pinning And Width Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 调整聊天页布局，使助手面板宽度更克制、会话记录固定、输入区更贴底、折叠按钮位置更准确。

**Architecture:** 仅修改聊天页组件和聊天页样式，并通过静态回归测试锁定关键类名与 CSS 片段。后端接口和交互逻辑不变。

**Tech Stack:** React, CSS, Python unittest, Vitest, Vite

---

### Task 1: Lock the new layout rules in tests

**Files:**
- Modify: `src/backend/tests/test_frontend_chat_render.py`

**Step 1: Write the failing test**
- 为助手 action 面板 `60%` 上限、固定会话栏、底部 `8px` 安全边距、分隔按钮中置和放大写断言。

**Step 2: Run test to verify it fails**
- Run: `python -m unittest src.backend.tests.test_frontend_chat_render -v`
- Expected: FAIL on old CSS values.

### Task 2: Implement the layout polish

**Files:**
- Modify: `src/frontend/src/pages/ChatPage.tsx`
- Modify: `src/frontend/src/styles/pages.css`

**Step 1: Write minimal implementation**
- 给助手 action 气泡增加更窄的上限规则。
- 固定会话栏位置并让历史列表独立滚动。
- 把输入区底部 padding 收到 8px，并同步调整消息区底部预留。
- 折叠按钮改到竖线中部，适度加大。

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
