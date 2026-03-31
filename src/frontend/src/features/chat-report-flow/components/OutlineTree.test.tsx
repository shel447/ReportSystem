import { fireEvent, render, screen } from "@testing-library/react";

import type { OutlineNode } from "../../../entities/chat/types";
import { OutlineTree } from "./OutlineTree";

const sampleOutline: OutlineNode[] = [
  {
    node_id: "node-1",
    title: "总部概览",
    description: "巡检范围",
    level: 1,
    display_text: "总部概览：巡检范围",
    node_kind: "group",
    ai_generated: false,
    children: [
      {
        node_id: "node-2",
        title: "执行摘要",
        description: "系统生成本节内容",
        level: 2,
        display_text: "执行摘要：系统生成本节内容",
        node_kind: "freeform_leaf",
        ai_generated: true,
        children: [],
      },
    ],
  },
];

describe("OutlineTree", () => {
  it("renders readonly outline tree with ai badge and collapse behavior", () => {
    render(<OutlineTree nodes={sampleOutline} mode="readonly" />);

    expect(screen.getByRole("tree")).toBeInTheDocument();
    expect(screen.getByText("总部概览：巡检范围")).toBeInTheDocument();
    expect(screen.getByText("执行摘要：系统生成本节内容")).toBeInTheDocument();
    expect(screen.getByText("AI")).toBeInTheDocument();
    expect(screen.queryByLabelText("编辑章节 node-1")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "新增同级章节 node-1" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "折叠章节 node-1" }));
    expect(screen.queryByText("执行摘要：系统生成本节内容")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "展开章节 node-1" }));
    expect(screen.getByText("执行摘要：系统生成本节内容")).toBeInTheDocument();
  });

  it("renders readonly structured blueprint nodes with readonly block chips and tooltip", () => {
    render(
      <OutlineTree
        mode="readonly"
        nodes={[
          {
            node_id: "node-readonly-structured",
            title: "范围分析",
            description: "",
            level: 1,
            display_text: "分析 总部 的巡检情况",
            node_kind: "structured_leaf",
            ai_generated: false,
            children: [],
            outline_instance: {
              document_template: "分析 {@target_scene} 的巡检情况",
              rendered_document: "分析 总部 的巡检情况",
              segments: [
                { kind: "text", text: "分析 " },
                { kind: "block", block_id: "target_scene", block_type: "param_ref", value: "总部" },
                { kind: "text", text: " 的巡检情况" },
              ],
              blocks: [
                { id: "target_scene", type: "param_ref", hint: "场景", value: "总部", param_id: "scene" },
              ],
            },
          },
        ]}
      />,
    );

    expect(screen.getByText("分析")).toBeInTheDocument();
    const chip = screen.getByText("总部");
    expect(chip).toHaveClass("outline-tree__block-chip", "outline-tree__block-chip--readonly");
    expect(chip).toHaveAttribute("title", "参数：场景（scene）");
    expect(screen.queryByText("分析 总部 的巡检情况")).not.toBeInTheDocument();
  });

  it("renders editable blueprint nodes with inline block chips", () => {
    render(
      <OutlineTree
        mode="editable"
        nodes={[
          {
            ...sampleOutline[0],
            children: [],
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
          },
        ]}
        collapsedNodeIds={new Set()}
        editingNodeId={null}
        selectedNodeId={null}
        draftDisplayText=""
        disabled={false}
        onToggleCollapse={() => undefined}
        onSelectNode={() => undefined}
        onBeginEdit={() => undefined}
        onDraftChange={() => undefined}
        onCommitEdit={() => undefined}
        onCancelEdit={() => undefined}
        onAddSibling={() => undefined}
        onAddChild={() => undefined}
        onMoveUp={() => undefined}
        onMoveDown={() => undefined}
        onPromote={() => undefined}
        onDemote={() => undefined}
        onDelete={() => undefined}
        onBeginBlockEdit={() => undefined}
        onBlockDraftChange={() => undefined}
        onCommitBlockEdit={() => undefined}
        onCancelBlockEdit={() => undefined}
        editingBlockKey={null}
        blockDraftValue=""
      />,
    );

    expect(screen.getByText("分析")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "编辑区块 focus_metric" })).toBeInTheDocument();
    expect(screen.getByText("温度")).toBeInTheDocument();
    expect(screen.queryByLabelText("编辑章节 node-1")).not.toBeInTheDocument();
  });

  it("renders time_range blocks with date range editors", () => {
    render(
      <OutlineTree
        mode="editable"
        nodes={[
          {
            node_id: "node-time",
            title: "时间分析",
            description: "",
            level: 1,
            display_text: "分析 2026-03-01 至 2026-03-07 的变化",
            node_kind: "structured_leaf",
            ai_generated: false,
            children: [],
            outline_instance: {
              document_template: "分析 {@period} 的变化",
              rendered_document: "分析 2026-03-01 至 2026-03-07 的变化",
              segments: [
                { kind: "text", text: "分析 " },
                { kind: "block", block_id: "period", block_type: "time_range", value: "2026-03-01 至 2026-03-07" },
                { kind: "text", text: " 的变化" },
              ],
              blocks: [
                { id: "period", type: "time_range", hint: "时间范围", value: "2026-03-01 至 2026-03-07", widget: "date_range" },
              ],
            },
          },
        ]}
        collapsedNodeIds={new Set()}
        editingNodeId={null}
        selectedNodeId={null}
        draftDisplayText=""
        disabled={false}
        onToggleCollapse={() => undefined}
        onSelectNode={() => undefined}
        onBeginEdit={() => undefined}
        onDraftChange={() => undefined}
        onCommitEdit={() => undefined}
        onCancelEdit={() => undefined}
        onAddSibling={() => undefined}
        onAddChild={() => undefined}
        onMoveUp={() => undefined}
        onMoveDown={() => undefined}
        onPromote={() => undefined}
        onDemote={() => undefined}
        onDelete={() => undefined}
        onBeginBlockEdit={() => undefined}
        onBlockDraftChange={() => undefined}
        onCommitBlockEdit={() => undefined}
        onCancelBlockEdit={() => undefined}
        editingBlockKey={"node-time:period"}
        blockDraftValue="2026-03-01 至 2026-03-07"
      />,
    );

    expect(screen.getByLabelText("开始日期 period")).toHaveAttribute("type", "date");
    expect(screen.getByLabelText("结束日期 period")).toHaveAttribute("type", "date");
    expect(screen.getByLabelText("开始日期 period")).toHaveClass("outline-tree__block-date--chip-editing");
    expect(screen.getByLabelText("结束日期 period")).toHaveClass("outline-tree__block-date--chip-editing");
    expect(screen.queryByLabelText("编辑区块值 period")).not.toBeInTheDocument();
  });

  it("renders enum-like block editors with chip-aligned selects", () => {
    render(
      <OutlineTree
        mode="editable"
        nodes={[
          {
            node_id: "node-select",
            title: "指标分析",
            description: "",
            level: 1,
            display_text: "分析 温度 的变化",
            node_kind: "structured_leaf",
            ai_generated: false,
            children: [],
            outline_instance: {
              document_template: "分析 {@focus_metric} 的变化",
              rendered_document: "分析 温度 的变化",
              segments: [
                { kind: "text", text: "分析 " },
                { kind: "block", block_id: "focus_metric", block_type: "indicator", value: "温度" },
                { kind: "text", text: " 的变化" },
              ],
              blocks: [
                { id: "focus_metric", type: "indicator", hint: "指标", value: "温度", options: ["温度", "湿度"] },
              ],
            },
          },
        ]}
        collapsedNodeIds={new Set()}
        editingNodeId={null}
        selectedNodeId={null}
        draftDisplayText=""
        disabled={false}
        onToggleCollapse={() => undefined}
        onSelectNode={() => undefined}
        onBeginEdit={() => undefined}
        onDraftChange={() => undefined}
        onCommitEdit={() => undefined}
        onCancelEdit={() => undefined}
        onAddSibling={() => undefined}
        onAddChild={() => undefined}
        onMoveUp={() => undefined}
        onMoveDown={() => undefined}
        onPromote={() => undefined}
        onDemote={() => undefined}
        onDelete={() => undefined}
        onBeginBlockEdit={() => undefined}
        onBlockDraftChange={() => undefined}
        onCommitBlockEdit={() => undefined}
        onCancelBlockEdit={() => undefined}
        editingBlockKey={"node-select:focus_metric"}
        blockDraftValue="温度"
      />,
    );

    expect(screen.getByLabelText("编辑区块值 focus_metric")).toHaveClass(
      "outline-tree__block-select--chip-editing",
    );
    expect(screen.getByText("分析")).toBeInTheDocument();
    expect(screen.getByText("的变化")).toBeInTheDocument();
  });

  it("renders param_ref blocks as editable chips with hover tooltip", () => {
    render(
      <OutlineTree
        mode="editable"
        nodes={[
          {
            node_id: "node-param",
            title: "范围分析",
            description: "",
            level: 1,
            display_text: "分析 总部 的巡检情况",
            node_kind: "structured_leaf",
            ai_generated: false,
            children: [],
            outline_instance: {
              document_template: "分析 {@target_scene} 的巡检情况",
              rendered_document: "分析 总部 的巡检情况",
              segments: [
                { kind: "text", text: "分析 " },
                { kind: "block", block_id: "target_scene", block_type: "param_ref", value: "总部" },
                { kind: "text", text: " 的巡检情况" },
              ],
              blocks: [
                { id: "target_scene", type: "param_ref", hint: "场景", value: "总部", param_id: "scene" },
              ],
            },
          },
        ]}
        collapsedNodeIds={new Set()}
        editingNodeId={null}
        selectedNodeId={null}
        draftDisplayText=""
        disabled={false}
        onToggleCollapse={() => undefined}
        onSelectNode={() => undefined}
        onBeginEdit={() => undefined}
        onDraftChange={() => undefined}
        onCommitEdit={() => undefined}
        onCancelEdit={() => undefined}
        onAddSibling={() => undefined}
        onAddChild={() => undefined}
        onMoveUp={() => undefined}
        onMoveDown={() => undefined}
        onPromote={() => undefined}
        onDemote={() => undefined}
        onDelete={() => undefined}
        onBeginBlockEdit={() => undefined}
        onBlockDraftChange={() => undefined}
        onCommitBlockEdit={() => undefined}
        onCancelBlockEdit={() => undefined}
        editingBlockKey={null}
        blockDraftValue=""
      />,
    );

    const chip = screen.getByRole("button", { name: "编辑区块 target_scene" });
    expect(chip).toHaveTextContent("总部");
    expect(chip).toHaveAttribute("title", "参数：场景（scene）");
    expect(screen.queryByText("来自参数 scene")).not.toBeInTheDocument();
  });

  it("keeps structured sentence in single-line mode while a block is being edited", () => {
    const { container } = render(
      <OutlineTree
        mode="editable"
        nodes={[
          {
            node_id: "node-inline",
            title: "范围分析",
            description: "",
            level: 1,
            display_text: "分析 总部 的巡检情况",
            node_kind: "structured_leaf",
            ai_generated: false,
            children: [],
            outline_instance: {
              document_template: "分析 {@target_scene} 的巡检情况",
              rendered_document: "分析 总部 的巡检情况",
              segments: [
                { kind: "text", text: "分析 " },
                { kind: "block", block_id: "target_scene", block_type: "param_ref", value: "总部" },
                { kind: "text", text: " 的巡检情况" },
              ],
              blocks: [
                { id: "target_scene", type: "param_ref", hint: "场景", value: "总部", param_id: "scene" },
              ],
            },
          },
        ]}
        collapsedNodeIds={new Set()}
        editingNodeId={null}
        selectedNodeId={null}
        draftDisplayText=""
        disabled={false}
        onToggleCollapse={() => undefined}
        onSelectNode={() => undefined}
        onBeginEdit={() => undefined}
        onDraftChange={() => undefined}
        onCommitEdit={() => undefined}
        onCancelEdit={() => undefined}
        onAddSibling={() => undefined}
        onAddChild={() => undefined}
        onMoveUp={() => undefined}
        onMoveDown={() => undefined}
        onPromote={() => undefined}
        onDemote={() => undefined}
        onDelete={() => undefined}
        onBeginBlockEdit={() => undefined}
        onBlockDraftChange={() => undefined}
        onCommitBlockEdit={() => undefined}
        onCancelBlockEdit={() => undefined}
        editingBlockKey={"node-inline:target_scene"}
        blockDraftValue="总部"
      />,
    );

    expect(container.querySelector(".outline-tree__segments--editing-block")).not.toBeNull();
    expect(screen.getByText("分析")).toBeInTheDocument();
    expect(screen.getByText("的巡检情况")).toBeInTheDocument();
    expect(screen.getByLabelText("编辑区块值 target_scene")).toHaveClass(
      "outline-tree__block-input--inline",
      "outline-tree__block-input--chip-editing",
    );
  });
});
