import { useQuery } from "@tanstack/react-query";

import { fetchTemplateInstances } from "../entities/template-instances/api";
import { EmptyState } from "../shared/ui/EmptyState";
import { PageSection } from "../shared/ui/PageSection";
import { PageIntroBar } from "../shared/layouts/PageIntroBar";
import { ListPageLayout } from "../shared/layouts/ListPageLayout";
import { formatDateTime } from "../shared/utils/format";

const CAPTURE_STAGE_LABELS = {
  outline_saved: "已保存大纲",
  outline_confirmed: "已确认生成",
} as const;

export function TemplateInstancesPage() {
  const templateInstancesQuery = useQuery({
    queryKey: ["template-instances"],
    queryFn: fetchTemplateInstances,
  });

  return (
    <div className="template-instances-page">
      <PageSection description="浏览对话式生成流程中保存下来的模板实例快照。">
        <ListPageLayout
          intro={
            <PageIntroBar
              eyebrow="Template Instances"
              description="模板实例记录的是大纲确认阶段的中间快照，保留参数与已展开大纲的历史。"
              badge={`${templateInstancesQuery.data?.length ?? 0} 条快照`}
            />
          }
          content={
            templateInstancesQuery.data?.length ? (
              <div className="template-instance-grid">
                {templateInstancesQuery.data.map((item) => (
                  <article key={item.template_instance_id} className="template-instance-card">
                    <div className="template-instance-card__header">
                      <strong>{item.template_name}</strong>
                      <span className="status-chip">
                        {CAPTURE_STAGE_LABELS[item.capture_stage] ?? item.capture_stage}
                      </span>
                    </div>
                    <p>保存时间：{formatDateTime(item.created_at)}</p>
                    <div className="template-instance-card__meta">
                      <span>{item.param_count} 个参数</span>
                      <span>{item.outline_node_count} 个章节节点</span>
                    </div>
                    {item.outline_preview.length ? (
                      <div className="template-instance-card__preview">
                        {item.outline_preview.map((line) => (
                          <p key={`${item.template_instance_id}-${line}`}>{line}</p>
                        ))}
                      </div>
                    ) : null}
                    {item.report_instance_id ? (
                      <p className="template-instance-card__linkage">
                        关联报告实例：{item.report_instance_id}
                      </p>
                    ) : null}
                  </article>
                ))}
              </div>
            ) : (
              !templateInstancesQuery.isLoading && (
                <EmptyState
                  title="暂无模板实例"
                  description="在对话助手中保存大纲或确认生成后，这里会记录模板实例快照。"
                />
              )
            )
          }
        />
      </PageSection>
    </div>
  );
}
