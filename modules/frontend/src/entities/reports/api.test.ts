import { fetchReport } from "./api";

describe("reports api", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it("calls report endpoint with encoded id and configured development user header", async () => {
    vi.stubEnv("VITE_DEV_USER_ID", "local-report-user");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ reportId: "rpt-1", status: "available", answerType: "REPORT", answer: {} }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchReport("rpt/1");

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/rest/chatbi/v1/reports/rpt%2F1");
    expect(new Headers(options.headers).get("X-User-Id")).toBe("local-report-user");
  });
});
