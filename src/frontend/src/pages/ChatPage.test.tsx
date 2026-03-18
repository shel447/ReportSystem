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
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ is_ready: true, index_status: { ready_count: 1 } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
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
        }),
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

    fireEvent.change(screen.getByPlaceholderText("输入消息，例如：制作设备巡检报告"), {
      target: { value: "制作设备巡检报告" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    await waitFor(() => {
      expect(screen.getByText("请提供参数「报告日期」的取值。")).toBeInTheDocument();
    });

    expect(fetchMock).toHaveBeenCalledWith("/api/system-settings", undefined);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/chat",
      expect.objectContaining({
        method: "POST",
      }),
    );
  });
});
