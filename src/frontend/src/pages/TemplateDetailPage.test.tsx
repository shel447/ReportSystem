import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { TemplateDetailPage } from "./TemplateDetailPage";

function renderPage(route = "/templates/new") {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
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

  it("creates a formal template payload rooted at catalogs", async () => {
    let savedPayload: Record<string, unknown> | null = null;
    const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (url === "/rest/chatbi/v1/templates" && init?.method === "POST") {
        savedPayload = JSON.parse(String(init.body));
        return Promise.resolve({ ok: true, json: async () => savedPayload });
      }
      if (url === "/rest/chatbi/v1/templates/tpl_network_daily" && !init?.method) {
        return Promise.resolve({ ok: true, json: async () => savedPayload });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    fireEvent.change(screen.getByLabelText("模板 ID"), { target: { value: "tpl_network_daily" } });
    fireEvent.change(screen.getByLabelText("分类"), { target: { value: "network_operations" } });
    fireEvent.change(screen.getByLabelText("名称"), { target: { value: "网络运行日报" } });
    fireEvent.change(screen.getByLabelText("描述"), { target: { value: "面向网络运维中心的统一日报模板。" } });

    fireEvent.click(screen.getByRole("button", { name: "新增目录" }));
    const catalogIdInputs = screen.getAllByLabelText("目录 ID");
    const catalogNameInputs = screen.getAllByLabelText("目录名称");
    fireEvent.change(catalogIdInputs[0], { target: { value: "catalog_overview" } });
    fireEvent.change(catalogNameInputs[0], { target: { value: "运行概览" } });
    fireEvent.click(screen.getByRole("button", { name: "新增章节" }));

    const sectionIdInputs = screen.getAllByLabelText("章节 ID");
    const sectionTitleInputs = screen.getAllByLabelText("章节标题");
    fireEvent.change(sectionIdInputs[0], { target: { value: "section_overview" } });
    fireEvent.change(sectionTitleInputs[0], { target: { value: "总体态势" } });

    fireEvent.click(screen.getByRole("button", { name: "保存模板" }));

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([url, requestInit]) => url === "/rest/chatbi/v1/templates" && requestInit?.method === "POST");
      expect(call).toBeTruthy();
      const payload = JSON.parse(String(call?.[1]?.body));
      expect(payload.id).toBe("tpl_network_daily");
      expect(payload.catalogs[0].id).toBe("catalog_overview");
      expect(payload.catalogs[0].sections[0].id).toBe("section_overview");
      expect(payload.sections).toBeUndefined();
    });
  });
});
