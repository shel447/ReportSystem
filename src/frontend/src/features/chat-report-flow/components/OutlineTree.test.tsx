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
});
