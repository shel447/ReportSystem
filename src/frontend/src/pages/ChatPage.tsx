import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Dispatch, MouseEvent as ReactMouseEvent, SetStateAction } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Menu, MessageSquarePlus, PanelLeftClose, PanelLeftOpen, PanelRightOpen, Send, Trash2, WandSparkles, X } from "lucide-react";
import { Link } from "react-router-dom";

import { deleteConversation, fetchConversation, fetchConversations, sendChatMessageStream } from "../entities/chat/api";
import type { ChatAsk, ChatResponse, ChatStreamDelta, ConversationDetail, ParameterValue, TemplateInstance, TemplateParameter } from "../entities/chat/types";
import type { ParameterScalar } from "../entities/templates/types";
import { resolveParameterOptions } from "../entities/parameter-options/api";
import { fetchSystemSettings } from "../entities/system-settings/api";
import { ChatReportWorkspace } from "../features/report-preview/ChatReportWorkspace";
import { createDemoStreamDeltas, DEMO_REPORT_TEMPLATES } from "../features/report-preview/demo-report-templates";
import type { DemoReportTemplate } from "../features/report-preview/demo-report-templates";
import { canPreviewStreamReport, reduceStreamReport } from "../features/report-preview/stream-report-reducer";
import { EmptyState } from "../shared/ui/EmptyState";

type ParameterDrafts = Record<string, ParameterValue[]>;
type DynamicOptionMap = Record<string, ParameterValue[]>;

