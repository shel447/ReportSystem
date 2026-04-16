import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { ChatPage } from "./ChatPage";

type MockResponse = {
  ok: boolean;
  json: () => Promise<unknown>;
};

type ChatRouteEntry =
  | string
  | {
      pathname: string;
      search?: string;
      state?: unknown;
    };

function renderChatPage(route: ChatRouteEntry = "/chat") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/chat" element={<ChatPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function createJsonResponse(payload: unknown): MockResponse {
  return {
    ok: true,
    json: async () => payload,
  };
}

function formatExpectedChatTimestamp(iso: string) {
  const value = new Date(iso);
  const now = new Date();
  const sameDay =
    value.getFullYear() === now.getFullYear()
    && value.getMonth() === now.getMonth()
    && value.getDate() === now.getDate();
  const pad = (part: number) => String(part).padStart(2, "0");
  const time = `${pad(value.getHours())}:${pad(value.getMinutes())}`;
  if (sameDay) {
    return time;
  }
  return `${pad(value.getMonth() + 1)}-${pad(value.getDate())} ${time}`;
}

describe("ChatPage", () => {
  it("renders empty history rail and sends message through chat api", async () => {
    const assistantTimestamp = new Date().toISOString();
    let resolveChat: ((value: unknown) => void) | undefined;
    const chatResponse = new Promise((resolve) => {
      resolveChat = resolve;
    });
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/rest/dev/system-settings") {
        return Promise.resolve(createJsonResponse({ is_ready: true, index_status: { ready_count: 1 } }));
      }
      if (url === "/rest/chatbi/v1/chat" && !init?.method) {
        return Promise.resolve(createJsonResponse([]));
      }
      if (url === "/rest/chatbi/v1/chat" && init?.method === "POST") {
        return Promise.resolve(createJsonResponse(chatResponse));
      }
      throw new Error(`Unhandled request: ${url} ${init?.method ?? "GET"}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const view = renderChatPage();

    expect(screen.getByText("您好！我是您的智能报告助手。")).toBeInTheDocument();
    expect(screen.getByTestId("chat-stream-shell")).toBeInTheDocument();
    expect(screen.getByTestId("chat-compose-dock")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "新建会话" })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("暂无历史会话")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "折叠会话栏" }));
    expect(screen.queryByText("暂无历史会话")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "展开会话栏" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "展开会话栏" }));
    await waitFor(() => {
      expect(screen.getByText("暂无历史会话")).toBeInTheDocument();
    });
    expect(fetchMock).toHaveBeenCalledWith("/rest/dev/system-settings", undefined);
    expect(fetchMock).toHaveBeenCalledWith(
      "/rest/chatbi/v1/chat",
      expect.objectContaining({
        headers: expect.any(Headers),
      }),
    );
    expect(fetchMock).not.toHaveBeenCalledWith(
      "/rest/chatbi/v1/chat",
      expect.objectContaining({ method: "POST" }),
    );

    const composer = screen.getByPlaceholderText("输入消息，例如：制作设备巡检报告") as HTMLTextAreaElement;
    fireEvent.change(composer, {
      target: { value: "制作设备巡检报告" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    expect(screen.getByText("制作设备巡检报告")).toBeInTheDocument();
    expect(screen.getByText("正在处理中")).toBeInTheDocument();
    expect(view.container.querySelector(".message-entry")).not.toBeNull();
    expect(view.container.querySelector(".message-entry__role")?.textContent).toBe("助手");
    expect(view.container.querySelector(".message-bubble__meta")).toBeNull();
    expect(composer.value).toBe("");
    expect(composer).toBeDisabled();
    expect(screen.getByRole("button", { name: "发送" })).toHaveClass("chat-send-button", "is-pending");
    expect(screen.queryByText("发送中...")).not.toBeInTheDocument();

    resolveChat?.({
      session_id: "s-1",
      reply: "请提供参数「报告日期」的取值。",
      messages: [
        { role: "user", content: "制作设备巡检报告", created_at: assistantTimestamp },
        {
          role: "assistant",
          content: "请提供参数「报告日期」的取值。",
          created_at: assistantTimestamp,
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

    expect(screen.getAllByText(formatExpectedChatTimestamp(assistantTimestamp)).length).toBeGreaterThan(0);
    expect(screen.queryByText("正在处理中")).not.toBeInTheDocument();
    expect(composer).not.toBeDisabled();
    expect(fetchMock).toHaveBeenCalledWith(
      "/rest/chatbi/v1/chat",
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
      if (url === "/rest/dev/system-settings") {
        return Promise.resolve(createJsonResponse({ is_ready: true, index_status: { ready_count: 1 } }));
      }
      if (url === "/rest/chatbi/v1/chat" && !init?.method) {
        return Promise.resolve(createJsonResponse(sessionList));
      }
      if (url === "/rest/chatbi/v1/chat/s-1" && !init?.method) {
        return Promise.resolve(createJsonResponse({
          session_id: "s-1",
          matched_template_id: "tpl-1",
          messages: [
            { role: "user", content: "制作设备巡检报告" },
            { role: "assistant", content: "请提供参数。" },
          ],
        }));
      }
      if (url === "/rest/chatbi/v1/chat/s-1" && init?.method === "DELETE") {
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
    expect(screen.queryByText("请提供参数")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "打开会话：制作设备巡检报告" }));

    await waitFor(() => {
      expect(screen.getByText("请提供参数。")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "更多操作：制作设备巡检报告" }));
    expect(screen.getByRole("button", { name: "重命名（暂未开放）" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "删除会话" }));

    await waitFor(() => {
      expect(screen.getByText("暂无历史会话")).toBeInTheDocument();
    });

    expect(screen.getByText("您好！我是您的智能报告助手。")).toBeInTheDocument();
    expect(screen.queryByText("请提供参数。")).not.toBeInTheDocument();
  });

  it("sends preferred capability when a quick entry is selected", async () => {
    let capturedBody: Record<string, unknown> | undefined;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/rest/dev/system-settings") {
        return Promise.resolve(createJsonResponse({ is_ready: true, index_status: { ready_count: 1 } }));
      }
      if (url === "/rest/chatbi/v1/chat" && !init?.method) {
        return Promise.resolve(createJsonResponse([]));
      }
      if (url === "/rest/chatbi/v1/chat" && init?.method === "POST") {
        capturedBody = JSON.parse(String(init.body ?? "{}"));
        return Promise.resolve(
          createJsonResponse({
            session_id: "s-query-1",
            reply: "这是问数结果。",
            messages: [
              { role: "user", content: "查一下昨天华东区域告警TOP10", created_at: new Date().toISOString() },
              { role: "assistant", content: "这是问数结果。", created_at: new Date().toISOString() },
            ],
          }),
        );
      }
      throw new Error(`Unhandled request: ${url} ${init?.method ?? "GET"}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderChatPage();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "快捷入口：智能问数" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "快捷入口：智能问数" }));
    fireEvent.change(screen.getByPlaceholderText("输入消息，例如：制作设备巡检报告"), {
      target: { value: "查一下昨天华东区域告警TOP10" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    await waitFor(() => {
      expect(screen.getByText("这是问数结果。")).toBeInTheDocument();
    });

    expect(capturedBody?.instruction).toBe("smart_query");
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
      if (url === "/rest/dev/system-settings") {
        return Promise.resolve(createJsonResponse({ is_ready: true, index_status: { ready_count: 1 } }));
      }
      if (url === "/rest/chatbi/v1/chat" && !init?.method) {
        return Promise.resolve(createJsonResponse([]));
      }
      if (url === "/rest/chatbi/v1/chat" && init?.method === "POST") {
        const body = JSON.parse(String(init.body ?? "{}"));
        if (!body.reply) {
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
      reply: "参数已收集完成，请确认后生成诉求。",
      messages: [
        { role: "user", content: "制作设备巡检报告" },
        { role: "assistant", content: "请提供参数「报告日期」的取值。" },
        { role: "user", content: "2026-03-19" },
        {
          role: "assistant",
          content: "参数已收集完成，请确认后生成诉求。",
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
      expect(screen.getByText("参数已收集完成，请确认后生成诉求。")).toBeInTheDocument();
    });

    expect(screen.queryByText("正在处理中")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "确认参数并生成诉求" })).toBeEnabled();
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
      if (url === "/rest/dev/system-settings") {
        return Promise.resolve(createJsonResponse({ is_ready: true, index_status: { ready_count: 1 } }));
      }
      if (url === "/rest/chatbi/v1/chat" && !init?.method) {
        return Promise.resolve(createJsonResponse([]));
      }
      if (url === "/rest/chatbi/v1/chat" && init?.method === "POST") {
        const body = JSON.parse(String(init.body ?? "{}"));
        if (!body.command?.name) {
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
      reply: "参数已收集完成，请确认后生成诉求。",
      messages: [
        { role: "user", content: "制作设备巡检报告" },
        {
          role: "assistant",
          content: "参数已收集完成，请确认后生成诉求。",
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
      expect(screen.getByRole("button", { name: "确认参数并生成诉求" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "确认参数并生成诉求" }));

    expect(screen.getByRole("button", { name: "确认参数并生成诉求" })).toBeDisabled();
    expect(screen.getByText("正在处理中")).toBeInTheDocument();

    resolveSecondChat?.({
      session_id: "s-1",
      reply: "参数已确认，请检查报告诉求。",
      messages: [
        { role: "user", content: "制作设备巡检报告" },
        { role: "assistant", content: "参数已收集完成，请确认后生成诉求。" },
        { role: "user", content: "确认参数并生成诉求" },
        {
          role: "assistant",
          content: "参数已确认，请检查报告诉求。",
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

    expect(screen.getByRole("button", { name: "保存诉求" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "确认生成" })).toBeEnabled();
  });

  it("loads an explicit forked session from query parameter and shows source badge", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/rest/dev/system-settings") {
        return Promise.resolve(createJsonResponse({ is_ready: true, index_status: { ready_count: 1 } }));
      }
      if (url === "/rest/chatbi/v1/chat" && !init?.method) {
        return Promise.resolve(createJsonResponse([]));
      }
      if (url === "/rest/chatbi/v1/chat/s-forked" && !init?.method) {
        return Promise.resolve(createJsonResponse({
          session_id: "s-forked",
          title: "设备巡检报告 copy_ab12cd",
          matched_template_id: "tpl-1",
          fork_meta: {
            source_kind: "session_message",
            source_title: "设备巡检报告",
            source_preview: "制作设备巡检报告",
            source_session_id: "s-1",
            source_message_id: "msg-1",
          },
          messages: [
            {
              role: "assistant",
              content: "请提供参数。",
              message_id: "msg-a1",
              created_at: "2026-03-20T12:00:00Z",
            },
          ],
        }));
      }
      throw new Error(`Unhandled request: ${url} ${init?.method ?? "GET"}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderChatPage("/chat?session_id=s-forked");

    expect(await screen.findByText("请提供参数。")).toBeInTheDocument();
    expect(screen.getByText("来源：设备巡检报告 copy_ab12cd · 来自历史消息")).toBeInTheDocument();
  });

  it("hydrates a prefetched update session immediately and labels the source as update", async () => {
    let resolveSession: ((value: unknown) => void) | undefined;
    const sessionResponse = new Promise((resolve) => {
      resolveSession = resolve;
    });
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/rest/dev/system-settings") {
        return Promise.resolve(createJsonResponse({ is_ready: true, index_status: { ready_count: 1 } }));
      }
      if (url === "/rest/chatbi/v1/chat" && !init?.method) {
        return Promise.resolve(createJsonResponse([]));
      }
      if (url === "/rest/chatbi/v1/chat/s-update" && !init?.method) {
        return Promise.resolve(createJsonResponse(sessionResponse));
      }
      throw new Error(`Unhandled request: ${url} ${init?.method ?? "GET"}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderChatPage({
      pathname: "/chat",
      search: "?session_id=s-update",
      state: {
        prefetchedSession: {
          session_id: "s-update",
          title: "设备巡检报告 copy_ab12cd",
          matched_template_id: "tpl-1",
          fork_meta: {
            source_kind: "update_from_instance",
            source_title: "设备巡检报告",
            source_preview: "确认诉求：生成基线",
            source_report_instance_id: "inst-1",
          },
          messages: [
            {
              role: "assistant",
              content: "参数已确认，请检查报告诉求。",
              action: {
                type: "review_outline",
                template_name: "设备巡检报告",
                template_id: "tpl-1",
                warnings: [],
                params_snapshot: [{ id: "report_date", label: "报告日期", value: "2026-03-19" }],
                outline: [
                  {
                    node_id: "node-1",
                    title: "确认诉求",
                    description: "生成基线",
                    display_text: "确认诉求：生成基线",
                    level: 1,
                    children: [],
                  },
                ],
              },
              created_at: "2026-03-20T12:00:00Z",
              message_id: "msg-update-1",
            },
          ],
        },
      },
    });

    expect(await screen.findByText("参数已确认，请检查报告诉求。")).toBeInTheDocument();
    expect(screen.getByText("更新来源")).toBeInTheDocument();
    expect(screen.getByText("来源：设备巡检报告 · 来自确认诉求")).toBeInTheDocument();
    expect(screen.queryByText("Fork 来源")).not.toBeInTheDocument();

    resolveSession?.({
      session_id: "s-update",
      title: "设备巡检报告 copy_ab12cd",
      matched_template_id: "tpl-1",
      fork_meta: {
        source_kind: "update_from_instance",
        source_title: "设备巡检报告",
        source_preview: "确认诉求：生成基线",
        source_report_instance_id: "inst-1",
      },
      messages: [
        {
          role: "assistant",
          content: "参数已确认，请检查报告诉求。",
          action: {
            type: "review_outline",
            template_name: "设备巡检报告",
            template_id: "tpl-1",
            warnings: [],
            params_snapshot: [{ id: "report_date", label: "报告日期", value: "2026-03-19" }],
            outline: [
              {
                node_id: "node-1",
                title: "确认诉求",
                description: "生成基线",
                display_text: "确认诉求：生成基线",
                level: 1,
                children: [],
              },
            ],
          },
          created_at: "2026-03-20T12:00:00Z",
          message_id: "msg-update-1",
        },
      ],
      });

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledWith(
          "/rest/chatbi/v1/chat/s-update",
          expect.objectContaining({
            headers: expect.any(Headers),
          }),
        );
      });
    });

  it("forks a user message into a new session and prefills the compose draft", async () => {
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
      if (url === "/rest/dev/system-settings") {
        return Promise.resolve(createJsonResponse({ is_ready: true, index_status: { ready_count: 1 } }));
      }
      if (url === "/rest/chatbi/v1/chat" && !init?.method) {
        return Promise.resolve(createJsonResponse(sessionList));
      }
      if (url === "/rest/chatbi/v1/chat/s-1" && !init?.method) {
        return Promise.resolve(createJsonResponse({
          session_id: "s-1",
          title: "制作设备巡检报告",
          matched_template_id: "tpl-1",
          messages: [
            { role: "user", content: "制作设备巡检报告", message_id: "msg-u1" },
            { role: "assistant", content: "请提供参数。", message_id: "msg-a1" },
          ],
        }));
      }
      if (url === "/rest/chatbi/v1/chat/forks" && init?.method === "POST") {
        sessionList = [
          {
            session_id: "s-fork",
            title: "制作设备巡检报告 copy_ab12cd",
            created_at: "2026-03-20T10:00:00Z",
            updated_at: "2026-03-20T10:00:00Z",
            message_count: 1,
            last_message_preview: "制作设备巡检报告",
            matched_template_id: "tpl-1",
            instance_id: null,
          },
          ...sessionList,
        ];
        return Promise.resolve(createJsonResponse({
          session_id: "s-fork",
          title: "制作设备巡检报告 copy_ab12cd",
          matched_template_id: "tpl-1",
          draft_message: "制作设备巡检报告",
          fork_meta: {
            source_kind: "session_message",
            source_title: "制作设备巡检报告",
            source_preview: "制作设备巡检报告",
            source_session_id: "s-1",
            source_message_id: "msg-u1",
          },
          messages: [
            { role: "user", content: "制作设备巡检报告", message_id: "msg-u1-copy" },
          ],
        }));
      }
      throw new Error(`Unhandled request: ${url} ${init?.method ?? "GET"}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderChatPage();

    expect(await screen.findByRole("button", { name: "打开会话：制作设备巡检报告" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "打开会话：制作设备巡检报告" }));

    await waitFor(() => {
      expect(screen.getByText("请提供参数。")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "更多操作：消息 msg-u1" }));
    fireEvent.click(screen.getByRole("button", { name: "Fork 为新会话" }));

    await waitFor(() => {
      expect(screen.getByText("来源：制作设备巡检报告 copy_ab12cd · 来自历史消息")).toBeInTheDocument();
    });
    expect(screen.getByDisplayValue("制作设备巡检报告")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "打开会话：制作设备巡检报告 copy_ab12cd" })).toBeInTheDocument();
    });
  });

  it("allows switching sessions while a chat response is pending without stale response taking over", async () => {
    let resolveChat: ((value: unknown) => void) | undefined;
    const chatResponse = new Promise((resolve) => {
      resolveChat = resolve;
    });
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/rest/dev/system-settings") {
        return Promise.resolve(createJsonResponse({ is_ready: true, index_status: { ready_count: 1 } }));
      }
      if (url === "/rest/chatbi/v1/chat" && !init?.method) {
        return Promise.resolve(createJsonResponse([
          {
            session_id: "s-1",
            title: "历史会话",
            created_at: "2026-03-20T09:00:00Z",
            updated_at: "2026-03-20T09:05:00Z",
            message_count: 2,
            last_message_preview: "已存在的回复",
            matched_template_id: null,
            instance_id: null,
          },
        ]));
      }
      if (url === "/rest/chatbi/v1/chat" && init?.method === "POST") {
        return Promise.resolve(createJsonResponse(chatResponse));
      }
      if (url === "/rest/chatbi/v1/chat/s-1" && !init?.method) {
        return Promise.resolve(createJsonResponse({
          session_id: "s-1",
          title: "历史会话",
          matched_template_id: null,
          messages: [
            { role: "user", content: "老问题", message_id: "msg-old-u" },
            { role: "assistant", content: "已存在的回复", message_id: "msg-old-a" },
          ],
        }));
      }
      throw new Error(`Unhandled request: ${url} ${init?.method ?? "GET"}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderChatPage();

    expect(await screen.findByRole("button", { name: "打开会话：历史会话" })).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("输入消息，例如：制作设备巡检报告"), {
      target: { value: "新的处理中请求" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    expect(screen.getByText("正在处理中")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "打开会话：历史会话" }));

    await waitFor(() => {
      expect(screen.getByText("已存在的回复")).toBeInTheDocument();
    });

    resolveChat?.({
      session_id: "s-new",
      title: "新的处理中请求",
      reply: "这是一条迟到的回复",
      messages: [
        { role: "user", content: "新的处理中请求", message_id: "msg-new-u" },
        { role: "assistant", content: "这是一条迟到的回复", message_id: "msg-new-a" },
      ],
    });

    await waitFor(() => {
      expect(screen.queryByText("正在处理中")).not.toBeInTheDocument();
    });

    expect(screen.getByText("已存在的回复")).toBeInTheDocument();
    expect(screen.queryByText("这是一条迟到的回复")).not.toBeInTheDocument();
  });

  it("allows resetting to a new conversation while pending without stale response replacing the empty state", async () => {
    let resolveChat: ((value: unknown) => void) | undefined;
    const chatResponse = new Promise((resolve) => {
      resolveChat = resolve;
    });
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/rest/dev/system-settings") {
        return Promise.resolve(createJsonResponse({ is_ready: true, index_status: { ready_count: 1 } }));
      }
      if (url === "/rest/chatbi/v1/chat" && !init?.method) {
        return Promise.resolve(createJsonResponse([]));
      }
      if (url === "/rest/chatbi/v1/chat" && init?.method === "POST") {
        return Promise.resolve(createJsonResponse(chatResponse));
      }
      throw new Error(`Unhandled request: ${url} ${init?.method ?? "GET"}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderChatPage();

    fireEvent.change(screen.getByPlaceholderText("输入消息，例如：制作设备巡检报告"), {
      target: { value: "会被放弃的请求" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    expect(screen.getByText("会被放弃的请求")).toBeInTheDocument();
    expect(screen.getByText("正在处理中")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "新建会话" }));

    await waitFor(() => {
      expect(screen.getByText("您好！我是您的智能报告助手。")).toBeInTheDocument();
    });

    resolveChat?.({
      session_id: "s-abandoned",
      title: "会被放弃的请求",
      reply: "迟到的回复不应覆盖空态",
      messages: [
        { role: "user", content: "会被放弃的请求", message_id: "msg-user" },
        { role: "assistant", content: "迟到的回复不应覆盖空态", message_id: "msg-assistant" },
      ],
    });

    await waitFor(() => {
      expect(screen.queryByText("正在处理中")).not.toBeInTheDocument();
    });

    expect(screen.getByText("您好！我是您的智能报告助手。")).toBeInTheDocument();
    expect(screen.queryByText("迟到的回复不应覆盖空态")).not.toBeInTheDocument();
  });
});
