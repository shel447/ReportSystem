import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { fetchReportView } from "../entities/reports/api";
import { DetailPageLayout } from "../shared/layouts/DetailPageLayout";
import { PageIntroBar } from "../shared/layouts/PageIntroBar";
import { EmptyState } from "../shared/ui/EmptyState";
import { PageSection } from "../shared/ui/PageSection";
import { SurfaceCard } from "../shared/ui/SurfaceCard";
import { prettyJson } from "../shared/utils/format";

export function ReportDetailPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const reportQuery = useQuery({
    queryKey: ["report-view", reportId],
    queryFn: () => fetchReportView(reportId!),
    enabled: Boolean(reportId),
  });

  const report = reportQuery.data;

  return (
    <div className="report-detail-page">
      <PageSection description="报告详情聚合展示最终模板实例与生成结果。">
        {!report ? (
          <EmptyState title="报告加载中" description="正在获取报告详情。" />
        ) : (
          <DetailPageLayout
            intro={(
              <PageIntroBar
                eyebrow="Reports"
                description={report.template_instance?.base_template?.name || report.reportId}
                badge={report.status}
                actions={(
                  <>
                    <Link className="ghost-button button-link" to="/reports">
                      返回报告中心
                    </Link>
                    <Link className="secondary-button button-link" to="/chat">
                      打开对话助手
                    </Link>
                  </>
                )}
              />
            )}
            summary={(
              <SurfaceCard className="summary-strip">
                <div className="summary-strip__item">
                  <span>报告 ID</span>
                  <strong>{report.reportId}</strong>
                </div>
                <div className="summary-strip__item">
                  <span>模板</span>
                  <strong>{report.template_instance?.base_template?.name || "未命名模板"}</strong>
                </div>
                <div className="summary-strip__item">
                  <span>分类</span>
                  <strong>{report.template_instance?.base_template?.category || "未分类"}</strong>
                </div>
              </SurfaceCard>
            )}
            content={(
              <div className="template-detail-grid">
                <SurfaceCard>
                  <div className="list-header">
                    <div>
                      <p className="section-kicker">Template Instance</p>
                      <h3>模板实例</h3>
                    </div>
                  </div>
                  <div className="detail-block detail-block--wide">
                    <pre>{prettyJson(report.template_instance ?? {})}</pre>
                  </div>
                </SurfaceCard>

                <SurfaceCard>
                  <div className="list-header">
                    <div>
                      <p className="section-kicker">Generated Content</p>
                      <h3>生成结果</h3>
                    </div>
                  </div>
                  <div className="detail-block detail-block--wide">
                    <pre>{prettyJson(report.generated_content ?? {})}</pre>
                  </div>
                </SurfaceCard>
              </div>
            )}
          />
        )}
      </PageSection>
    </div>
  );
}
