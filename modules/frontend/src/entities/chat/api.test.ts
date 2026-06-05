import { parseSsePayload, sendChatMessageStream, stopChat } from "./api";

describe("chat stream api", () => {
  it("parses sse payload into ordered chat stream events", () => {
    const events = parseSsePayload(
      [
        'event: message',
        'data: {"conversationId":"conv_1","chatId":"chat_1","eventType":"status","sequence":1,"timestamp":1,"status":"running"}',
        "",
        'event: message',
        'data: {"conversationId":"conv_1","chatId":"chat_1","eventType":"step_delta","sequence":2,"timestamp":2,"status":"running","toolCall":{"name":"onequery"},"sourceSubflow":{"alias":"analysis","callId":"subflow_1"}}',
        "",
        'event: message',
        'data: {"conversationId":"conv_1","chatId":"chat_1","eventType":"answer","sequence":3,"timestamp":3,"status":"running","delta":[{"action":"init_report","report":{"reportId":"rpt_1","title":"网络运行日报"}}]}',
        "",
      ].join("\n"),
    );

    expect(events).toHaveLength(3);
    expect(events[0].eventType).toBe("status");
    expect(events[1].toolCall?.name).toBe("onequery");
    expect(events[1].sourceSubflow?.alias).toBe("analysis");
    expect(events[2].delta?.[0]).toEqual({
      action: "init_report",
      report: { reportId: "rpt_1", title: "网络运行日报" },
    });
  });

  it("aggregates runtime step events into the final chat response", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        [
          'data: {"conversationId":"conv_1","chatId":"chat_1","eventType":"status","sequence":1,"timestamp":1,"status":"running"}',
          "",
          'data: {"conversationId":"conv_1","chatId":"chat_1","eventType":"step_delta","sequence":2,"timestamp":2,"status":"running","step":{"code":"report.template.match","stepId":"report.template.match","title":"识别模板","status":"running","parentStepId":"report","stepPath":["report","template"]}}',
          "",
          'data: {"conversationId":"conv_1","chatId":"chat_1","eventType":"done","sequence":3,"timestamp":3,"status":"finished"}',
          "",
        ].join("\n"),
        { headers: { "Content-Type": "text/event-stream" } },
      ),
    );

    const response = await sendChatMessageStream({ conversationId: "conv_1", question: "生成日报" });

    expect(response.steps).toEqual([{ code: "report.template.match", stepId: "report.template.match", title: "识别模板", status: "running", parentStepId: "report", stepPath: ["report", "template"] }]);
    const requestBody = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body));
    expect(requestBody).not.toHaveProperty("requestId");
    expect(requestBody).not.toHaveProperty("apiVersion");
    fetchMock.mockRestore();
  });

  it("stops a running chat by chat id", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ chatId: "chat_1", status: "stop_requested" }), { status: 200 }),
    );

    await expect(stopChat("chat_1")).resolves.toEqual({ chatId: "chat_1", status: "stop_requested" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/rest/chatbi/v1/chat/chat_1/stop",
      expect.objectContaining({ method: "POST" }),
    );
    fetchMock.mockRestore();
  });
});