export function ChatPage() {
  const queryClient = useQueryClient();
  const [activeConversationId, setActiveConversationId] = useState("");
  const [question, setQuestion] = useState("");
  const [latestResponse, setLatestResponse] = useState<ChatResponse | null>(null);
  const [parameterDrafts, setParameterDrafts] = useState<ParameterDrafts>({});
  const [dynamicOptions, setDynamicOptions] = useState<DynamicOptionMap>({});
  const [errorMessage, setErrorMessage] = useState("");
  const [streamDeltas, setStreamDeltas] = useState<ChatStreamDelta[]>([]);
  const [streamStatus, setStreamStatus] = useState<ChatResponse["status"] | "idle">("idle");
  const [historyCollapsed, setHistoryCollapsed] = useState(false);
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [workspaceMode, setWorkspaceMode] = useState<"chat" | "report">("chat");
  const [reportWidth, setReportWidth] = useState(() => readStoredReportWidth());
  const [editorDirty, setEditorDirty] = useState(false);
  const [activeDemoTemplate, setActiveDemoTemplate] = useState<DemoReportTemplate | null>(null);
  const [demoReport, setDemoReport] = useState<Record<string, unknown> | null>(null);
  const demoTimers = useRef<number[]>([]);

  const settingsQuery = useQuery({ queryKey: ["system-settings"], queryFn: fetchSystemSettings });
  const conversationsQuery = useQuery({ queryKey: ["conversations"], queryFn: fetchConversations });
  const conversationQuery = useQuery({ queryKey: ["conversation", activeConversationId], queryFn: () => fetchConversation(activeConversationId), enabled: Boolean(activeConversationId) });

  const sendMutation = useMutation({
    mutationFn: (payload: Parameters<typeof sendChatMessageStream>[0]) =>
      sendChatMessageStream(payload, {
        onEvent: (event) => {
          if (event.delta?.length) {
            setStreamDeltas((current) => current.concat(event.delta ?? []));
            setReportOpen(true);
          }
          setStreamStatus(event.status);
        },
      }),
    onMutate: () => {
      clearDemoTimers(demoTimers.current);
      setActiveDemoTemplate(null);
      setDemoReport(null);
      setStreamDeltas([]);
      setStreamStatus("running");
    },
    onSuccess: async (response) => {
      setLatestResponse(response);
      setActiveConversationId(response.conversationId);
      setQuestion("");
      setErrorMessage("");
      setStreamStatus(response.status);
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
      await queryClient.invalidateQueries({ queryKey: ["conversation", response.conversationId] });
    },
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : "对话请求失败。");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteConversation,
    onSuccess: async (_, conversationId) => {
      if (conversationId === activeConversationId) {
        setActiveConversationId("");
        setLatestResponse(null);
      }
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : "删除会话失败。");
    },
  });

  const currentAsk = latestResponse?.ask?.status === "pending" ? latestResponse.ask : null;
  const currentTemplateInstance = useMemo(() => {
    if (latestResponse?.ask) {
      return latestResponse.ask.reportContext.templateInstance;
    }
    if (latestResponse?.answer?.answerType === "REPORT") {
      return latestResponse.answer.answer.templateInstance;
    }
    return null;
  }, [currentAsk, latestResponse]);

  useEffect(() => {
    if (!currentAsk) {
      setParameterDrafts({});
      setDynamicOptions({});
      return;
    }
    const nextDrafts: ParameterDrafts = {};
    for (const parameter of currentAsk.parameters) {
      nextDrafts[parameter.id] = parameter.values ?? [];
    }
    setParameterDrafts(nextDrafts);
  }, [currentAsk]);

  useEffect(() => {
    let cancelled = false;
    async function loadDynamicOptions(ask: ChatAsk) {
      const entries = ask.parameters.filter((parameter) => parameter.inputType === "dynamic" && parameter.source);
      if (!entries.length) {
        setDynamicOptions({});
        return;
      }
      const resolved: DynamicOptionMap = {};
      const contextValues = parametersToValueMap(ask.reportContext.templateInstance.parameters);
      for (const parameter of entries) {
        try {
          const response = await resolveParameterOptions({ parameterId: parameter.id, source: parameter.source ?? "", contextValues });
          resolved[parameter.id] = response.options;
        } catch {
          resolved[parameter.id] = [];
        }
      }
      if (!cancelled) {
        setDynamicOptions(resolved);
      }
    }
    if (currentAsk) {
      void loadDynamicOptions(currentAsk);
    }
    return () => {
      cancelled = true;
    };
  }, [currentAsk]);

  const conversationMessages = useMemo(() => normalizeConversationMessages(conversationQuery.data), [conversationQuery.data]);
  const streamReport = useMemo(() => reduceStreamReport(streamDeltas), [streamDeltas]);
  const reportAnswer = latestResponse?.answer?.answerType === "REPORT" ? latestResponse.answer.answer : null;
  const artifactReport = demoReport ?? reportAnswer?.report ?? streamReport;
  const artifactReportId = activeDemoTemplate?.id ?? reportAnswer?.reportId;
  const artifactEditable = Boolean(demoReport || reportAnswer);

  useEffect(() => {
    if (!activeConversationId || !conversationQuery.data) {
      return;
    }
    const persistedResponse = findLatestResponse(conversationQuery.data);
    if (persistedResponse) {
      setLatestResponse(persistedResponse);
    }
  }, [activeConversationId, conversationQuery.data]);

  useEffect(() => () => clearDemoTimers(demoTimers.current), []);

  useEffect(() => {
    if (artifactReport && (demoReport || reportAnswer || canPreviewStreamReport(streamReport))) {
      setReportOpen(true);
    }
  }, [artifactReport, demoReport, reportAnswer, streamReport]);

  const canSubmitQuestion = question.trim().length > 0 && !sendMutation.isPending;
  const visibleMessages = activeDemoTemplate ? [
    { key: `${activeDemoTemplate.id}-user`, role: "user", text: `生成演示报告：${activeDemoTemplate.name}` },
    { key: `${activeDemoTemplate.id}-assistant`, role: "assistant", text: streamStatus === "running" ? "正在使用 mock delta 构造报告，右侧预览会逐步更新。" : "演示报告已生成，可以在右侧预览或切换到本地编辑。" },
  ] : conversationMessages;

  const confirmDiscardLocalEdit = useCallback(() => {
    if (!editorDirty) return true;
    return window.confirm("存在未导出的本地修改，确定丢弃并切换吗？");
  }, [editorDirty]);

  const resetWorkspace = useCallback(() => {
    if (!confirmDiscardLocalEdit()) return;
    clearDemoTimers(demoTimers.current);
    setActiveConversationId("");
    setActiveDemoTemplate(null);
    setDemoReport(null);
    setLatestResponse(null);
    setStreamDeltas([]);
    setStreamStatus("idle");
    setErrorMessage("");
    setReportOpen(false);
    setWorkspaceMode("chat");
    setHistoryDrawerOpen(false);
  }, [confirmDiscardLocalEdit]);

  const selectConversation = useCallback((conversationId: string) => {
    if (!confirmDiscardLocalEdit()) return;
    clearDemoTimers(demoTimers.current);
    setActiveDemoTemplate(null);
    setDemoReport(null);
    setStreamDeltas([]);
    setLatestResponse(null);
    setReportOpen(false);
    setActiveConversationId(conversationId);
    setWorkspaceMode("chat");
    setHistoryDrawerOpen(false);
  }, [confirmDiscardLocalEdit]);

  const runDemoTemplate = useCallback((template: DemoReportTemplate) => {
    if (!confirmDiscardLocalEdit()) return;
    clearDemoTimers(demoTimers.current);
    const deltas = createDemoStreamDeltas(template);
    setActiveConversationId("");
    setLatestResponse(null);
    setActiveDemoTemplate(template);
    setDemoReport(null);
    setStreamDeltas([]);
    setStreamStatus("running");
    setReportOpen(true);
    setWorkspaceMode("report");
    setHistoryDrawerOpen(false);
    deltas.forEach((delta, index) => {
      const timer = window.setTimeout(() => {
        setStreamDeltas((current) => current.concat(delta));
        if (index === deltas.length - 1) {
          setDemoReport(structuredClone(template.report));
          setStreamStatus("finished");
        }
      }, 120 * (index + 1));
      demoTimers.current.push(timer);
    });
  }, [confirmDiscardLocalEdit]);

  const submitQuestion = useCallback(() => {
    if (!canSubmitQuestion) return;
    sendMutation.mutate({ conversationId: activeConversationId || undefined, instruction: "generate_report", question: question.trim() });
  }, [activeConversationId, canSubmitQuestion, question, sendMutation]);

  const startReportResize = useCallback((event: ReactMouseEvent<HTMLDivElement>) => {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = reportWidth;
    const onMouseMove = (moveEvent: MouseEvent) => {
      const maxWidth = Math.max(460, Math.min(960, window.innerWidth - 620));
      setReportWidth(clamp(startWidth + startX - moveEvent.clientX, 460, maxWidth));
    };
    const onMouseUp = () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
      setReportWidth((current) => {
        window.localStorage.setItem("report-system.chat.report-width", String(current));
        return current;
      });
    };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
  }, [reportWidth]);

  return (
    <div className="chat-page">
      <aside className={`chat-history-panel${historyCollapsed ? " is-collapsed" : ""}${historyDrawerOpen ? " is-drawer-open" : ""}`}>
        <div className="chat-history-panel__header">
          <strong>会话</strong>
          <div className="chat-history-panel__actions">
            <button className="icon-button" type="button" title="新建会话" aria-label="新建会话" onClick={resetWorkspace}><MessageSquarePlus size={17} /></button>
            <button className="icon-button chat-history-panel__drawer-close" type="button" title="关闭会话列表" aria-label="关闭会话列表" onClick={() => setHistoryDrawerOpen(false)}><X size={17} /></button>
          </div>
        </div>
        <div className="chat-history-panel__body">
          <div className="chat-history-list">
            {conversationsQuery.data?.map((item) => (
              <article key={item.conversationId} className={`chat-history-item${item.conversationId === activeConversationId && !activeDemoTemplate ? " is-active" : ""}`}>
                <button type="button" className="chat-history-item__main" onClick={() => selectConversation(item.conversationId)}>
                  <strong>{item.title || "未命名会话"}</strong>
                  <span>{item.lastMessagePreview || "暂无摘要"}</span>
                </button>
                <button className="icon-button chat-history-item__delete" type="button" title="删除会话" aria-label={`删除会话 ${item.title}`} onClick={() => deleteMutation.mutate(item.conversationId)}><Trash2 size={14} /></button>
              </article>
            ))}
          </div>
          <div className="chat-demo-list">
            <div className="chat-demo-list__heading"><WandSparkles size={15} /><strong>BI Engine 演示</strong></div>
            {DEMO_REPORT_TEMPLATES.map((template) => (
              <button key={template.id} className={`chat-demo-template${template.id === activeDemoTemplate?.id ? " is-active" : ""}`} type="button" onClick={() => runDemoTemplate(template)}>
                <strong>{template.name}</strong>
                <span>{template.structureType === "paged" ? "PPT" : "Flow"} · {template.description}</span>
              </button>
            ))}
          </div>
        </div>
      </aside>

      {historyDrawerOpen ? <button className="chat-history-backdrop" type="button" aria-label="关闭会话列表" onClick={() => setHistoryDrawerOpen(false)} /> : null}

      <main className={`chat-thread${workspaceMode === "report" ? " is-mobile-hidden" : ""}`}>
        <div className="chat-thread__toolbar">
          <div>
            <button className="icon-button chat-thread__mobile-menu" type="button" title="打开会话列表" aria-label="打开会话列表" onClick={() => setHistoryDrawerOpen(true)}><Menu size={18} /></button>
            <button className="icon-button chat-thread__history-toggle" type="button" title={historyCollapsed ? "展开会话列表" : "收起会话列表"} aria-label={historyCollapsed ? "展开会话列表" : "收起会话列表"} onClick={() => setHistoryCollapsed((current) => !current)}>{historyCollapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}</button>
            <strong>{activeDemoTemplate?.name ?? conversationQuery.data?.title ?? "新对话"}</strong>
          </div>
          {artifactReport ? <button className="icon-text-button" type="button" onClick={() => { setReportOpen(true); setWorkspaceMode("report"); }}><PanelRightOpen size={16} />报告</button> : null}
        </div>

        <div className="chat-thread__scroll">
          <div className="chat-thread__content">
            {!settingsQuery.data?.is_ready ? <InlineBanner title="系统设置未完成">真实生成链路暂不可用，可以先使用左侧 BI Engine 演示模板。</InlineBanner> : null}
            {errorMessage ? <InlineBanner title="请求失败">{errorMessage}</InlineBanner> : null}
            <div className="message-list">
              {visibleMessages.length ? visibleMessages.map((message) => (
                <div key={message.key} className={`message-entry message-entry--${message.role}`}>
                  <div className="message-entry__body">
                    <article className={`message-bubble message-bubble--${message.role}`}><p>{message.text}</p></article>
                    {"createdAt" in message && message.createdAt ? <div className="message-entry__time">{formatDateTime(message.createdAt)}</div> : null}
                  </div>
                </div>
              )) : <EmptyState title="开始一段报告对话" description="输入报告诉求，或从左侧选择一份 BI Engine 演示模板。" />}

              {latestResponse?.ask ? (
                <div className="message-entry message-entry--assistant">
                  <div className="message-entry__body message-entry__body--has-action">
                    <article className="message-bubble message-bubble--assistant message-bubble--has-action">
                      <strong>{latestResponse.ask.title}</strong>
                      <p>{latestResponse.ask.text}</p>
                      {latestResponse.ask.status === "pending" ? (
                        <AskPanel
                          ask={latestResponse.ask}
                          parameterDrafts={parameterDrafts}
                          dynamicOptions={dynamicOptions}
                          onChange={setParameterDrafts}
                          onSubmitFill={() => submitAskReply(latestResponse, "fill_params", parameterDrafts, dynamicOptions, sendMutation.mutate)}
                          onSubmitConfirm={() => submitAskReply(latestResponse, "confirm_params", parameterDrafts, dynamicOptions, sendMutation.mutate)}
                          submitting={sendMutation.isPending}
                        />
                      ) : <p>该追问已被后续回复消费。</p>}
                    </article>
                  </div>
                </div>
              ) : null}

              {reportAnswer ? (
                <div className="message-entry message-entry--assistant">
                  <div className="message-entry__body">
                    <article className="message-bubble message-bubble--assistant">
                      <strong>报告已生成</strong>
                      <p>章节完成度：{reportAnswer.generationProgress.completedSections}/{reportAnswer.generationProgress.totalSections}</p>
                      <div className="action-row action-row--compact"><Link className="secondary-button button-link" to={`/reports/${reportAnswer.reportId}`}>打开报告详情</Link></div>
                    </article>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>

        <div className="chat-compose-dock">
          <div className="chat-compose">
            <label className="sr-only" htmlFor="chat-input">输入问题</label>
            <textarea
              id="chat-input"
              rows={1}
              placeholder="描述你想生成的报告..."
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  submitQuestion();
                }
              }}
            />
            <button className="chat-send-button" type="button" title="发送" aria-label="发送" disabled={!canSubmitQuestion} onClick={submitQuestion}><Send size={17} /></button>
          </div>
        </div>
      </main>

      {reportOpen && artifactReport ? (
        <>
          <div className="chat-workspace-splitter" role="separator" aria-label="调整报告区宽度" onMouseDown={startReportResize} />
          <div className={`chat-report-slot${workspaceMode === "chat" ? " is-mobile-hidden" : ""}`} style={{ width: `${reportWidth}px` }}>
            <ChatReportWorkspace
              key={artifactReportId ?? "stream-report"}
              report={artifactReport}
              reportId={artifactReportId}
              templateInstance={currentTemplateInstance}
              deltas={streamDeltas}
              status={streamStatus}
              editable={artifactEditable}
              mock={Boolean(activeDemoTemplate)}
              onDirtyChange={setEditorDirty}
              onClose={() => { setReportOpen(false); setWorkspaceMode("chat"); }}
            />
          </div>
        </>
      ) : null}

      {reportOpen && artifactReport ? <div className="chat-mobile-workspace-switch" role="tablist" aria-label="切换工作区">
        <button type="button" className={workspaceMode === "chat" ? "is-active" : ""} onClick={() => setWorkspaceMode("chat")}>对话</button>
        <button type="button" className={workspaceMode === "report" ? "is-active" : ""} onClick={() => setWorkspaceMode("report")}>报告</button>
      </div> : null}
    </div>
  );
}

