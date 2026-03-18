import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { App } from "./App";

describe("App shell", () => {
  it("renders the shared navigation and defaults to chat page", () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter
          initialEntries={["/chat"]}
          future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
        >
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByRole("navigation", { name: "主导航" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /对话助手/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /模板管理/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /报告实例/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "对话助手", level: 1 })).toBeInTheDocument();
  });
});
