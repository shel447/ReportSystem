import { fireEvent, render, screen } from "@testing-library/react";

import { ChatActionPanel } from "./ChatActionPanel";

describe("ChatActionPanel", () => {
  it("renders ask_param with matched template and date widget", () => {
    render(
      <ChatActionPanel
        action={{
          type: "ask_param",
          template_name: "设备巡检报告",
          param: {
            id: "report_date",
            label: "报告日期",
            input_type: "date",
            multi: false,
            options: [],
          },
          widget: { kind: "date" },
          selected_values: [],
          progress: { collected: 0, required: 2 },
        }}
        onSubmitParam={vi.fn()}
        onSubmitOutline={vi.fn()}
        onSelectTemplate={vi.fn()}
        onCommand={vi.fn()}
      />,
    );

    expect(screen.getByText("已匹配模板：")).toBeInTheDocument();
    expect(screen.getByText("设备巡检报告")).toBeInTheDocument();
    expect(screen.getByLabelText("报告日期")).toHaveAttribute("type", "date");
  });

  it("renders review_params and triggers confirm command", () => {
    const onCommand = vi.fn();
    render(
      <ChatActionPanel
        action={{
          type: "review_params",
          template_name: "设备巡检报告",
          params: [
            { id: "report_date", label: "报告日期", value: "2026-03-18", required: true },
            { id: "devices", label: "设备", value: ["D00001", "D00002"], required: true },
          ],
          missing_required: [],
        }}
        onSubmitParam={vi.fn()}
        onSubmitOutline={vi.fn()}
        onSelectTemplate={vi.fn()}
        onCommand={onCommand}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "确认参数并生成大纲" }));

    expect(screen.getByText("D00001、D00002")).toBeInTheDocument();
    expect(onCommand).toHaveBeenCalledWith("prepare_outline_review");
  });

  it("renders candidate selector and submits selected template", () => {
    const onSelectTemplate = vi.fn();
    render(
      <ChatActionPanel
        action={{
          type: "show_template_candidates",
          selected_template_id: "tpl-1",
          candidates: [
            {
              template_id: "tpl-1",
              template_name: "资产统计报告",
              scenario: "资产运营",
              description: "统计资产规模与分布",
              report_type: "special",
              template_type: "资产统计",
              score_label: "高相关",
              match_reasons: ["关键词命中：资产统计"],
            },
          ],
        }}
        onSubmitParam={vi.fn()}
        onSubmitOutline={vi.fn()}
        onSelectTemplate={onSelectTemplate}
        onCommand={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "使用此模板" }));

    expect(screen.getByText("关键词命中：资产统计")).toBeInTheDocument();
    expect(onSelectTemplate).toHaveBeenCalledWith("tpl-1");
  });

  it("renders review_outline as a content tree with inline editing and AI badge", () => {
    const onSubmitOutline = vi.fn();
    const onCommand = vi.fn();
    render(
      <ChatActionPanel
        action={{
          type: "review_outline",
          template_id: "tpl-1",
          template_name: "设备巡检报告",
          warnings: ["foreach 已展开"],
          params_snapshot: [{ id: "scene", label: "场景", value: "总部" }],
          outline: [
            {
              node_id: "node-1",
              title: "总部概览",
              description: "巡检范围",
              level: 1,
              display_text: "分析 温度 的变化",
              node_kind: "group",
              ai_generated: false,
              outline_instance: {
                document_template: "分析 {@focus_metric} 的变化",
                rendered_document: "分析 温度 的变化",
                segments: [
                  { kind: "text", text: "分析 " },
                  { kind: "block", block_id: "focus_metric", block_type: "indicator", value: "温度" },
                  { kind: "text", text: " 的变化" },
                ],
                blocks: [{ id: "focus_metric", type: "indicator", hint: "指标", value: "温度" }],
              },
              children: [
                {
                  node_id: "node-2",
                  title: "二级小节",
                  description: "",
                  level: 2,
                  display_text: "二级小节：系统生成本节内容",
                  node_kind: "freeform_leaf",
                  ai_generated: true,
                  children: [],
                },
              ],
            },
          ],
        }}
        onSubmitParam={vi.fn()}
        onSubmitOutline={onSubmitOutline}
        onSelectTemplate={vi.fn()}
        onCommand={onCommand}
      />,
    );

    expect(screen.queryByText("章节标题")).not.toBeInTheDocument();
    expect(screen.queryByText("章节说明")).not.toBeInTheDocument();
    expect(screen.getByText("AI")).toBeInTheDocument();
    expect(screen.getByText("分析")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "编辑区块 focus_metric" })).toBeInTheDocument();
    expect(screen.getByText("二级小节：系统生成本节内容")).toBeInTheDocument();
    expect(screen.queryByText("新增同级")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "新增同级章节 node-1" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "折叠章节 node-1" }));
    expect(screen.queryByText("二级小节：系统生成本节内容")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "展开章节 node-1" }));

    fireEvent.click(screen.getByRole("button", { name: "编辑区块 focus_metric" }));
    const inlineBlockInput = screen.getByLabelText("编辑区块值 focus_metric");
    fireEvent.change(inlineBlockInput, { target: { value: "湿度" } });
    fireEvent.keyDown(inlineBlockInput, { key: "Enter" });

    fireEvent.click(screen.getByRole("button", { name: "保存大纲" }));
    fireEvent.click(screen.getByRole("button", { name: "确认生成" }));
    fireEvent.click(screen.getByRole("button", { name: "返回改参数" }));

    expect(screen.getByText("foreach 已展开")).toBeInTheDocument();
    expect(onSubmitOutline).toHaveBeenCalledWith(
      "edit_outline",
      expect.arrayContaining([
        expect.objectContaining({
          outline_instance: expect.objectContaining({
            rendered_document: "分析 湿度 的变化",
            blocks: expect.arrayContaining([expect.objectContaining({ id: "focus_metric", value: "湿度" })]),
          }),
        }),
      ]),
    );
    expect(onSubmitOutline).toHaveBeenCalledWith(
      "confirm_outline_generation",
      expect.arrayContaining([
        expect.objectContaining({
          outline_instance: expect.objectContaining({
            rendered_document: "分析 湿度 的变化",
            blocks: expect.arrayContaining([expect.objectContaining({ id: "focus_metric", value: "湿度" })]),
          }),
        }),
      ]),
    );
    expect(onCommand).toHaveBeenCalledWith("edit_param");
  });

  it("renders confirm_task_switch and triggers confirm or cancel commands", () => {
    const onCommand = vi.fn();
    render(
      <ChatActionPanel
        action={{
          type: "confirm_task_switch",
          from_capability: "report_generation",
          to_capability: "smart_query",
          reason: "检测到你正在发起智能问数，这会结束当前报告制作流程。",
        }}
        onSubmitParam={vi.fn()}
        onSubmitOutline={vi.fn()}
        onSelectTemplate={vi.fn()}
        onCommand={onCommand}
      />,
    );

    expect(screen.getByText("任务切换确认")).toBeInTheDocument();
    expect(screen.getByText("制作报告")).toBeInTheDocument();
    expect(screen.getByText("智能问数")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "继续切换" }));
    fireEvent.click(screen.getByRole("button", { name: "留在当前任务" }));

    expect(onCommand).toHaveBeenCalledWith("confirm_task_switch");
    expect(onCommand).toHaveBeenCalledWith("cancel_task_switch");
  });
});
