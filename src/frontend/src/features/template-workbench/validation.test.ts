import { describe, expect, it } from "vitest";

import { createEmptyWorkbenchState, type TemplateWorkbenchState } from "./state";
import { validateWorkbench } from "./validation";

function buildState(): TemplateWorkbenchState {
  const state = createEmptyWorkbenchState();
  state.meta.name = "设备巡检报告";
  state.parameters = [
    {
      uiKey: "param-1",
      id: "date",
      label: "日期",
      required: true,
      inputType: "date",
      multi: false,
      options: [],
      source: "",
    },
    {
      uiKey: "param-2",
      id: "devices",
      label: "设备列表",
      required: true,
      inputType: "dynamic",
      multi: true,
      options: [],
      source: "devices",
    },
  ];
  state.sections = [
    {
      uiKey: "section-1",
      title: "概览 {date}",
      description: "",
      foreachEnabled: false,
      foreachParam: "",
      foreachAlias: "item",
      kind: "content",
      content: {
        datasets: [],
        presentation: {
          type: "text",
          template: "巡检日期 {date}",
          anchor: "{$value}",
          datasetId: "",
          chartType: "bar",
          sections: [],
        },
      },
      children: [],
    },
  ];
  return state;
}

describe("template workbench validation", () => {
  it("reports duplicate parameter ids and missing dynamic source", () => {
    const state = buildState();
    state.parameters[1].id = "date";
    state.parameters[1].source = "";

    const errors = validateWorkbench(state);

    expect(errors).toContain("参数标识不能重复：date");
    expect(errors).toContain("动态参数必须配置来源：设备列表");
  });

  it("reports invalid foreach and dataset dependency cycles", () => {
    const state = buildState();
    state.sections[0].foreachEnabled = true;
    state.sections[0].foreachParam = "date";
    state.sections[0].content = {
      datasets: [
        {
          uiKey: "dataset-1",
          id: "summary",
          dependsOn: ["trend"],
          source: {
            kind: "sql",
            query: "SELECT 1",
            description: "",
            keyCol: "",
            valueCol: "",
            prompt: "",
            contextRefs: [],
            contextQueries: [],
            knowledgeQueryTemplate: "",
            knowledgeParams: { subject: "", symptoms: "", objective: "" },
          },
        },
        {
          uiKey: "dataset-2",
          id: "trend",
          dependsOn: ["summary"],
          source: {
            kind: "sql",
            query: "SELECT 2",
            description: "",
            keyCol: "",
            valueCol: "",
            prompt: "",
            contextRefs: [],
            contextQueries: [],
            knowledgeQueryTemplate: "",
            knowledgeParams: { subject: "", symptoms: "", objective: "" },
          },
        },
      ],
      presentation: {
        type: "composite_table",
        template: "",
        anchor: "{$value}",
        datasetId: "",
        chartType: "bar",
        columns: 2,
        sections: [],
      },
    };

    const errors = validateWorkbench(state);

    expect(errors).toContain("foreach 只能绑定多值参数：概览 {date}");
    expect(errors).toContain("数据集依赖存在环：概览 {date}");
    expect(errors).toContain("复合表至少需要一个分区：概览 {date}");
  });

  it("reports invalid outline block bindings and param refs", () => {
    const state = buildState();
    state.sections[0].outline = {
      document: "分析 {@focus_metric}",
      blocks: [
        {
          uiKey: "block-1",
          id: "focus_metric",
          type: "param_ref",
          hint: "指标来源",
          defaultValue: "",
          options: [],
          source: "",
          paramId: "missing_param",
          multi: false,
          widget: "",
        },
      ],
    };
    state.sections[0].content = {
      datasets: [],
      presentation: {
        type: "text",
        template: "展示 {@missing_block}",
        anchor: "{$value}",
        datasetId: "",
        chartType: "bar",
        sections: [],
      },
    };

    const errors = validateWorkbench(state);

    expect(errors).toContain("诉求要素 param_ref 必须绑定已有参数：概览 {date} / focus_metric");
    expect(errors).toContain("执行链路引用了不存在的诉求要素：概览 {date} / missing_block");
  });
});
