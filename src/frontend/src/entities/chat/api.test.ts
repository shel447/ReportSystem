import { sendChatMessage } from "./api";

describe("chat api contract adapter", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("maps legacy chat request into contract payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        conversationId: "s-1",
        chatId: "chat-res-1",
        status: "waiting_user",
        steps: [],
        delta: [],
        ask: {
          mode: "form",
          type: "confirm",
          parameters: [],
        },
        answer: null,
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await sendChatMessage({
      session_id: "s-1",
      message: "制作设备巡检报告",
      preferred_capability: "report_generation",
    });

    const [, options] = fetchMock.mock.calls[0];
    const body = JSON.parse(String(options.body));
    expect(body.conversationId).toBe("s-1");
    expect(body.instruction).toBe("generate_report");
    expect(body.question).toBe("制作设备巡检报告");
    expect(typeof body.chatId).toBe("string");
    expect(body.chatId.startsWith("chat-")).toBe(true);
  });

  it("maps param submit and generation command into contract reply+command", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        conversationId: "s-2",
        chatId: "chat-res-2",
        status: "finished",
        steps: [],
        delta: [],
        ask: null,
        answer: {
          answerType: "report_ready",
          reportId: "rpt-1",
          templateInstanceId: "ti-1",
          summary: "报告已生成",
          document: {
            document_id: "doc-1",
            download_url: "/rest/chatbi/v1/documents/doc-1/download",
          },
        },
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await sendChatMessage({
      session_id: "s-2",
      command: "confirm_outline_generation",
      param_id: "scene",
      param_value: "总部",
    });

    const [, options] = fetchMock.mock.calls[0];
    const body = JSON.parse(String(options.body));
    expect(body.reply).toEqual({
      type: "fill_params",
      parameters: {
        scene: "总部",
      },
    });
    expect(body.command).toEqual({ name: "confirm_generate_report" });
  });

  it("maps contract ask response back to legacy action payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        conversationId: "s-3",
        chatId: "chat-res-3",
        status: "waiting_user",
        steps: [],
        delta: [],
        ask: {
          mode: "form",
          type: "fill_params",
          title: "请填写参数",
          parameters: [
            {
              id: "scene",
              label: "场景",
              inputType: "enum",
              required: true,
              multi: false,
              options: [{ label: "总部", value: "总部" }],
            },
          ],
        },
        answer: null,
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await sendChatMessage({
      message: "制作设备巡检报告",
    });

    expect(response.session_id).toBe("s-3");
    expect(response.action?.type).toBe("ask_param");
    const action = response.action as { type: string; param?: { id?: string; options?: string[] } };
    expect(action.param?.id).toBe("scene");
    expect(action.param?.options).toEqual(["总部"]);
  });

  it("maps report_ready answer to download_document action", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        conversationId: "s-4",
        chatId: "chat-res-4",
        status: "finished",
        steps: [],
        delta: [],
        ask: null,
        answer: {
          answerType: "report_ready",
          reportId: "rpt-9",
          templateInstanceId: "ti-9",
          summary: "报告已生成",
          document: {
            document_id: "doc-9",
            file_name: "report.md",
            download_url: "/rest/chatbi/v1/documents/doc-9/download",
          },
        },
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await sendChatMessage({ message: "确认生成" });

    expect(response.session_id).toBe("s-4");
    expect(response.reply).toBe("报告已生成");
    expect(response.action?.type).toBe("download_document");
  });
});