type AskPanelProps = {
  ask: ChatAsk;
  parameterDrafts: ParameterDrafts;
  dynamicOptions: DynamicOptionMap;
  onChange: Dispatch<SetStateAction<ParameterDrafts>>;
  onSubmitFill: () => void;
  onSubmitConfirm: () => void;
  submitting: boolean;
};

function AskPanel({ ask, parameterDrafts, dynamicOptions, onChange, onSubmitFill, onSubmitConfirm, submitting }: AskPanelProps) {
  return (
    <div className="stack-list">
      {ask.parameters.map((parameter) => {
        const value = parameterDrafts[parameter.id] ?? parameter.values ?? [];
        const options = parameter.inputType === "dynamic" ? dynamicOptions[parameter.id] ?? parameter.options ?? [] : parameter.options ?? [];
        const currentText = value.map((item) => String(item.label ?? "")).filter(Boolean).join("\n");
        const selectedValues = value.map((item) => String(item.label));

        return (
          <div key={parameter.id} className="form-grid">
            <label className="field field--full">
              <span className="field-label">{parameter.label}</span>
              {parameter.inputType === "enum" || parameter.inputType === "dynamic" ? (
                <select
                  multiple={parameter.multi}
                  value={parameter.multi ? selectedValues : (selectedValues[0] ?? "")}
                  onChange={(event) => {
                    const selected = Array.from(event.currentTarget.selectedOptions)
                      .map((optionElement) => options.find((option) => String(option.label) === optionElement.value) ?? null)
                      .filter((option): option is ParameterValue => Boolean(option));
                    onChange((current) => ({ ...current, [parameter.id]: parameter.multi ? selected : (selected[0] ? [selected[0]] : []) }));
                  }}
                >
                  {!parameter.multi ? <option value="">请选择</option> : null}
                  {options.map((option) => <option key={`${parameter.id}-${option.value}`} value={String(option.label)}>{String(option.label)}</option>)}
                </select>
              ) : parameter.multi ? (
                <textarea
                  rows={4}
                  value={currentText}
                  onChange={(event) => {
                    const values = event.target.value
                      .split(/\r?\n/)
                      .map((item) => item.trim())
                      .filter(Boolean)
                      .map((item) => ({ label: item, value: item, query: item }));
                    onChange((current) => ({ ...current, [parameter.id]: values }));
                  }}
                  placeholder={parameter.placeholder || parameter.description || `${parameter.label}（每行一个）`}
                />
              ) : (
                <input
                  value={value[0]?.label ? String(value[0].label) : ""}
                  onChange={(event) => {
                    const text = event.target.value;
                    onChange((current) => ({ ...current, [parameter.id]: text ? [{ label: text, value: text, query: text }] : [] }));
                  }}
                  placeholder={parameter.placeholder || parameter.description || parameter.label}
                />
              )}
            </label>
          </div>
        );
      })}
      <div className="action-row">
        {ask.type === "fill_params" ? <button className="primary-button" type="button" disabled={submitting} onClick={onSubmitFill}>{submitting ? "提交中..." : "提交参数"}</button> : null}
        {ask.type === "confirm_params" ? <button className="primary-button" type="button" disabled={submitting} onClick={onSubmitConfirm}>{submitting ? "生成中..." : "确认并生成"}</button> : null}
      </div>
    </div>
  );
}

