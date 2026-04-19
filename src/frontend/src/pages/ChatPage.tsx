import { useEffect, useMemo, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { deleteConversation, fetchConversation, fetchConversations, sendChatMessageStream } from "../entities/chat/api";
import type { ChatAsk, ChatResponse, ChatStreamDelta, ConversationDetail, ParameterValue, TemplateInstance, TemplateParameter } from "../entities/chat/types";
import { resolveParameterOptions } from "../entities/parameter-options/api";
import { fetchSystemSettings } from "../entities/system-settings/api";
import { PageSection } from "../shared/ui/PageSection";
import { SurfaceCard } from "../shared/ui/SurfaceCard";
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

  const settingsQuery = useQuery({ queryKey: ["system-settings"], queryFn: fetchSystemSettings });
  const conversationsQuery = useQuery({ queryKey: ["conversations"], queryFn: fetchConversations });
  const conversationQuery = useQuery({ queryKey: ["conversation", activeConversationId], queryFn: () => fetchConversation(activeConversationId), enabled: Boolean(activeConversationId) });

  const sendMutation = useMutation({
    mutationFn: (payload: Parameters<typeof sendChatMessageStream>[0]) =>
      sendChatMessageStream(payload, {
        onEvent: (event) => {
          if (event.delta?.length) {
            setStreamDeltas((current) => current.concat(event.delta ?? []));
          }
          setStreamStatus(event.status);
        },
      }),
    onMutate: () => {
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

  useEffect(() => {
    if (!activeConversationId || !conversationQuery.data) {
      return;
    }
    setLatestResponse(findLatestResponse(conversationQuery.data));
  }, [activeConversationId, conversationQuery.data]);

  const canSubmitQuestion = question.trim().length > 0 && !sendMutation.isPending;

  return (
    <div className="chat-page">
      <PageSection description="对话接口是模板实例运行态的唯一外部入口。参数补齐、诉求确认和报告生成都通过 /chat 推进。">
        <div className="chat-page__shell">
          <aside className="chat-history-panel">
            <div className="chat-history-panel__header">
              <strong>会话记录</strong>
              <button className="chat-history-panel__new" type="button" onClick={() => { setActiveConversationId(""); setLatestResponse(null); setErrorMessage(""); }}>新建</button>
            </div>
            <div className="chat-history-panel__body">
              {conversationsQuery.data?.length ? (
                <div className="chat-history-list">
                  {conversationsQuery.data.map((item) => (
                    <article key={item.conversationId} className={`chat-history-item${item.conversationId === activeConversationId ? " is-active" : ""}`}>
                      <button type="button" className="chat-history-item__main" onClick={() => setActiveConversationId(item.conversationId)}>
                        <strong>{item.title || "未命名会话"}</strong>
                        <span>{item.lastMessagePreview || "暂无摘要"}</span>
                      </button>
                      <button className="chat-history-item__menu-trigger" type="button" aria-label={`删除会话 ${item.title}`} onClick={() => deleteMutation.mutate(item.conversationId)}>删除</button>
                    </article>
                  ))}
                </div>
              ) : <EmptyState title="暂无历史会话" description="发送第一条问题后，这里会记录对话会话。" />}
            </div>
          </aside>

          <div className="chat-page__workspace">
            {!settingsQuery.data?.is_ready ? <InlineBanner title="系统设置未完成">Completion 与 Embedding 尚未配置完成，真实生成链路可能被阻断。</InlineBanner> : null}
            {errorMessage ? <InlineBanner title="请求失败">{errorMessage}</InlineBanner> : null}

            <SurfaceCard className="chat-stream-card">
              <div className="message-list">
                {conversationMessages.length ? conversationMessages.map((message) => (
                  <div key={message.key} className={`message-entry message-entry--${message.role}`}>
                    <div className="message-entry__role">{message.role === "assistant" ? "助手" : "我"}</div>
                    <div className="message-entry__body">
                      <article className={`message-bubble message-bubble--${message.role}`}><p>{message.text}</p></article>
                      {message.createdAt ? <div className="message-entry__time">{formatDateTime(message.createdAt)}</div> : null}
                    </div>
                  </div>
                )) : <EmptyState title="开始对话" description="输入问题，系统会匹配模板、补齐参数，并返回模板实例片段。" />}

                {latestResponse?.ask ? (
                  <div className="message-entry message-entry--assistant">
                    <div className="message-entry__role">助手</div>
                    <div className="message-entry__body">
                      <article className="message-bubble message-bubble--assistant message-bubble--has-action">
                        <strong>{latestResponse.ask.title}</strong>
                        <p>{latestResponse.ask.text}</p>
                        {latestResponse.ask.status === "pending" ? (
                          <AskPanel
                            ask={latestResponse.ask}
                            parameterDrafts={parameterDrafts}
                            dynamicOptions={dynamicOptions}
                            onChange={setParameterDrafts}
                            onSubmitFill={() => {
                              if (!latestResponse.ask) {
                                return;
                              }
                              const mergedParameters = mergeAskParameters(latestResponse.ask.parameters, parameterDrafts, dynamicOptions);
                              sendMutation.mutate({
                                conversationId: latestResponse.conversationId,
                                instruction: "generate_report",
                                reply: {
                                  type: "fill_params",
                                  sourceChatId: latestResponse.chatId,
                                  parameters: mergedParameters,
                                  reportContext: { templateInstance: mergeTemplateInstanceParameters(latestResponse.ask.reportContext.templateInstance, mergedParameters) },
                                },
                              });
                            }}
                            onSubmitConfirm={() => {
                              if (!latestResponse.ask) {
                                return;
                              }
                              const mergedParameters = mergeAskParameters(latestResponse.ask.parameters, parameterDrafts, dynamicOptions);
                              const mergedTemplateInstance = mergeTemplateInstanceParameters(latestResponse.ask.reportContext.templateInstance, mergedParameters);
                              sendMutation.mutate({
                                conversationId: latestResponse.conversationId,
                                instruction: "generate_report",
                                reply: {
                                  type: "confirm_params",
                                  sourceChatId: latestResponse.chatId,
                                  parameters: mergedParameters,
                                  reportContext: { templateInstance: mergedTemplateInstance },
                                },
                              });
                            }}
                            submitting={sendMutation.isPending}
                          />
                        ) : (
                          <p>该追问已被后续回复消费，当前会话中不可继续修改。</p>
                        )}
                      </article>
                    </div>
                  </div>
                ) : null}

                {latestResponse?.answer?.answerType === "REPORT" ? (
                  <div className="message-entry message-entry--assistant">
                    <div className="message-entry__role">报告</div>
                    <div className="message-entry__body">
                      <article className="message-bubble message-bubble--assistant message-bubble--has-action">
                        <strong>报告已生成</strong>
                        <p>状态：{latestResponse.answer.answer.status}，章节完成度：{latestResponse.answer.answer.generationProgress.completedSections}/{latestResponse.answer.answer.generationProgress.totalSections}</p>
                        <div className="action-row action-row--compact"><Link className="primary-button button-link" to={`/reports/${latestResponse.answer.answer.reportId}`}>打开报告</Link></div>
                      </article>
                    </div>
                  </div>
                ) : null}
              </div>
            </SurfaceCard>

            {currentTemplateInstance ? (
              <SurfaceCard>
                <div className="list-header"><div><p className="section-kicker">Template Instance</p><h3>当前模板实例</h3></div></div>
                <TemplateInstancePreview templateInstance={currentTemplateInstance} />
              </SurfaceCard>
            ) : null}

            {streamDeltas.length ? (
              <SurfaceCard>
                <div className="list-header">
                  <div>
                    <p className="section-kicker">Stream Delta</p>
                    <h3>增量生成进度</h3>
                  </div>
                  <span>{streamStatus === "running" ? "生成中" : "已完成"}</span>
                </div>
                <ul className="stack-list">
                  {streamDeltas.map((delta, index) => (
                    <li key={`${delta.action}-${index}`}>{describeDelta(delta)}</li>
                  ))}
                </ul>
              </SurfaceCard>
            ) : null}

            <SurfaceCard className="chat-compose-card">
              <div className="chat-compose">
                <label className="sr-only" htmlFor="chat-input">输入问题</label>
                <textarea
                  id="chat-input"
                  rows={4}
                  placeholder="输入问题，例如：帮我生成总部网络运行日报"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      if (canSubmitQuestion) {
                        sendMutation.mutate({ conversationId: activeConversationId || undefined, instruction: "generate_report", question: question.trim() });
                      }
                    }
                  }}
                />
                <div className="action-row"><button className="primary-button" type="button" disabled={!canSubmitQuestion} onClick={() => sendMutation.mutate({ conversationId: activeConversationId || undefined, instruction: "generate_report", question: question.trim() })}>{sendMutation.isPending ? "处理中..." : "发送"}</button></div>
              </div>
            </SurfaceCard>
          </div>
        </div>
      </PageSection>
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
        const currentText = value.map((item) => String(item.display ?? "")).filter(Boolean).join("\n");
        const selectedValues = value.map((item) => String(item.display));

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
                      .map((optionElement) => options.find((option) => String(option.display) === optionElement.value) ?? null)
                      .filter((option): option is ParameterValue => Boolean(option));
                    onChange((current) => ({ ...current, [parameter.id]: parameter.multi ? selected : (selected[0] ? [selected[0]] : []) }));
                  }}
                >
                  {!parameter.multi ? <option value="">请选择</option> : null}
                  {options.map((option) => <option key={`${parameter.id}-${option.value}`} value={String(option.display)}>{String(option.display)}</option>)}
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
                      .map((item) => ({ display: item, value: item, query: item }));
                    onChange((current) => ({ ...current, [parameter.id]: values }));
                  }}
                  placeholder={parameter.placeholder || parameter.description || `${parameter.label}（每行一个）`}
                />
              ) : (
                <input
                  value={value[0]?.display ? String(value[0].display) : ""}
                  onChange={(event) => {
                    const text = event.target.value;
                    onChange((current) => ({ ...current, [parameter.id]: text ? [{ display: text, value: text, query: text }] : [] }));
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

function TemplateInstancePreview({ templateInstance }: { templateInstance: TemplateInstance }) {
  return (
    <div className="stack-list">
      <div className="template-card__meta"><span>{templateInstance.templateId}</span><span>{templateInstance.status}</span><span>revision {templateInstance.revision}</span></div>
      {templateInstance.catalogs.map((catalog) => <TemplateInstanceCatalogPreview key={catalog.id} catalog={catalog} />)}
    </div>
  );
}

function TemplateInstanceCatalogPreview({ catalog }: { catalog: TemplateInstance["catalogs"][number] }) {
  return (
    <div className="template-editor-subcard">
      <strong>{catalog.renderedTitle}</strong>
      {(catalog.sections ?? []).map((section) => (
        <div key={section.id} className="template-inline-group">
          <div className="template-inline-group__header"><strong>{section.id}</strong><span>{section.skeletonStatus}</span></div>
          <p>{section.outline.renderedRequirement ?? section.outline.requirement}</p>
        </div>
      ))}
      {(catalog.subCatalogs ?? []).map((subCatalog) => <TemplateInstanceCatalogPreview key={subCatalog.id} catalog={subCatalog} />)}
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
