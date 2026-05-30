import type { ChatStreamDelta } from "../../entities/chat/types";

export type DemoReportTemplate = {
  id: string;
  name: string;
  description: string;
  structureType: "flow" | "paged";
  report: Record<string, unknown>;
};

const MONTHLY_ROWS = [
  { month: "1月", online: 812, offline: 526, completion: 72 },
  { month: "2月", online: 938, offline: 584, completion: 78 },
  { month: "3月", online: 1026, offline: 601, completion: 83 },
  { month: "4月", online: 1182, offline: 648, completion: 88 },
  { month: "5月", online: 1268, offline: 692, completion: 92 },
  { month: "6月", online: 1396, offline: 735, completion: 96 },
];

const REGION_ROWS = [
  { region: "华东", revenue: 3860, growth: 18.2, owner: "区域一部", status: "领先" },
  { region: "华南", revenue: 3180, growth: 13.6, owner: "区域二部", status: "稳定" },
  { region: "华北", revenue: 2840, growth: 9.8, owner: "区域三部", status: "稳定" },
  { region: "西南", revenue: 1960, growth: 21.4, owner: "区域四部", status: "增长" },
  { region: "西北", revenue: 1280, growth: 7.6, owner: "区域五部", status: "关注" },
  { region: "东北", revenue: 1120, growth: 6.4, owner: "区域六部", status: "关注" },
];

const TABLE_COLUMNS = [
  { title: "区域", key: "region", type: "string", width: 100 },
  { title: "收入（万元）", key: "revenue", type: "double", width: 130, sortable: true },
  { title: "同比增长", key: "growth", type: "double", width: 110, sortable: true, uiConfig: { valueFormat: { type: "percentage", decimalPlaces: 1 } } },
  { title: "负责团队", key: "owner", type: "string", width: 120, filterable: true },
  { title: "状态", key: "status", type: "string", width: 90, enumConfig: [{ label: "领先", value: "领先" }, { label: "稳定", value: "稳定" }, { label: "增长", value: "增长" }, { label: "关注", value: "关注" }] },
];

function text(id: string, content: string, title?: string) {
  return { id, type: "text", dataProperties: { dataType: "static", title, content } };
}

function markdown(id: string, content: string) {
  return { id, type: "markdown", dataProperties: { dataType: "static", content } };
}

function table(id: string, title: string, rows = REGION_ROWS) {
  return {
    id,
    type: "table",
    dataProperties: {
      dataType: "static",
      title,
      columns: TABLE_COLUMNS,
      data: rows,
      mergeColumns: [{ title: "经营表现", columns: ["revenue", "growth"] }],
    },
    advanceProperties: { pagination: { enabled: true, pageSize: 6 } },
  };
}

function compositeTable(id: string) {
  return {
    id,
    type: "compositeTable",
    dataProperties: { dataType: "static", title: "区域经营组合表" },
    tables: [
      table(`${id}-east`, "重点区域", REGION_ROWS.slice(0, 3)),
      table(`${id}-west`, "成长区域", REGION_ROWS.slice(3, 5)),
      table(`${id}-watch`, "关注区域", REGION_ROWS.slice(5)),
    ],
  };
}

function chart(
  id: string,
  title: string,
  type: "line" | "bar" | "pie" | "scatter" | "radar" | "gauge" | "candlestick",
  data: Array<Record<string, unknown>>,
  encode: Record<string, unknown>,
  columns: Array<Record<string, unknown>>,
  advanceProperties?: Record<string, unknown>,
) {
  return {
    id,
    type: "chart",
    dataProperties: {
      dataType: "static",
      title,
      columns,
      data,
      series: [{ type, name: title, encode }],
      ...(type === "line" || type === "bar" || type === "scatter" || type === "candlestick"
        ? { xAxis: { type: "category" }, yAxis: { type: "value" } }
        : {}),
    },
    ...(advanceProperties ? { advanceProperties } : {}),
  };
}

const lineChart = chart(
  "chart-line-monthly",
  "月度渠道收入趋势",
  "line",
  MONTHLY_ROWS,
  { x: "month", y: "online" },
  [{ title: "月份", key: "month", type: "string" }, { title: "线上", key: "online", type: "double" }],
);

