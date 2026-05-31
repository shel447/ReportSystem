import { render, screen } from "@testing-library/react";

import { ConversationLayout } from "./ConversationLayout";
import { DetailPageLayout } from "./DetailPageLayout";
import { ListPageLayout } from "./ListPageLayout";
import { PageIntroBar } from "./PageIntroBar";

describe("shared page layouts", () => {
  it("renders a compact page toolbar with a single heading", () => {
    render(
      <PageIntroBar
        title="页面标题"
        description="统一的页面引导文案。"
        actions={<button type="button">主操作</button>}
        badge="Draft"
      />,
    );

    expect(screen.getByText("统一的页面引导文案。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "主操作" })).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "页面标题", level: 1 })).toBeInTheDocument();
  });

  it("renders list and detail layouts with stable regions", () => {
    render(
      <>
        <ListPageLayout
          intro={<PageIntroBar title="列表页" />}
          content={<div>列表内容</div>}
        />
        <DetailPageLayout
          intro={<PageIntroBar title="详情页" />}
          summary={<div>摘要区域</div>}
          content={<div>正文区域</div>}
        />
      </>,
    );

    expect(screen.getByText("列表内容")).toBeInTheDocument();
    expect(screen.getByText("摘要区域")).toBeInTheDocument();
    expect(screen.getByText("正文区域")).toBeInTheDocument();
  });

  it("renders conversation layout with intro, notices, stream, and composer", () => {
    render(
      <ConversationLayout
        intro={<PageIntroBar title="流程说明" />}
        notices={<div>状态提醒</div>}
        stream={<div>消息流</div>}
        composer={<div>输入区</div>}
      />,
    );

    expect(screen.getByText("流程说明")).toBeInTheDocument();
    expect(screen.getByText("状态提醒")).toBeInTheDocument();
    expect(screen.getByText("消息流")).toBeInTheDocument();
    expect(screen.getByText("输入区")).toBeInTheDocument();
  });
});
