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
          updatedAt: "2026-04-18T09:00:00Z",
        },
      ]),
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    expect(await screen.findByText("网络运行日报")).toBeInTheDocument();
    expect(screen.getByText("network_operations")).toBeInTheDocument();
    expect(screen.getByText("tpl_network_daily")).toBeInTheDocument();
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
