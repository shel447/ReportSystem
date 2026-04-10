import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import type { OutlineNode } from "../entities/chat/types";
import { createDocument, fetchDocuments } from "../entities/documents/api";
import type { ReportDocument } from "../entities/documents/types";
import {
  fetchInstance,
  fetchInstanceBaseline,
  fetchInstanceForkSources,
  forkInstanceChat,
  regenerateSection,
  updateInstanceChat,
} from "../entities/instances/api";
import type { InstanceBaselineNode, InstanceForkSource, InstanceSection } from "../entities/instances/types";
import { fetchTemplates } from "../entities/templates/api";
import { OutlineTree } from "../features/chat-report-flow/components/OutlineTree";
import { formatDateTime, formatFileSize, prettyJson } from "../shared/utils/format";
import { DetailPageLayout } from "../shared/layouts/DetailPageLayout";
import { PageIntroBar } from "../shared/layouts/PageIntroBar";
import { EmptyState } from "../shared/ui/EmptyState";
import { PageSection } from "../shared/ui/PageSection";
import { StatusBanner } from "../shared/ui/StatusBanner";
import { SurfaceCard } from "../shared/ui/SurfaceCard";

export function InstanceDetailPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { instanceId } = useParams<{ instanceId: string }>();
  const [errorMessage, setErrorMessage] = useState("");
  const [latestDocument, setLatestDocument] = useState<ReportDocument | null>(null);
  const [showBaseline, setShowBaseline] = useState(false);
  const [showForkPicker, setShowForkPicker] = useState(false);
  const intent = useMemo(() => new URLSearchParams(location.search).get("intent") ?? "", [location.search]);

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
  const baselineQuery = useQuery({
    queryKey: ["instance-baseline", instanceId],
    queryFn: () => fetchInstanceBaseline(instanceId!),
    enabled: Boolean(instanceId && showBaseline),
  });
  const forkSourcesQuery = useQuery({
    queryKey: ["instance-fork-sources", instanceId],
    queryFn: () => fetchInstanceForkSources(instanceId!),
    enabled: Boolean(instanceId && showForkPicker),
  });

  useEffect(() => {
    const latest = documentsQuery.data && documentsQuery.data.length > 0 ? documentsQuery.data[0] : null;
    setLatestDocument(latest);
  }, [documentsQuery.data]);

  useEffect(() => {
    if (intent === "update") {
      setShowBaseline(true);
    }
  }, [intent]);

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

  const updateChatMutation = useMutation({
    mutationFn: () => updateInstanceChat(instanceId!),
    onSuccess: (payload) => {
      navigate(`/chat?session_id=${payload.session_id}`, {
        state: { prefetchedSession: payload },
      });
    },
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : "无法打开更新会话。");
    },
  });

  const forkChatMutation = useMutation({
    mutationFn: (sourceMessageId: string) => forkInstanceChat(instanceId!, sourceMessageId),
    onSuccess: (payload) => {
      setShowForkPicker(false);
      navigate(`/chat?session_id=${payload.session_id}`);
    },
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : "无法从该节点分支。");
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
                  <div className="action-row action-row--compact">
                    {currentInstance.supports_update_chat ? (
                      <button className="ghost-button" type="button" onClick={() => setShowBaseline(true)}>
                        更新
                      </button>
                    ) : null}
                    {currentInstance.supports_fork_chat ? (
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={() => setShowForkPicker((value) => !value)}
                      >
                        Fork
                      </button>
                    ) : null}
                    <Link className="ghost-button button-link" to="/instances">
                      返回列表
                    </Link>
                  </div>
                }
              />
            }
            summary={
              <div className="summary-stack">
                <SurfaceCard className="summary-strip">
                  {currentInstance.report_time ? (
                    <div className="summary-strip__item">
                      <span>报告时间</span>
                      <strong>{formatDateTime(currentInstance.report_time)}</strong>
                    </div>
                  ) : null}
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
                {currentInstance.has_generation_baseline ? (
                  <SurfaceCard>
                    <div className="action-row action-row--compact">
                      <button className="ghost-button" type="button" onClick={() => setShowBaseline((value) => !value)}>
                        查看确认诉求
                      </button>
                    </div>
                    {showBaseline && baselineQuery.data ? (
                      <div className="detail-block detail-block--wide">
                        <p className="muted-text">更新预览：确认诉求 / 生成基线</p>
                        <div className="inline-panel">
                          <strong>已确认参数</strong>
                          <div className="reason-list">
                            {formatBaselineParams(baselineQuery.data.params_snapshot).map((item) => (
                              <span key={item}>{item}</span>
                            ))}
                          </div>
                        </div>
                        <OutlineTree mode="readonly" nodes={toOutlineNodes(baselineQuery.data.outline)} />
                        {currentInstance.supports_update_chat ? (
                          <div className="action-row action-row--compact">
                            <button
                              className="primary-button"
                              type="button"
                              onClick={() => updateChatMutation.mutate()}
                              disabled={updateChatMutation.isPending}
                            >
                              {updateChatMutation.isPending ? "正在创建会话..." : "继续到对话助手修改"}
                            </button>
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                    {showForkPicker ? (
                      <div className="instance-fork-picker">
                        <p className="muted-text">选择来源消息节点</p>
                        <div className="instance-fork-picker__list">
                          {(forkSourcesQuery.data ?? []).map((source: InstanceForkSource) => (
                            <button
                              key={source.message_id}
                              type="button"
                              className="instance-fork-picker__item"
                              onClick={() => forkChatMutation.mutate(source.message_id)}
                            >
                              <strong>{source.role === "assistant" ? "助手" : "我"}</strong>
                              <span>{source.preview}</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </SurfaceCard>
                ) : null}
              </div>
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

function formatBaselineParams(paramsSnapshot: Record<string, unknown>) {
  const entries = Object.entries(paramsSnapshot ?? {});
  if (!entries.length) {
    return ["暂无已确认参数"];
  }
  return entries.map(([key, value]) => `${key}：${formatBaselineValue(value)}`);
}

function formatBaselineValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).join("、");
  }
  if (value == null) {
    return "";
  }
  return String(value);
}

function toOutlineNodes(nodes: InstanceBaselineNode[]): OutlineNode[] {
  return (nodes ?? []).map((node) => ({
    node_id: node.node_id,
    title: node.title ?? "",
    description: node.description ?? "",
    level: node.level,
    children: toOutlineNodes(node.children ?? []),
    ...(node.display_text ? { display_text: node.display_text } : {}),
    ...(node.dynamic_meta ? { dynamic_meta: node.dynamic_meta } : {}),
    ...(typeof node.ai_generated === "boolean" ? { ai_generated: node.ai_generated } : {}),
    ...(node.node_kind ? { node_kind: node.node_kind } : {}),
    ...(node.outline_instance ? { outline_instance: node.outline_instance } : {}),
    ...(node.execution_bindings ? { execution_bindings: node.execution_bindings } : {}),
  }));
}
