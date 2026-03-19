import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ChatPage } from "./ChatPage";

function renderChatPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ChatPage />
    </QueryClientProvider>,
  );
}

describe("ChatPage", () => {
  it("keeps the chat workspace focused and sends message through chat api", async () => {
    let resolveChat: ((value: unknown) => void) | undefined;
    const chatResponse = new Promise((resolve) => {
      resolveChat = resolve;
    });
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ is_ready: true, index_status: { ready_count: 1 } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => chatResponse,
      });
    vi.stubGlobal("fetch", fetchMock);

    renderChatPage();

    expect(screen.getByText("您好！我是您的智能报告助手。")).toBeInTheDocument();
    expect(screen.getByTestId("chat-stream-shell")).toBeInTheDocument();
    expect(screen.getByTestId("chat-compose-dock")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "对话助手" })).not.toBeInTheDocument();
    expect(screen.queryByText("Conversation Workflow")).not.toBeInTheDocument();
    expect(screen.queryByText("模板匹配")).not.toBeInTheDocument();
    expect(screen.queryByText("补参")).not.toBeInTheDocument();
    expect(screen.queryByText("确认")).not.toBeInTheDocument();
    expect(screen.queryByText("生成")).not.toBeInTheDocument();
    expect(screen.queryByText("下载")).not.toBeInTheDocument();
    expect(screen.queryByText("从自然语言需求进入模板匹配、结构化补参与文档下载的完整链路。")).not.toBeInTheDocument();
    expect(screen.queryByText("支持直接输入自然语言需求")).not.toBeInTheDocument();

    const composer = screen.getByPlaceholderText("输入消息，例如：制作设备巡检报告") as HTMLTextAreaElement;
    fireEvent.change(composer, {
      target: { value: "制作设备巡检报告" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    expect(screen.getByText("制作设备巡检报告")).toBeInTheDocument();
    expect(screen.getByText("正在处理中")).toBeInTheDocument();
    expect(composer.value).toBe("");
    expect(composer).toBeDisabled();
    expect(screen.getByRole("button", { name: "发送" })).toHaveClass("chat-send-button", "is-pending");
    expect(screen.queryByText("发送中...")).not.toBeInTheDocument();

    resolveChat?.({
      session_id: "s-1",
      reply: "请提供参数「报告日期」的取值。",
      action: {
        type: "ask_param",
        template_name: "设备巡检报告",
        param: { id: "report_date", label: "报告日期", input_type: "date", multi: false, options: [] },
        widget: { kind: "date" },
        selected_values: [],
        progress: { collected: 0, required: 2 },
      },
    });

    await waitFor(() => {
      expect(screen.getByText("请提供参数「报告日期」的取值。")).toBeInTheDocument();
    });

    expect(screen.queryByText("正在处理中")).not.toBeInTheDocument();
    expect(composer).not.toBeDisabled();

    expect(fetchMock).toHaveBeenCalledWith("/api/system-settings", undefined);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/chat",
      expect.objectContaining({
        method: "POST",
      }),
    );
  });

  it("optimistically appends structured parameter submissions while pending", async () => {
    let resolveFirstChat: ((value: unknown) => void) | undefined;
    let resolveSecondChat: ((value: unknown) => void) | undefined;
    const firstChatResponse = new Promise((resolve) => {
      resolveFirstChat = resolve;
    });
    const secondChatResponse = new Promise((resolve) => {
      resolveSecondChat = resolve;
    });
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ is_ready: true, index_status: { ready_count: 1 } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => firstChatResponse,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => secondChatResponse,
      });
    vi.stubGlobal("fetch", fetchMock);

    renderChatPage();

    fireEvent.change(screen.getByPlaceholderText("输入消息，例如：制作设备巡检报告"), {
      target: { value: "制作设备巡检报告" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    resolveFirstChat?.({
      session_id: "s-1",
      reply: "请提供参数「报告日期」的取值。",
      messages: [
        { role: "user", content: "制作设备巡检报告" },
        {
          role: "assistant",
          content: "请提供参数「报告日期」的取值。",
          action: {
            type: "ask_param",
            template_name: "设备巡检报告",
            param: { id: "report_date", label: "报告日期", input_type: "date", multi: false, options: [] },
            widget: { kind: "date" },
            selected_values: [],
            progress: { collected: 0, required: 2 },
          },
        },
      ],
    });

    await waitFor(() => {
      expect(screen.getByLabelText("报告日期")).toBeInTheDocument();
    });

    const dateInput = screen.getByLabelText("报告日期") as HTMLInputElement;
    fireEvent.change(dateInput, { target: { value: "2026-03-19" } });
    fireEvent.click(screen.getByRole("button", { name: "提交" }));

    expect(screen.getByText("2026-03-19")).toBeInTheDocument();
    expect(screen.getByText("正在处理中")).toBeInTheDocument();
    expect(dateInput).toBeDisabled();
    expect(screen.getByRole("button", { name: "提交" })).toBeDisabled();

    resolveSecondChat?.({
      session_id: "s-1",
      reply: "参数已收集完成，请确认生成。",
      messages: [
        { role: "user", content: "制作设备巡检报告" },
        { role: "assistant", content: "请提供参数「报告日期」的取值。" },
        { role: "user", content: "2026-03-19" },
        {
          role: "assistant",
          content: "参数已收集完成，请确认生成。",
          action: {
            type: "review_params",
            template_name: "设备巡检报告",
            params: [
              { id: "report_date", label: "报告日期", value: "2026-03-19", required: true },
            ],
            missing_required: [],
          },
        },
      ],
    });

    await waitFor(() => {
      expect(screen.getByText("参数已收集完成，请确认生成。")).toBeInTheDocument();
    });

    expect(screen.queryByText("正在处理中")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "确认生成" })).toBeEnabled();
  });
});
