import { useState } from "react";
import { FileText, LayoutTemplate, MessageCircleQuestion, MessageSquare, Settings } from "lucide-react";
import { NavLink } from "react-router-dom";

import { FeedbackDialog } from "../../features/feedback-dialog/FeedbackDialog";
import { FOOTER_META, PAGE_META } from "../../shared/navigation";

type AppShellProps = {
  pathname: string;
  children: React.ReactNode;
};

export function AppShell({ pathname, children }: AppShellProps) {
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const isDesignerWorkspace = /^\/reports\/[^/]+\/designer$/.test(pathname);
  const isChatWorkspace = pathname === "/chat";

  return (
    <div className={`app-shell${isDesignerWorkspace ? " app-shell--designer" : ""}${isChatWorkspace ? " app-shell--chat" : ""}`}>
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
              title={item.label}
            >
              <span className="nav-icon" aria-hidden="true">
                {resolveNavigationIcon(item.href)}
              </span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="footer-actions">
            <button className="footer-link" type="button" title="提意见" aria-label="提意见" onClick={() => setFeedbackOpen(true)}>
              <span className="nav-icon" aria-hidden="true"><MessageCircleQuestion size={18} /></span>
              <span>提意见</span>
            </button>
            {FOOTER_META.map((item) => (
              <NavLink
                key={item.href}
                to={item.href}
                className={({ isActive }) => `footer-link${isActive ? " active" : ""}`}
                title={item.label}
              >
                <span className="nav-icon" aria-hidden="true">
                  {resolveNavigationIcon(item.href)}
                </span>
                <span>{item.label}</span>
              </NavLink>
            ))}
          </div>
        </div>
      </aside>
      <main className="app-main">
        <section className="page-body">{children}</section>
      </main>
      <FeedbackDialog open={feedbackOpen} onClose={() => setFeedbackOpen(false)} />
    </div>
  );
}

function resolveNavigationIcon(href: string) {
  if (href === "/chat") return <MessageSquare size={18} />;
  if (href === "/templates") return <LayoutTemplate size={18} />;
  if (href === "/reports") return <FileText size={18} />;
  return <Settings size={18} />;
}
