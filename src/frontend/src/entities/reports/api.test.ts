import { fetchReport } from "./api";

describe("reports api", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("calls report endpoint with encoded id and user header", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ reportId: "rpt-1", status: "available", answerType: "REPORT", answer: {} }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchReport("rpt/1");

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/rest/chatbi/v1/reports/rpt%2F1");
    expect(new Headers(options.headers).get("X-User-Id")).toBe("default");
  });
});
