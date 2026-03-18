import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createDocument, fetchDocuments } from "../entities/documents/api";
import type { ReportDocument } from "../entities/documents/types";
import { fetchInstance, fetchInstances, regenerateSection } from "../entities/instances/api";
import type { InstanceSection } from "../entities/instances/types";
import { fetchTemplates } from "../entities/templates/api";
import { formatDateTime, formatFileSize, prettyJson } from "../shared/utils/format";
import { EmptyState } from "../shared/ui/EmptyState";
import { PageSection } from "../shared/ui/PageSection";
import { StatusBanner } from "../shared/ui/StatusBanner";
import { SurfaceCard } from "../shared/ui/SurfaceCard";

export function InstancesPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [latestDocument, setLatestDocument] = useState<ReportDocument | null>(null);

  const instancesQuery = useQuery({
    queryKey: ["instances"],
    queryFn: fetchInstances,
  });
  const templatesQuery = useQuery({
    queryKey: ["templates"],
    queryFn: fetchTemplates,
  });

  useEffect(() => {
    if (!selectedId && instancesQuery.data?.length) {
      setSelectedId(instancesQuery.data[0].instance_id);
    }
  }, [instancesQuery.data, selectedId]);

  const instanceDetailQuery = useQuery({
    queryKey: ["instance-detail", selectedId],
    queryFn: () => fetchInstance(selectedId),
    enabled: Boolean(selectedId),
  });
  const documentsQuery = useQuery({
    queryKey: ["documents", selectedId],
    queryFn: () => fetchDocuments(selectedId),
    enabled: Boolean(selectedId),
  });

  useEffect(() => {
    const latest = documentsQuery.data && documentsQuery.data.length > 0 ? documentsQuery.data[0] : null;
    setLatestDocument(latest);
  }, [documentsQuery.data]);

  const regenerateMutation = useMutation({
    mutationFn: ({ instanceId, sectionIndex }: { instanceId: string; sectionIndex: number }) =>
      regenerateSection(instanceId, sectionIndex),
    onSuccess: async (updated) => {
      setErrorMessage("");
      queryClient.setQueryData(["instance-detail", updated.instance_id], updated);
      await queryClient.invalidateQueries({ queryKey: ["instances"] });
    },
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : "章节重生成失败。");
    },
  });

  const documentMutation = useMutation({
    mutationFn: (instanceId: string) => createDocument(instanceId),
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

  const currentInstance = instanceDetailQuery.data ?? instancesQuery.data?.find((item) => item.instance_id === selectedId);
  const templateName = currentInstance ? templateNameMap.get(currentInstance.template_id) ?? currentInstance.template_id : "";

  return (
    <div className="instances-page">
      <PageSection
        title="报告实例"
        description="统一查看实例状态、章节证据链路与 Markdown 文档产物。"
      >
        {errorMessage ? (
          <StatusBanner tone="warning" title="操作未完成">
            {errorMessage}
          </StatusBanner>
        ) : null}

        <div className="split-layout">
          <SurfaceCard className="split-layout__sidebar">
            <div className="list-header">
              <div>
                <p className="section-kicker">Instances</p>
                <h3>实例列表</h3>
              </div>
              <span className="inline-badge">{instancesQuery.data?.length ?? 0}</span>
            </div>
            <div className="list-stack">
              {instancesQuery.data?.map((instance) => (
                <button
                  key={instance.instance_id}
                  className={`list-item${selectedId === instance.instance_id ? " active" : ""}`}
                  type="button"
                  onClick={() => setSelectedId(instance.instance_id)}
                >
                  <strong>{templateNameMap.get(instance.template_id) ?? instance.template_id}</strong>
                  <span>{instance.status} / {formatDateTime(instance.updated_at)}</span>
                </button>
              ))}
              {!instancesQuery.data?.length && !instancesQuery.isLoading ? (
                <EmptyState title="暂无实例" description="在对话助手中完成参数确认后，会自动生成实例。" />
              ) : null}
            </div>
          </SurfaceCard>

          <div className="split-layout__content">
            {!currentInstance ? (
              <SurfaceCard>
                <EmptyState title="请选择实例" description="左侧选择实例后查看章节明细与文档。" />
              </SurfaceCard>
            ) : (
              <>
                <SurfaceCard>
                  <div className="list-header">
                    <div>
                      <p className="section-kicker">Instance Detail</p>
                      <h3>{templateName}</h3>
                      <p className="muted-text">
                        {currentInstance.instance_id} / 更新于 {formatDateTime(currentInstance.updated_at)}
                      </p>
                    </div>
                    <span className="status-chip">{currentInstance.status}</span>
                  </div>

                  <div className="detail-grid">
                    <div className="detail-block">
                      <span>创建时间</span>
                      <strong>{formatDateTime(currentInstance.created_at)}</strong>
                    </div>
                    <div className="detail-block">
                      <span>模板 ID</span>
                      <strong>{currentInstance.template_id}</strong>
                    </div>
                    <div className="detail-block detail-block--wide">
                      <span>输入参数</span>
                      <pre>{prettyJson(currentInstance.input_params ?? {})}</pre>
                    </div>
                  </div>

                  <div className="action-row">
                    <button
                      className="primary-button"
                      type="button"
                      onClick={() => documentMutation.mutate(currentInstance.instance_id)}
                    >
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
                        onRegenerate={() =>
                          regenerateMutation.mutate({
                            instanceId: currentInstance.instance_id,
                            sectionIndex: index,
                          })
                        }
                      />
                    ))}
                    {!currentInstance.outline_content?.length ? (
                      <EmptyState title="暂无章节" description="当前实例还没有可展示的章节内容。" />
                    ) : null}
                  </div>
                </SurfaceCard>
              </>
            )}
          </div>
        </div>
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
        <div className="section-panel__meta">
          <span className="status-chip">{section.status ?? "unknown"}</span>
          <span className="status-chip status-chip--soft">{section.data_status ?? "unknown"}</span>
        </div>
      </summary>
      <div className="section-panel__body">
        <div className="action-row">
          <button className="secondary-button" type="button" onClick={onRegenerate}>
            重生成章节
          </button>
        </div>
        <article className="markdown-preview">{section.content || "该章节暂无正文。"}</article>
        <div className="debug-block">
          <h4>调试信息</h4>
          <pre>{prettyJson(section.debug ?? {})}</pre>
        </div>
      </div>
    </details>
  );
}