export function mergeAskParameters(parameters: TemplateParameter[], parameterDrafts: ParameterDrafts, dynamicOptions: DynamicOptionMap): TemplateParameter[] {
  return parameters.map((parameter) => ({
    ...parameter,
    values: parameterDrafts[parameter.id] ?? parameter.values ?? [],
    options: parameter.inputType === "dynamic" ? dynamicOptions[parameter.id] ?? parameter.options : parameter.options,
  }));
}

export function mergeTemplateInstanceParameters(templateInstance: TemplateInstance, parameters: TemplateParameter[]): TemplateInstance {
  const parameterMap = new Map(parameters.map((parameter) => [parameter.id, parameter]));
  return {
    ...templateInstance,
    parameters: mergeParameterList(templateInstance.parameters, parameterMap),
    catalogs: templateInstance.catalogs.map((catalog) => mergeCatalogParameters(catalog, parameterMap)),
  };
}

function parametersToValueMap(parameters: TemplateParameter[]): Record<string, ParameterValue[]> {
  return Object.fromEntries(parameters.filter((parameter) => parameter.values?.length).map((parameter) => [parameter.id, parameter.values ?? []]));
}

function parameterValuesToReplyMap(parameters: TemplateParameter[]): Record<string, ParameterScalar[]> {
  return Object.fromEntries(
    parameters
      .filter((parameter) => parameter.values?.length)
      .map((parameter) => [parameter.id, (parameter.values ?? []).map((value) => value.value)]),
  );
}

