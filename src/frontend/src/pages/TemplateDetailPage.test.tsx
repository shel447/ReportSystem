import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { TemplateDetailPage } from "./TemplateDetailPage";

function renderTemplateDetailPage(pathname = "/templates/tpl-1") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[pathname]}>
        <Routes>
          <Route path="/templates/new" element={<TemplateDetailPage />} />
          <Route path="/templates/:templateId" element={<TemplateDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function buildTemplatePayload(name = "设备巡检报告") {
  return {
    template_id: "tpl-1",
    name,
    description: "巡检模板",
    report_type: "daily",
    scenario: "集团",
    type: "巡检",
    scene: "总部",
    match_keywords: ["巡检"],
    content_params: [],
    parameters: [
      { id: "date", label: "日期", input_type: "date", required: true },
      { id: "devices", label: "设备列表", input_type: "dynamic", required: true, multi: true, source: "devices" },
    ],
    outline: [],
    sections: [
      {
        title: "概览 {date}",
        content: {
          presentation: { type: "text", template: "巡检日期 {date}" },
        },
      },
      {
        title: "设备 {$device}",
        foreach: { param: "devices", as: "device" },
        content: {
          presentation: { type: "simple_table", dataset_id: "" },
        },
      },
    ],
    schema_version: "v2.0",
    output_formats: ["md"],
    version: "1.0",
  };
}

describe("TemplateDetailPage", () => {
  it("renders the template workbench with export entry and structural preview", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url === "/api/templates/tpl-1" && !init?.method) {
          return {
            ok: true,
            json: async () => buildTemplatePayload(),
          };
        }
        throw new Error(`Unexpected fetch ${url}`);
      }),
    );

    renderTemplateDetailPage();

    expect(await screen.findByDisplayValue("设备巡检报告")).toBeInTheDocument();
    expect(screen.getByText("参数工作台")).toBeInTheDocument();
    expect(screen.getByText("章节工作台")).toBeInTheDocument();
    expect(screen.getByText("结构预览")).toBeInTheDocument();
    expect(screen.queryByText("parameters")).not.toBeInTheDocument();
    expect(screen.queryByText("sections")).not.toBeInTheDocument();

    const exportLink = screen.getByRole("link", { name: "导出 JSON" });
    expect(exportLink).toHaveAttribute("href", "/api/templates/tpl-1/export");

    fireEvent.click(screen.getByRole("button", { name: /设备列表/ }));
    fireEvent.change(screen.getByLabelText("设备列表预览值"), {
      target: { value: "A站设备, B站设备" },
    });

    expect(await screen.findByText("设备 A站设备")).toBeInTheDocument();
    expect(screen.getByText("设备 B站设备")).toBeInTheDocument();
  });

  it("saves the structured workbench payload after editing metadata", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/templates/tpl-1" && !init?.method) {
        return {
          ok: true,
          json: async () => buildTemplatePayload(),
        };
      }
      if (url === "/api/templates/tpl-1" && init?.method === "PUT") {
        return {
          ok: true,
          json: async () => buildTemplatePayload("设备巡检报告-新版"),
        };
      }
      throw new Error(`Unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderTemplateDetailPage();

    expect(await screen.findByDisplayValue("设备巡检报告")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("模板名称"), {
      target: { value: "设备巡检报告-新版" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存模板" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/templates/tpl-1",
        expect.objectContaining({
          method: "PUT",
          body: expect.any(String),
        }),
      );
    });

    const payload = JSON.parse(
      fetchMock.mock.calls.find(([url, init]) => url === "/api/templates/tpl-1" && init?.method === "PUT")?.[1]
        ?.body as string,
    );
    expect(payload.name).toBe("设备巡检报告-新版");
    expect(payload.parameters[0].id).toBe("date");
    expect(payload.sections[0].title).toBe("概览 {date}");
    expect(payload).not.toHaveProperty("previewSamples");

    expect(await screen.findByDisplayValue("设备巡检报告-新版")).toBeInTheDocument();
  });

  it("saves structured dataset configuration without raw json editing", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/templates/tpl-1" && !init?.method) {
        return {
          ok: true,
          json: async () => buildTemplatePayload(),
        };
      }
      if (url === "/api/templates/tpl-1" && init?.method === "PUT") {
        return {
          ok: true,
          json: async () => buildTemplatePayload(),
        };
      }
      throw new Error(`Unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderTemplateDetailPage();

    expect(await screen.findByDisplayValue("设备巡检报告")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /概览 \{date\}/ }));
    fireEvent.click(screen.getByRole("button", { name: "新增数据集" }));
    fireEvent.change(screen.getByLabelText("数据集 ID"), {
      target: { value: "summary" },
    });
    fireEvent.change(screen.getByLabelText("数据源类型"), {
      target: { value: "sql" },
    });
    fireEvent.change(screen.getByLabelText("SQL 文本"), {
      target: { value: "SELECT 1 AS value" },
    });
    fireEvent.change(screen.getByLabelText("展示类型"), {
      target: { value: "value" },
    });
    fireEvent.change(screen.getByLabelText("绑定数据集"), {
      target: { value: "summary" },
    });

    fireEvent.click(screen.getByRole("button", { name: "保存模板" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/templates/tpl-1",
        expect.objectContaining({
          method: "PUT",
          body: expect.any(String),
        }),
      );
    });

    const payload = JSON.parse(
      fetchMock.mock.calls.find(([url, init]) => url === "/api/templates/tpl-1" && init?.method === "PUT")?.[1]
        ?.body as string,
    );
    expect(payload.sections[0].content.datasets).toEqual([
      {
        id: "summary",
        source: {
          kind: "sql",
          query: "SELECT 1 AS value",
        },
      },
    ]);
    expect(payload.sections[0].content.presentation).toEqual({
      type: "value",
      dataset_id: "summary",
      anchor: "{$value}",
    });
  });

  it("blocks save when parameter ids are duplicated", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url === "/api/templates/tpl-1" && !init?.method) {
          return {
            ok: true,
            json: async () => buildTemplatePayload(),
          };
        }
        throw new Error(`Unexpected fetch ${url}`);
      }),
    );

    renderTemplateDetailPage();

    expect(await screen.findByDisplayValue("设备巡检报告")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /设备列表/ }));
    fireEvent.change(screen.getByLabelText("参数标识"), {
      target: { value: "date" },
    });

    expect(await screen.findByText("参数标识不能重复：date")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "保存模板" })).toBeDisabled();
  });
});
