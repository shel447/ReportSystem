import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { TemplatesPage } from "./TemplatesPage";

function renderTemplatesPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <TemplatesPage />
    </QueryClientProvider>,
  );
}

describe("TemplatesPage", () => {
  it("loads template list, renders detail, and updates template", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
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
      if (url === "/api/templates/tpl-1" && !init?.method) {
        return {
          ok: true,
          json: async () => ({
            template_id: "tpl-1",
            name: "设备巡检报告",
            description: "巡检模板",
            report_type: "daily",
            scenario: "集团",
            type: "巡检",
            scene: "总部",
            match_keywords: ["巡检"],
            content_params: [],
            parameters: [{ id: "date", label: "日期", input_type: "date", required: true }],
            outline: [],
            sections: [{ title: "概览", content: { presentation: { type: "text", template: "ok" } } }],
            schema_version: "v2.0",
            output_formats: ["md"],
            version: "1.0",
          }),
        };
      }
      if (url === "/api/templates/tpl-1" && init?.method === "PUT") {
        return {
          ok: true,
          json: async () => ({
            template_id: "tpl-1",
            name: "设备巡检报告-新版",
            description: "巡检模板",
            report_type: "daily",
            scenario: "集团",
            type: "巡检",
            scene: "总部",
            match_keywords: ["巡检"],
            content_params: [],
            parameters: [{ id: "date", label: "日期", input_type: "date", required: true }],
            outline: [],
            sections: [{ title: "概览", content: { presentation: { type: "text", template: "ok" } } }],
            schema_version: "v2.0",
            output_formats: ["md"],
            version: "1.0",
          }),
        };
      }
      throw new Error(`Unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderTemplatesPage();

    expect(await screen.findByText("设备巡检报告")).toBeInTheDocument();
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
        }),
      );
    });

    expect(await screen.findByDisplayValue("设备巡检报告-新版")).toBeInTheDocument();
  });
});
