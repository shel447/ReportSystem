import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { createDocument, fetchDocuments } from "../entities/documents/api";
import type { ReportDocument } from "../entities/documents/types";
import { fetchInstance, regenerateSection } from "../entities/instances/api";
import type { InstanceSection } from "../entities/instances/types";
import { fetchTemplates } from "../entities/templates/api";
import { formatDateTime, formatFileSize, prettyJson } from "../shared/utils/format";
import { DetailPageLayout } from "../shared/layouts/DetailPageLayout";
import { PageIntroBar } from "../shared/layouts/PageIntroBar";
import { EmptyState } from "../shared/ui/EmptyState";
import { PageSection } from "../shared/ui/PageSection";
import { StatusBanner } from "../shared/ui/StatusBanner";
import { SurfaceCard } from "../shared/ui/SurfaceCard";

export function InstanceDetailPage() {
  const queryClient = useQueryClient();
  const { instanceId } = useParams<{ instanceId: string }>();
  const [errorMessage, setErrorMessage] = useState("");
  const [latestDocument, setLatestDocument] = useState<ReportDocument | null>(null);

  const instanceDetailQuery = useQuery({
    queryKey: ["instance-detail", instanceId],
    queryFn: () => fetchInstance(instanceId!),
    enabled: Boolean(instanceId),
  });
  const documentsQuery = useQuery({
    queryKey: ["documents", instanceId],
    queryFn: () => fetchDocuments(instanceId),
    enabled: Boolean(instanceId),
  });
  const templatesQuery = useQuery({
    queryKey: ["templates"],
    queryFn: fetchTemplates,
  });

  useEffect(() => {
    const latest = documentsQuery.data && documentsQuery.data.length > 0 ? documentsQuery.data[0] : null;
    setLatestDocument(latest);
  }, [documentsQuery.data]);

  const regenerateMutation = useMutation({
    mutationFn: ({ sectionIndex }: { sectionIndex: number }) => regenerateSection(instanceId!, sectionIndex),
    onSuccess: async (updated) => {
      setErrorMessage("");
      queryClient.setQueryData(["instance-detail", updated.instance_id], updated);
    },
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : "章节重生成失败。");
    },
  });

  const documentMutation = useMutation({
    mutationFn: () => createDocument(instanceId!),
    onSuccess: async (document) => {
      setErrorMessage("");
      setLatestDocument(document);
      queryClient.setQueryData(["documents", document.instance_id], (current: ReportDocument[] | undefined) => [
        document,
        ...(current ?? []),
      ]);
    },
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : "文档生成失败。");
    },
  });

  const templateNameMap = useMemo(() => {
    const entries = templatesQuery.data ?? [];
    return new Map(entries.map((item) => [item.template_id, item.name]));
  }, [templatesQuery.data]);

  const currentInstance = instanceDetailQuery.data;
  const templateName = currentInstance
    ? templateNameMap.get(currentInstance.template_id) ?? currentInstance.template_id
    : "";

  return (
    <div className="instance-detail-page">
      <PageSection description="查看实例详情、章节内容与 Markdown 文档产物。">
        {errorMessage ? (
          <StatusBanner tone="warning" title="操作未完成">
            {errorMessage}
          </StatusBanner>
        ) : null}

        {!currentInstance ? (
          <EmptyState title="实例加载中" description="正在获取实例详情。" />
        ) : (
          <DetailPageLayout
            intro={
              <PageIntroBar
                eyebrow="Instance Detail"
                description={templateName}
                badge={currentInstance.status}
                actions={
                  <Link className="ghost-button button-link" to="/instances">
                    返回列表
                  </Link>
                }
              />
            }
            summary={
              <SurfaceCard className="summary-strip">
                <div className="summary-strip__item">
                  <span>创建时间</span>
                  <strong>{formatDateTime(currentInstance.created_at)}</strong>
                </div>
                <div className="summary-strip__item">
                  <span>更新时间</span>
                  <strong>{formatDateTime(currentInstance.updated_at)}</strong>
                </div>
                <div className="summary-strip__item">
                  <span>模板 ID</span>
                  <strong>{currentInstance.template_id}</strong>
                </div>
                <div className="summary-strip__item">
                  <span>章节数</span>
                  <strong>{currentInstance.outline_content?.length ?? 0}</strong>
                </div>
              </SurfaceCard>
            }
            content={
              <div className="instance-detail-grid">
                <SurfaceCard>
                  <div className="list-header">
                    <div>
                      <p className="section-kicker">Input Parameters</p>
                      <h3>输入参数</h3>
                    </div>
                  </div>
                  <div className="detail-block detail-block--wide">
                    <pre>{prettyJson(currentInstance.input_params ?? {})}</pre>
                  </div>
                </SurfaceCard>

                <SurfaceCard>
                  <div className="list-header">
                    <div>
                      <p className="section-kicker">Documents</p>
                      <h3>文档产物</h3>
                    </div>
                  </div>
                  <div className="action-row action-row--compact">
                    <button className="primary-button" type="button" onClick={() => documentMutation.mutate()}>
                      {documentMutation.isPending ? "生成中..." : "生成 Markdown"}
                    </button>
                    {latestDocument?.download_url ? (
                      <a className="secondary-button button-link" href={latestDocument.download_url}>
                        下载最新 Markdown
                      </a>
                    ) : null}
                  </div>
                  {latestDocument ? (
                    <p className="muted-text">
                      最新文档：{latestDocument.file_name} / {formatFileSize(latestDocument.file_size)}
                    </p>
                  ) : null}
                </SurfaceCard>

                <SurfaceCard>
                  <div className="list-header">
                    <div>
                      <p className="section-kicker">Sections</p>
                      <h3>章节详情</h3>
                    </div>
                  </div>

                  <div className="accordion-stack">
                    {(currentInstance.outline_content ?? []).map((section, index) => (
                      <SectionPanel
                        key={`${section.title}-${index}`}
                        section={section}
                        index={index}
                        onRegenerate={() => regenerateMutation.mutate({ sectionIndex: index })}
                      />
                    ))}
                    {!currentInstance.outline_content?.length ? (
                      <EmptyState title="暂无章节" description="当前实例还没有可展示的章节内容。" />
                    ) : null}
                  </div>
                </SurfaceCard>
              </div>
            }
          />
        )}
      </PageSection>
    </div>
  );
}

