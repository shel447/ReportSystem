import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { ReportDesignerPage } from "./ReportDesignerPage";

vi.mock("@cloudsop/bi-designer", () => ({
  applyAutoLayoutToDoc: (doc: Record<string, unknown>) => doc,
  createEditorStore: (doc: Record<string, unknown>) => ({
    getState: () => ({ doc, docRevision: 1, isDirty: false, setDoc: vi.fn(), getDoc: () => doc }),
    subscribe: () => () => undefined,
  }),
  PptEditor: () => <div data-testid="ppt-editor">PPT Designer</div>,
  ReportEditor: () => <div data-testid="report-editor">Report Designer</div>,
}));

function renderDesigner() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/reports/rpt-1/designer"]}>
        <Routes>
          <Route path="/reports/:reportId/designer" element={<ReportDesignerPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function stubReport(report: Record<string, unknown>) {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    json: async () => ({
      reportId: "rpt-1",
      status: "available",
      answerType: "REPORT",
      answer: { reportId: "rpt-1", status: "available", report },
    }),
  })));
}

describe("ReportDesignerPage", () => {
  it("opens ReportEditor for flow DSL", async () => {
    stubReport({ structureType: "flow", basicInfo: {}, catalogs: [], layout: { type: "flow" } });
    renderDesigner();
    expect(await screen.findByTestId("report-editor")).toBeInTheDocument();
    expect(screen.getByText("下载 DSL JSON")).toBeInTheDocument();
  });

  it("opens PptEditor for paged DSL", async () => {
    stubReport({ basicInfo: { reportType: "ppt" }, content: [] });
    renderDesigner();
    expect(await screen.findByTestId("ppt-editor")).toBeInTheDocument();
  });
});
