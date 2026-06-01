import { chatbiPath, devPath, requestJson } from "./http";

describe("requestJson", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it("injects explicitly configured development user header for chatbi routes", async () => {
    vi.stubEnv("VITE_DEV_USER_ID", "local-user");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await requestJson(chatbiPath("/templates"));

    const [, options] = fetchMock.mock.calls[0];
    expect(new Headers(options.headers).get("X-User-Id")).toBe("local-user");
  });

  it("does not invent a default user header", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await requestJson(chatbiPath("/templates"));

    const [, options] = fetchMock.mock.calls[0];
    expect(new Headers(options.headers).get("X-User-Id")).toBeNull();
  });

  it("does not inject user header for dev routes", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await requestJson(devPath("/system-settings"));

    const [, options] = fetchMock.mock.calls[0];
    expect(new Headers(options?.headers).get("X-User-Id")).toBeNull();
  });
});
