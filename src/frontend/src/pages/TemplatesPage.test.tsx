import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";

import { TemplatesPage } from "./TemplatesPage";

function ImportTarget() {
  const location = useLocation();
  return (
    <div>
      <div data-testid="import-target-path">{location.pathname}</div>
      <pre data-testid="import-target-state">{JSON.stringify(location.state)}</pre>
    </div>
  );
}

function renderTemplatesPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/templates"]}>
        <Routes>
          <Route path="/templates" element={<TemplatesPage />} />
          <Route path="/templates/new" element={<ImportTarget />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TemplatesPage", () => {
  it("loads template cards without embedding the full editor", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/rest/chatbi/v1/templates") {
        return {
          ok: true,
          json: async () => [
            {
              id: "tpl-1",
              name: "设备巡检报告",
              description: "巡检模板",
              category: "巡检",
              parameter_count: 3,
              top_level_section_count: 4,
            },
          ],
        };
      }
      throw new Error(`Unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderTemplatesPage();

    expect(await screen.findByRole("link", { name: /设备巡检报告/ })).toHaveAttribute(
      "href",
      "/templates/tpl-1",
    );
    expect(screen.getByText("3 个参数")).toBeInTheDocument();
    expect(screen.getByText("4 个顶层章节")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "新建模板" })).toHaveAttribute("href", "/templates/new");
    expect(screen.queryByLabelText("模板名称")).not.toBeInTheDocument();
  });

  it("imports a json template draft and navigates to the new template page", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/rest/chatbi/v1/templates" && !init?.method) {
        return {
          ok: true,
          json: async () => [],
        };
      }
      if (url === "/rest/chatbi/v1/templates/import/preview" && init?.method === "POST") {
        return {
          ok: true,
          json: async () => ({
            normalized_template: {
              id: "imported_template",
              name: "导入模板",
              description: "",
              category: "巡检",
              parameters: [],
              sections: [],
            },
            source_kind: "system_export",
            warnings: [],
            conflict: {
              status: "none",
              matched_templates: [],
              overwrite_supported: false,
              default_action: "create_copy",
            },
          }),
        };
      }
      throw new Error(`Unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderTemplatesPage();
    await screen.findByText("暂无模板");

    const file = new File(
      [
        JSON.stringify({
          name: "导入模板",
          category: "巡检",
          description: "导入描述",
          parameters: [],
          sections: [],
        }),
      ],
      "template.json",
      { type: "application/json" },
    );

    fireEvent.change(screen.getByLabelText("导入模板文件"), {
      target: { files: [file] },
    });

    await screen.findByTestId("import-target-path");
    expect(screen.getByTestId("import-target-path")).toHaveTextContent("/templates/new");
    expect(screen.getByTestId("import-target-state")).toHaveTextContent("\"saveMode\":\"create_copy\"");
    expect(screen.getByTestId("import-target-state")).toHaveTextContent("\"name\":\"导入模板\"");
  });

  it("requires conflict resolution before navigating when a single target matches", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/rest/chatbi/v1/templates" && !init?.method) {
        return {
          ok: true,
          json: async () => [],
        };
      }
      if (url === "/rest/chatbi/v1/templates/import/preview" && init?.method === "POST") {
        return {
          ok: true,
          json: async () => ({
            normalized_template: {
              id: "imported_template",
              name: "导入模板",
              description: "",
              category: "巡检",
              parameters: [],
              sections: [],
            },
            source_kind: "system_export",
            warnings: [],
            conflict: {
              status: "single_match",
              matched_templates: [{ template_id: "tpl-1", name: "已有模板" }],
              overwrite_supported: true,
              default_action: "create_copy",
            },
          }),
        };
      }
      throw new Error(`Unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderTemplatesPage();
    await screen.findByText("暂无模板");

    const file = new File(
      [
        JSON.stringify({
          name: "导入模板",
          category: "巡检",
          description: "导入描述",
          parameters: [],
          sections: [],
        }),
      ],
      "template.json",
      { type: "application/json" },
    );

    fireEvent.change(screen.getByLabelText("导入模板文件"), {
      target: { files: [file] },
    });

    expect(await screen.findByRole("dialog", { name: "处理模板冲突" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "覆盖现有模板" }));

    await waitFor(() => {
      expect(screen.getByTestId("import-target-path")).toHaveTextContent("/templates/new");
    });
    expect(screen.getByTestId("import-target-state")).toHaveTextContent("\"saveMode\":\"overwrite\"");
    expect(screen.getByTestId("import-target-state")).toHaveTextContent("\"targetTemplateId\":\"tpl-1\"");
  });
});