const barChart = chart(
  "chart-bar-region",
  "区域收入对比",
  "bar",
  REGION_ROWS,
  { x: "region", y: "revenue" },
  [{ title: "区域", key: "region", type: "string" }, { title: "收入", key: "revenue", type: "double" }],
);

const pieChart = chart(
  "chart-pie-channel",
  "渠道收入占比",
  "pie",
  [{ channel: "线上", value: 61 }, { channel: "线下", value: 31 }, { channel: "合作伙伴", value: 8 }],
  { name: "channel", value: "value" },
  [{ title: "渠道", key: "channel", type: "string" }, { title: "占比", key: "value", type: "double" }],
);

const scatterChart = chart(
  "chart-scatter-growth",
  "收入与增长分布",
  "scatter",
  REGION_ROWS,
  { x: "revenue", y: "growth" },
  [{ title: "收入", key: "revenue", type: "double" }, { title: "增长", key: "growth", type: "double" }],
);

const radarChart = chart(
  "chart-radar-capability",
  "区域能力雷达",
  "radar",
  [{ region: "华东", values: [92, 86, 88, 81] }],
  { name: "region", value: "values" },
  [{ title: "区域", key: "region", type: "string" }, { title: "能力值", key: "values", type: "double" }],
  { eChartOption: { radar: { indicator: [{ name: "收入", max: 100 }, { name: "增长", max: 100 }, { name: "客户", max: 100 }, { name: "交付", max: 100 }] } } },
);

const gaugeChart = chart(
  "chart-gauge-target",
  "年度目标达成率",
  "gauge",
  [{ metric: "达成率", value: 86 }],
  { value: "value" },
  [{ title: "指标", key: "metric", type: "string" }, { title: "达成率", key: "value", type: "double" }],
);

const candlestickChart = chart(
  "chart-kline-price",
  "产品价格波动",
  "candlestick",
  [
    { day: "周一", open: 20, close: 25, low: 18, high: 28 },
    { day: "周二", open: 25, close: 23, low: 21, high: 27 },
    { day: "周三", open: 23, close: 29, low: 22, high: 31 },
    { day: "周四", open: 29, close: 27, low: 25, high: 30 },
  ],
  { x: "day", open: "open", close: "close", low: "low", high: "high" },
  [{ title: "日期", key: "day", type: "string" }, { title: "开盘", key: "open", type: "double" }, { title: "收盘", key: "close", type: "double" }, { title: "最低", key: "low", type: "double" }, { title: "最高", key: "high", type: "double" }],
);

const flowReport = {
  structureType: "flow",
  basicInfo: { id: "demo-flow-operations", schemaVersion: "1.0.0", status: "Success", name: "经营分析综合报告", reportType: "word" },
  catalogs: [
    {
      id: "catalog-overview",
      name: "经营总览",
      sections: [{ id: "section-overview", title: "核心结论", components: [text("text-overview", "本期经营质量保持稳定，华东和西南区域贡献了主要增量。"), markdown("markdown-overview", "### 管理摘要\n- 收入同比增长 **14.8%**\n- 目标达成率维持在合理区间") ] }],
      subCatalogs: [{
        id: "catalog-overview-charts",
        name: "趋势与结构",
        sections: [{ id: "section-main-charts", title: "关键趋势", components: [lineChart, barChart, pieChart] }],
      }],
    },
    {
      id: "catalog-tables",
      name: "区域明细",
      sections: [
        { id: "section-table", title: "基础表格", components: [table("table-region", "区域经营明细")] },
        { id: "section-composite", title: "组合表格", components: [compositeTable("table-composite")] },
      ],
    },
    {
      id: "catalog-chart-lab",
      name: "高级图表",
      sections: [{ id: "section-chart-lab", title: "高级图表组件", components: [scatterChart, radarChart, gaugeChart, candlestickChart] }],
    },
  ],
  layout: { type: "flow" },
};

