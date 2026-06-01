import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { TemplatesPage } from "./TemplatesPage";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <TemplatesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TemplatesPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders template summaries from the formal template list endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ([
        {
          id: "tpl_network_daily",
          category: "network_operations",
          name: "网络运行日报",
          description: "面向网络运维中心的统一日报模板。",
          schemaVersion: "template.v3",
          structureType: "paged",
          updatedAt: "2026-04-18T09:00:00Z",
        },
      ]),
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    expect(await screen.findByText("网络运行日报")).toBeInTheDocument();
    expect(screen.getAllByText("PPT").length).toBeGreaterThan(0);
    expect(screen.getAllByText("network_operations").length).toBeGreaterThan(0);
    expect(screen.getByPlaceholderText("搜索 ID、名称、描述或分类")).toBeInTheDocument();
    expect(screen.getByLabelText("结构类型筛选")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /网络运行日报/ })).toHaveClass("template-table__row");
  });

  it("previews selected template json before opening import draft", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (url === "/rest/chatbi/v1/templates/import/preview") {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            normalizedTemplate: {
              id: "tpl_imported_paged",
              category: "network_operations",
              name: "导入分页模板",
              description: "分页模板",
              schemaVersion: "template.v3",
              structureType: "paged",
              parameters: [],
              chapters: [],
            },
            warnings: [],
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPage();

    const file = new File([JSON.stringify({ id: "tpl_imported_paged" })], "template.json", { type: "application/json" });
    fireEvent.change(screen.getByLabelText("导入模板文件"), { target: { files: [file] } });

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([url]) => url === "/rest/chatbi/v1/templates/import/preview");
      expect(call).toBeTruthy();
      expect(JSON.parse(String(call?.[1]?.body)).content.id).toBe("tpl_imported_paged");
    });
  });

  it("shows import failure for invalid json", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    renderPage();

    const file = new File(["{invalid"], "template.json", { type: "application/json" });
    fireEvent.change(screen.getByLabelText("导入模板文件"), { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("导入失败")).toBeInTheDocument();
    });
  });
});
