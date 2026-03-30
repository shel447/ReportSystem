import { describe, expect, it } from "vitest";

import type { TemplateWorkbenchState } from "./state";
import { buildBlueprintPreview, buildStructuralPreview } from "./preview";

function createState(): TemplateWorkbenchState {
  return {
    meta: {
      templateId: "tpl-1",
      name: "设备巡检报告",
      description: "",
      reportType: "daily",
      scenario: "集团",
      type: "巡检",
      scene: "总部",
      schemaVersion: "v2.0",
      matchKeywords: [],
      outputFormats: ["md"],
      compatibility: { contentParams: [], outline: [], migratedFromLegacy: false },
    },
    parameters: [
      {
        uiKey: "p-date",
        id: "date",
        label: "日期",
        required: true,
        inputType: "date",
        multi: false,
        options: [],
        source: "",
      },
      {
        uiKey: "p-devices",
        id: "devices",
        label: "设备列表",
        required: true,
        inputType: "dynamic",
        multi: true,
        options: [],
        source: "devices",
      },
    ],
    sections: [
      {
        uiKey: "s1",
        title: "概览 {date}",
        description: "",
        foreachEnabled: false,
        foreachParam: "",
        foreachAlias: "item",
        kind: "content",
        outline: {
          document: "分析 {@focus_metric} 在 {date} 的变化",
          blocks: [
            {
              uiKey: "b-1",
              id: "focus_metric",
              type: "indicator",
              hint: "指标",
              defaultValue: "温度",
              options: [],
              source: "",
              paramId: "",
              multi: false,
              widget: "",
            },
          ],
        },
        content: {
          datasets: [],
          presentation: { type: "text", template: "日期 {date}" },
        },
        children: [],
      },
      {
        uiKey: "s2",
        title: "设备 {$device}",
        description: "",
        foreachEnabled: true,
        foreachParam: "devices",
        foreachAlias: "device",
        kind: "content",
        outline: {
          document: "检查 {$device} 的 {@inspection_scope}",
          blocks: [
            {
              uiKey: "b-2",
              id: "inspection_scope",
              type: "scope",
              hint: "检查范围",
              defaultValue: "连接状态",
              options: [],
              source: "",
              paramId: "",
              multi: false,
              widget: "",
            },
          ],
        },
        content: {
          datasets: [],
          presentation: { type: "simple_table", datasetId: "" },
        },
        children: [],
      },
    ],
    previewSamples: {
      date: "2026-03-19",
      devices: ["A站设备", "B站设备"],
    },
  };
}

describe("template workbench preview", () => {
  it("renders outline blueprint preview with block defaults and foreach expansion", () => {
    const preview = buildBlueprintPreview(createState());

    expect(preview.sections).toHaveLength(3);
    expect(preview.sections[0].title).toBe("概览 2026-03-19");
    expect(preview.sections[0].content).toBe("分析 温度 在 2026-03-19 的变化");
    expect(preview.sections[1].content).toBe("检查 A站设备 的 连接状态");
    expect(preview.sections[2].content).toBe("检查 B站设备 的 连接状态");
  });

  it("renders placeholders and expands foreach sections from preview samples", () => {
    const preview = buildStructuralPreview(createState());

    expect(preview.sections).toHaveLength(3);
    expect(preview.sections[0].title).toBe("概览 2026-03-19");
    expect(preview.sections[0].content).toContain("日期 2026-03-19");
    expect(preview.sections[1].title).toBe("设备 A站设备");
    expect(preview.sections[1].content).toContain("表格预览");
    expect(preview.sections[2].title).toBe("设备 B站设备");
  });
});
