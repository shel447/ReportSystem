import { parseSsePayload } from "./api";

describe("chat stream api", () => {
  it("parses sse payload into ordered chat stream events", () => {
    const events = parseSsePayload(
      [
        'event: message',
        'data: {"conversationId":"conv_1","chatId":"chat_1","eventType":"status","sequence":1,"timestamp":1,"status":"running"}',
        "",
        'event: message',
        'data: {"conversationId":"conv_1","chatId":"chat_1","eventType":"answer","sequence":2,"timestamp":2,"status":"running","delta":[{"action":"init_report","report":{"reportId":"rpt_1","title":"网络运行日报"}}]}',
        "",
      ].join("\n"),
    );

    expect(events).toHaveLength(2);
    expect(events[0].eventType).toBe("status");
    expect(events[1].delta?.[0]).toEqual({
      action: "init_report",
      report: { reportId: "rpt_1", title: "网络运行日报" },
    });
  });
});
