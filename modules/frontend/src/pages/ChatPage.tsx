import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Dispatch, MouseEvent as ReactMouseEvent, SetStateAction } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Menu, MessageSquarePlus, PanelLeftClose, PanelLeftOpen, PanelRightOpen, Send, WandSparkles, X } from "lucide-react";
import { Link } from "react-router-dom";

import { buildChatId, fetchConversation, fetchConversations, sendChatMessageStream, stopChat } from "../entities/chat/api";
import type { ChatAsk, ChatRequest, ChatResponse, ChatStreamDelta, ConversationAnswer, ConversationDetail, ConversationRecord, ParameterValue, TemplateInstance, TemplateParameter } from "../entities/chat/types";
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
type ChatDisplayMessage = {
  key: string;
  chatId: string;
  role: "user" | "assistant";
  text: string;
  response?: ChatResponse;
  createdAt?: string;
};
type OptimisticTurn = {
  chatId: string;
  conversationId?: string;
  userText: string;
  createdAt: string;
  sourceChatId?: string;
  response?: ChatResponse;
  error?: string;
};

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
  const [activeStreamingChatId, setActiveStreamingChatId] = useState<string | null>(null);
  const [queuedChats, setQueuedChats] = useState<Array<{ chatId: string; question: string }>>([]);
  const [optimisticTurns, setOptimisticTurns] = useState<OptimisticTurn[]>([]);
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
    onMutate: (payload) => {
      clearDemoTimers(demoTimers.current);
      setActiveDemoTemplate(null);
      setDemoReport(null);
      setStreamDeltas([]);
      setStreamStatus("running");
      const chatId = payload.chatId ?? buildChatId();
      setActiveStreamingChatId(chatId);
      setOptimisticTurns((current) => upsertOptimisticTurn(current, {
        chatId,
        conversationId: payload.conversationId,
        userText: describeChatRequest(payload),
        createdAt: new Date().toISOString(),
        sourceChatId: payload.reply?.sourceChatId,
      }));
      return { chatId };
    },
    onSuccess: async (response) => {
      setOptimisticTurns((current) => updateOptimisticTurn(current, response.chatId, {
        chatId: response.chatId,
        conversationId: response.conversationId,
        response,
      }));
      setLatestResponse(response);
      setActiveConversationId(response.conversationId);
      setQuestion("");
      setErrorMessage("");
      setStreamStatus(response.status);
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
      await queryClient.invalidateQueries({ queryKey: ["conversation", response.conversationId] });
    },
    onError: (error, _payload, context) => {
      const message = error instanceof Error ? error.message : "对话请求失败。";
      setErrorMessage(message);
      setOptimisticTurns((current) => updateOptimisticTurn(current, context?.chatId ?? "", { error: message }));
    },
    onSettled: () => {
      setActiveStreamingChatId(null);
    },
  });

  const stopMutation = useMutation({
    mutationFn: stopChat,
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : "停止当前对话失败。");
    },
  });

  const currentAsk = latestResponse?.ask?.status === "pending" ? latestResponse.ask : null;
  const currentTemplateInstance = useMemo(() => {
    if (latestResponse?.ask?.reportContext) {
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
    for (const parameter of currentAsk.parameters ?? []) {
      nextDrafts[parameter.id] = parameter.values ?? [];
    }
    setParameterDrafts(nextDrafts);
  }, [currentAsk]);

  useEffect(() => {
    let cancelled = false;
    async function loadDynamicOptions(ask: ChatAsk) {
      const entries = (ask.parameters ?? []).filter((parameter) => parameter.inputType === "dynamic" && parameter.source);
      if (!entries.length) {
        setDynamicOptions({});
        return;
      }
      const resolved: DynamicOptionMap = {};
      const contextValues = parametersToValueMap(ask.reportContext?.templateInstance.parameters ?? []);
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
  const consumedAskChatIds = useMemo(() => new Set(optimisticTurns.map((turn) => turn.sourceChatId).filter((id): id is string => Boolean(id))), [optimisticTurns]);
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

  const canSubmitQuestion = question.trim().length > 0;
  const visibleMessages = activeDemoTemplate ? [
    { key: `${activeDemoTemplate.id}-user`, chatId: `${activeDemoTemplate.id}-user`, role: "user" as const, text: `生成演示报告：${activeDemoTemplate.name}` },
    { key: `${activeDemoTemplate.id}-assistant`, chatId: `${activeDemoTemplate.id}-assistant`, role: "assistant" as const, text: streamStatus === "running" ? "正在使用 mock delta 构造报告，右侧预览会逐步更新。" : "演示报告已生成，可以在右侧预览或切换到本地编辑。" },
  ] : mergeConversationAndOptimisticMessages(conversationMessages, optimisticTurns);

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
    setOptimisticTurns([]);
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
    setOptimisticTurns([]);
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
    setOptimisticTurns([]);
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
    const nextQuestion = question.trim();
    const chatId = buildChatId();
    if (sendMutation.isPending) {
      setQueuedChats((current) => current.concat({ chatId, question: nextQuestion }));
      setQuestion("");
      return;
    }
    sendMutation.mutate({ conversationId: activeConversationId || undefined, chatId, question: nextQuestion });
  }, [activeConversationId, canSubmitQuestion, question, sendMutation]);

  useEffect(() => {
    if (sendMutation.isPending || !queuedChats.length) {
      return;
    }
    const [next, ...rest] = queuedChats;
    setQueuedChats(rest);
    sendMutation.mutate({
      conversationId: activeConversationId || latestResponse?.conversationId || undefined,
      chatId: next.chatId,
      question: next.question,
    });
  }, [activeConversationId, latestResponse?.conversationId, queuedChats, sendMutation]);

  const stopCurrentChat = useCallback(() => {
    if (!activeStreamingChatId) return;
    stopMutation.mutate(activeStreamingChatId);
  }, [activeStreamingChatId, stopMutation]);

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
          <div className="chat-thread__toolbar-actions">
            {activeStreamingChatId ? (
              <button className="secondary-button" type="button" disabled={stopMutation.isPending} onClick={stopCurrentChat}>
                {stopMutation.isPending ? "停止中..." : "停止"}
              </button>
            ) : null}
            {artifactReport ? <button className="icon-text-button" type="button" onClick={() => { setReportOpen(true); setWorkspaceMode("report"); }}><PanelRightOpen size={16} />报告</button> : null}
          </div>
        </div>

        <div className="chat-thread__scroll">
          <div className="chat-thread__content">
            {!settingsQuery.data?.is_ready ? <InlineBanner title="系统设置未完成">真实生成链路暂不可用，可以先使用左侧 BI Engine 演示模板。</InlineBanner> : null}
            {errorMessage ? <InlineBanner title="请求失败">{errorMessage}</InlineBanner> : null}
            <div className="message-list">
              {visibleMessages.length ? visibleMessages.map((message) => (
                <div key={message.key} className={`message-entry message-entry--${message.role}`}>
                  <div className={`message-entry__body${message.response ? " message-entry__body--has-action" : ""}`}>
                    {message.response ? (
                      <AssistantResponseCard
                        response={message.response}
                        consumed={consumedAskChatIds.has(message.response.chatId)}
                        parameterDrafts={parameterDrafts}
                        dynamicOptions={dynamicOptions}
                        onChange={setParameterDrafts}
                        onSubmitFill={() => submitAskReply(message.response!, "fill_params", parameterDrafts, dynamicOptions, sendMutation.mutate)}
                        onSubmitConfirm={() => submitAskReply(message.response!, "confirm_params", parameterDrafts, dynamicOptions, sendMutation.mutate)}
                        submitting={sendMutation.isPending}
                      />
                    ) : (
                      <article className={`message-bubble message-bubble--${message.role}`}><p>{message.text}</p></article>
                    )}
                    {"createdAt" in message && message.createdAt ? <div className="message-entry__time">{formatDateTime(message.createdAt)}</div> : null}
                  </div>
                </div>
              )) : <EmptyState title="开始一段报告对话" description="输入报告诉求，或从左侧选择一份 BI Engine 演示模板。" />}
            </div>
          </div>
        </div>

        <div className="chat-compose-dock">
          {queuedChats.length ? <div className="chat-queue-status">排队中 {queuedChats.length} 条，当前回复结束后自动发送。</div> : null}
          <div className="chat-compose">
            <label className="sr-only" htmlFor="chat-input">输入问题</label>
            <textarea
              id="chat-input"
              rows={1}
              placeholder="描述报告诉求，或直接询问业务数据..."
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
      {(ask.parameters ?? []).map((parameter) => {
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

type AssistantResponseCardProps = {
  response: ChatResponse;
  consumed: boolean;
  parameterDrafts: ParameterDrafts;
  dynamicOptions: DynamicOptionMap;
  onChange: Dispatch<SetStateAction<ParameterDrafts>>;
  onSubmitFill: () => void;
  onSubmitConfirm: () => void;
  submitting: boolean;
};

function AssistantResponseCard({
  response,
  consumed,
  parameterDrafts,
  dynamicOptions,
  onChange,
  onSubmitFill,
  onSubmitConfirm,
  submitting,
}: AssistantResponseCardProps) {
  if (response.ask) {
    const ask = consumed ? { ...response.ask, status: "replied" as const } : response.ask;
    const canReply = ask.status === "pending" && Boolean(ask.reportContext);
    return (
      <article className="message-bubble message-bubble--assistant message-bubble--has-action">
        <div className="card-heading">
          <div>
            <strong>{ask.title}</strong>
            <p className="template-hint">{ask.text}</p>
          </div>
          {ask.status === "replied" ? <span className="status-pill">已回复</span> : null}
        </div>
        {canReply ? (
          <AskPanel
            ask={ask}
            parameterDrafts={parameterDrafts}
            dynamicOptions={dynamicOptions}
            onChange={onChange}
            onSubmitFill={onSubmitFill}
            onSubmitConfirm={onSubmitConfirm}
            submitting={submitting}
          />
        ) : ask.status === "replied" ? (
          <p className="template-hint">该追问已被后续回复消费。</p>
        ) : null}
      </article>
    );
  }

  if (response.answer?.answerType === "REPORT") {
    const report = response.answer.answer;
    return (
      <article className="message-bubble message-bubble--assistant message-bubble--has-action">
        <div className="card-heading">
          <div>
            <strong>报告已生成</strong>
            <p className="template-hint">已冻结报告内容，可以在右侧预览或进入报告详情。</p>
          </div>
          <span className="status-pill">{report.status === "available" ? "可用" : report.status}</span>
        </div>
        <div className="action-row">
          <Link className="primary-button" to={`/reports/${encodeURIComponent(report.reportId)}`}>打开报告详情</Link>
        </div>
      </article>
    );
  }

  if (response.answer?.answerType === "DATA_ANALYSIS") {
    return (
      <article className="message-bubble message-bubble--assistant message-bubble--has-action">
        <div className="card-heading">
          <div>
            <strong>智能问数已完成</strong>
            <p className="template-hint">{response.answer.answer.summary}</p>
          </div>
        </div>
      </article>
    );
  }

  if (response.answer?.answerType === "REPORT_TEMPLATE") {
    const warnings = response.answer.answer.warnings ?? [];
    return (
      <article className="message-bubble message-bubble--assistant message-bubble--has-action">
        <div className="card-heading">
          <div>
            <strong>模板草案已提取</strong>
            <p className="template-hint">{warnings.length ? `存在 ${warnings.length} 条提示，请检查后保存。` : "模板结构已完成规范化。"}</p>
          </div>
        </div>
      </article>
    );
  }

  if (response.errors.length) {
    return (
      <article className="message-bubble message-bubble--assistant message-bubble--has-action">
        <div className="card-heading">
          <div>
            <strong>请求失败</strong>
            <p className="template-hint">{response.errors.map(renderErrorMessage).join("；")}</p>
          </div>
        </div>
      </article>
    );
  }

  if (response.status === "running" || response.status === "waiting_user") {
    const latestStep = response.steps[response.steps.length - 1];
    return (
      <article className="message-bubble message-bubble--assistant message-bubble--pending">
        <p>{latestStep?.title ?? "正在处理..."}</p>
      </article>
    );
  }

  return (
    <article className="message-bubble message-bubble--assistant">
      <p>{extractMessageText({ response }) || "已完成"}</p>
    </article>
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

function normalizeConversationMessages(conversation: ConversationDetail | undefined): ChatDisplayMessage[] {
  if (!conversation) {
    return [];
  }
  const records = Array.isArray(conversation.records) ? conversation.records : [];
  return records.flatMap((record, recordIndex) => {
    const messages: ChatDisplayMessage[] = [];
    if (record.question) {
      messages.push({
        key: `${record.chatId}-user-${recordIndex}`,
        chatId: record.chatId,
        role: "user",
        createdAt: normalizeRecordTime(record.askTime),
        text: record.question,
      });
    }
    record.answers.forEach((answer, answerIndex) => {
      if (answer.type === "TEXT") {
        messages.push({
          key: `${record.chatId}-answer-${answerIndex}`,
          chatId: record.chatId,
          role: "assistant",
          createdAt: normalizeRecordTime(answer.answerTime),
          text: answer.content,
        });
        return;
      }
      const response = chatResponseFromPiuAnswer(conversation.conversationId, record, answer);
      if (!response) {
        return;
      }
      messages.push({
        key: `${record.chatId}-answer-${answerIndex}`,
        chatId: record.chatId,
        role: "assistant",
        createdAt: normalizeRecordTime(answer.answerTime),
        text: extractMessageText({ response }),
        response,
      });
    });
    return messages;
  });
}

function mergeConversationAndOptimisticMessages(historyMessages: ChatDisplayMessage[], optimisticTurns: OptimisticTurn[]): ChatDisplayMessage[] {
  const known = new Set(historyMessages.map((message) => messageKey(message.chatId, message.role)));
  const projected: ChatDisplayMessage[] = [];
  for (const turn of optimisticTurns) {
    if (!known.has(messageKey(turn.chatId, "user"))) {
      projected.push({
        key: `${turn.chatId}-optimistic-user`,
        chatId: turn.chatId,
        role: "user",
        text: turn.userText,
        createdAt: turn.createdAt,
      });
    }
    if ((turn.response || turn.error) && !known.has(messageKey(turn.chatId, "assistant"))) {
      const response = turn.response ?? createLocalErrorResponse(turn);
      projected.push({
        key: `${turn.chatId}-optimistic-assistant`,
        chatId: turn.chatId,
        role: "assistant",
        text: extractMessageText({ response }),
        response,
        createdAt: turn.createdAt,
      });
    }
  }
  return historyMessages.concat(projected);
}

function messageKey(chatId: string, role: "user" | "assistant") {
  return `${chatId}:${role}`;
}

function upsertOptimisticTurn(current: OptimisticTurn[], turn: OptimisticTurn): OptimisticTurn[] {
  const index = current.findIndex((item) => item.chatId === turn.chatId);
  if (index < 0) {
    return current.concat(turn);
  }
  return current.map((item, itemIndex) => (itemIndex === index ? { ...item, ...turn } : item));
}

function updateOptimisticTurn(current: OptimisticTurn[], chatId: string, patch: Partial<OptimisticTurn>): OptimisticTurn[] {
  if (!chatId) {
    return current;
  }
  const index = current.findIndex((item) => item.chatId === chatId);
  if (index < 0) {
    return current.concat({
      chatId,
      userText: "继续对话",
      createdAt: new Date().toISOString(),
      ...patch,
    });
  }
  return current.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item));
}

function describeChatRequest(payload: ChatRequest) {
  if (payload.reply?.type === "confirm_params") {
    return "确认并生成报告";
  }
  if (payload.reply?.type === "fill_params") {
    return "已补充报告参数";
  }
  return payload.question?.trim() || "继续对话";
}

function extractMessageResponse(content: Record<string, unknown>): ChatResponse | undefined {
  const response = content.response;
  if (response && typeof response === "object") {
    return response as ChatResponse;
  }
  return undefined;
}

function createLocalErrorResponse(turn: OptimisticTurn): ChatResponse {
  return {
    conversationId: turn.conversationId ?? "",
    chatId: turn.chatId,
    status: "failed",
    steps: [],
    ask: null,
    answer: null,
    errors: [turn.error ?? "请求失败"],
    timestamp: Date.now(),
    apiVersion: "v1",
  };
}

function findLatestResponse(conversation: ConversationDetail | undefined): ChatResponse | null {
  if (!conversation) {
    return null;
  }
  for (const record of [...(conversation.records ?? [])].reverse()) {
    for (const answer of [...record.answers].reverse()) {
      if (answer.type !== "PIU") {
        continue;
      }
      const response = chatResponseFromPiuAnswer(conversation.conversationId, record, answer);
      if (response) {
        return response;
      }
    }
  }
  return null;
}

function chatResponseFromPiuAnswer(conversationId: string, record: ConversationRecord, answer: ConversationAnswer): ChatResponse | null {
  const payload = parsePiuContent(answer.content);
  const answers = payload?.answers;
  if (!answers || typeof answers !== "object") {
    return null;
  }
  const answerRecord = answers as Record<string, unknown>;
  return {
    conversationId,
    chatId: record.chatId,
    status: inferResponseStatus(answerRecord),
    steps: Array.isArray(answerRecord.steps) ? answerRecord.steps as ChatResponse["steps"] : [],
    ask: isRecord(answerRecord.ask) ? answerRecord.ask as ChatResponse["ask"] : null,
    answer: isRecord(answerRecord.answer) ? answerRecord.answer as ChatResponse["answer"] : null,
    errors: Array.isArray(answerRecord.errors) ? answerRecord.errors : [],
    timestamp: normalizeRecordTimestamp(answer.answerTime),
    apiVersion: "v1",
  };
}

function parsePiuContent(content: string): { piuName?: string; answers?: unknown } | null {
  try {
    const parsed = JSON.parse(content);
    return isRecord(parsed) ? parsed as { piuName?: string; answers?: unknown } : null;
  } catch {
    return null;
  }
}

function inferResponseStatus(answers: Record<string, unknown>): ChatResponse["status"] {
  const ask = answers.ask;
  if (isRecord(ask) && ask.status === "pending") {
    return "waiting_user";
  }
  const errors = answers.errors;
  if (Array.isArray(errors) && errors.length) {
    return "failed";
  }
  if (answers.answer) {
    return "finished";
  }
  return "running";
}

function normalizeRecordTime(value: string | number | null | undefined): string | undefined {
  if (value === null || value === undefined || value === "") {
    return undefined;
  }
  if (typeof value === "number") {
    return new Date(value).toISOString();
  }
  return value;
}

function normalizeRecordTimestamp(value: string | number | null | undefined): number {
  if (typeof value === "number") {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Date.parse(value);
    return Number.isNaN(parsed) ? Date.now() : parsed;
  }
  return Date.now();
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
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
      if (answerRecord.answerType === "DATA_ANALYSIS") {
        const payload = answerRecord.answer;
        if (payload && typeof payload === "object" && typeof (payload as Record<string, unknown>).summary === "string") {
          return String((payload as Record<string, unknown>).summary);
        }
        return "智能问数已完成";
      }
    }
  }
  return "";
}

function renderErrorMessage(error: unknown) {
  if (typeof error === "string") {
    return error;
  }
  if (error && typeof error === "object") {
    const record = error as Record<string, unknown>;
    if (typeof record.errorMsg === "string") {
      return record.errorMsg;
    }
    if (typeof record.message === "string") {
      return record.message;
    }
    if (typeof record.detail === "string") {
      return record.detail;
    }
  }
  return "系统处理失败，请稍后重试。";
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
  if (!response.ask.reportContext) return;
  const mergedParameters = mergeAskParameters(response.ask.parameters ?? [], parameterDrafts, dynamicOptions);
  mutate({
    conversationId: response.conversationId,
    chatId: buildChatId(),
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
