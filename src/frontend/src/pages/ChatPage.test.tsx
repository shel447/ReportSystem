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
  it("renders welcome state and sends message through chat api", async () => {
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