function SectionPanel({
  section,
  index,
  onRegenerate,
}: {
  section: InstanceSection;
  index: number;
  onRegenerate: () => void;
}) {
  return (
    <details className="section-panel" open={index === 0}>
      <summary>
        <div>
          <strong>{section.title || `章节 ${index + 1}`}</strong>
          <p>{section.description || "无章节描述"}</p>
        </div>
        {section.status || section.data_status ? (
          <div className="section-panel__meta">
            {section.status ? <span className="status-chip">{formatSectionStatus(section.status)}</span> : null}
            {section.data_status ? (
              <span className="status-chip status-chip--soft">{formatDataStatus(section.data_status)}</span>
            ) : null}
          </div>
        ) : null}
      </summary>
      <div className="section-panel__body">
        <div className="action-row action-row--compact">
          <button className="secondary-button" type="button" onClick={onRegenerate}>
            重生成章节
          </button>
        </div>
        <article className="markdown-preview">{section.content || "该章节暂无正文。"}</article>
        <details className="debug-disclosure">
          <summary>查看调试信息</summary>
          <div className="debug-block">
            <pre>{prettyJson(section.debug ?? {})}</pre>
          </div>
        </details>
      </div>
    </details>
  );
}

function formatSectionStatus(status: string) {
  if (status === "generated") {
    return "已生成";
  }
  if (status === "failed") {
    return "生成失败";
  }
  return status;
}

function formatDataStatus(status: string) {
  if (status === "success") {
    return "查询成功";
  }
  if (status === "failed") {
    return "查询失败";
  }
  return status;
}
