import { sendChatMessage } from "./api";

describe("chat api", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("posts the formal /chat contract with default user header", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        conversationId: "conv_1",
        chatId: "chat_1",
        status: "waiting_user",
        steps: [],
        ask: null,
        answer: null,
        errors: [],
        timestamp: 1713427200000,
        apiVersion: "v1",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await sendChatMessage({
      conversationId: "conv_1",
      instruction: "generate_report",
      question: "生成网络运行日报",
    });

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/rest/chatbi/v1/chat");
    expect(new Headers(options.headers).get("X-User-Id")).toBe("default");
    expect(options.method).toBe("POST");
    const payload = JSON.parse(String(options.body));
    expect(payload.conversationId).toBe("conv_1");
    expect(payload.instruction).toBe("generate_report");
    expect(payload.question).toBe("生成网络运行日报");
    expect(payload.apiVersion).toBe("v1");
    expect(typeof payload.chatId).toBe("string");
  });
});
