import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { TemplateDetailPage } from "./TemplateDetailPage";
import type { ReportTemplate } from "../entities/templates/types";

function renderPage(route = "/templates/new", state?: Record<string, unknown>) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[state ? { pathname: route, state } : route]}>
        <Routes>
          <Route path="/templates/new" element={<TemplateDetailPage />} />
          <Route path="/templates/:templateId" element={<TemplateDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TemplateDetailPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("creates a formal template payload rooted at recursive catalogs", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (url === "/rest/chatbi/v1/templates" && init?.method === "POST") {
        return Promise.resolve({ ok: true, json: async () => JSON.parse(String(init.body)) });
      }
      if (url === "/rest/chatbi/v1/templates/tpl_network_daily" && !init?.method) {
        return Promise.resolve({ ok: true, json: async () => ({}) });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    fireEvent.change(screen.getByLabelText("模板 ID"), { target: { value: "tpl_network_daily" } });
    fireEvent.change(screen.getByLabelText("分类"), { target: { value: "network_operations" } });
    fireEvent.change(screen.getByLabelText("名称"), { target: { value: "网络运行日报" } });
    fireEvent.change(screen.getByLabelText("描述"), { target: { value: "面向网络运维中心的统一日报模板。" } });

    fireEvent.click(screen.getByRole("button", { name: "新增根目录" }));
    fireEvent.change(screen.getByLabelText("目录 ID"), { target: { value: "catalog_overview" } });
    fireEvent.change(screen.getByLabelText("目录标题"), { target: { value: "运行概览" } });
    fireEvent.click(screen.getByRole("button", { name: "新增章节" }));
    fireEvent.change(screen.getByLabelText("章节 ID"), { target: { value: "section_overview" } });
    fireEvent.change(screen.getByLabelText("诉求文本"), { target: { value: "分析{@scope_item}的总体运行态势。" } });

    fireEvent.click(screen.getByRole("button", { name: "保存模板" }));

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([url, requestInit]) => url === "/rest/chatbi/v1/templates" && requestInit?.method === "POST");
      expect(call).toBeTruthy();
      const payload = JSON.parse(String(call?.[1]?.body));
      expect(payload.id).toBe("tpl_network_daily");
      expect(payload.catalogs[0].id).toBe("catalog_overview");
      expect(payload.catalogs[0].title).toBe("运行概览");
      expect(payload.catalogs[0].sections[0].id).toBe("section_overview");
      expect(payload.catalogs[0].sections[0].title).toBeUndefined();
      expect(payload.sections).toBeUndefined();
      expect(payload.structureType).toBe("flow");
    });
  });

  it("saves an imported paged template without converting chapters to catalogs", async () => {
    const pagedDraft: ReportTemplate = {
      id: "tpl_network_paged",
      category: "network_operations",
      name: "网络运行 PPT",
      description: "分页模板",
      schemaVersion: "template.v3",
      structureType: "paged",
      parameters: [],
      chapters: [
        {
          id: "chapter_overview",
          title: "运行概览",
          slides: [
            {
              id: "slide_traffic",
              title: "流量趋势",
              layout: { layoutId: "two-column" },
              sections: [
                {
                  id: "section_traffic",
                  outline: { requirement: "展示流量趋势。", items: [] },
                  content: {
                    datasets: [{ id: "datasetTraffic", sourceType: "sql", source: "select * from network_traffic" }],
                    presentation: {
                      kind: "chart",
                      blocks: [
                        {
                          id: "chartTraffic",
                          type: "chart",
                          title: "流量趋势",
                          datasetId: "datasetTraffic",
                          properties: { preferredType: "line" },
                        },
                      ],
                    },
                  },
                },
              ],
            },
          ],
        },
      ],
    };
    const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (url === "/rest/chatbi/v1/templates" && init?.method === "POST") {
        return Promise.resolve({ ok: true, json: async () => JSON.parse(String(init.body)) });
      }
      if (url === "/rest/chatbi/v1/templates/tpl_network_paged" && !init?.method) {
        return Promise.resolve({ ok: true, json: async () => ({}) });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPage("/templates/new", {
      importDraft: pagedDraft,
      importWarnings: [{ code: "normalized", message: "已规范化为分页模板" }],
    });

    expect(screen.getByDisplayValue("PPT / paged")).toBeInTheDocument();
    expect(screen.getByText("PPT 章节与页面")).toBeInTheDocument();
    expect(screen.getByLabelText("模板结构导航")).toBeInTheDocument();
    expect(screen.getAllByText("运行概览").length).toBeGreaterThan(0);
    expect(screen.getAllByText("流量趋势").length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: "新增根目录" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "保存模板" }));

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([url, requestInit]) => url === "/rest/chatbi/v1/templates" && requestInit?.method === "POST");
      expect(call).toBeTruthy();
      const payload = JSON.parse(String(call?.[1]?.body));
      expect(payload.structureType).toBe("paged");
      expect(payload.chapters[0].slides[0].sections[0].content.datasets[0].source).toBe("select * from network_traffic");
      expect(payload.chapters[0].slides[0].layout.layoutId).toBe("two-column");
      expect(payload.catalogs).toBeUndefined();
    });
  });
});
