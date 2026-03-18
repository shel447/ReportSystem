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
    expect(screen.getByRole("link", { name: /报告实例/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "对话助手", level: 1 })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: "对话助手" })).toHaveLength(1);
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
});
