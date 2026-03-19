# 2026-03-19 Shell Feedback Placement Design

## Goal
- Keep `系统设置` fixed in the left sidebar during desktop scrolling.
- Move `提意见` from the sidebar footer to the top-right page header.
- Render `提意见` as a borderless text action.

## Approach
- Treat the desktop sidebar as a sticky column with viewport-height constraints.
- Keep `系统设置` as the only footer navigation action in the sidebar.
- Add a dedicated header action group to `AppShell`, hosting the feedback trigger and existing workspace pill.
- Use a minimal text-button style for the feedback trigger so it reads as a utility action instead of a card/button.

## Validation
- App shell tests verify the button is in the header action group and not in the sidebar footer.
- Static style tests verify sticky sidebar and header feedback-link styles.
