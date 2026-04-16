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

    fireEvent.click(screen.getByRole("button", { name: "确认参数并生成诉求" }));

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
              category: "资产统计",
              description: "统计资产规模与分布",
              report_type: "special",
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
              requirement_instance: {
                requirement: "分析 {@focus_metric} 的变化",
                rendered_requirement: "分析 温度 的变化",
                segments: [
                  { kind: "text", text: "分析 " },
                  { kind: "item", item_id: "focus_metric", item_type: "indicator", value: "温度" },
                  { kind: "text", text: " 的变化" },
                ],
                items: [{ id: "focus_metric", type: "indicator", hint: "指标", value: "温度" }],
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
    expect(screen.getByRole("button", { name: "编辑要素 focus_metric" })).toBeInTheDocument();
    expect(screen.getByText("二级小节：系统生成本节内容")).toBeInTheDocument();
    expect(screen.queryByText("新增同级")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "新增同级章节 node-1" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "折叠章节 node-1" }));
    expect(screen.queryByText("二级小节：系统生成本节内容")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "展开章节 node-1" }));

    fireEvent.click(screen.getByRole("button", { name: "编辑要素 focus_metric" }));
    const inlineBlockInput = screen.getByLabelText("编辑要素值 focus_metric");
    fireEvent.change(inlineBlockInput, { target: { value: "湿度" } });
    fireEvent.keyDown(inlineBlockInput, { key: "Enter" });

    fireEvent.click(screen.getByRole("button", { name: "保存诉求" }));
    fireEvent.click(screen.getByRole("button", { name: "确认生成" }));
    fireEvent.click(screen.getByRole("button", { name: "返回改参数" }));

    expect(screen.getByText("foreach 已展开")).toBeInTheDocument();
    expect(onSubmitOutline).toHaveBeenCalledWith(
      "edit_outline",
      expect.arrayContaining([
        expect.objectContaining({
          requirement_instance: expect.objectContaining({
            rendered_requirement: "分析 湿度 的变化",
            items: expect.arrayContaining([expect.objectContaining({ id: "focus_metric", value: "湿度" })]),
          }),
        }),
      ]),
    );
    expect(onSubmitOutline).toHaveBeenCalledWith(
      "confirm_outline_generation",
      expect.arrayContaining([
        expect.objectContaining({
          requirement_instance: expect.objectContaining({
            rendered_requirement: "分析 湿度 的变化",
            items: expect.arrayContaining([expect.objectContaining({ id: "focus_metric", value: "湿度" })]),
          }),
        }),
      ]),
    );
    expect(onCommand).toHaveBeenCalledWith("edit_param");
  });

  it("uses select editor for enum-like blocks and shows param_ref as editable chip with tooltip", () => {
    render(
      <ChatActionPanel
        action={{
          type: "review_outline",
          template_id: "tpl-2",
          template_name: "指标分析报告",
          warnings: [],
          params_snapshot: [{ id: "scene", label: "场景", value: "总部" }],
          outline: [
            {
              node_id: "node-3",
              title: "指标分析",
              description: "",
              level: 1,
              display_text: "分析 温度 在 总部 的变化",
              node_kind: "structured_leaf",
              ai_generated: false,
              children: [],
              requirement_instance: {
                requirement: "分析 {@metric} 在 {@target_scene} 的变化",
                rendered_requirement: "分析 温度 在 总部 的变化",
                segments: [
                  { kind: "text", text: "分析 " },
                  { kind: "item", item_id: "metric", item_type: "indicator", value: "温度" },
                  { kind: "text", text: " 在 " },
                  { kind: "item", item_id: "target_scene", item_type: "param_ref", value: "总部" },
                  { kind: "text", text: " 的变化" },
                ],
                items: [
                  { id: "metric", type: "indicator", hint: "指标", value: "温度", options: ["温度", "湿度"] },
                  { id: "target_scene", type: "param_ref", hint: "场景", value: "总部", param_id: "scene" },
                ],
              },
            },
          ],
        }}
        onSubmitParam={vi.fn()}
        onSubmitOutline={vi.fn()}
        onSelectTemplate={vi.fn()}
        onCommand={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "编辑要素 metric" }));
    expect(screen.getByLabelText("编辑要素值 metric")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "编辑要素 target_scene" })).toHaveAttribute("title", "参数：场景（scene）");
    expect(screen.queryByText("来自参数 scene")).not.toBeInTheDocument();
  });

  it("keeps structured outline when full sentence edit only changes block values", () => {
    const onSubmitOutline = vi.fn();
    render(
      <ChatActionPanel
        action={{
          type: "review_outline",
          template_id: "tpl-3",
          template_name: "指标分析报告",
          warnings: [],
          params_snapshot: [],
          outline: [
            {
              node_id: "node-4",
              title: "指标分析",
              description: "",
              level: 1,
              display_text: "分析 温度 的变化",
              node_kind: "structured_leaf",
              ai_generated: false,
              children: [],
              requirement_instance: {
                requirement: "分析 {@metric} 的变化",
                rendered_requirement: "分析 温度 的变化",
                segments: [
                  { kind: "text", text: "分析 " },
                  { kind: "item", item_id: "metric", item_type: "indicator", value: "温度" },
                  { kind: "text", text: " 的变化" },
                ],
                items: [{ id: "metric", type: "indicator", hint: "指标", value: "温度" }],
              },
            },
          ],
        }}
        onSubmitParam={vi.fn()}
        onSubmitOutline={onSubmitOutline}
        onSelectTemplate={vi.fn()}
        onCommand={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByText("分析"));
    const input = screen.getByLabelText("编辑章节 node-4");
    fireEvent.change(input, { target: { value: "分析 湿度 的变化" } });
    fireEvent.keyDown(input, { key: "Enter" });
    fireEvent.click(screen.getByRole("button", { name: "保存诉求" }));

    expect(onSubmitOutline).toHaveBeenCalledWith(
      "edit_outline",
      expect.arrayContaining([
        expect.objectContaining({
          requirement_instance: expect.objectContaining({
            rendered_requirement: "分析 湿度 的变化",
            items: expect.arrayContaining([expect.objectContaining({ id: "metric", value: "湿度" })]),
          }),
        }),
      ]),
    );
  });

  it("degrades to freeform when full sentence edit changes static text", () => {
    const onSubmitOutline = vi.fn();
    render(
      <ChatActionPanel
        action={{
          type: "review_outline",
          template_id: "tpl-4",
          template_name: "指标分析报告",
          warnings: [],
          params_snapshot: [],
          outline: [
            {
              node_id: "node-5",
              title: "指标分析",
              description: "",
              level: 1,
              display_text: "分析 温度 的变化",
              node_kind: "structured_leaf",
              ai_generated: false,
              children: [],
              requirement_instance: {
                requirement: "分析 {@metric} 的变化",
                rendered_requirement: "分析 温度 的变化",
                segments: [
                  { kind: "text", text: "分析 " },
                  { kind: "item", item_id: "metric", item_type: "indicator", value: "温度" },
                  { kind: "text", text: " 的变化" },
                ],
                items: [{ id: "metric", type: "indicator", hint: "指标", value: "温度" }],
              },
            },
          ],
        }}
        onSubmitParam={vi.fn()}
        onSubmitOutline={onSubmitOutline}
        onSelectTemplate={vi.fn()}
        onCommand={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByText("分析"));
    const input = screen.getByLabelText("编辑章节 node-5");
    fireEvent.change(input, { target: { value: "重点分析 湿度 的变化" } });
    fireEvent.keyDown(input, { key: "Enter" });
    fireEvent.click(screen.getByRole("button", { name: "保存诉求" }));

    expect(onSubmitOutline).toHaveBeenCalledWith(
      "edit_outline",
      expect.arrayContaining([
        expect.objectContaining({
          node_id: "node-5",
          title: "重点分析 湿度 的变化",
          description: "",
          outline_mode: "freeform",
        }),
      ]),
    );
    const degradedNode = onSubmitOutline.mock.calls.at(-1)?.[1]?.[0];
    expect(degradedNode).not.toHaveProperty("requirement_instance");
  });

  it("commits pending sentence edits before confirm generation", () => {
    const onSubmitOutline = vi.fn();
    render(
      <ChatActionPanel
        action={{
          type: "review_outline",
          template_id: "tpl-5",
          template_name: "指标分析报告",
          warnings: [],
          params_snapshot: [],
          outline: [
            {
              node_id: "node-6",
              title: "指标分析",
              description: "",
              level: 1,
              display_text: "分析 温度 的变化",
              node_kind: "structured_leaf",
              ai_generated: false,
              children: [],
              requirement_instance: {
                requirement: "分析 {@metric} 的变化",
                rendered_requirement: "分析 温度 的变化",
                segments: [
                  { kind: "text", text: "分析 " },
                  { kind: "item", item_id: "metric", item_type: "indicator", value: "温度" },
                  { kind: "text", text: " 的变化" },
                ],
                items: [{ id: "metric", type: "indicator", hint: "指标", value: "温度" }],
              },
            },
          ],
        }}
        onSubmitParam={vi.fn()}
        onSubmitOutline={onSubmitOutline}
        onSelectTemplate={vi.fn()}
        onCommand={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByText("分析"));
    const input = screen.getByLabelText("编辑章节 node-6");
    fireEvent.change(input, { target: { value: "重点分析 湿度 的变化" } });
    fireEvent.click(screen.getByRole("button", { name: "确认生成" }));

    expect(onSubmitOutline).toHaveBeenCalledWith(
      "confirm_outline_generation",
      expect.arrayContaining([
        expect.objectContaining({
          node_id: "node-6",
          title: "重点分析 湿度 的变化",
          description: "",
          outline_mode: "freeform",
        }),
      ]),
    );
    const degradedNode = onSubmitOutline.mock.calls.at(-1)?.[1]?.[0];
    expect(degradedNode).not.toHaveProperty("requirement_instance");
  });

  it("commits pending block edits before confirm generation", () => {
    const onSubmitOutline = vi.fn();
    render(
      <ChatActionPanel
        action={{
          type: "review_outline",
          template_id: "tpl-6",
          template_name: "指标分析报告",
          warnings: [],
          params_snapshot: [],
          outline: [
            {
              node_id: "node-7",
              title: "指标分析",
              description: "",
              level: 1,
              display_text: "分析 总部 的变化",
              node_kind: "structured_leaf",
              ai_generated: false,
              children: [],
              requirement_instance: {
                requirement: "分析 {@target_scene} 的变化",
                rendered_requirement: "分析 总部 的变化",
                segments: [
                  { kind: "text", text: "分析 " },
                  { kind: "item", item_id: "target_scene", item_type: "param_ref", value: "总部" },
                  { kind: "text", text: " 的变化" },
                ],
                items: [{ id: "target_scene", type: "param_ref", hint: "场景", value: "总部", param_id: "scene" }],
              },
            },
          ],
        }}
        onSubmitParam={vi.fn()}
        onSubmitOutline={onSubmitOutline}
        onSelectTemplate={vi.fn()}
        onCommand={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "编辑要素 target_scene" }));
    const input = screen.getByLabelText("编辑要素值 target_scene");
    fireEvent.change(input, { target: { value: "分部" } });
    fireEvent.click(screen.getByRole("button", { name: "确认生成" }));

    expect(onSubmitOutline).toHaveBeenCalledWith(
      "confirm_outline_generation",
      expect.arrayContaining([
        expect.objectContaining({
          requirement_instance: expect.objectContaining({
            rendered_requirement: "分析 分部 的变化",
            items: expect.arrayContaining([expect.objectContaining({ id: "target_scene", value: "分部" })]),
          }),
        }),
      ]),
    );
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

