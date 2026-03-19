import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { sendChatMessage } from "../entities/chat/api";
import type { ChatAction, ChatMessageItem, ChatRequest, ChatResponse } from "../entities/chat/types";
import { fetchSystemSettings } from "../entities/system-settings/api";
import { SurfaceCard } from "../shared/ui/SurfaceCard";
import { ChatActionPanel } from "../features/chat-report-flow/components/ChatActionPanel";
import { ConversationLayout } from "../shared/layouts/ConversationLayout";

const WELCOME_MESSAGE = "您好！我是您的智能报告助手。";
const INPUT_PLACEHOLDER = "输入消息，例如：制作设备巡检报告";

export function ChatPage() {
  const [draft, setDraft] = useState("");
  const [sessionId, setSessionId] = useState("");
  const chatPageRef = useRef<HTMLDivElement | null>(null);
  const composeDockRef = useRef<HTMLDivElement | null>(null);
  const messageEndRef = useRef<HTMLDivElement | null>(null);
  const [messages, setMessages] = useState<ChatMessageItem[]>([
    {
      role: "assistant",
      content: WELCOME_MESSAGE,
    },
  ]);
  const [errorMessage, setErrorMessage] = useState("");
  const [composeLayout, setComposeLayout] = useState(() => ({
    left: 0,
    width: typeof window !== "undefined" ? window.innerWidth : 0,
    reserve: 176,
  }));

  const systemSettingsQuery = useQuery({
    queryKey: ["system-settings"],
    queryFn: fetchSystemSettings,
  });

  const chatMutation = useMutation({
    mutationFn: (payload: ChatRequest) => sendChatMessage(payload),
  });

  const latestAction = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const item = messages[index];
      if (item.role === "assistant" && item.action) {
        return item.action;
      }
    }
    return null;
  }, [messages]);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView?.({ block: "end" });
  }, [messages]);

  useLayoutEffect(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    const measure = () => {
      const container = chatPageRef.current;
      const composeDock = composeDockRef.current;
      if (!container || !composeDock) {
        return;
      }

      const containerRect = container.getBoundingClientRect();
      const composeRect = composeDock.getBoundingClientRect();
      const nextLayout = {
        left: Math.max(containerRect.left, 0),
        width: Math.max(containerRect.width, 0),
        reserve: Math.max(Math.ceil(composeRect.height), 176),
      };

      setComposeLayout((current) => {
        if (
          current.left === nextLayout.left
          && current.width === nextLayout.width
          && current.reserve === nextLayout.reserve
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
    if (resizeObserver && chatPageRef.current && composeDockRef.current) {
      resizeObserver.observe(chatPageRef.current);
      resizeObserver.observe(composeDockRef.current);
    }

    return () => {
      window.removeEventListener("resize", handleResize);
      resizeObserver?.disconnect();
    };
  }, []);

  const sendPayload = (payload: Omit<ChatRequest, "session_id">, optimisticContent: string) => {
    const request: ChatRequest = {
      session_id: sessionId || undefined,
      ...payload,
    };

    setErrorMessage("");
    if (optimisticContent) {
      setMessages((current) => appendOptimisticMessage(current, optimisticContent));
    }

    chatMutation.mutate(request, {
      onSuccess: (response) => {
        setErrorMessage("");
        setSessionId(response.session_id);
        setMessages(buildVisibleMessages(response, optimisticContent));
      },
      onError: (error) => {
        setErrorMessage(error instanceof Error ? error.message : "对话请求失败。");
      },
    });
  };

  const submitMessage = () => {
    const nextMessage = draft.trim();
    if (!nextMessage || chatMutation.isPending) {
      return;
    }
    setDraft("");
    sendPayload(
      {
        message: nextMessage,
      },
      nextMessage,
    );
  };

  const runAction = (payload: Omit<ChatRequest, "session_id">) => {
    sendPayload(payload, buildOptimisticActionMessage(payload, latestAction));
  };

  const chatPageStyle = {
    "--chat-compose-left": `${composeLayout.left}px`,
    "--chat-compose-width": `${composeLayout.width}px`,
    "--chat-compose-reserve": `${composeLayout.reserve}px`,
  } as CSSProperties;

  return (
    <div ref={chatPageRef} className="chat-page" style={chatPageStyle}>
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
          </>
        }
        stream={
          <div className="chat-stream-shell" data-testid="chat-stream-shell">
            <SurfaceCard className="chat-stream-card">
              <div className="message-list">
                {messages.map((message, index) => (
                  <article
                    key={`${message.role}-${index}-${message.content}`}
                    className={`message-bubble message-bubble--${message.role}${message.action ? " message-bubble--has-action" : ""}`}
                  >
                    <div className="message-bubble__meta">{message.role === "assistant" ? "助手" : "我"}</div>
                    {message.content ? <p>{message.content}</p> : null}
                    {message.action ? (
                      <div className="message-bubble__action">
                        <ChatActionPanel
                          action={message.action}
                          disabled={chatMutation.isPending}
                          onSubmitParam={(paramId, value) => {
                            if (Array.isArray(value)) {
                              runAction({ param_id: paramId, param_values: value });
                              return;
                            }
                            runAction({ param_id: paramId, param_value: value });
                          }}
                          onSelectTemplate={(templateId) => runAction({ selected_template_id: templateId })}
                          onCommand={(command, targetParamId) =>
                            runAction({ command, target_param_id: targetParamId })
                          }
                        />
                      </div>
                    ) : null}
                  </article>
                ))}
                {chatMutation.isPending ? (
                  <article className="message-bubble message-bubble--assistant message-bubble--pending" aria-live="polite">
                    <div className="message-bubble__meta">助手</div>
                    <div className="message-pending" role="status">
                      <span>正在处理中</span>
                      <span className="message-pending__dots" aria-hidden="true">
                        <i />
                        <i />
                        <i />
                      </span>
                    </div>
                  </article>
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
                <label className="sr-only" htmlFor="chat-input">
                  发送消息
                </label>
                <textarea
                  id="chat-input"
                  rows={3}
                  placeholder={INPUT_PLACEHOLDER}
                  value={draft}
                  disabled={chatMutation.isPending}
                  onChange={(event) => setDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      submitMessage();
                    }
                  }}
                />
                <button
                  className={`chat-send-button${chatMutation.isPending ? " is-pending" : ""}`}
                  type="button"
                  onClick={submitMessage}
                  disabled={chatMutation.isPending}
                  aria-label="发送"
                  aria-busy={chatMutation.isPending}
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
  if (payload.command === "confirm_generation") {
    return "确认生成";
  }
  if (payload.command === "reset_params") {
    return "重置参数";
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
  return [...messages, { role: "user" as const, content }];
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
  const source = response.messages ?? [];
  const normalized = source
    .filter((item) => {
      if (item.role !== "assistant" && item.role !== "user") {
        return false;
      }
      return Boolean(item.content) || Boolean(item.action);
    })
    .map((item) => ({
      role: item.role,
      content: item.content ?? "",
      action: item.action ?? null,
    }));

  if (!normalized.length) {
    const fallback = fallbackUserContent ? [{ role: "user" as const, content: fallbackUserContent }] : [];
    return [...fallback, { role: "assistant", content: response.reply, action: response.action ?? null }];
  }
  return normalized;
}
