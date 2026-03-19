import { describe, expect, it } from "vitest";

import type { TemplateWorkbenchState } from "./state";
import { buildStructuralPreview } from "./preview";

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