const pagedReport = {
  structureType: "paged",
  basicInfo: { id: "demo-paged-review", schemaVersion: "1.0.0", status: "Success", name: "经营复盘演示汇报", reportType: "ppt" },
  cover: { title: "经营复盘演示汇报", subTitle: "渠道、区域与目标达成分析", author: "ChatBI" },
  backCover: { text: "感谢阅读" },
  content: [
    {
      id: "chapter-main",
      type: "section",
      title: "经营复盘",
      slides: [
        { id: "slide-trend", title: "经营趋势", layout: { type: "grid", autoLayout: true }, components: [lineChart, barChart] },
        { id: "slide-structure", title: "渠道结构", layout: { type: "grid", autoLayout: true }, components: [pieChart, gaugeChart] },
        { id: "slide-table", title: "区域明细", layout: { type: "grid", autoLayout: true }, components: [table("ppt-table-region", "区域经营明细")] },
        { id: "slide-composite", title: "组合表格", layout: { type: "grid", autoLayout: true }, components: [compositeTable("ppt-composite")] },
        { id: "slide-advanced", title: "高级图表", layout: { type: "grid", autoLayout: true }, components: [scatterChart, radarChart, candlestickChart] },
      ],
    },
  ],
  layout: { type: "absolute" },
};

export const DEMO_REPORT_TEMPLATES: DemoReportTemplate[] = [
  {
    id: "demo-flow-operations",
    name: "经营分析综合报告",
    description: "Flow 报告：递归目录、文本、Markdown、基础表格、组合表格和完整图表类型。",
    structureType: "flow",
    report: flowReport,
  },
  {
    id: "demo-paged-review",
    name: "经营复盘演示汇报",
    description: "Paged 报告：多页 PPT、图表、表格和组合表格，直接进入 BI Designer。",
    structureType: "paged",
    report: pagedReport,
  },
];

export function createDemoStreamDeltas(template: DemoReportTemplate): ChatStreamDelta[] {
  const report = template.report;
  const deltas: ChatStreamDelta[] = [
    { action: "init_report", report: { reportId: template.id, title: template.name, structureType: template.structureType } },
  ];
  if (template.structureType === "flow") {
    appendCatalogDeltas(deltas, (report.catalogs as Array<Record<string, unknown>>) ?? [], null, null);
    return deltas;
  }
  for (const chapter of (report.content as Array<Record<string, unknown>>) ?? []) {
    deltas.push({ action: "add_chapter", structureType: "paged", chapters: [{ id: String(chapter.id), title: String(chapter.title ?? chapter.id) }] });
    for (const slide of (chapter.slides as Array<Record<string, unknown>>) ?? []) {
      deltas.push({ action: "add_slide", structureType: "paged", chapterId: String(chapter.id), slides: [{ id: String(slide.id), title: String(slide.title ?? slide.id), layout: (slide.layout as Record<string, unknown>) ?? {} }] });
      deltas.push({
        action: "add_section",
        structureType: "paged",
        parentCatalogId: null,
        parentCatalog: null,
        chapterId: String(chapter.id),
        slideId: String(slide.id),
        sections: [{ sectionId: `${String(slide.id)}-content`, status: "finished", requirement: String(slide.title ?? slide.id), components: (slide.components as Array<Record<string, unknown>>) ?? [] }],
      });
    }
  }
  return deltas;
}

function appendCatalogDeltas(deltas: ChatStreamDelta[], catalogs: Array<Record<string, unknown>>, parentCatalogId: string | null, parentCatalog: number[] | null) {
  if (catalogs.length) {
    deltas.push({
      action: "add_catalog",
      structureType: "flow",
      parentCatalogId,
      parentCatalog,
      catalogs: catalogs.map((catalog) => ({ catalogId: String(catalog.id), title: String(catalog.name ?? catalog.id) })),
    });
  }
  catalogs.forEach((catalog, index) => {
    const path = parentCatalog ? [...parentCatalog, index] : [index];
    const sections = (catalog.sections as Array<Record<string, unknown>>) ?? [];
    if (sections.length) {
      deltas.push({
        action: "add_section",
        structureType: "flow",
        parentCatalogId: String(catalog.id),
        parentCatalog: path,
        sections: sections.map((section) => ({
          sectionId: String(section.id),
          status: "finished",
          requirement: String(section.title ?? section.id),
          components: (section.components as Array<Record<string, unknown>>) ?? [],
        })),
      });
    }
    appendCatalogDeltas(deltas, (catalog.subCatalogs as Array<Record<string, unknown>>) ?? [], String(catalog.id), path);
  });
}
