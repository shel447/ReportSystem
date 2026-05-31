// @vitest-environment node

import config from "../../vite.config";

describe("vite dev proxy", () => {
  test("proxies rest api routes to backend server", () => {
    expect(config.server?.proxy?.["/rest"]).toEqual(
      expect.objectContaining({
        target: "http://127.0.0.1:8300",
        changeOrigin: true,
      }),
    );
  });
});
