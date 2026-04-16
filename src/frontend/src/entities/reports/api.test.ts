import { fetchReportView } from "./api";

describe("reports api", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("calls report view endpoint with encoded id", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ reportId: "rpt-1", status: "completed", template_instance: { id: "ti-1" }, generated_content: {} }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchReportView("rpt/1");

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/rest/chatbi/v1/reports/rpt%2F1");
    expect(new Headers(options.headers).get("X-User-Id")).toBe("default");
  });
});
