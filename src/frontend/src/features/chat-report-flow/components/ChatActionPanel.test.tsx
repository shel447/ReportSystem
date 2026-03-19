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

  it("renders review_outline and submits edited tree", () => {
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
              children: [],
            },
          ],
        }}
        onSubmitParam={vi.fn()}
        onSubmitOutline={onSubmitOutline}
        onSelectTemplate={vi.fn()}
        onCommand={onCommand}
      />,
    );

    fireEvent.change(screen.getByLabelText("章节标题 node-1"), { target: { value: "总部总览" } });
    fireEvent.click(screen.getByRole("button", { name: "保存大纲" }));
    fireEvent.click(screen.getByRole("button", { name: "确认生成" }));
    fireEvent.click(screen.getByRole("button", { name: "返回改参数" }));

    expect(screen.getByText("foreach 已展开")).toBeInTheDocument();
    expect(onSubmitOutline).toHaveBeenCalledWith(
      "edit_outline",
      expect.arrayContaining([expect.objectContaining({ title: "总部总览" })]),
    );
    expect(onSubmitOutline).toHaveBeenCalledWith(
      "confirm_outline_generation",
      expect.arrayContaining([expect.objectContaining({ title: "总部总览" })]),
    );
    expect(onCommand).toHaveBeenCalledWith("edit_param");
  });
});
