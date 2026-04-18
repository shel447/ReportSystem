import { useEffect, useMemo, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import {
  deleteConversation,
  fetchConversation,
  fetchConversations,
  sendChatMessage,
} from "../entities/chat/api";
import type { ChatAsk, ChatResponse, ConversationDetail, TemplateInstance, TrioValue } from "../entities/chat/types";
import { resolveParameterOptions } from "../entities/parameter-options/api";
import { fetchSystemSettings } from "../entities/system-settings/api";
import { PageSection } from "../shared/ui/PageSection";
import { SurfaceCard } from "../shared/ui/SurfaceCard";
import { EmptyState } from "../shared/ui/EmptyState";

type ParameterDrafts = Record<string, TrioValue[]>;
type DynamicOptionMap = Record<string, TrioValue[]>;

export function ChatPage() {
  const queryClient = useQueryClient();
  const [activeConversationId, setActiveConversationId] = useState("");
  const [question, setQuestion] = useState("");
  const [latestResponse, setLatestResponse] = useState<ChatResponse | null>(null);
  const [parameterDrafts, setParameterDrafts] = useState<ParameterDrafts>({});
  const [dynamicOptions, setDynamicOptions] = useState<DynamicOptionMap>({});
  const [errorMessage, setErrorMessage] = useState("");

  const settingsQuery = useQuery({
    queryKey: ["system-settings"],
    queryFn: fetchSystemSettings,
  });

  const conversationsQuery = useQuery({
    queryKey: ["conversations"],
    queryFn: fetchConversations,
  });

  const conversationQuery = useQuery({
    queryKey: ["conversation", activeConversationId],
    queryFn: () => fetchConversation(activeConversationId),
    enabled: Boolean(activeConversationId),
  });

  const sendMutation = useMutation({
    mutationFn: sendChatMessage,
    onSuccess: async (response) => {
      setLatestResponse(response);
      setActiveConversationId(response.conversationId);
      setQuestion("");
      setErrorMessage("");
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

  const currentAsk = latestResponse?.ask ?? null;
  const currentTemplateInstance = useMemo(() => {
    if (currentAsk) {
      return currentAsk.reportContext.templateInstance;
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
    for (const item of currentAsk.parameters) {
      nextDrafts[item.parameter.id] = item.currentValue ?? [];
    }
    setParameterDrafts(nextDrafts);
  }, [currentAsk]);

  useEffect(() => {
    let cancelled = false;
    async function loadDynamicOptions(ask: ChatAsk) {
      const entries = ask.parameters.filter((item) => item.parameter.inputType === "dynamic" && item.parameter.openSource?.url);
      if (!entries.length) {
        setDynamicOptions({});
        return;
      }

      const resolved: DynamicOptionMap = {};
      for (const entry of entries) {
        try {
          const response = await resolveParameterOptions({
            parameterId: entry.parameter.id,
            openSource: entry.parameter.openSource!,
            contextValues: ask.reportContext.templateInstance.parameterValues,
          });
          resolved[entry.parameter.id] = response.options;
        } catch {
          resolved[entry.parameter.id] = [];
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

  const conversationMessages = useMemo(
    () => normalizeConversationMessages(conversationQuery.data),
    [conversationQuery.data],
  );

  useEffect(() => {
    if (!activeConversationId) {
      return;
    }
    if (!conversationQuery.data) {
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
              <button
                className="chat-history-panel__new"
                type="button"
                onClick={() => {
                  setActiveConversationId("");
                  setLatestResponse(null);
                  setErrorMessage("");
                }}
              >
                新建
              </button>
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
                      <button
                        className="chat-history-item__menu-trigger"
                        type="button"
                        aria-label={`删除会话 ${item.title}`}
                        onClick={() => deleteMutation.mutate(item.conversationId)}
                      >
                        删除
                      </button>
                    </article>
                  ))}
                </div>
              ) : (
                <EmptyState title="暂无历史会话" description="发送第一条问题后，这里会记录对话会话。" />
              )}
            </div>
          </aside>

          <div className="chat-page__workspace">
            {!settingsQuery.data?.is_ready ? (
              <InlineBanner title="系统设置未完成">
                Completion 与 Embedding 尚未配置完成，真实生成链路可能被阻断。
              </InlineBanner>
            ) : null}
            {errorMessage ? <InlineBanner title="请求失败">{errorMessage}</InlineBanner> : null}

            <SurfaceCard className="chat-stream-card">
              <div className="message-list">
                {conversationMessages.length ? conversationMessages.map((message) => (
                  <div key={message.key} className={`message-entry message-entry--${message.role}`}>
                    <div className="message-entry__role">{message.role === "assistant" ? "助手" : "我"}</div>
                    <div className="message-entry__body">
                      <article className={`message-bubble message-bubble--${message.role}`}>
                        <p>{message.text}</p>
                      </article>
                      {message.createdAt ? <div className="message-entry__time">{formatDateTime(message.createdAt)}</div> : null}
                    </div>
                  </div>
                )) : (
                  <EmptyState title="开始对话" description="输入问题，系统会匹配模板、补齐参数，并返回模板实例片段。" />
                )}

                {latestResponse?.ask ? (
                  <div className="message-entry message-entry--assistant">
                    <div className="message-entry__role">助手</div>
                    <div className="message-entry__body">
                      <article className="message-bubble message-bubble--assistant message-bubble--has-action">
                        <strong>{latestResponse.ask.title}</strong>
                        <p>{latestResponse.ask.text}</p>
                        <AskPanel
                          ask={latestResponse.ask}
                          parameterDrafts={parameterDrafts}
                          dynamicOptions={dynamicOptions}
                          onChange={setParameterDrafts}
                          onSubmitFill={() => {
                            if (!latestResponse.ask) {
                              return;
                            }
                            sendMutation.mutate({
                              conversationId: latestResponse.conversationId,
                              instruction: "generate_report",
                              reply: {
                                type: "fill_params",
                                parameters: parameterDrafts,
                                reportContext: {
                                  templateInstance: mergeTemplateInstanceParameters(
                                    latestResponse.ask.reportContext.templateInstance,
                                    parameterDrafts,
                                  ),
                                },
                              },
                            });
                          }}
                          onSubmitConfirm={() => {
                            if (!latestResponse.ask) {
                              return;
                            }
                            const mergedTemplateInstance = mergeTemplateInstanceParameters(
                              latestResponse.ask.reportContext.templateInstance,
                              parameterDrafts,
                            );
                            sendMutation.mutate({
                              conversationId: latestResponse.conversationId,
                              instruction: "generate_report",
                              reply: {
                                type: "confirm_params",
                                parameters: mergedTemplateInstance.parameterValues,
                                reportContext: {
                                  templateInstance: mergedTemplateInstance,
                                },
                              },
                            });
                          }}
                          submitting={sendMutation.isPending}
                        />
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
                        <p>
                          状态：{latestResponse.answer.answer.status}，章节完成度：
                          {latestResponse.answer.answer.generationProgress.completedSections}/
                          {latestResponse.answer.answer.generationProgress.totalSections}
                        </p>
                        <div className="action-row action-row--compact">
                          <Link className="primary-button button-link" to={`/reports/${latestResponse.answer.answer.reportId}`}>
                            打开报告
                          </Link>
                        </div>
                      </article>
                    </div>
                  </div>
                ) : null}
              </div>
            </SurfaceCard>

            {currentTemplateInstance ? (
              <SurfaceCard>
                <div className="list-header">
                  <div>
                    <p className="section-kicker">Template Instance</p>
                    <h3>当前模板实例</h3>
                  </div>
                </div>
                <TemplateInstancePreview templateInstance={currentTemplateInstance} />
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
                        sendMutation.mutate({
                          conversationId: activeConversationId || undefined,
                          instruction: "generate_report",
                          question: question.trim(),
                        });
                      }
                    }
                  }}
                />
                <div className="action-row">
                  <button
                    className="primary-button"
                    type="button"
                    disabled={!canSubmitQuestion}
                    onClick={() => sendMutation.mutate({
                      conversationId: activeConversationId || undefined,
                      instruction: "generate_report",
                      question: question.trim(),
                    })}
                  >
                    {sendMutation.isPending ? "处理中..." : "发送"}
                  </button>
                </div>
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
      {ask.parameters.map((item) => {
        const value = parameterDrafts[item.parameter.id] ?? [];
        const options = item.parameter.inputType === "dynamic" ? dynamicOptions[item.parameter.id] ?? [] : item.parameter.options ?? [];
        const currentText = value[0]?.display ? String(value[0].display) : "";

        return (
          <div key={item.parameter.id} className="form-grid">
            <label className="field field--full">
              <span className="field-label">{item.parameter.label}</span>
              {item.parameter.inputType === "enum" || item.parameter.inputType === "dynamic" ? (
                <select
                  value={currentText}
                  onChange={(event) => {
                    const selected = options.find((option) => String(option.display) === event.target.value) ?? null;
                    onChange((current) => ({
                      ...current,
                      [item.parameter.id]: selected ? [selected] : [],
                    }));
                  }}
                >
                  <option value="">请选择</option>
                  {options.map((option) => (
                    <option key={`${item.parameter.id}-${option.value}`} value={String(option.display)}>
                      {String(option.display)}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  value={currentText}
                  onChange={(event) => {
                    const text = event.target.value;
                    onChange((current) => ({
                      ...current,
                      [item.parameter.id]: text ? [{ display: text, value: text, query: text }] : [],
                    }));
                  }}
                  placeholder={item.parameter.placeholder || item.parameter.description || item.parameter.label}
                />
              )}
            </label>
          </div>
        );
      })}

      <div className="action-row">
        {ask.type === "fill_params" ? (
          <button className="primary-button" type="button" disabled={submitting} onClick={onSubmitFill}>
            {submitting ? "提交中..." : "提交参数"}
          </button>
        ) : null}
        {ask.type === "confirm_params" ? (
          <button className="primary-button" type="button" disabled={submitting} onClick={onSubmitConfirm}>
            {submitting ? "生成中..." : "确认并生成"}
          </button>
        ) : null}
      </div>
    </div>
  );
}

function TemplateInstancePreview({ templateInstance }: { templateInstance: TemplateInstance }) {
  return (
    <div className="stack-list">
      <div className="template-card__meta">
        <span>{templateInstance.templateId}</span>
        <span>{templateInstance.status}</span>
        <span>revision {templateInstance.revision}</span>
      </div>
      {templateInstance.catalogs.map((catalog) => (
        <div key={catalog.id} className="template-editor-subcard">
          <strong>{catalog.name}</strong>
          {(catalog.sections || []).map((section) => (
            <div key={section.id} className="template-inline-group">
              <div className="template-inline-group__header">
                <strong>{section.title}</strong>
                <span>{section.skeletonStatus}</span>
              </div>
              <p>{section.requirementInstance.text}</p>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function mergeTemplateInstanceParameters(templateInstance: TemplateInstance, parameterDrafts: ParameterDrafts): TemplateInstance {
  return {
    ...templateInstance,
    parameterValues: {
      ...templateInstance.parameterValues,
      ...parameterDrafts,
    },
  };
}

function normalizeConversationMessages(conversation: ConversationDetail | undefined) {
  if (!conversation) {
    return [];
  }
  return conversation.messages.map((item, index) => ({
    key: `${item.chatId}-${index}`,
    role: item.role,
    createdAt: item.createdAt ?? undefined,
    text: extractMessageText(item.content),
  }));
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
