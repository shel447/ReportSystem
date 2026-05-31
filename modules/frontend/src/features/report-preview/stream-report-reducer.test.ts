import { canPreviewStreamReport, reduceStreamReport } from "./stream-report-reducer";

describe("stream report reducer", () => {
  it("builds a flow report from catalog and section deltas", () => {
    const report = reduceStreamReport([
      { action: "init_report", report: { reportId: "rpt-flow", title: "日报" } },
      {
        action: "add_catalog",
        structureType: "flow",
        parentCatalogId: null,
        parentCatalog: null,
        catalogs: [{ catalogId: "catalog-overview", title: "运行概览" }],
      },
      {
        action: "add_section",
        structureType: "flow",
        parentCatalogId: "catalog-overview",
        parentCatalog: [0],
        sections: [{
          sectionId: "section-kpi",
          status: "finished",
          requirement: "核心指标",
          components: [{ id: "text-1", type: "text", dataProperties: { content: "稳定" } }],
        }],
      },
    ]);

    expect(report).toMatchObject({
      structureType: "flow",
      catalogs: [{
        id: "catalog-overview",
        name: "运行概览",
        sections: [{
          id: "section-kpi",
          title: "核心指标",
          components: [{ id: "text-1", type: "text" }],
        }],
      }],
    });
    expect(canPreviewStreamReport(report)).toBe(true);
  });

  it("keeps future paged deltas renderable", () => {
    const report = reduceStreamReport([
      { action: "init_report", report: { reportId: "rpt-ppt", title: "周报", structureType: "paged" } },
      { action: "add_chapter", structureType: "paged", chapters: [{ id: "chapter-1", title: "总览" }] },
      {
        action: "add_slide",
        structureType: "paged",
        chapterId: "chapter-1",
        slides: [{ id: "slide-1", title: "指标", layout: { type: "absolute" } }],
      },
      {
        action: "add_section",
        structureType: "paged",
        parentCatalogId: null,
        parentCatalog: null,
        chapterId: "chapter-1",
        slideId: "slide-1",
        sections: [{
          sectionId: "section-1",
          status: "finished",
          requirement: "指标",
          components: [{ id: "table-1", type: "table" }],
        }],
      },
    ]);

    expect(report).toMatchObject({
      structureType: "paged",
      content: [{
        id: "chapter-1",
        slides: [{
          id: "slide-1",
          components: [{ id: "table-1", type: "table" }],
        }],
      }],
    });
    expect(canPreviewStreamReport(report)).toBe(true);
  });
});
