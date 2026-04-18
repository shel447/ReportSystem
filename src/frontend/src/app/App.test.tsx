import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { App } from "./App";

describe("App shell", () => {
  function renderApp(pathname: string) {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter
          initialEntries={[pathname]}
          future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
        >
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    );
  }

  it("renders the shared navigation and a single shell heading for chat", () => {
    renderApp("/chat");

    expect(screen.getByRole("navigation", { name: "主导航" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /对话助手/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /报告模板/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /报告中心/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "对话助手", level: 1 })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: "对话助手" })).toHaveLength(1);
  });

  it("keeps navigation scoped to chat templates and reports", () => {
    const view = renderApp("/chat");
    const navItems = Array.from(view.container.querySelectorAll(".nav-item")).map((item) => item.textContent?.trim() ?? "");

    expect(navItems).toEqual(["CH对话助手", "TP报告模板", "RP报告中心"]);
  });

  it("resolves template detail routes without redirecting to chat", () => {
    renderApp("/templates/abc-123");

    expect(screen.getByRole("heading", { name: "模板详情", level: 1 })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "对话助手", level: 1 })).not.toBeInTheDocument();
  });

  it("resolves template creation route without redirecting to chat", () => {
    renderApp("/templates/new");

    expect(screen.getByRole("heading", { name: "模板详情", level: 1 })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "对话助手", level: 1 })).not.toBeInTheDocument();
  });

  it("resolves report detail routes without redirecting to chat", () => {
    renderApp("/reports/rpt-001");

    expect(screen.getByRole("heading", { name: "报告详情", level: 1 })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "对话助手", level: 1 })).not.toBeInTheDocument();
  });

  it("redirects unknown routes back to chat", () => {
    renderApp("/instances/inst-001");

    expect(screen.getByRole("heading", { name: "对话助手", level: 1 })).toBeInTheDocument();
  });

  it("keeps secondary pages on a single route heading", () => {
    const reportsView = renderApp("/reports/rpt-001");
    expect(screen.getAllByRole("heading", { name: "报告详情" })).toHaveLength(1);
    reportsView.unmount();

    renderApp("/settings");
    expect(screen.getAllByRole("heading", { name: "系统设置" })).toHaveLength(1);
  });

  it("keeps settings in the sidebar footer and moves feedback to the header", () => {
    const view = renderApp("/chat");
    const sidebarFooter = view.container.querySelector(".sidebar-footer");
    const headerActions = view.container.querySelector(".app-header__actions");
    const feedbackIcon = view.container.querySelector(".header-feedback-link__icon");

    expect(sidebarFooter).not.toBeNull();
    expect(headerActions).not.toBeNull();
    expect(feedbackIcon).not.toBeNull();
    expect(sidebarFooter?.textContent).toContain("系统设置");
    expect(sidebarFooter?.textContent).not.toContain("提意见");
    expect(headerActions?.textContent).toContain("提意见");
    expect(screen.queryByText("默认工作区")).not.toBeInTheDocument();
  });
});
