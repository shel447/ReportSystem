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
});
