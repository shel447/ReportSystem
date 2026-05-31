import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { SettingsPage } from "./SettingsPage";

function renderSettingsPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <SettingsPage />
    </QueryClientProvider>,
  );
}

describe("SettingsPage", () => {
  it("shows summarized inline feedback under actions and dismisses it automatically", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          completion: {
            base_url: "https://example.com/v1",
            model: "gpt-4o-mini",
            timeout_sec: 60,
            temperature: 0.2,
            has_api_key: true,
            masked_api_key: "sk-***",
            configured: true,
          },
          embedding: {
            base_url: "https://example.com/v1",
            model: "text-embedding-3-small",
            timeout_sec: 60,
            has_api_key: true,
            masked_api_key: "sk-***",
            configured: true,
            use_completion_auth: true,
          },
          is_ready: true,
          index_status: { ready_count: 2, error_count: 0 },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          target: "both",
          completion: { ok: true, model: "gpt-4o-mini", preview: "completion test ok" },
          embedding: { ok: true, model: "text-embedding-3-small", dimension: 1536 },
        }),
      });
    vi.stubGlobal("fetch", fetchMock);

    renderSettingsPage();

    fireEvent.click(screen.getByRole("button", { name: "测试连接" }));

    const feedback = await screen.findByTestId("settings-action-feedback");
    expect(feedback).toHaveTextContent("连接测试成功：Completion、Embedding 均可用");
    expect(screen.queryByText("操作反馈")).not.toBeInTheDocument();

    await waitFor(() => {
      expect(screen.queryByTestId("settings-action-feedback")).not.toBeInTheDocument();
    }, { timeout: 4000 });
  });
});
