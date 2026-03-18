import { render, screen } from "@testing-library/react";

import { ConversationLayout } from "./ConversationLayout";
import { DetailPageLayout } from "./DetailPageLayout";
import { ListPageLayout } from "./ListPageLayout";
import { PageIntroBar } from "./PageIntroBar";

describe("shared page layouts", () => {
  it("renders intro copy and actions without adding a page heading", () => {
    render(
      <PageIntroBar
        description="统一的页面引导文案。"
        actions={<button type="button">主操作</button>}
        badge="Draft"
      />,
    );

    expect(screen.getByText("统一的页面引导文案。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "主操作" })).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
    expect(screen.queryByRole("heading")).not.toBeInTheDocument();
  });

  it("renders list and detail layouts with stable regions", () => {
    render(
      <>
        <ListPageLayout
          intro={<PageIntroBar description="列表页" />}
          content={<div>列表内容</div>}
        />
        <DetailPageLayout
          intro={<PageIntroBar description="详情页" />}
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
        intro={<PageIntroBar description="流程说明" />}
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
