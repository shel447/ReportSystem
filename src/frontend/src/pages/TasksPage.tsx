import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchTasks, pauseTask, resumeTask, runTaskNow } from "../entities/tasks/api";
import { fetchTemplates } from "../entities/templates/api";
import { ListPageLayout } from "../shared/layouts/ListPageLayout";
import { PageIntroBar } from "../shared/layouts/PageIntroBar";
import { formatDateTime } from "../shared/utils/format";
import { EmptyState } from "../shared/ui/EmptyState";
import { PageSection } from "../shared/ui/PageSection";
import { StatusBanner } from "../shared/ui/StatusBanner";
import { SurfaceCard } from "../shared/ui/SurfaceCard";

export function TasksPage() {
  const queryClient = useQueryClient();
  const [message, setMessage] = useState("");
  const tasksQuery = useQuery({
    queryKey: ["tasks"],
    queryFn: fetchTasks,
  });
  const templatesQuery = useQuery({
    queryKey: ["templates"],
    queryFn: fetchTemplates,
  });

  const templateNameMap = useMemo(
    () => new Map((templatesQuery.data ?? []).map((item) => [item.template_id, item.name])),
    [templatesQuery.data],
  );

  const actionMutation = useMutation({
    mutationFn: async ({ taskId, action }: { taskId: string; action: "run" | "pause" | "resume" }) => {
      if (action === "run") {
        return runTaskNow(taskId);
      }
      if (action === "pause") {
        return pauseTask(taskId);
      }
      return resumeTask(taskId);
    },
    onSuccess: async (result) => {
      setMessage(typeof result?.message === "string" ? result.message : "任务操作已执行。");
      await queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: (error) => {
      setMessage(error instanceof Error ? error.message : "任务操作失败。");
    },
  });

  return (
    <div className="tasks-page">
      <PageSection description="查看任务状态，并直接执行运行、暂停和恢复。">
        {message ? (
          <StatusBanner tone="info" title="任务反馈">
            {message}
          </StatusBanner>
        ) : null}

        <ListPageLayout
          intro={
            <PageIntroBar
              eyebrow="Scheduled Tasks"
              description="统一查看任务运行情况，并在表格内直接执行运行、暂停或恢复。"
              badge={`${tasksQuery.data?.length ?? 0} 个任务`}
            />
          }
          content={
            <SurfaceCard>
              <div className="table-shell">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>任务名称</th>
                      <th>模板</th>
                      <th>状态</th>
                      <th>最近运行</th>
                      <th>执行情况</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(tasksQuery.data ?? []).map((task) => (
                      <tr key={task.task_id}>
                        <td>{task.name}</td>
                        <td>{templateNameMap.get(task.template_id) ?? task.template_id}</td>
                        <td>{task.status}</td>
                        <td>{formatDateTime(task.last_run_at)}</td>
                        <td>
                          {task.success_runs}/{task.total_runs}
                        </td>
                        <td>
                          <div className="action-row action-row--compact">
                            <button
                              className="secondary-button"
                              type="button"
                              onClick={() => actionMutation.mutate({ taskId: task.task_id, action: "run" })}
                            >
                              立即运行
                            </button>
                            {task.enabled ? (
                              <button
                                className="ghost-button ghost-button--inline"
                                type="button"
                                onClick={() => actionMutation.mutate({ taskId: task.task_id, action: "pause" })}
                              >
                                暂停
                              </button>
                            ) : (
                              <button
                                className="ghost-button ghost-button--inline"
                                type="button"
                                onClick={() => actionMutation.mutate({ taskId: task.task_id, action: "resume" })}
                              >
                                恢复
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!tasksQuery.data?.length && !tasksQuery.isLoading ? (
                  <EmptyState title="暂无定时任务" description="任务创建能力保留不变，这里统一承接查看与运行。" />
                ) : null}
              </div>
            </SurfaceCard>
          }
        />
      </PageSection>
    </div>
  );
}