function mergeCatalogParameters(catalog: TemplateInstance["catalogs"][number], parameterMap: Map<string, TemplateParameter>): TemplateInstance["catalogs"][number] {
  return {
    ...catalog,
    parameters: catalog.parameters ? mergeParameterList(catalog.parameters, parameterMap) : catalog.parameters,
    sections: catalog.sections?.map((section) => ({
      ...section,
      parameters: section.parameters ? mergeParameterList(section.parameters, parameterMap) : section.parameters,
    })),
    subCatalogs: catalog.subCatalogs?.map((subCatalog) => mergeCatalogParameters(subCatalog, parameterMap)),
  };
}

function mergeParameterList(parameters: TemplateParameter[], parameterMap: Map<string, TemplateParameter>): TemplateParameter[] {
  return parameters.map((parameter) => parameterMap.get(parameter.id) ?? parameter);
}

function normalizeConversationMessages(conversation: ConversationDetail | undefined) {
  if (!conversation) {
    return [];
  }
  const messages = Array.isArray(conversation.messages) ? conversation.messages : [];
  return messages.map((item, index) => ({ key: `${item.chatId}-${index}`, role: item.role, createdAt: item.createdAt ?? undefined, text: extractMessageText(item.content) }));
}

function describeDelta(delta: ChatStreamDelta) {
  if (delta.action === "init_report") {
    return `初始化报告：${delta.report.title}`;
  }
  if (delta.action === "add_catalog") {
    return `新增目录：${delta.catalogs.map((item) => item.title).join("、")}`;
  }
  if (delta.action === "add_chapter") {
    return `新增 PPT 章节：${delta.chapters.map((item) => item.title).join("、")}`;
  }
  if (delta.action === "add_slide") {
    return `新增幻灯片：${delta.slides.map((item) => item.title ?? item.id).join("、")}`;
  }
  return `新增章节：${delta.sections.map((item) => item.requirement).join("、")}`;
}

