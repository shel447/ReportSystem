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
    expect(screen.getByRole("link", { name: /模板管理/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /模板实例/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /报告实例/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "对话助手", level: 1 })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: "对话助手" })).toHaveLength(1);
  });

  it("keeps template instances between templates and report instances in navigation", () => {
    const view = renderApp("/chat");
    const navItems = Array.from(view.container.querySelectorAll(".nav-item")).map((item) => item.textContent?.trim() ?? "");

    expect(navItems).toEqual(["CH对话助手", "TP模板管理", "TI模板实例", "IN报告实例", "DOC报告文档", "TSK定时任务"]);
  });

  it("resolves template detail routes without redirecting to chat", () => {
    renderApp("/templates/abc-123");

    expect(screen.getByRole("heading", { name: "模板管理", level: 1 })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "对话助手", level: 1 })).not.toBeInTheDocument();
  });

  it("resolves template creation route without redirecting to chat", () => {
    renderApp("/templates/new");

    expect(screen.getByRole("heading", { name: "模板管理", level: 1 })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "对话助手", level: 1 })).not.toBeInTheDocument();
  });

  it("resolves instance detail routes without redirecting to chat", () => {
    renderApp("/instances/inst-001");

    expect(screen.getByRole("heading", { name: "报告实例", level: 1 })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "对话助手", level: 1 })).not.toBeInTheDocument();
  });

  it("keeps secondary pages on a single route heading", () => {
    const documentsView = renderApp("/documents");
    expect(screen.getAllByRole("heading", { name: "报告文档" })).toHaveLength(1);
    documentsView.unmount();

    const tasksView = renderApp("/tasks");
    expect(screen.getAllByRole("heading", { name: "定时任务" })).toHaveLength(1);
    tasksView.unmount();

    renderApp("/settings");
    expect(screen.getAllByRole("heading", { name: "系统设置" })).toHaveLength(1);
  });

  it("keeps settings in the sidebar footer and moves feedback to the header", () => {
    const view = renderApp("/chat");
    const sidebarFooter = view.container.querySelector(".sidebar-footer");
    const headerActions = view.container.querySelector(".app-header__actions");

    expect(sidebarFooter).not.toBeNull();
    expect(headerActions).not.toBeNull();
    expect(sidebarFooter?.textContent).toContain("系统设置");
    expect(sidebarFooter?.textContent).not.toContain("提意见");
    expect(headerActions?.textContent).toContain("提意见");
    expect(screen.queryByText("默认工作区")).not.toBeInTheDocument();
  });
});
