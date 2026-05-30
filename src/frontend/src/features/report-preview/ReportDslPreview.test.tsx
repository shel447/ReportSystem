import { act, render, screen } from "@testing-library/react";
import type { EditorStoreApi } from "@cloudsop/bi-designer";

import { ReportDslPreview } from "./ReportDslPreview";

vi.mock("@cloudsop/bi-engine", () => ({
  BIEngine: ({ schema }: { schema: { id: string } }) => <div data-testid="bi-component">{schema.id}</div>,
}));

vi.mock("@cloudsop/bi-designer", () => ({
  applyAutoLayoutToDoc: (report: Record<string, unknown>) => report,
  createEditorStore: (doc: Record<string, unknown>) => ({ getState: () => ({ doc, docRevision: 1, getDoc: () => doc }), subscribe: () => () => undefined }),
  PptSlideFrame: ({ slide }: { slide: { id: string } }) => <div data-testid="ppt-slide">{slide.id}</div>,
}));

describe("ReportDslPreview", () => {
  it("renders flow components recursively through BIEngine", () => {
    render(
      <ReportDslPreview
        report={{
          structureType: "flow",
          catalogs: [{
            id: "catalog-1",
            name: "总览",
            subCatalogs: [{
              id: "catalog-1-1",
              name: "指标",
              sections: [{ id: "section-1", components: [{ id: "text-1", type: "text" }] }],
            }],
          }],
        }}
      />,
    );

    expect(screen.getAllByText("总览")).toHaveLength(2);
    expect(screen.getAllByText("指标")).toHaveLength(2);
    expect(screen.getByTestId("bi-component")).toHaveTextContent("text-1");
    expect(screen.getByLabelText("报告大纲")).toBeInTheDocument();
  });

  it("recognizes paged reports from basicInfo.reportType and renders a slide", () => {
    render(
      <ReportDslPreview
        report={{
          basicInfo: { reportType: "ppt" },
          content: [{ id: "chapter-1", type: "section", slides: [{ id: "slide-1", title: "首页", components: [] }] }],
        }}
      />,
    );

    expect(screen.getByTestId("ppt-slide")).toHaveTextContent("__ppt_cover__");
    expect(screen.getByText("1 / 5")).toBeInTheDocument();
    expect(screen.getByLabelText("幻灯片大纲")).toBeInTheDocument();
  });

  it("renders store updates immediately in preview", () => {
    let doc = {
      structureType: "flow",
      catalogs: [{ id: "catalog-live", name: "初始目录", sections: [] }],
    };
    let revision = 1;
    const listeners = new Set<() => void>();
    const store = {
      getState: () => ({ doc, docRevision: revision, getDoc: () => doc }),
      subscribe: (listener: () => void) => {
        listeners.add(listener);
        return () => listeners.delete(listener);
      },
    } as unknown as EditorStoreApi;

    render(<ReportDslPreview store={store} />);
    expect(screen.getAllByText("初始目录")).toHaveLength(2);

    act(() => {
      doc = { structureType: "flow", catalogs: [{ id: "catalog-live", name: "编辑后的目录", sections: [] }] };
      revision += 1;
      listeners.forEach((listener) => listener());
    });
    expect(screen.getAllByText("编辑后的目录")).toHaveLength(2);
  });
});
