import { Link } from "react-router-dom";

import { EmptyState } from "../shared/ui/EmptyState";
import { PageSection } from "../shared/ui/PageSection";
import { SurfaceCard } from "../shared/ui/SurfaceCard";

export function ReportCenterPage() {
  return (
    <div className="reports-page">
      <PageSection description="报告实例不再作为独立公开资源暴露，最终产物统一从报告中心查看。">
        <SurfaceCard>
          <EmptyState
            title="报告中心"
            description="当前版本通过对话生成报告。生成完成后，可从对话结果中的 reportId 跳转到报告详情。"
          />
          <div className="action-row action-row--compact">
            <Link className="primary-button button-link" to="/chat">
              前往对话助手
            </Link>
            <Link className="ghost-button button-link" to="/templates">
              查看模板
            </Link>
          </div>
        </SurfaceCard>
      </PageSection>
    </div>
  );
}
