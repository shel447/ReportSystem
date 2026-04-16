import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { TemplateDetailPage } from "./TemplateDetailPage";

function renderTemplateDetailPage(initialEntry: string | { pathname: string; state?: unknown } = "/templates/tpl_1") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
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
    id: "tpl_1",
    name,
    description: "巡检模板",
    category: "巡检",
    parameters: [
      { id: "date", label: "日期", input_type: "date", required: true },
      { id: "scene", label: "场景", input_type: "enum", required: true, options: ["总部", "区域"] },
      { id: "devices", label: "设备列表", input_type: "dynamic", required: true, multi: true, source: "devices" },
    ],
    sections: [
      {
        title: "概览 {date}",
        outline: {
          requirement: "分析 {@focus_metric} 在 {date} 的变化",
          items: [
            {
              id: "focus_metric",
              type: "indicator",
              hint: "重点指标",
              default: "温度",
              options: ["温度", "湿度"],
              widget: "select",
            },
            {
              id: "analysis_period",
              type: "time_range",
              hint: "分析周期",
              default: "2026-03-01 至 2026-03-07",
              widget: "date_range",
            },
            {
              id: "target_scene",
              type: "param_ref",
              hint: "场景来源",
              param_id: "scene",
            },
            {
              id: "top_n",
              type: "number",
              hint: "Top N",
              default: "5",
            },
            {
              id: "alarm_threshold",
              type: "threshold",
              hint: "阈值",
              default: "80",
            },
            {
              id: "include_closed_loop",
              type: "boolean",
              hint: "是否包含闭环",
              default: "true",
            },
            {
              id: "compare_operator",
              type: "operator",
              hint: "比较符",
              default: ">=",
            },
          ],
        },
        content: {
          presentation: { type: "text", template: "巡检日期 {date}，指标 {@focus_metric}" },
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
  };
}

describe("TemplateDetailPage", () => {
  it("renders the template workbench with export entry and structural preview", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url === "/rest/chatbi/v1/templates/tpl_1" && !init?.method) {
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
    expect(screen.getByRole("heading", { name: "结构预览" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "诉求预览" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "执行预览" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "模板 JSON" })).toBeInTheDocument();
    expect(screen.queryByText("兼容迁移")).not.toBeInTheDocument();
    expect(screen.queryByText("parameters")).not.toBeInTheDocument();
    expect(screen.queryByText("sections")).not.toBeInTheDocument();
    expect(screen.getByText("参数工作台").closest(".surface-card")).toHaveClass("template-workbench__parameters");
    fireEvent.click(screen.getByRole("button", { name: /概览 \{date\}/ }));
    expect(screen.getByRole("tab", { name: "诉求" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "执行链路" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "同步状态" })).toBeInTheDocument();
    expect(screen.getByLabelText("诉求文稿")).toHaveValue("分析 {@focus_metric} 在 {date} 的变化");

    const exportLink = screen.getByRole("link", { name: "导出 JSON" });
    expect(exportLink).toHaveAttribute("href", "/rest/chatbi/v1/templates/tpl_1/export");

    fireEvent.change(screen.getByLabelText("日期预览值"), {
      target: { value: "2026-03-19" },
    });
    fireEvent.click(screen.getByRole("tab", { name: "诉求预览" }));
    expect(await screen.findByText("分析 温度 在 2026-03-19 的变化")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /设备列表/ }));
    const previewInput = await screen.findByLabelText("设备列表预览值");
    fireEvent.change(previewInput, {
      target: { value: "A站设备, B站设备" },
    });

    fireEvent.click(screen.getByRole("tab", { name: "执行预览" }));
    expect(await screen.findByText("设备 A站设备")).toBeInTheDocument();
    expect(screen.getByText("设备 B站设备")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "同步状态" }));
    expect(screen.getByText("已同步")).toBeInTheDocument();
    expect(screen.getByText("focus_metric")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "模板 JSON" }));
    const jsonPanel = screen.getByRole("tabpanel", { name: "模板 JSON" });
    expect(jsonPanel).toHaveTextContent("当前模板已按新版单轨结构维护。");
    expect(jsonPanel).toHaveTextContent('"name": "设备巡检报告"');
  });

  it("saves the structured workbench payload after editing metadata", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/rest/chatbi/v1/templates/tpl_1" && !init?.method) {
        return {
          ok: true,
          json: async () => buildTemplatePayload(),
        };
      }
      if (url === "/rest/chatbi/v1/templates/tpl_1" && init?.method === "PUT") {
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

    const parameterCard = screen.getByText("参数工作台").closest(".surface-card");
    expect(parameterCard).not.toBeNull();
    fireEvent.click(
      within(parameterCard as HTMLElement).getByRole("button", {
        name: /场景 scene \/ 固定选项 \/ 必填 \/ 单值 \/ 结构化表单/,
      }),
    );
    fireEvent.change(screen.getByLabelText("追问模式"), {
      target: { value: "chat" },
    });
    fireEvent.change(screen.getByLabelText("模板名称"), {
      target: { value: "设备巡检报告-新版" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存模板" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/rest/chatbi/v1/templates/tpl_1",
        expect.objectContaining({
          method: "PUT",
          body: expect.any(String),
        }),
      );
    });

    const payload = JSON.parse(
      fetchMock.mock.calls.find(([url, init]) => url === "/rest/chatbi/v1/templates/tpl_1" && init?.method === "PUT")?.[1]
        ?.body as string,
    );
    expect(payload.name).toBe("设备巡检报告-新版");
    expect(payload.parameters[0].id).toBe("date");
    expect(payload.parameters[1].interaction_mode).toBe("chat");
    expect(payload.sections[0].title).toBe("概览 {date}");
    expect(payload).not.toHaveProperty("previewSamples");

    expect(await screen.findByDisplayValue("设备巡检报告-新版")).toBeInTheDocument();
  });

  it("saves imported draft as a new template copy", async () => {
    const importedDraft = {
      id: "imported_template",
      name: "导入模板",
      description: "",
      category: "巡检",
      parameters: [],
      sections: [],
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/rest/chatbi/v1/templates" && init?.method === "POST") {
        return {
          ok: true,
          json: async () => ({
            ...importedDraft,
            id: "tpl_new",
            created_at: "2026-04-02T00:00:00",
          }),
        };
      }
      throw new Error(`Unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderTemplateDetailPage({
      pathname: "/templates/new",
      state: {
        importDraft: importedDraft,
        saveMode: "create_copy",
      },
    });

    expect(await screen.findByDisplayValue("导入模板")).toBeInTheDocument();
    expect(screen.getByText("当前为导入草稿，尚未保存。")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "保存模板" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/rest/chatbi/v1/templates",
        expect.objectContaining({
          method: "POST",
          body: expect.any(String),
        }),
      );
    });
  });

  it("saves imported draft in overwrite mode using the target template id", async () => {
    const importedDraft = {
      id: "imported_template",
      name: "导入模板",
      description: "",
      category: "巡检",
      parameters: [],
      sections: [],
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/rest/chatbi/v1/templates/tpl-9" && init?.method === "PUT") {
        return {
          ok: true,
          json: async () => ({
            ...importedDraft,
            id: "tpl_9",
            created_at: "2026-04-02T00:00:00",
          }),
        };
      }
      throw new Error(`Unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderTemplateDetailPage({
      pathname: "/templates/new",
      state: {
        importDraft: importedDraft,
        saveMode: "overwrite",
        targetTemplateId: "tpl-9",
        targetTemplateName: "已有模板",
      },
    });

    expect(await screen.findByDisplayValue("导入模板")).toBeInTheDocument();
    expect(screen.getByText("当前为导入草稿，尚未保存。")).toBeInTheDocument();
    expect(screen.getByText("保存后将覆盖模板：已有模板。")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "保存模板" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/rest/chatbi/v1/templates/tpl-9",
        expect.objectContaining({
          method: "PUT",
          body: expect.any(String),
        }),
      );
    });
  });

  it("saves structured dataset configuration without raw json editing", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/rest/chatbi/v1/templates/tpl_1" && !init?.method) {
        return {
          ok: true,
          json: async () => buildTemplatePayload(),
        };
      }
      if (url === "/rest/chatbi/v1/templates/tpl_1" && init?.method === "PUT") {
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
    fireEvent.click(screen.getByRole("tab", { name: "执行链路" }));
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
        "/rest/chatbi/v1/templates/tpl_1",
        expect.objectContaining({
          method: "PUT",
          body: expect.any(String),
        }),
      );
    });

    const payload = JSON.parse(
      fetchMock.mock.calls.find(([url, init]) => url === "/rest/chatbi/v1/templates/tpl_1" && init?.method === "PUT")?.[1]
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

  it("items save when parameter ids are duplicated", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
      if (url === "/rest/chatbi/v1/templates/tpl_1" && !init?.method) {
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
    await screen.findByLabelText("参数标识");
    fireEvent.change(screen.getByLabelText("参数标识"), {
      target: { value: "date" },
    });

    fireEvent.click(screen.getByRole("tab", { name: "模板 JSON" }));
    expect(await screen.findByText("参数标识不能重复：date")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "保存模板" })).toBeDisabled();
  });

  it("renders typed outline item config controls in requirement workbench", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
      if (url === "/rest/chatbi/v1/templates/tpl_1" && !init?.method) {
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
    fireEvent.click(screen.getByRole("button", { name: /概览 \{date\}/ }));
    fireEvent.click(screen.getByRole("button", { name: /analysis_period/i }));

    expect(screen.getByLabelText("时间控件 analysis_period")).toHaveValue("date_range");
    expect(screen.queryByLabelText("动态来源 analysis_period")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("固定选项 analysis_period")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /target_scene/i }));
    expect(screen.getByLabelText("绑定参数 target_scene")).toHaveValue("scene");
    expect(screen.queryByLabelText("固定选项 target_scene")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("动态来源 target_scene")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /focus_metric/i }));
    expect(screen.getByLabelText("选项来源 focus_metric")).toHaveValue("options");
    expect(screen.getByLabelText("固定选项 focus_metric")).toHaveValue("温度, 湿度");

    fireEvent.change(screen.getByLabelText("选项来源 focus_metric"), {
      target: { value: "source" },
    });

    expect(await screen.findByLabelText("动态来源 focus_metric")).toBeInTheDocument();
    expect(screen.queryByLabelText("固定选项 focus_metric")).not.toBeInTheDocument();
  });

  it("renders specialized controls for number, threshold, boolean, and operator items", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
      if (url === "/rest/chatbi/v1/templates/tpl_1" && !init?.method) {
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
    fireEvent.click(screen.getByRole("button", { name: /概览 \{date\}/ }));
    fireEvent.click(screen.getByRole("button", { name: /top_n/i }));

    expect(screen.getByLabelText("数值默认值 top_n")).toHaveAttribute("type", "number");
    fireEvent.click(screen.getByRole("button", { name: /alarm_threshold/i }));
    expect(screen.getByLabelText("数值默认值 alarm_threshold")).toHaveAttribute("type", "number");
    fireEvent.click(screen.getByRole("button", { name: /include_closed_loop/i }));
    expect(screen.getByLabelText("布尔默认值 include_closed_loop")).toHaveValue("true");
    fireEvent.click(screen.getByRole("button", { name: /compare_operator/i }));
    expect(screen.getByLabelText("运算符默认值 compare_operator")).toHaveValue(">=");

    fireEvent.click(screen.getByRole("button", { name: /top_n/i }));
    expect(screen.queryByLabelText("控件形态 top_n")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /alarm_threshold/i }));
    expect(screen.queryByLabelText("控件形态 alarm_threshold")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /include_closed_loop/i }));
    expect(screen.queryByLabelText("控件形态 include_closed_loop")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /compare_operator/i }));
    expect(screen.queryByLabelText("控件形态 compare_operator")).not.toBeInTheDocument();
  });
});
