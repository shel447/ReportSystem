import { createDemoStreamDeltas, DEMO_REPORT_TEMPLATES } from "./demo-report-templates";

describe("demo report templates", () => {
  it("covers flow, paged and the BI Engine component families", () => {
    expect(DEMO_REPORT_TEMPLATES.map((item) => item.structureType)).toEqual(["flow", "paged"]);
    const components = DEMO_REPORT_TEMPLATES.flatMap((template) => collectComponents(template.report));
    expect(new Set(components.map((component) => component.type))).toEqual(new Set(["text", "markdown", "table", "compositeTable", "chart"]));
    expect(new Set(components.filter((component) => component.type === "chart").flatMap((component) => readChartTypes(component)))).toEqual(
      new Set(["line", "bar", "pie", "scatter", "radar", "gauge", "candlestick"]),
    );
  });

  it("creates reducer-compatible flow and paged delta sequences", () => {
    const flowDeltas = createDemoStreamDeltas(DEMO_REPORT_TEMPLATES[0]);
    const pagedDeltas = createDemoStreamDeltas(DEMO_REPORT_TEMPLATES[1]);
    expect(flowDeltas.some((delta) => delta.action === "add_catalog")).toBe(true);
    expect(flowDeltas.some((delta) => delta.action === "add_section")).toBe(true);
    expect(pagedDeltas.some((delta) => delta.action === "add_chapter")).toBe(true);
    expect(pagedDeltas.some((delta) => delta.action === "add_slide")).toBe(true);
    expect(pagedDeltas.some((delta) => delta.action === "add_section" && delta.structureType === "paged")).toBe(true);
  });

  it("uses formal cover fields instead of a persisted fake cover slide", () => {
    const paged = DEMO_REPORT_TEMPLATES.find((template) => template.structureType === "paged")!;
    expect(paged.report.cover).toMatchObject({ title: "经营复盘演示汇报" });
    const slides = ((paged.report.content as Array<Record<string, unknown>>)[0].slides as Array<Record<string, unknown>>);
    expect(slides.some((slide) => slide.id === "slide-cover")).toBe(false);
  });
});

function collectComponents(report: Record<string, unknown>) {
  if (report.structureType === "flow") {
    return collectCatalogComponents((report.catalogs as Array<Record<string, unknown>>) ?? []);
  }
  return ((report.content as Array<Record<string, unknown>>) ?? []).flatMap((chapter) =>
    ((chapter.slides as Array<Record<string, unknown>>) ?? []).flatMap((slide) => (slide.components as Array<Record<string, unknown>>) ?? []),
  );
}

function collectCatalogComponents(catalogs: Array<Record<string, unknown>>): Array<Record<string, unknown>> {
  return catalogs.flatMap((catalog) => [
    ...((catalog.sections as Array<Record<string, unknown>>) ?? []).flatMap((section) => (section.components as Array<Record<string, unknown>>) ?? []),
    ...collectCatalogComponents((catalog.subCatalogs as Array<Record<string, unknown>>) ?? []),
  ]);
}

function readChartTypes(component: Record<string, unknown>) {
  const dataProperties = component.dataProperties as Record<string, unknown>;
  return ((dataProperties.series as Array<Record<string, unknown>>) ?? []).map((series) => String(series.type));
}
