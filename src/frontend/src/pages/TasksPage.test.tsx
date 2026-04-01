import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { TasksPage } from "./TasksPage";

function renderTasksPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/tasks"]}>
        <Routes>
          <Route path="/tasks" element={<TasksPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TasksPage", () => {
  it("restores task creation from an existing instance", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/rest/chatbi/v1/scheduled-tasks" && !init?.method) {
        return {
          ok: true,
          json: async () => [],
        };
      }
      if (url === "/rest/chatbi/v1/templates" && !init?.method) {
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
      if (url === "/rest/chatbi/v1/instances" && !init?.method) {
        return {
          ok: true,
          json: async () => [
            {
              instance_id: "inst-1",
              template_id: "tpl-1",
              status: "generated",
              input_params: { scene: "总部" },
              outline_content: [],
              created_at: "2026-03-31T08:00:00",
              updated_at: "2026-03-31T08:05:00",
            },
          ],
        };
      }
      if (url === "/rest/chatbi/v1/scheduled-tasks" && init?.method === "POST") {
        return {
          ok: true,
          json: async () => ({
            task_id: "task-1",
            user_id: "default",
            name: "总部巡检日报",
            description: "每日生成",
            source_instance_id: "inst-1",
            template_id: "tpl-1",
            schedule_type: "recurring",
            cron_expression: "0 8 * * *",
            enabled: true,
            auto_generate_doc: true,
            time_param_name: "report_date",
            time_format: "%Y-%m-%d",
            use_schedule_time_as_report_time: true,
            status: "active",
            total_runs: 0,
            success_runs: 0,
            created_at: "2026-03-31T09:00:00",
          }),
        };
      }
      throw new Error(`Unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderTasksPage();

    expect(await screen.findByRole("button", { name: "新建任务" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "新建任务" }));

    expect(await screen.findByRole("dialog", { name: "新建定时任务" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("任务名称"), {
      target: { value: "总部巡检日报" },
    });
    fireEvent.change(screen.getByLabelText("说明"), {
      target: { value: "每日生成" },
    });
    fireEvent.change(screen.getByLabelText("源报告实例"), {
      target: { value: "inst-1" },
    });
    fireEvent.change(screen.getByLabelText("调度方式"), {
      target: { value: "recurring" },
    });
    fireEvent.change(screen.getByLabelText("Cron 表达式"), {
      target: { value: "0 8 * * *" },
    });
    fireEvent.change(screen.getByLabelText("时间参数名"), {
      target: { value: "report_date" },
    });
    fireEvent.click(screen.getByLabelText("执行时间写入报告时间"));

    fireEvent.click(screen.getByRole("button", { name: "创建任务" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/rest/chatbi/v1/scheduled-tasks",
        expect.objectContaining({
          method: "POST",
          body: expect.any(String),
        }),
      );
    });

    const request = fetchMock.mock.calls.find(
      ([url, init]) => url === "/rest/chatbi/v1/scheduled-tasks" && init?.method === "POST",
    )?.[1];
    const payload = JSON.parse(String(request?.body ?? "{}"));
    expect(payload.source_instance_id).toBe("inst-1");
    expect(payload.template_id).toBe("tpl-1");
    expect(payload.use_schedule_time_as_report_time).toBe(true);
    expect(payload.time_param_name).toBe("report_date");
  });
});
