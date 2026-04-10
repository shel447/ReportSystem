import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { InstanceDetailPage } from "./InstanceDetailPage";

function renderInstanceDetailPage(pathname = "/instances/inst-1") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[pathname]}>
        <Routes>
          <Route path="/instances/:instanceId" element={<InstanceDetailPage />} />
          <Route path="/chat" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function LocationProbe() {
  return <div data-testid="chat-location">chat-route</div>;
}

describe("InstanceDetailPage", () => {
  it("loads one instance, generates markdown, and nests debug info in a secondary disclosure", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/rest/chatbi/v1/instances/inst-1" && !init?.method) {
        return {
          ok: true,
          json: async () => ({
            instance_id: "inst-1",
            template_id: "tpl-1",
            status: "generated",
            input_params: { report_date: "2026-03-18" },
            outline_content: [
              {
                title: "概览",
                description: "章节说明",
                content: "正文",
                status: "generated",
                data_status: "success",
                debug: { compiled_sql: "SELECT 1", row_count: 1 },
              },
            ],
            report_time: "2026-03-31T08:00:00",
            report_time_source: "scheduled_execution",
            created_at: "2026-03-18T10:00:00",
            updated_at: "2026-03-18T10:01:00",
            has_generation_baseline: true,
            supports_update_chat: true,
            supports_fork_chat: true,
          }),
        };
      }
      if (url === "/rest/chatbi/v1/instances/inst-1/baseline" && !init?.method) {
        return {
          ok: true,
          json: async () => ({
            instance_id: "inst-1",
            params_snapshot: { report_date: "2026-03-18" },
            outline: [
              {
                node_id: "node-1",
                title: "确认诉求",
                description: "生成基线",
                display_text: "分析 总部 的巡检情况",
                level: 1,
                node_kind: "structured_leaf",
                ai_generated: false,
                requirement_instance: {
                  requirement_template: "分析 {@target_scene} 的巡检情况",
                  rendered_requirement: "分析 总部 的巡检情况",
                  segments: [
                    { kind: "text", text: "分析 " },
                    { kind: "slot", slot_id: "target_scene", slot_type: "param_ref", value: "总部" },
                    { kind: "text", text: " 的巡检情况" },
                  ],
                  slots: [
                    { id: "target_scene", type: "param_ref", hint: "场景", value: "总部", param_id: "scene" },
                  ],
                },
                children: [],
              },
            ],
          }),
        };
      }
      if (url === "/rest/chatbi/v1/instances/inst-1/update-chat" && init?.method === "POST") {
        return {
          ok: true,
          json: async () => ({
            session_id: "sess-update",
            title: "设备巡检报告 copy_ab12cd",
            matched_template_id: "tpl-1",
            fork_meta: {
              source_kind: "update_from_instance",
              source_title: "设备巡检报告",
              source_preview: "确认诉求",
              source_report_instance_id: "inst-1",
            },
            messages: [
              {
                role: "assistant",
                content: "已恢复确认诉求，请继续修改。",
                action: {
                  type: "review_outline",
                  template_name: "设备巡检报告",
                  template_id: "tpl-1",
                  warnings: [],
                  params_snapshot: [{ id: "report_date", label: "报告日期", value: "2026-03-18" }],
                  outline: [
                    {
                      node_id: "node-1",
                      title: "确认诉求",
                      description: "生成基线",
                      display_text: "确认诉求：生成基线",
                      level: 1,
                      children: [],
                    },
                  ],
                },
              },
            ],
          }),
        };
      }
      if (url === "/rest/chatbi/v1/instances/inst-1/fork-sources" && !init?.method) {
        return {
          ok: true,
          json: async () => [
            { message_id: "msg-a1", role: "assistant", preview: "请输入参数", action_type: "ask_param" },
          ],
        };
      }
      if (url === "/rest/chatbi/v1/instances/inst-1/fork-chat" && init?.method === "POST") {
        return {
          ok: true,
          json: async () => ({ session_id: "sess-fork" }),
        };
      }
      if (url === "/rest/chatbi/v1/templates" && !init?.method) {
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
            },
          ],
        };
      }
      if (url === "/rest/chatbi/v1/documents?instance_id=inst-1" && !init?.method) {
        return {
          ok: true,
          json: async () => [],
        };
      }
      if (url === "/rest/chatbi/v1/documents" && init?.method === "POST") {
        return {
          ok: true,
          json: async () => ({
            document_id: "doc-1",
            instance_id: "inst-1",
            template_id: "tpl-1",
            format: "md",
            file_path: "generated/doc-1.md",
            file_name: "doc-1.md",
            file_size: 1200,
            status: "ready",
            version: 1,
            download_url: "/rest/chatbi/v1/documents/doc-1/download",
          }),
        };
      }
      throw new Error(`Unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderInstanceDetailPage();

    expect(await screen.findByText("概览")).toBeInTheDocument();
    expect(screen.getByText("报告时间")).toBeInTheDocument();
    expect(screen.getByText("查看调试信息")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "更新" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Fork" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "查看确认诉求" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "查看确认诉求" }));

    expect(await screen.findByText("分析")).toBeInTheDocument();
    expect(screen.getByText("总部")).toHaveClass("outline-tree__block-chip--readonly");
    expect(screen.getByText("总部")).toHaveAttribute("title", "参数：场景（scene）");
    expect(screen.getByText("report_date：2026-03-18")).toBeInTheDocument();
    expect(screen.getByRole("tree")).toBeInTheDocument();
    expect(screen.queryByText('"node_id": "node-1"')).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "新增同级章节 node-1" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "生成 Markdown" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/rest/chatbi/v1/documents",
        expect.objectContaining({
          method: "POST",
        }),
      );
    });

    expect(await screen.findByRole("link", { name: "下载最新 Markdown" })).toHaveAttribute(
      "href",
      "/rest/chatbi/v1/documents/doc-1/download",
    );
  });

  it("auto-expands update preview from intent query and only creates chat on explicit continue", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/rest/chatbi/v1/instances/inst-1" && !init?.method) {
        return {
          ok: true,
          json: async () => ({
            instance_id: "inst-1",
            template_id: "tpl-1",
            status: "generated",
            input_params: { report_date: "2026-03-18" },
            outline_content: [],
            created_at: "2026-03-18T10:00:00",
            updated_at: "2026-03-18T10:01:00",
            has_generation_baseline: true,
            supports_update_chat: true,
            supports_fork_chat: true,
          }),
        };
      }
      if (url === "/rest/chatbi/v1/instances/inst-1/baseline" && !init?.method) {
        return {
          ok: true,
          json: async () => ({
            instance_id: "inst-1",
            params_snapshot: { report_date: "2026-03-18" },
            outline: [
              {
                node_id: "node-1",
                title: "确认诉求",
                description: "生成基线",
                display_text: "分析 总部 的巡检情况",
                level: 1,
                node_kind: "structured_leaf",
                ai_generated: false,
                requirement_instance: {
                  requirement_template: "分析 {@target_scene} 的巡检情况",
                  rendered_requirement: "分析 总部 的巡检情况",
                  segments: [
                    { kind: "text", text: "分析 " },
                    { kind: "slot", slot_id: "target_scene", slot_type: "param_ref", value: "总部" },
                    { kind: "text", text: " 的巡检情况" },
                  ],
                  slots: [
                    { id: "target_scene", type: "param_ref", hint: "场景", value: "总部", param_id: "scene" },
                  ],
                },
                children: [],
              },
            ],
          }),
        };
      }
      if (url === "/rest/chatbi/v1/instances/inst-1/update-chat" && init?.method === "POST") {
        return {
          ok: true,
          json: async () => ({
            session_id: "sess-update",
            title: "设备巡检报告 copy_ab12cd",
            matched_template_id: "tpl-1",
            fork_meta: {
              source_kind: "update_from_instance",
              source_title: "设备巡检报告",
              source_preview: "确认诉求",
              source_report_instance_id: "inst-1",
            },
            messages: [
              {
                role: "assistant",
                content: "已恢复确认诉求，请继续修改。",
                action: {
                  type: "review_outline",
                  template_name: "设备巡检报告",
                  template_id: "tpl-1",
                  warnings: [],
                  params_snapshot: [{ id: "report_date", label: "报告日期", value: "2026-03-18" }],
                  outline: [
                    {
                      node_id: "node-1",
                      title: "确认诉求",
                      description: "生成基线",
                      display_text: "确认诉求：生成基线",
                      level: 1,
                      children: [],
                    },
                  ],
                },
              },
            ],
          }),
        };
      }
      if (url === "/rest/chatbi/v1/templates" && !init?.method) {
        return {
          ok: true,
          json: async () => [{ template_id: "tpl-1", name: "设备巡检报告", report_type: "daily" }],
        };
      }
      if (url === "/rest/chatbi/v1/documents?instance_id=inst-1" && !init?.method) {
        return {
          ok: true,
          json: async () => [],
        };
      }
      if (url === "/rest/chatbi/v1/instances/inst-1/fork-sources" && !init?.method) {
        return {
          ok: true,
          json: async () => [],
        };
      }
      throw new Error(`Unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderInstanceDetailPage("/instances/inst-1?intent=update");

    expect(await screen.findByText("分析")).toBeInTheDocument();
    expect(screen.getByText("总部")).toHaveAttribute("title", "参数：场景（scene）");
    expect(screen.getByText("report_date：2026-03-18")).toBeInTheDocument();
    expect(screen.getByRole("tree")).toBeInTheDocument();
    expect(screen.queryByText('"node_id": "node-1"')).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "继续到对话助手修改" })).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalledWith(
      "/rest/chatbi/v1/instances/inst-1/update-chat",
      expect.objectContaining({ method: "POST" }),
    );

    fireEvent.click(screen.getByRole("button", { name: "继续到对话助手修改" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/rest/chatbi/v1/instances/inst-1/update-chat",
        expect.objectContaining({ method: "POST" }),
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId("chat-location")).toBeInTheDocument();
    });
  });

  it("omits placeholder status chips for legacy sections without runtime markers", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url === "/rest/chatbi/v1/instances/inst-legacy" && !init?.method) {
          return {
            ok: true,
            json: async () => ({
              instance_id: "inst-legacy",
              template_id: "tpl-1",
              status: "draft",
              input_params: { report_date: "2026-03-18" },
              outline_content: [
                {
                  title: "旧版章节",
                  description: "兼容章节",
                  content: "旧版正文",
                  debug: {},
                },
              ],
              created_at: "2026-03-18T10:00:00",
              updated_at: "2026-03-18T10:01:00",
              has_generation_baseline: false,
              supports_update_chat: false,
              supports_fork_chat: false,
            }),
          };
        }
        if (url === "/rest/chatbi/v1/templates" && !init?.method) {
          return {
            ok: true,
            json: async () => [
              {
                template_id: "tpl-1",
                name: "旧版模板",
                report_type: "daily",
              },
            ],
          };
        }
        if (url === "/rest/chatbi/v1/documents?instance_id=inst-legacy" && !init?.method) {
          return {
            ok: true,
            json: async () => [],
          };
        }
        throw new Error(`Unexpected fetch ${url}`);
      }),
    );

    renderInstanceDetailPage("/instances/inst-legacy");

    expect(await screen.findByText("旧版章节")).toBeInTheDocument();
    expect(screen.queryByText("unknown")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "更新" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Fork" })).not.toBeInTheDocument();
  });
});
