import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { TemplateInstancesPage } from "./TemplateInstancesPage";

function renderTemplateInstancesPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <TemplateInstancesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TemplateInstancesPage", () => {
  it("loads read-only template instance cards with outline summaries", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/template-instances") {
        return {
          ok: true,
          json: async () => [
            {
              template_instance_id: "ti-1",
              template_id: "tpl-1",
              template_name: "设备巡检报告",
              session_id: "sess-1",
              capture_stage: "outline_confirmed",
              report_instance_id: "inst-9",
              param_count: 2,
              outline_node_count: 3,
              outline_preview: ["执行摘要：巡检结论", "设备 A001：检查项"],
              created_at: "2026-03-19T10:00:00",
            },
          ],
        };
      }
      throw new Error(`Unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderTemplateInstancesPage();

    expect(await screen.findByText("设备巡检报告")).toBeInTheDocument();
    expect(screen.getByText("已确认生成")).toBeInTheDocument();
    expect(screen.getByText("2 个参数")).toBeInTheDocument();
    expect(screen.getByText("3 个章节节点")).toBeInTheDocument();
    expect(screen.getByText("执行摘要：巡检结论")).toBeInTheDocument();
    expect(screen.getByText("关联报告实例：inst-9")).toBeInTheDocument();
  });
});
