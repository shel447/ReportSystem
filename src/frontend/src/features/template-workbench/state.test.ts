import { describe, expect, it } from "vitest";

import type { TemplateDetail } from "../../entities/templates/types";
import { createEmptyWorkbenchState, toTemplatePayload, toWorkbenchState } from "./state";

describe("template workbench state", () => {
  it("builds a structured workbench state from template detail", () => {
    const template: TemplateDetail = {
      template_id: "tpl-1",
      name: "设备巡检报告",
      description: "巡检模板",
      report_type: "daily",
      scenario: "集团",
      type: "巡检",
      scene: "总部",
      match_keywords: ["巡检"],
      content_params: [],
      parameters: [
        { id: "date", label: "日期", input_type: "date", required: true },
        { id: "devices", label: "设备列表", input_type: "dynamic", required: true, multi: true, source: "devices" },
      ],
      outline: [],
      sections: [
        {
          title: "概览 {date}",
          outline: {
            requirement: "分析 {@focus_metric} 在 {date} 的变化",
            items: [
              { id: "focus_metric", type: "indicator", hint: "关注指标", default: "振动" },
            ],
          },
          content: {
            datasets: [{ id: "summary", source: { kind: "sql", query: "SELECT 1 AS value" } }],
            presentation: { type: "text", template: "巡检日期 {date}" },
          },
        },
      ],
      schema_version: "v2.0",
      output_formats: ["md"],
      version: "1.0",
    };

    const state = toWorkbenchState(template);

    expect(state.meta.name).toBe("设备巡检报告");
    expect(state.parameters).toHaveLength(2);
    expect(state.parameters[0].label).toBe("日期");
    expect(state.parameters[1].multi).toBe(true);
    expect(state.sections).toHaveLength(1);
    expect(state.sections[0].outline?.requirement).toBe("分析 {@focus_metric} 在 {date} 的变化");
    expect(state.sections[0].outline?.items[0].id).toBe("focus_metric");
    expect(state.sections[0].content?.datasets[0].source.kind).toBe("sql");
    expect(state.previewSamples).toEqual({});
  });

  it("serializes workbench state to template payload without preview-only fields", () => {
    const state = createEmptyWorkbenchState();
    state.meta.name = "资产统计报告";
    state.meta.type = "资产统计";
    state.meta.scene = "省公司";
    state.parameters.push({
      uiKey: "param-1",
      id: "date",
      label: "日期",
      required: true,
      inputType: "date",
      multi: false,
      options: [],
      source: "",
    });
    state.previewSamples.date = "2026-03-19";
    state.sections.push({
      uiKey: "section-1",
      title: "概览 {date}",
      description: "",
      foreachEnabled: false,
      foreachParam: "",
      foreachAlias: "item",
      kind: "content",
      outline: {
        requirement: "分析 {@focus_metric} 在 {date} 的变化",
        items: [
          {
            uiKey: "item-1",
            id: "focus_metric",
            type: "indicator",
            hint: "关注指标",
            defaultValue: "振动",
            options: ["振动", "温度"],
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
    });

    const payload = toTemplatePayload(state);

    expect(payload.name).toBe("资产统计报告");
    expect(payload.type).toBe("资产统计");
    expect(payload.parameters[0]).toEqual({
      id: "date",
      label: "日期",
      required: true,
      input_type: "date",
    });
    expect(payload.sections[0]).toEqual({
      title: "概览 {date}",
      outline: {
        requirement: "分析 {@focus_metric} 在 {date} 的变化",
        items: [
          {
            id: "focus_metric",
            type: "indicator",
            hint: "关注指标",
            default: "振动",
            options: ["振动", "温度"],
          },
        ],
      },
      content: {
        presentation: { type: "text", template: "日期 {date}" },
      },
    });
    expect(payload).not.toHaveProperty("previewSamples");
  });
});
