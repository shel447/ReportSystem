import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchDocuments } from "../entities/documents/api";
import { fetchTemplates } from "../entities/templates/api";
import { ListPageLayout } from "../shared/layouts/ListPageLayout";
import { PageIntroBar } from "../shared/layouts/PageIntroBar";
import { formatDateTime, formatFileSize } from "../shared/utils/format";
import { EmptyState } from "../shared/ui/EmptyState";
import { PageSection } from "../shared/ui/PageSection";
import { SurfaceCard } from "../shared/ui/SurfaceCard";

export function DocumentsPage() {
  const documentsQuery = useQuery({
    queryKey: ["documents", "all"],
    queryFn: () => fetchDocuments(),
  });
  const templatesQuery = useQuery({
    queryKey: ["templates"],
    queryFn: fetchTemplates,
  });

  const templateNameMap = useMemo(
    () => new Map((templatesQuery.data ?? []).map((item) => [item.template_id, item.name])),
    [templatesQuery.data],
  );

  return (
    <div className="documents-page">
      <PageSection description="集中查看系统内已生成的 Markdown 文档并下载。">
        <ListPageLayout
          intro={
            <PageIntroBar
              eyebrow="Generated Documents"
              description="统一收拢所有已生成文档，便于按模板和时间快速查看。"
              badge={`${documentsQuery.data?.length ?? 0} 份文档`}
            />
          }
          content={
            <SurfaceCard>
              <div className="table-shell">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>模板</th>
                      <th>文件</th>
                      <th>大小</th>
                      <th>生成时间</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(documentsQuery.data ?? []).map((document) => (
                      <tr key={document.document_id}>
                        <td>{templateNameMap.get(document.template_id) ?? document.template_id}</td>
                        <td>{document.file_name}</td>
                        <td>{formatFileSize(document.file_size)}</td>
                        <td>{formatDateTime(document.created_at)}</td>
                        <td>
                          <a className="secondary-button button-link" href={document.download_url}>
                            下载
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!documentsQuery.data?.length && !documentsQuery.isLoading ? (
                  <EmptyState title="暂无文档" description="先在对话或实例页生成 Markdown 文档。" />
                ) : null}
              </div>
            </SurfaceCard>
          }
        />
      </PageSection>
    </div>
  );
}
