import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { fetchTemplates } from "../entities/templates/api";
import { EmptyState } from "../shared/ui/EmptyState";
import { PageSection } from "../shared/ui/PageSection";
import { PageIntroBar } from "../shared/layouts/PageIntroBar";
import { ListPageLayout } from "../shared/layouts/ListPageLayout";

export function TemplatesPage() {
  const templatesQuery = useQuery({
    queryKey: ["templates"],
    queryFn: fetchTemplates,
  });

  return (
    <div className="templates-page">
      <PageSection description="浏览模板目录并进入独立详情页进行配置。">
        <ListPageLayout
          intro={
            <PageIntroBar
              eyebrow="Template Catalog"
              description="模板列表只负责浏览和进入，配置工作在独立详情页中完成。"
              actions={
                <Link className="primary-button button-link" to="/templates/new">
                  新建模板
                </Link>
              }
              badge={`${templatesQuery.data?.length ?? 0} 个模板`}
            />
          }
          content={
            templatesQuery.data?.length ? (
              <div className="template-catalog-grid">
                {templatesQuery.data.map((template) => (
                  <Link
                    key={template.template_id}
                    className="template-card"
                    to={`/templates/${template.template_id}`}
                  >
                    <div className="template-card__header">
                      <strong>{template.name}</strong>
                      <span className="status-chip status-chip--soft">{template.report_type}</span>
                    </div>
                    <p>{template.description || "暂无模板描述"}</p>
                    <div className="template-card__meta">
                      {[template.type, template.scene || template.scenario].filter(Boolean).map((item) => (
                        <span key={item}>{item}</span>
                      ))}
                    </div>
                    <div className="template-card__meta">
                      <span>{template.parameter_count ?? 0} 个参数</span>
                      <span>{template.top_level_section_count ?? 0} 个顶层章节</span>
                      {template.schema_version ? <span>{template.schema_version}</span> : null}
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              !templatesQuery.isLoading && (
                <EmptyState title="暂无模板" description="点击“新建模板”，开始录入新版模板定义。" />
              )
            )
          }
        />
      </PageSection>
    </div>
  );
}
