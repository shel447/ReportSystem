import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";

import {
  fetchInstanceForkSources,
  fetchInstances,
  forkInstanceChat,
} from "../entities/instances/api";
import type { InstanceForkSource } from "../entities/instances/types";
import { fetchTemplates } from "../entities/templates/api";
import { formatDateTime } from "../shared/utils/format";
import { EmptyState } from "../shared/ui/EmptyState";
import { PageSection } from "../shared/ui/PageSection";
import { PageIntroBar } from "../shared/layouts/PageIntroBar";
import { ListPageLayout } from "../shared/layouts/ListPageLayout";

export function InstancesPage() {
  const navigate = useNavigate();
  const [forkPicker, setForkPicker] = useState<{
    instanceId: string;
    sources: InstanceForkSource[];
  } | null>(null);

  const instancesQuery = useQuery({
    queryKey: ["instances"],
    queryFn: fetchInstances,
  });
  const templatesQuery = useQuery({
    queryKey: ["templates"],
    queryFn: fetchTemplates,
  });

  const forkSourcesMutation = useMutation({
    mutationFn: fetchInstanceForkSources,
    onSuccess: (sources, instanceId) => {
      setForkPicker({ instanceId, sources });
    },
  });

  const forkMutation = useMutation({
    mutationFn: ({ instanceId, sourceMessageId }: { instanceId: string; sourceMessageId: string }) =>
      forkInstanceChat(instanceId, sourceMessageId),
    onSuccess: (payload) => {
      setForkPicker(null);
      navigate(`/chat?session_id=${payload.session_id}`);
    },
  });

  const templateNameMap = useMemo(() => {
    const entries = templatesQuery.data ?? [];
    return new Map(entries.map((item) => [item.template_id, item.name]));
  }, [templatesQuery.data]);

  return (
    <div className="instances-page">
      <PageSection description="浏览报告实例，并从生成基线继续更新或从来源对话节点分支。">
        <ListPageLayout
          intro={
            <PageIntroBar
              eyebrow="Instances"
              description="实例列表负责浏览、继续更新和从来源对话分支，章节详情与文档操作放在独立详情页。"
              badge={`${instancesQuery.data?.length ?? 0} 个实例`}
            />
          }
          content={
            instancesQuery.data?.length ? (
              <div className="instance-catalog-grid">
                {instancesQuery.data.map((instance) => {
                  const isForkPickerOpen = forkPicker?.instanceId === instance.instance_id;
                  return (
                    <article key={instance.instance_id} className="instance-card">
                      <Link className="instance-card__link" to={`/instances/${instance.instance_id}`}>
                        <div className="instance-card__header">
                          <strong>{templateNameMap.get(instance.template_id) ?? instance.template_id}</strong>
                          <span className="status-chip">{instance.status}</span>
                        </div>
                        <p>{instance.report_time ? `报告时间：${formatDateTime(instance.report_time)}` : `更新时间：${formatDateTime(instance.updated_at)}`}</p>
                        <div className="instance-card__meta">
                          <span>{instance.instance_id}</span>
                          <span>{Object.keys(instance.input_params ?? {}).length} 个输入参数</span>
                        </div>
                      </Link>
                      {instance.supports_update_chat || instance.supports_fork_chat ? (
                        <div className="action-row action-row--compact instance-card__actions">
                          {instance.supports_update_chat ? (
                            <button
                              className="ghost-button"
                              type="button"
                              onClick={() => navigate(`/instances/${instance.instance_id}?intent=update`)}
                            >
                              更新
                            </button>
                          ) : null}
                          {instance.supports_fork_chat ? (
                            <button
                              className="ghost-button"
                              type="button"
                              onClick={() => {
                                if (isForkPickerOpen) {
                                  setForkPicker(null);
                                  return;
                                }
                                forkSourcesMutation.mutate(instance.instance_id);
                              }}
                            >
                              Fork
                            </button>
                          ) : null}
                        </div>
                      ) : null}
                      {isForkPickerOpen ? (
                        <div className="instance-fork-picker">
                          <p className="muted-text">选择来源消息节点</p>
                          <div className="instance-fork-picker__list">
                            {forkPicker.sources.map((source) => (
                              <button
                                key={source.message_id}
                                type="button"
                                className="instance-fork-picker__item"
                                onClick={() =>
                                  forkMutation.mutate({
                                    instanceId: instance.instance_id,
                                    sourceMessageId: source.message_id,
                                  })
                                }
                              >
                                <strong>{source.role === "assistant" ? "助手" : "我"}</strong>
                                <span>{source.preview}</span>
                              </button>
                            ))}
                          </div>
                        </div>
                      ) : null}
                    </article>
                  );
                })}
              </div>
            ) : (
              !instancesQuery.isLoading && (
                <EmptyState title="暂无实例" description="在对话助手中完成参数确认后，会自动生成实例。" />
              )
            )
          }
        />
      </PageSection>
    </div>
  );
}
