import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, useSearchParams } from "react-router-dom";

import { deleteChatSession, fetchChatSession, fetchChatSessions, forkChatSession, sendChatMessage } from "../entities/chat/api";
import type {
  ChatAction,
  ChatForkMeta,
  ChatForkResponse,
  ChatMessageItem,
  ChatRequest,
  ChatResponse,
  ChatSessionDetail,
  ChatSessionPayload,
} from "../entities/chat/types";
import { fetchSystemSettings } from "../entities/system-settings/api";
import { ChatActionPanel } from "../features/chat-report-flow/components/ChatActionPanel";
import { ConversationLayout } from "../shared/layouts/ConversationLayout";
import { EmptyState } from "../shared/ui/EmptyState";
import { SurfaceCard } from "../shared/ui/SurfaceCard";

const WELCOME_MESSAGE = "您好！我是您的智能报告助手。";
const INPUT_PLACEHOLDER = "输入消息，例如：制作设备巡检报告";
const DEFAULT_MESSAGES: ChatMessageItem[] = [
  {
    role: "assistant",
    content: WELCOME_MESSAGE,
  },
];

type ChatPageLocationState = {
  prefetchedSession?: ChatSessionPayload | null;
};

export function ChatPage() {
  const queryClient = useQueryClient();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [draft, setDraft] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [activeSessionId, setActiveSessionId] = useState("");
  const [sessionTitle, setSessionTitle] = useState("");
  const [activeForkMeta, setActiveForkMeta] = useState<ChatForkMeta | null>(null);
  const [historyCollapsed, setHistoryCollapsed] = useState(false);
  const [menuSessionId, setMenuSessionId] = useState("");
  const [menuMessageId, setMenuMessageId] = useState("");
  const [preferredCapability, setPreferredCapability] = useState<"report_generation" | "smart_query" | "fault_diagnosis" | "">("");
  const viewRevisionRef = useRef(0);
  const chatWorkspaceRef = useRef<HTMLDivElement | null>(null);
  const chatHistoryRailRef = useRef<HTMLDivElement | null>(null);
  const composeDockRef = useRef<HTMLDivElement | null>(null);
  const messageEndRef = useRef<HTMLDivElement | null>(null);
  const autoOpenedSessionRef = useRef("");
  const [messages, setMessages] = useState<ChatMessageItem[]>(DEFAULT_MESSAGES);
  const [errorMessage, setErrorMessage] = useState("");
  const [viewRevision, setViewRevision] = useState(0);
  const [pendingViewRevisions, setPendingViewRevisions] = useState<number[]>([]);
  const [composeLayout, setComposeLayout] = useState(() => ({
    left: 0,
    width: typeof window !== "undefined" ? window.innerWidth : 0,
    reserve: 176,
    historyLeft: 0,
    historyTop: 0,
    historyWidth: 280,
    historyHeight: typeof window !== "undefined" ? window.innerHeight : 0,
  }));

  const systemSettingsQuery = useQuery({
    queryKey: ["system-settings"],
    queryFn: fetchSystemSettings,
  });

  const chatSessionsQuery = useQuery({
    queryKey: ["chat-sessions"],
    queryFn: fetchChatSessions,
  });

  const loadSessionMutation = useMutation({
    mutationFn: (nextSessionId: string) => fetchChatSession(nextSessionId),
  });

  const deleteSessionMutation = useMutation({
    mutationFn: (nextSessionId: string) => deleteChatSession(nextSessionId),
  });

  const forkSessionMutation = useMutation({
    mutationFn: forkChatSession,
  });

  const chatMutation = useMutation({
    mutationFn: (payload: ChatRequest) => sendChatMessage(payload),
  });
  const prefetchedSession = (location.state as ChatPageLocationState | null | undefined)?.prefetchedSession ?? null;
  const sessionSourceBanner = getSessionSourceBanner(activeForkMeta, sessionTitle);

  const latestAction = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const item = messages[index];
      if (item.role === "assistant" && item.action) {
        return item.action;
      }
    }
    return null;
  }, [messages]);

  const isCurrentViewPending = pendingViewRevisions.includes(viewRevision);

  const advanceViewRevision = () => {
    viewRevisionRef.current += 1;
    setViewRevision(viewRevisionRef.current);
    return viewRevisionRef.current;
  };

  useEffect(() => {
    messageEndRef.current?.scrollIntoView?.({ block: "end" });
  }, [messages]);

  useLayoutEffect(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    const measure = () => {
      const workspace = chatWorkspaceRef.current;
      const historyRail = chatHistoryRailRef.current;
      const composeDock = composeDockRef.current;
      if (!workspace || !composeDock || !historyRail) {
        return;
      }

      const containerRect = workspace.getBoundingClientRect();
      const historyRect = historyRail.getBoundingClientRect();
      const composeRect = composeDock.getBoundingClientRect();
      const nextLayout = {
        left: Math.max(containerRect.left, 0),
        width: Math.max(containerRect.width, 0),
        reserve: Math.max(Math.ceil(composeRect.height), 176),
        historyLeft: Math.max(historyRect.left, 0),
        historyTop: Math.max(historyRect.top, 0),
        historyWidth: Math.max(historyRect.width, historyCollapsed ? 36 : 280),
        historyHeight: Math.max(window.innerHeight - Math.max(historyRect.top, 0), 0),
      };

      setComposeLayout((current) => {
        if (
          current.left === nextLayout.left
          && current.width === nextLayout.width
          && current.reserve === nextLayout.reserve
          && current.historyLeft === nextLayout.historyLeft
          && current.historyTop === nextLayout.historyTop
          && current.historyWidth === nextLayout.historyWidth
          && current.historyHeight === nextLayout.historyHeight
        ) {
          return current;
        }
        return nextLayout;
      });
    };

    const handleResize = () => {
      window.requestAnimationFrame(measure);
    };

    measure();
    window.addEventListener("resize", handleResize);

    const resizeObserver = typeof ResizeObserver !== "undefined" ? new ResizeObserver(measure) : null;
    if (resizeObserver && chatWorkspaceRef.current && composeDockRef.current && chatHistoryRailRef.current) {
      resizeObserver.observe(chatWorkspaceRef.current);
      resizeObserver.observe(composeDockRef.current);
      resizeObserver.observe(chatHistoryRailRef.current);
    }

    return () => {
      window.removeEventListener("resize", handleResize);
      resizeObserver?.disconnect();
    };
  }, [historyCollapsed]);

  const resetToEmptyConversation = () => {
    advanceViewRevision();
    setDraft("");
    setSessionId("");
    setActiveSessionId("");
    setSessionTitle("");
    setActiveForkMeta(null);
    setPreferredCapability("");
    setMenuSessionId("");
    setMenuMessageId("");
    setMessages(DEFAULT_MESSAGES);
    setErrorMessage("");
    setSearchParams({});
  };

  const syncChatResponse = (response: ChatResponse, optimisticContent: string) => {
    setErrorMessage("");
    setSessionId(response.session_id);
    setActiveSessionId(response.session_id);
    if (response.title) {
      setSessionTitle(response.title);
    }
    if (response.fork_meta !== undefined) {
      setActiveForkMeta(response.fork_meta ?? null);
    }
    setMessages(buildVisibleMessages(response, optimisticContent));
    void queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
  };

  const hydrateSessionSnapshot = (session: ChatSessionPayload) => {
    setSessionId(session.session_id);
    setActiveSessionId(session.session_id);
    setSessionTitle(session.title ?? "");
    setActiveForkMeta(session.fork_meta ?? null);
    setDraft(session.draft_message ?? "");
    setMenuMessageId("");
    setMenuSessionId("");
    setErrorMessage("");
    setMessages(buildVisibleMessagesFromSession(session));
    void queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
  };

  const sendPayload = (payload: Omit<ChatRequest, "session_id">, optimisticContent: string) => {
    const requestViewRevision = viewRevisionRef.current;
    const request: ChatRequest = {
      session_id: sessionId || undefined,
      ...payload,
    };

    setErrorMessage("");
    setPendingViewRevisions((current) =>
      current.includes(requestViewRevision) ? current : [...current, requestViewRevision],
    );
    if (optimisticContent) {
      setMessages((current) => appendOptimisticMessage(current, optimisticContent));
    }

    chatMutation.mutate(request, {
      onSuccess: (response) => {
        setPendingViewRevisions((current) => current.filter((value) => value !== requestViewRevision));
        if (requestViewRevision !== viewRevisionRef.current) {
          void queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
          return;
        }
        syncChatResponse(response, optimisticContent);
      },
      onError: (error) => {
        setPendingViewRevisions((current) => current.filter((value) => value !== requestViewRevision));
        if (requestViewRevision !== viewRevisionRef.current) {
          return;
        }
        setErrorMessage(error instanceof Error ? error.message : "对话请求失败。");
      },
    });
  };

  const submitMessage = () => {
    const nextMessage = draft.trim();
    if (!nextMessage || isCurrentViewPending) {
      return;
    }
    setDraft("");
    sendPayload(
      {
        message: nextMessage,
        preferred_capability: preferredCapability || undefined,
      },
      nextMessage,
    );
  };

  const runAction = (payload: Omit<ChatRequest, "session_id">) => {
    sendPayload(payload, buildOptimisticActionMessage(payload, latestAction));
  };

  const openSession = (nextSessionId: string) => {
    if (loadSessionMutation.isPending || deleteSessionMutation.isPending || forkSessionMutation.isPending) {
      return;
    }
    const nextViewRevision = advanceViewRevision();
    setErrorMessage("");
    loadSessionMutation.mutate(nextSessionId, {
      onSuccess: (session) => {
        if (viewRevisionRef.current !== nextViewRevision) {
          return;
        }
        hydrateSessionSnapshot(session);
      },
      onError: (error) => {
        if (viewRevisionRef.current !== nextViewRevision) {
          return;
        }
        setErrorMessage(error instanceof Error ? error.message : "加载历史会话失败。");
      },
    });
  };

  const removeSession = (nextSessionId: string) => {
    if (loadSessionMutation.isPending || deleteSessionMutation.isPending || forkSessionMutation.isPending) {
      return;
    }
    deleteSessionMutation.mutate(nextSessionId, {
      onSuccess: () => {
        setMenuSessionId("");
        if (nextSessionId === sessionId || nextSessionId === activeSessionId) {
          resetToEmptyConversation();
        }
        void queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
      },
      onError: (error) => {
        setErrorMessage(error instanceof Error ? error.message : "删除历史会话失败。");
      },
    });
  };

  const applyForkedSession = (payload: ChatForkResponse) => {
    hydrateSessionSnapshot(payload);
  };

  useEffect(() => {
    if (!prefetchedSession) {
      return;
    }
    if (prefetchedSession.session_id === activeSessionId && prefetchedSession.session_id === sessionId) {
      return;
    }
    hydrateSessionSnapshot(prefetchedSession);
  }, [activeSessionId, prefetchedSession, sessionId]);

  const runForkFromMessage = (messageId: string) => {
    const sourceSessionId = activeSessionId || sessionId;
    if (!sourceSessionId || forkSessionMutation.isPending) {
      return;
    }
    forkSessionMutation.mutate(
      {
        source_kind: "session_message",
        source_session_id: sourceSessionId,
        source_message_id: messageId,
      },
      {
        onSuccess: (payload) => {
          applyForkedSession(payload);
        },
        onError: (error) => {
          setErrorMessage(error instanceof Error ? error.message : "Fork 会话失败。");
        },
      },
    );
  };

  useEffect(() => {
    const requestedSessionId = searchParams.get("session_id") ?? "";
    if (!requestedSessionId) {
      autoOpenedSessionRef.current = "";
      return;
    }
    if (
      requestedSessionId === activeSessionId
      || requestedSessionId === autoOpenedSessionRef.current
      || loadSessionMutation.isPending
    ) {
      return;
    }
    autoOpenedSessionRef.current = requestedSessionId;
    openSession(requestedSessionId);
  }, [activeSessionId, loadSessionMutation.isPending, searchParams]);

  const chatPageStyle = {
    "--chat-compose-left": `${composeLayout.left}px`,
    "--chat-compose-width": `${composeLayout.width}px`,
    "--chat-compose-reserve": `${composeLayout.reserve}px`,
    "--chat-history-left": `${composeLayout.historyLeft}px`,
    "--chat-history-top": `${composeLayout.historyTop}px`,
    "--chat-history-width": `${composeLayout.historyWidth}px`,
    "--chat-history-height": `${composeLayout.historyHeight}px`,
  } as CSSProperties;

  return (
    <div className="chat-page" style={chatPageStyle}>
      <div className={`chat-page__shell${historyCollapsed ? " is-history-collapsed" : ""}`}>
        <div ref={chatHistoryRailRef} className="chat-history-rail">
          <aside className={`chat-history-panel${historyCollapsed ? " is-collapsed" : ""}`}>
            {!historyCollapsed ? (
              <>
                <div className="chat-history-panel__header">
                  <strong>会话记录</strong>
                  <div className="chat-history-panel__actions">
                    <button
                      className="chat-history-panel__new"
                      type="button"
                      aria-label="新建会话"
                      onClick={resetToEmptyConversation}
                    >
                      <span className="chat-history-panel__new-icon" aria-hidden="true">+</span>
                      <span>新建</span>
                    </button>
                  </div>
                </div>
                <div className="chat-history-panel__body">
                  {chatSessionsQuery.isLoading ? (
                    <p className="muted-text">正在加载会话记录…</p>
                  ) : chatSessionsQuery.data?.length ? (
                    <div className="chat-history-list">
                      {chatSessionsQuery.data.map((item) => (
                        <article
                          key={item.session_id}
                          className={`chat-history-item${item.session_id === activeSessionId ? " is-active" : ""}`}
                        >
                          <button
                            type="button"
                            className="chat-history-item__main"
                            aria-label={`打开会话：${item.title}`}
                            onClick={() => openSession(item.session_id)}
                          >
                            <strong title={item.title}>{item.title}</strong>
                          </button>
                          <div className="chat-history-item__menu-wrap">
                            <button
                              type="button"
                              className="chat-history-item__menu-trigger"
                              aria-label={`更多操作：${item.title}`}
                              aria-expanded={menuSessionId === item.session_id}
                              onClick={() =>
                                setMenuSessionId((current) => (current === item.session_id ? "" : item.session_id))
                              }
                            >
                              ...
                            </button>
                            {menuSessionId === item.session_id ? (
                              <div className="chat-history-item__menu" role="menu" aria-label={`会话操作：${item.title}`}>
                                <button type="button" disabled>
                                  重命名（暂未开放）
                                </button>
                                <button type="button" aria-label="删除会话" onClick={() => removeSession(item.session_id)}>
                                  删除会话
                                </button>
                              </div>
                            ) : null}
                          </div>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <EmptyState
                      title="暂无历史会话"
                      description="发送第一条消息后，这里会记录你的对话历史。"
                    />
                  )}
                </div>
              </>
            ) : null}
            <button
              className="chat-history-panel__divider-toggle"
              type="button"
              aria-label={historyCollapsed ? "展开会话栏" : "折叠会话栏"}
              onClick={() => setHistoryCollapsed((current) => !current)}
            >
              <span aria-hidden="true">{historyCollapsed ? ">>" : "<<"}</span>
            </button>
          </aside>
        </div>
        <div ref={chatWorkspaceRef} className="chat-page__workspace">
          <ConversationLayout
            notices={
              <>
                {systemSettingsQuery.data && !systemSettingsQuery.data.is_ready ? (
                  <ChatInlineBanner title="系统设置未完成">
                    Completion 与 Embedding 尚未配置完成。当前仍可查看界面，但实际生成会被后端阻断。
                  </ChatInlineBanner>
                ) : null}

                {errorMessage ? (
                  <ChatInlineBanner title="请求失败">{errorMessage}</ChatInlineBanner>
                ) : null}

                {sessionSourceBanner ? (
                  <ChatInlineBanner title={sessionSourceBanner.title}>
                    {sessionSourceBanner.body}
                  </ChatInlineBanner>
                ) : null}
              </>
            }
            stream={
              <div className="chat-stream-shell" data-testid="chat-stream-shell">
                <SurfaceCard className="chat-stream-card">
                  <div className="message-list">
                    {messages.map((message, index) => {
                      const isCompactAssistantMessage = message.role === "assistant" && !message.action;
                      const bodyClassName = [
                        "message-entry__body",
                        isCompactAssistantMessage ? "message-entry__body--compact" : "",
                        message.action ? "message-entry__body--has-action" : "",
                      ]
                        .filter(Boolean)
                        .join(" ");

                      return (
                        <div
                          key={`${message.role}-${index}-${message.content}`}
                          className={`message-entry message-entry--${message.role}`}
                        >
                          <div className="message-entry__role">{message.role === "assistant" ? "助手" : "我"}</div>
                          <div className={bodyClassName}>
                            {message.message_id ? (
                              <div className="message-entry__menu-wrap">
                                <button
                                  type="button"
                                  className="message-entry__menu-trigger"
                                  aria-label={`更多操作：消息 ${message.message_id}`}
                                  aria-expanded={menuMessageId === message.message_id}
                                  onClick={() =>
                                    setMenuMessageId((current) => (current === message.message_id ? "" : message.message_id ?? ""))
                                  }
                                >
                                  ...
                                </button>
                                {menuMessageId === message.message_id ? (
                                  <div className="message-entry__menu" role="menu" aria-label={`消息操作：${message.message_id}`}>
                                    <button type="button" onClick={() => runForkFromMessage(message.message_id ?? "")}>
                                      Fork 为新会话
                                    </button>
                                  </div>
                                ) : null}
                              </div>
                            ) : null}
                            <article
                              className={`message-bubble message-bubble--${message.role}${message.action ? " message-bubble--has-action" : ""}`}
                            >
                              {message.content ? <p>{message.content}</p> : null}
                              {message.action ? (
                                <div className="message-bubble__action">
                                  <ChatActionPanel
                                    action={message.action}
                                    disabled={isCurrentViewPending}
                                    onSubmitParam={(paramId, value) => {
                                      if (Array.isArray(value)) {
                                        runAction({ param_id: paramId, param_values: value });
                                        return;
                                      }
                                      runAction({ param_id: paramId, param_value: value });
                                    }}
                                    onSubmitOutline={(command, outline) => runAction({ command, outline_override: outline })}
                                    onSelectTemplate={(templateId) => runAction({ selected_template_id: templateId })}
                                    onCommand={(command, targetParamId) =>
                                      runAction({ command, target_param_id: targetParamId })
                                    }
                                  />
                                </div>
                              ) : null}
                            </article>
                            {message.created_at ? (
                              <div className="message-entry__time">{formatChatTimestamp(message.created_at)}</div>
                            ) : null}
                          </div>
                        </div>
                      );
                    })}
                    {isCurrentViewPending ? (
                      <div className="message-entry message-entry--assistant">
                        <div className="message-entry__role">助手</div>
                        <div className="message-entry__body">
                          <article className="message-bubble message-bubble--assistant message-bubble--pending" aria-live="polite">
                            <div className="message-pending" role="status">
                              <span>正在处理中</span>
                              <span className="message-pending__dots" aria-hidden="true">
                                <i />
                                <i />
                                <i />
                              </span>
                            </div>
                          </article>
                        </div>
                      </div>
                    ) : null}
                    <div ref={messageEndRef} />
                  </div>
                </SurfaceCard>
              </div>
            }
            composer={
              <div ref={composeDockRef} className="chat-compose-dock" data-testid="chat-compose-dock">
                <SurfaceCard className="chat-compose-card">
                  <div className="chat-compose">
                    <div className="chat-quick-actions">
                      {[
                        { id: "report_generation", label: "制作报告" },
                        { id: "smart_query", label: "智能问数" },
                        { id: "fault_diagnosis", label: "智能故障" },
                      ].map((item) => (
                        <button
                          key={item.id}
                          type="button"
                          className={`chat-quick-actions__button${preferredCapability === item.id ? " is-active" : ""}`}
                          aria-label={`快捷入口：${item.label}`}
                          onClick={() =>
                            setPreferredCapability((current) => (current === item.id ? "" : (item.id as typeof preferredCapability)))
                          }
                        >
                          {item.label}
                        </button>
                      ))}
                    </div>
                    <label className="sr-only" htmlFor="chat-input">
                      发送消息
                    </label>
                    <textarea
                      id="chat-input"
                      rows={3}
                      placeholder={INPUT_PLACEHOLDER}
                      value={draft}
                      disabled={isCurrentViewPending}
                      onChange={(event) => setDraft(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" && !event.shiftKey) {
                          event.preventDefault();
                          submitMessage();
                        }
                      }}
                    />
                    <button
                      className={`chat-send-button${isCurrentViewPending ? " is-pending" : ""}`}
                      type="button"
                      onClick={submitMessage}
                      disabled={isCurrentViewPending}
                      aria-label="发送"
                      aria-busy={isCurrentViewPending}
                    >
                      <span className="chat-send-button__glyph" aria-hidden="true" />
                      <span className="sr-only">发送</span>
                    </button>
                  </div>
                </SurfaceCard>
              </div>
            }
          />
        </div>
      </div>
    </div>
  );
}

function buildOptimisticActionMessage(payload: Omit<ChatRequest, "session_id">, latestAction: ChatAction | null) {
  if (payload.param_values?.length) {
    return payload.param_values.join("、");
  }
  if (payload.param_value?.trim()) {
    return payload.param_value.trim();
  }
  if (payload.selected_template_id && latestAction?.type === "show_template_candidates") {
    const candidate = latestAction.candidates.find((item) => item.template_id === payload.selected_template_id);
    return candidate ? `选择模板：${candidate.template_name}` : "选择模板";
  }
  if (payload.command === "prepare_outline_review" || payload.command === "confirm_generation") {
    return "确认参数并生成诉求";
  }
  if (payload.command === "edit_outline") {
    return "保存诉求";
  }
  if (payload.command === "confirm_outline_generation") {
    return "确认生成";
  }
  if (payload.command === "reset_params") {
    return "重置参数";
  }
  if (payload.command === "confirm_task_switch") {
    return "继续切换任务";
  }
  if (payload.command === "cancel_task_switch") {
    return "留在当前任务";
  }
  if (payload.command === "edit_param" && latestAction?.type === "review_outline") {
    return "返回改参数";
  }
  if (payload.command === "edit_param" && latestAction?.type === "review_params") {
    const param = latestAction.params.find((item) => item.id === payload.target_param_id);
    return param ? `编辑参数：${param.label}` : "编辑参数";
  }
  return "";
}

function appendOptimisticMessage(messages: ChatMessageItem[], content: string) {
  if (!content) {
    return messages;
  }
  return [...messages, { role: "user" as const, content, created_at: new Date().toISOString() }];
}

type ChatInlineBannerProps = {
  title: string;
  children: string;
};

function ChatInlineBanner({ title, children }: ChatInlineBannerProps) {
  return (
    <div className="chat-inline-banner" role="status">
      <strong>{title}</strong>
      <span>{children}</span>
    </div>
  );
}

function buildVisibleMessages(response: ChatResponse, fallbackUserContent = ""): ChatMessageItem[] {
  return normalizeVisibleMessages(response.messages ?? [], fallbackUserContent, response.reply, response.action ?? null);
}

function buildVisibleMessagesFromSession(session: ChatSessionPayload | ChatSessionDetail): ChatMessageItem[] {
  return normalizeVisibleMessages(session.messages ?? []);
}

function normalizeVisibleMessages(
  source: Array<{ role: "user" | "assistant"; content: string; action?: ChatAction | null; created_at?: string; message_id?: string; meta?: unknown }>,
  fallbackUserContent = "",
  fallbackReply = "",
  fallbackAction: ChatAction | null = null,
): ChatMessageItem[] {
  const normalized = source
    .filter((item) => {
      if (item.role !== "assistant" && item.role !== "user") {
        return false;
      }
      if (isContextStateMessage(item.meta)) {
        return false;
      }
      return Boolean(item.content) || Boolean(item.action);
    })
    .map((item) => ({
      role: item.role,
      content: item.content ?? "",
      action: item.action ?? null,
      created_at: item.created_at,
      message_id: item.message_id,
    }));

  if (!normalized.length) {
    const fallback = fallbackUserContent
      ? [{ role: "user" as const, content: fallbackUserContent, created_at: new Date().toISOString() }]
      : [];
    if (!fallbackReply && !fallbackAction) {
      return DEFAULT_MESSAGES;
    }
    return [...fallback, { role: "assistant", content: fallbackReply, action: fallbackAction }];
  }
  return normalized;
}

function isContextStateMessage(meta: unknown) {
  return typeof meta === "object" && meta !== null && "type" in meta && (meta as { type?: string }).type === "context_state";
}

function getSessionSourceBanner(meta: ChatForkMeta | null, sessionTitle: string) {
  if (!meta) {
    return null;
  }

  if (meta.source_kind === "update_from_instance") {
    return {
      title: "更新来源",
      body: `来源：${meta.source_title || sessionTitle || "未命名会话"} · 来自确认诉求`,
    };
  }

  return {
    title: "Fork 来源",
    body: `来源：${sessionTitle || meta.source_title || "未命名分支"} · ${meta.source_kind === "session_message" ? "来自历史消息" : "来自确认诉求"}`,
  };
}

function formatChatTimestamp(timestamp: string) {
  const value = new Date(timestamp);
  if (Number.isNaN(value.getTime())) {
    return "";
  }
  const now = new Date();
  const sameDay =
    value.getFullYear() === now.getFullYear()
    && value.getMonth() === now.getMonth()
    && value.getDate() === now.getDate();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  const hours = String(value.getHours()).padStart(2, "0");
  const minutes = String(value.getMinutes()).padStart(2, "0");
  if (sameDay) {
    return `${hours}:${minutes}`;
  }
  return `${month}-${day} ${hours}:${minutes}`;
}
