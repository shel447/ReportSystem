import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ReportCenterPage } from "./ReportCenterPage";

describe("ReportCenterPage", () => {
  it("guides users back to chat and templates instead of exposing removed instance resources", () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ReportCenterPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByText("当前没有已生成的报告。通过对话生成后，这里会自动展示最近的报告。")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "前往对话助手" })).toHaveAttribute("href", "/chat");
    expect(screen.getByRole("link", { name: "查看模板" })).toHaveAttribute("href", "/templates");
    expect(screen.queryByText("实例列表")).not.toBeInTheDocument();
  });
});
