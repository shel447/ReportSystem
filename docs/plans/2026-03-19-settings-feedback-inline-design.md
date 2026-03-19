# Settings Feedback Inline Design

## Background

The current settings page reports all operation results through a page-level `StatusBanner` at the top of the page. This creates two UX problems:

- the feedback appears far away from the action buttons that triggered it
- the banner is visually heavier than the action itself, especially for routine success states

The desired behavior is a lighter, action-local feedback line placed directly under the operation buttons and dismissed automatically after a short delay.

## Goals

1. Move settings operation feedback directly below the action buttons.
2. Replace verbose feedback with short summaries.
3. Auto-dismiss feedback after a short interval.
4. Keep the change local to the settings page.

## Non-goals

- No API changes.
- No global toast or notification system.
- No changes to feedback behavior on other pages.

## Approved Decisions

- A single shared feedback line will sit below the full button group.
- Feedback will auto-dismiss after three seconds.
- Connection test results will show a summary sentence, not raw JSON.
- New feedback replaces previous feedback immediately.

## Design

### Feedback model

The page should use a structured feedback state instead of a raw string:

- `tone`: `success | error | info`
- `text`: short summary

This allows the action area to render a lightweight inline notice without reusing the heavy page banner.

### Feedback placement

The settings operations block will render:

1. the action row
2. the inline feedback line directly below it

The existing top-of-page `StatusBanner` should be removed entirely for this page.

### Summary rules

- Save success: `系统设置已保存`
- Save failure: `系统设置保存失败：<摘要>`
- Reindex success: `模板索引已重建`
- Reindex failure: `重建模板索引失败：<摘要>`
- Test success:
  - both ok: `连接测试成功：Completion、Embedding 均可用`
  - completion ok: `连接测试成功：Completion 可用`
  - embedding ok: `连接测试成功：Embedding 可用`
- Test failure:
  - summarize only failing targets, for example:
    - `连接测试失败：Embedding 认证失败`
    - `连接测试失败：Completion 超时；Embedding 未配置`

### Auto-dismiss

Each new feedback event resets a three-second timer. When the timer expires, the feedback is cleared. If another action finishes before the timer ends, the old timer is cancelled and replaced.

## Testing

- Frontend page test:
  - feedback does not appear as a top `操作反馈` banner
  - test action produces the summarized inline feedback
  - feedback disappears after three seconds
- Backend text regression:
  - settings page no longer contains the top `StatusBanner` block for operation feedback
  - inline feedback hook classes exist in the page stylesheet
