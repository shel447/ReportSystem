import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { TemplateInstancesPage } from "./TemplateInstancesPage";

function renderTemplateInstancesPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/template-instances"]}>
        <Routes>
          <Route path="/template-instances" element={<TemplateInstancesPage />} />
          <Route path="/chat" element={<div data-testid="chat-route">chat route</div>} />
        </Routes>
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

  it("offers fork action for outline_saved template instances and navigates to chat", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
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
              capture_stage: "outline_saved",
              report_instance_id: null,
              param_count: 2,
              outline_node_count: 3,
              outline_preview: ["执行摘要：巡检结论", "设备 A001：检查项"],
              created_at: "2026-03-19T10:00:00",
            },
          ],
        };
      }
      if (url === "/api/chat/forks" && init?.method === "POST") {
        return {
          ok: true,
          json: async () => ({
            session_id: "s-forked",
            title: "设备巡检报告 copy_ab12cd",
            messages: [],
            draft_message: "",
            matched_template_id: "tpl-1",
            fork_meta: {
              source_kind: "template_instance",
              source_title: "设备巡检报告",
              source_preview: "已保存大纲",
              source_template_instance_id: "ti-1",
            },
          }),
        };
      }
      throw new Error(`Unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderTemplateInstancesPage();

    expect(await screen.findByRole("button", { name: "Fork 到对话助手" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Fork 到对话助手" }));

    await waitFor(() => {
      expect(screen.getByTestId("chat-route")).toBeInTheDocument();
    });
  });
});
