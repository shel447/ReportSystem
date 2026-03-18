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
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("InstanceDetailPage", () => {
  it("loads one instance, generates markdown, and nests debug info in a secondary disclosure", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/instances/inst-1" && !init?.method) {
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
            created_at: "2026-03-18T10:00:00",
            updated_at: "2026-03-18T10:01:00",
          }),
        };
      }
      if (url === "/api/templates" && !init?.method) {
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
      if (url === "/api/documents?instance_id=inst-1" && !init?.method) {
        return {
          ok: true,
          json: async () => [],
        };
      }
      if (url === "/api/documents" && init?.method === "POST") {
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
            download_url: "/api/documents/doc-1/download",
          }),
        };
      }
      throw new Error(`Unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderInstanceDetailPage();

    expect(await screen.findByText("概览")).toBeInTheDocument();
    expect(screen.getByText("查看调试信息")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "生成 Markdown" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/documents",
        expect.objectContaining({
          method: "POST",
        }),
      );
    });

    expect(await screen.findByRole("link", { name: "下载最新 Markdown" })).toHaveAttribute(
      "href",
      "/api/documents/doc-1/download",
    );
  });

  it("omits placeholder status chips for legacy sections without runtime markers", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url === "/api/instances/inst-legacy" && !init?.method) {
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
            }),
          };
        }
        if (url === "/api/templates" && !init?.method) {
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
        if (url === "/api/documents?instance_id=inst-legacy" && !init?.method) {
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
  });
});
