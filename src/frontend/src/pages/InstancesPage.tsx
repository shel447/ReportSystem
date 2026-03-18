import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { fetchInstances } from "../entities/instances/api";
import { fetchTemplates } from "../entities/templates/api";
import { formatDateTime } from "../shared/utils/format";
import { EmptyState } from "../shared/ui/EmptyState";
import { PageSection } from "../shared/ui/PageSection";
import { PageIntroBar } from "../shared/layouts/PageIntroBar";
import { ListPageLayout } from "../shared/layouts/ListPageLayout";

export function InstancesPage() {
  const instancesQuery = useQuery({
    queryKey: ["instances"],
    queryFn: fetchInstances,
  });
  const templatesQuery = useQuery({
    queryKey: ["templates"],
    queryFn: fetchTemplates,
  });

  const templateNameMap = useMemo(() => {
    const entries = templatesQuery.data ?? [];
    return new Map(entries.map((item) => [item.template_id, item.name]));
  }, [templatesQuery.data]);

  return (
    <div className="instances-page">
      <PageSection description="浏览报告实例，并进入详情页查看章节与文档产物。">
        <ListPageLayout
          intro={
            <PageIntroBar
              eyebrow="Instances"
              description="实例列表只负责浏览和进入，章节详情与文档操作放在独立详情页。"
              badge={`${instancesQuery.data?.length ?? 0} 个实例`}
            />
          }
          content={
            instancesQuery.data?.length ? (
              <div className="instance-catalog-grid">
                {instancesQuery.data.map((instance) => (
                  <Link
                    key={instance.instance_id}
                    className="instance-card"
                    to={`/instances/${instance.instance_id}`}
                  >
                    <div className="instance-card__header">
                      <strong>{templateNameMap.get(instance.template_id) ?? instance.template_id}</strong>
                      <span className="status-chip">{instance.status}</span>
                    </div>
                    <p>更新时间：{formatDateTime(instance.updated_at)}</p>
                    <div className="instance-card__meta">
                      <span>{instance.instance_id}</span>
                      <span>{Object.keys(instance.input_params ?? {}).length} 个输入参数</span>
                    </div>
                  </Link>
                ))}
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
