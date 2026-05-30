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

  it("renders the shared navigation and removes the generic page heading from chat", () => {
    renderApp("/chat");

    expect(screen.getByRole("navigation", { name: "主导航" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /对话助手/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /报告模板/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /报告中心/ })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "对话助手", level: 1 })).not.toBeInTheDocument();
    expect(screen.getByText("新对话")).toBeInTheDocument();
  });

  it("keeps navigation scoped to chat templates and reports", () => {
    const view = renderApp("/chat");
    const navItems = Array.from(view.container.querySelectorAll(".nav-item")).map((item) => item.textContent?.trim() ?? "");

    expect(navItems).toEqual(["对话助手", "报告模板", "报告中心"]);
  });

  it("resolves template creation route without redirecting to chat", () => {
    renderApp("/templates/new");

    expect(screen.getByRole("heading", { name: "新建模板", level: 1 })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "对话助手", level: 1 })).not.toBeInTheDocument();
  });

  it("redirects unknown routes back to chat", () => {
    renderApp("/instances/inst-001");

    expect(screen.queryByRole("heading", { name: "对话助手", level: 1 })).not.toBeInTheDocument();
    expect(screen.getByText("新对话")).toBeInTheDocument();
  });

  it("keeps secondary pages on a compact single-line toolbar", () => {
    renderApp("/settings");
    expect(screen.getAllByRole("heading", { name: "系统设置" })).toHaveLength(1);
    expect(screen.queryByText("Smart Report Workspace")).not.toBeInTheDocument();
  });

  it("keeps settings and feedback in the global icon rail", () => {
    const view = renderApp("/settings");
    const sidebarFooter = view.container.querySelector(".sidebar-footer");
    const shell = view.container.querySelector(".app-shell");

    expect(sidebarFooter).not.toBeNull();
    expect(shell).not.toBeNull();
    expect(sidebarFooter?.textContent).toContain("系统设置");
    expect(sidebarFooter?.textContent).toContain("提意见");
    expect(screen.getByRole("button", { name: "提意见" })).toBeInTheDocument();
    expect(view.container.querySelector(".app-header")).toBeNull();
    expect(screen.queryByText("默认工作区")).not.toBeInTheDocument();
  });
});
