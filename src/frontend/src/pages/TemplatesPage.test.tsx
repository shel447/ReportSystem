import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { TemplatesPage } from "./TemplatesPage";

function renderTemplatesPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <TemplatesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TemplatesPage", () => {
  it("loads template cards without embedding the full editor", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/templates") {
        return {
          ok: true,
          json: async () => [
            {
              template_id: "tpl-1",
              name: "设备巡检报告",
              description: "巡检模板",
              report_type: "daily",
              scenario: "集团",
              type: "巡检",
              scene: "总部",
              schema_version: "v2.0",
              parameter_count: 3,
              top_level_section_count: 4,
            },
          ],
        };
      }
      throw new Error(`Unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderTemplatesPage();

    expect(await screen.findByRole("link", { name: /设备巡检报告/ })).toHaveAttribute(
      "href",
      "/templates/tpl-1",
    );
    expect(screen.getByText("3 个参数")).toBeInTheDocument();
    expect(screen.getByText("4 个顶层章节")).toBeInTheDocument();
    expect(screen.getByText("v2.0")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "新建模板" })).toHaveAttribute("href", "/templates/new");
    expect(screen.queryByLabelText("模板名称")).not.toBeInTheDocument();
  });
});