function findLatestResponse(conversation: ConversationDetail | undefined): ChatResponse | null {
  if (!conversation) {
    return null;
  }
  for (const message of [...conversation.messages].reverse()) {
    const value = message.content.response;
    if (value && typeof value === "object") {
      return value as ChatResponse;
    }
  }
  return null;
}

function extractMessageText(content: Record<string, unknown>) {
  if (typeof content.question === "string") {
    return content.question;
  }
  const response = content.response;
  if (response && typeof response === "object") {
    const responseRecord = response as Record<string, unknown>;
    const ask = responseRecord.ask;
    if (ask && typeof ask === "object") {
      const askRecord = ask as Record<string, unknown>;
      if (typeof askRecord.text === "string" && askRecord.text) {
        return askRecord.text;
      }
      if (typeof askRecord.title === "string") {
        return askRecord.title;
      }
    }
    const answer = responseRecord.answer;
    if (answer && typeof answer === "object") {
      const answerRecord = answer as Record<string, unknown>;
      if (answerRecord.answerType === "REPORT") {
        return "报告已生成";
      }
      if (answerRecord.answerType === "REPORT_TEMPLATE") {
        return "模板草案已提取";
      }
    }
  }
  return "";
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", { hour12: false });
}

function InlineBanner({ title, children }: { title: string; children: string }) {
  return (
    <div className="chat-inline-banner" role="status">
      <strong>{title}</strong>
      <span>{children}</span>
    </div>
  );
}

function submitAskReply(
  response: ChatResponse,
  type: "fill_params" | "confirm_params",
  parameterDrafts: ParameterDrafts,
  dynamicOptions: DynamicOptionMap,
  mutate: (payload: Parameters<typeof sendChatMessageStream>[0]) => void,
) {
  if (!response.ask) return;
  const mergedParameters = mergeAskParameters(response.ask.parameters, parameterDrafts, dynamicOptions);
  mutate({
    conversationId: response.conversationId,
    instruction: "generate_report",
    reply: {
      type,
      sourceChatId: response.chatId,
      parameters: parameterValuesToReplyMap(mergedParameters),
      reportContext: { templateInstance: mergeTemplateInstanceParameters(response.ask.reportContext.templateInstance, mergedParameters) },
    },
  });
}

function clearDemoTimers(timers: number[]) {
  timers.forEach((timer) => window.clearTimeout(timer));
  timers.length = 0;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function readStoredReportWidth() {
  const value = Number(window.localStorage.getItem("report-system.chat.report-width"));
  return Number.isFinite(value) && value > 0 ? value : 560;
}
