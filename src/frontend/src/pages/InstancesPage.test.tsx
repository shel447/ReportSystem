import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";

import { InstancesPage } from "./InstancesPage";

function renderInstancesPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/instances"]}>
        <Routes>
          <Route path="/instances" element={<InstancesPage />} />
          <Route path="/instances/:instanceId" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location-probe">{`${location.pathname}${location.search}`}</div>;
}

describe("InstancesPage", () => {
  it("loads instance cards without embedding section detail", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/rest/chatbi/v1/instances") {
        return {
          ok: true,
          json: async () => [
            {
              instance_id: "inst-1",
              template_id: "tpl-1",
              status: "generated",
              input_params: { report_date: "2026-03-18" },
              outline_content: [],
              report_time: "2026-03-31T08:00:00",
              report_time_source: "scheduled_execution",
              created_at: "2026-03-18T10:00:00",
              updated_at: "2026-03-18T10:01:00",
              has_generation_baseline: true,
              supports_update_chat: true,
              supports_fork_chat: true,
            },
          ],
        };
      }
      if (url === "/rest/chatbi/v1/instances/inst-1/fork-sources") {
        return {
          ok: true,
          json: async () => [
            { message_id: "msg-1", role: "assistant", preview: "请输入参数", action_type: "ask_param" },
          ],
        };
      }
      if (url === "/rest/chatbi/v1/instances/inst-1/fork-chat") {
        return {
          ok: true,
          json: async () => ({ session_id: "sess-forked" }),
        };
      }
      if (url === "/rest/chatbi/v1/templates") {
        return {
          ok: true,
          json: async () => [
            {
              template_id: "tpl-1",
              name: "设备巡检报告",
              description: "巡检模板",
              report_type: "daily",
              scenario: "集团",
              type: "巡检",
              scene: "总部",
            },
          ],
        };
      }
      throw new Error(`Unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderInstancesPage();

    expect(await screen.findByRole("link", { name: /设备巡检报告/ })).toHaveAttribute(
      "href",
      "/instances/inst-1",
    );
    expect(screen.getByText(/报告时间/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "更新" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Fork" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "生成 Markdown" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "更新" }));

    await waitFor(() => {
      expect(screen.getByTestId("location-probe")).toHaveTextContent("/instances/inst-1?intent=update");
    });
  });
});
