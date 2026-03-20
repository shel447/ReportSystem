import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ChatPage } from "./ChatPage";

type MockResponse = {
  ok: boolean;
  json: () => Promise<unknown>;
};

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

function createJsonResponse(payload: unknown): MockResponse {
  return {
    ok: true,
    json: async () => payload,
  };
}

describe("ChatPage", () => {
  it("renders empty history rail and sends message through chat api", async () => {
    let resolveChat: ((value: unknown) => void) | undefined;
    const chatResponse = new Promise((resolve) => {
      resolveChat = resolve;
    });
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/system-settings") {
        return Promise.resolve(createJsonResponse({ is_ready: true, index_status: { ready_count: 1 } }));
      }
      if (url === "/api/chat" && !init?.method) {
        return Promise.resolve(createJsonResponse([]));
      }
      if (url === "/api/chat" && init?.method === "POST") {
        return Promise.resolve(createJsonResponse(chatResponse));
      }
      throw new Error(`Unhandled request: ${url} ${init?.method ?? "GET"}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderChatPage();

    expect(screen.getByText("您好！我是您的智能报告助手。")).toBeInTheDocument();
    expect(screen.getByTestId("chat-stream-shell")).toBeInTheDocument();
    expect(screen.getByTestId("chat-compose-dock")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "新建会话" })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("暂无历史会话")).toBeInTheDocument();
    });
    expect(fetchMock).toHaveBeenCalledWith("/api/system-settings", undefined);
    expect(fetchMock).toHaveBeenCalledWith("/api/chat", undefined);
    expect(fetchMock).not.toHaveBeenCalledWith(
      "/api/chat",
      expect.objectContaining({ method: "POST" }),
    );

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
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/chat",
      expect.objectContaining({
        method: "POST",
      }),
    );
  });

  it("loads a historical session and deleting it returns to empty state", async () => {
    let sessionList = [
      {
        session_id: "s-1",
        title: "制作设备巡检报告",
        created_at: "2026-03-20T09:00:00Z",
        updated_at: "2026-03-20T09:05:00Z",
        message_count: 2,
        last_message_preview: "请提供参数",
        matched_template_id: "tpl-1",
        instance_id: null,
      },
    ];
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/system-settings") {
        return Promise.resolve(createJsonResponse({ is_ready: true, index_status: { ready_count: 1 } }));
      }
      if (url === "/api/chat" && !init?.method) {
        return Promise.resolve(createJsonResponse(sessionList));
      }
      if (url === "/api/chat/s-1" && !init?.method) {
        return Promise.resolve(createJsonResponse({
          session_id: "s-1",
          matched_template_id: "tpl-1",
          messages: [
            { role: "user", content: "制作设备巡检报告" },
            { role: "assistant", content: "请提供参数。" },
          ],
        }));
      }
      if (url === "/api/chat/s-1" && init?.method === "DELETE") {
        sessionList = [];
        return Promise.resolve(createJsonResponse({ message: "deleted" }));
      }
      throw new Error(`Unhandled request: ${url} ${init?.method ?? "GET"}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderChatPage();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "打开会话：制作设备巡检报告" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "打开会话：制作设备巡检报告" }));

    await waitFor(() => {
      expect(screen.getByText("请提供参数。")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "删除会话：制作设备巡检报告" }));

    await waitFor(() => {
      expect(screen.getByText("暂无历史会话")).toBeInTheDocument();
    });

    expect(screen.getByText("您好！我是您的智能报告助手。")).toBeInTheDocument();
    expect(screen.queryByText("请提供参数。")).not.toBeInTheDocument();
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
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/system-settings") {
        return Promise.resolve(createJsonResponse({ is_ready: true, index_status: { ready_count: 1 } }));
      }
      if (url === "/api/chat" && !init?.method) {
        return Promise.resolve(createJsonResponse([]));
      }
      if (url === "/api/chat" && init?.method === "POST") {
        const body = JSON.parse(String(init.body ?? "{}"));
        if (body.message) {
          return Promise.resolve(createJsonResponse(firstChatResponse));
        }
        return Promise.resolve(createJsonResponse(secondChatResponse));
      }
      throw new Error(`Unhandled request: ${url} ${init?.method ?? "GET"}`);
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
      reply: "参数已收集完成，请确认后生成大纲。",
      messages: [
        { role: "user", content: "制作设备巡检报告" },
        { role: "assistant", content: "请提供参数「报告日期」的取值。" },
        { role: "user", content: "2026-03-19" },
        {
          role: "assistant",
          content: "参数已收集完成，请确认后生成大纲。",
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
      expect(screen.getByText("参数已收集完成，请确认后生成大纲。")).toBeInTheDocument();
    });

    expect(screen.queryByText("正在处理中")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "确认参数并生成大纲" })).toBeEnabled();
  });

  it("shows outline review before final generation", async () => {
    let resolveFirstChat: ((value: unknown) => void) | undefined;
    let resolveSecondChat: ((value: unknown) => void) | undefined;
    const firstChatResponse = new Promise((resolve) => {
      resolveFirstChat = resolve;
    });
    const secondChatResponse = new Promise((resolve) => {
      resolveSecondChat = resolve;
    });
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/system-settings") {
        return Promise.resolve(createJsonResponse({ is_ready: true, index_status: { ready_count: 1 } }));
      }
      if (url === "/api/chat" && !init?.method) {
        return Promise.resolve(createJsonResponse([]));
      }
      if (url === "/api/chat" && init?.method === "POST") {
        const body = JSON.parse(String(init.body ?? "{}"));
        if (body.message) {
          return Promise.resolve(createJsonResponse(firstChatResponse));
        }
        return Promise.resolve(createJsonResponse(secondChatResponse));
      }
      throw new Error(`Unhandled request: ${url} ${init?.method ?? "GET"}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderChatPage();

    fireEvent.change(screen.getByPlaceholderText("输入消息，例如：制作设备巡检报告"), {
      target: { value: "制作设备巡检报告" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    resolveFirstChat?.({
      session_id: "s-1",
      reply: "参数已收集完成，请确认后生成大纲。",
      messages: [
        { role: "user", content: "制作设备巡检报告" },
        {
          role: "assistant",
          content: "参数已收集完成，请确认后生成大纲。",
          action: {
            type: "review_params",
            template_name: "设备巡检报告",
            params: [{ id: "report_date", label: "报告日期", value: "2026-03-19", required: true }],
            missing_required: [],
          },
        },
      ],
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "确认参数并生成大纲" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "确认参数并生成大纲" }));

    expect(screen.getByRole("button", { name: "确认参数并生成大纲" })).toBeDisabled();
    expect(screen.getByText("正在处理中")).toBeInTheDocument();

    resolveSecondChat?.({
      session_id: "s-1",
      reply: "参数已确认，请检查报告大纲。",
      messages: [
        { role: "user", content: "制作设备巡检报告" },
        { role: "assistant", content: "参数已收集完成，请确认后生成大纲。" },
        { role: "user", content: "确认参数并生成大纲" },
        {
          role: "assistant",
          content: "参数已确认，请检查报告大纲。",
          action: {
            type: "review_outline",
            template_name: "设备巡检报告",
            template_id: "tpl-1",
            warnings: [],
            params_snapshot: [{ id: "report_date", label: "报告日期", value: "2026-03-19" }],
            outline: [
              {
                node_id: "node-1",
                title: "总部概览",
                description: "巡检范围",
                display_text: "总部概览：巡检范围",
                node_kind: "freeform_leaf",
                ai_generated: true,
                level: 1,
                children: [],
              },
            ],
          },
        },
      ],
    });

    await waitFor(() => {
      expect(screen.getByText("总部概览：巡检范围")).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: "保存大纲" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "确认生成" })).toBeEnabled();
  });
});

