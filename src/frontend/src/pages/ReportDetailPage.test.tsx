import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { ReportDetailPage } from "./ReportDetailPage";

function renderReportDetailPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/reports/rpt-1"]}>
        <Routes>
          <Route path="/reports/:reportId" element={<ReportDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ReportDetailPage", () => {
  it("loads aggregated report view and renders template instance with generated content", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/rest/chatbi/v1/reports/rpt-1") {
        return {
          ok: true,
          json: async () => ({
            reportId: "rpt-1",
            status: "available",
            answerType: "REPORT",
            answer: {
              reportId: "rpt-1",
              status: "available",
              report: {
                basicInfo: {
                  id: "rpt-1",
                  schemaVersion: "1.0.0",
                  mode: "published",
                  status: "Success",
                  name: "运维日报模板",
                  category: "ops_daily",
                  description: "日报说明",
                },
                catalogs: [
                  {
                    id: "catalog_1",
                    name: "总览",
                    sections: [
                      {
                        id: "section_1",
                        title: "总览",
                        summary: { overview: "ok" },
                        components: [],
                      },
                    ],
                  },
                ],
                layout: { type: "grid", grid: { cols: 12, rowHeight: 24 } },
              },
              templateInstance: {
                id: "ti-1",
                templateId: "tpl-1",
                schemaVersion: "template-instance.vNext-draft",
                template: {
                  id: "tpl-1",
                  name: "运维日报模板",
                  category: "ops_daily",
                  description: "日报说明",
                  schemaVersion: "template.v3",
                  parameters: [],
                  catalogs: [],
                },
                conversationId: "conv-1",
                status: "completed",
                captureStage: "report_ready",
                revision: 3,
                parameters: [],
                parameterConfirmation: { missingParameterIds: [], confirmed: true },
                catalogs: [
                  {
                    id: "catalog_overview",
                    title: "运行概览",
                    renderedTitle: "运行概览",
                    sections: [
                      {
                        id: "section_device_profile",
                        outline: {
                          requirement: "分析总部网络的设备巡检结果。",
                          renderedRequirement: "分析总部网络的设备巡检结果。",
                          items: [],
                        },
                        runtimeContext: { bindings: [] },
                        skeletonStatus: "reusable",
                        userEdited: false,
                        content: {
                          datasets: [
                            {
                              id: "dataset_device_basic",
                              name: "设备基础信息",
                              sourceType: "sql",
                              sourceRef: "sql.network.device_basic",
                            },
                          ],
                          presentation: {
                            kind: "mixed",
                            blocks: [
                              {
                                id: "block_device_inspection",
                                type: "composite_table",
                                title: "核心设备巡检信息",
                                parts: [
                                  {
                                    id: "part_basic_info",
                                    title: "基础信息",
                                    sourceType: "query",
                                    datasetId: "dataset_device_basic",
                                    tableLayout: { kind: "table", showHeader: true },
                                    runtimeContext: {
                                      status: "pending",
                                      resolvedDatasetId: "dataset_device_basic",
                                      resolvedQuery: "scope_id = 'hq-network'",
                                    },
                                  },
                                ],
                              },
                            ],
                          },
                        },
                      },
                    ],
                  },
                ],
                documents: [],
                createdAt: "2026-04-18T09:00:00Z",
                updatedAt: "2026-04-18T09:00:00Z",
              },
              documents: [],
              generationProgress: { totalSections: 1, completedSections: 1 },
            },
          }),
        };
      }
      throw new Error(`Unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderReportDetailPage();

    expect((await screen.findAllByText("运维日报模板")).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("available").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("rpt-1")).toBeInTheDocument();
    expect(screen.getByText("模板实例快照")).toBeInTheDocument();
    expect(screen.getByText("正式报告内容")).toBeInTheDocument();
    expect(screen.getAllByText(/总览/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("核心设备巡检信息")).toBeInTheDocument();
  });
});
