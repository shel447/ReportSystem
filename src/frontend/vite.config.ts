import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: [
      {
        find: "@cloudsop/bi-engine/schema",
        replacement: new URL("./vendor/bi-engine/packages/bi-engine/src/schema/index.ts", import.meta.url).pathname,
      },
      {
        find: "@cloudsop/bi-engine",
        replacement: new URL("./vendor/bi-engine/packages/bi-engine/src/index.ts", import.meta.url).pathname,
      },
      {
        find: "@cloudsop/bi-designer",
        replacement: new URL("./vendor/bi-engine/packages/bi-designer/src/index.ts", import.meta.url).pathname,
      },
      {
        find: "@cloudsop/bi-signal/react",
        replacement: new URL("./vendor/bi-engine/packages/signal/src/react.ts", import.meta.url).pathname,
      },
      {
        find: "@cloudsop/bi-signal",
        replacement: new URL("./vendor/bi-engine/packages/signal/src/index.ts", import.meta.url).pathname,
      },
    ],
  },
  server: {
    proxy: {
      "/rest": {
        target: "http://127.0.0.1:8300",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    globals: true,
    include: ["src/**/*.test.{ts,tsx}"],
    exclude: ["vendor/**"],
  },
});
