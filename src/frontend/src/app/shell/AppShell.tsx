import { useState } from "react";
import { NavLink } from "react-router-dom";

import { FeedbackDialog } from "../../features/feedback-dialog/FeedbackDialog";
import { FOOTER_META, PAGE_META } from "../../shared/navigation";

type AppShellProps = {
  pathname: string;
  children: React.ReactNode;
};

export function AppShell({ pathname, children }: AppShellProps) {
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const routeMeta = [...PAGE_META, ...FOOTER_META];
  const pageTitle = routeMeta.find((item) => pathname.startsWith(item.href))?.label ?? "智能报告系统";

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="brand-panel">
          <span className="brand-mark">RS</span>
          <div>
            <p className="brand-title">智能报告系统</p>
            <p className="brand-subtitle">Bright Workbench</p>
          </div>
        </div>
        <nav className="nav-list" aria-label="主导航">
          {PAGE_META.map((item) => (
            <NavLink
              key={item.href}
              to={item.href}
              className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
            >
              <span className="nav-icon" aria-hidden="true">
                {item.icon}
              </span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="footer-actions">
            <button className="ghost-button" type="button" onClick={() => setFeedbackOpen(true)}>
              提意见
            </button>
            {FOOTER_META.map((item) => (
              <NavLink
                key={item.href}
                to={item.href}
                className={({ isActive }) => `footer-link${isActive ? " active" : ""}`}
              >
                <span className="nav-icon" aria-hidden="true">
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </NavLink>
            ))}
          </div>
        </div>
      </aside>
      <main className="app-main">
        <header className="app-header">
          <div>
            <p className="eyebrow">Smart Report Workspace</p>
            <h1>{pageTitle}</h1>
          </div>
          <div className="user-pill">默认工作区</div>
        </header>
        <section className="page-body">{children}</section>
      </main>
      <FeedbackDialog open={feedbackOpen} onClose={() => setFeedbackOpen(false)} />
    </div>
  );
}
