import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { sendChatMessage } from "../entities/chat/api";
import type { ChatAction, ChatMessageItem, ChatRequest, ChatResponse } from "../entities/chat/types";
import { fetchSystemSettings } from "../entities/system-settings/api";
import { PageSection } from "../shared/ui/PageSection";
import { StatusBanner } from "../shared/ui/StatusBanner";
import { SurfaceCard } from "../shared/ui/SurfaceCard";
import { ChatActionPanel } from "../features/chat-report-flow/components/ChatActionPanel";

const WELCOME_MESSAGE = "您好！我是您的智能报告助手。";
const INPUT_PLACEHOLDER = "输入消息，例如：制作设备巡检报告";

export function ChatPage() {
  const [draft, setDraft] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState<ChatMessageItem[]>([
    {
      role: "assistant",
      content: WELCOME_MESSAGE,
    },
  ]);
  const [errorMessage, setErrorMessage] = useState("");

  const systemSettingsQuery = useQuery({
    queryKey: ["system-settings"],
    queryFn: fetchSystemSettings,
  });

  const chatMutation = useMutation({
    mutationFn: (payload: ChatRequest) => sendChatMessage(payload),
    onSuccess: (response) => {
      setErrorMessage("");
      setSessionId(response.session_id);
      setMessages(buildVisibleMessages(response));
      setDraft("");
    },
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : "对话请求失败。");
    },
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

  const submitMessage = () => {
    if (!draft.trim() || chatMutation.isPending) {
      return;
    }
    chatMutation.mutate({
      session_id: sessionId || undefined,
      message: draft.trim(),
    });
  };

  const runAction = (payload: Omit<ChatRequest, "session_id">) => {
    chatMutation.mutate({
      session_id: sessionId || undefined,
      ...payload,
    });
  };

  return (
    <div className="chat-page">
      <PageSection
        title="对话助手"
        description="从自然语言需求进入模板匹配、结构化补参与文档下载的完整链路。"
      >
        <div className="chat-layout">
          <SurfaceCard className="hero-card">
            <p className="section-kicker">Conversation Workflow</p>
            <h3>模板匹配、补参确认与 Markdown 生成集中在同一条工作流里。</h3>
            <p>
              先锁定模板，再逐项补齐必填参数，最后确认生成并下载。对话区会持续保留上下文，不再跳出零散面板。
            </p>
          </SurfaceCard>

          {systemSettingsQuery.data && !systemSettingsQuery.data.is_ready ? (
            <StatusBanner tone="warning" title="系统设置未完成">
              Completion 与 Embedding 尚未配置完成。当前仍可查看界面，但实际生成会被后端阻断。
            </StatusBanner>
          ) : null}

          {errorMessage ? (
            <StatusBanner tone="warning" title="请求失败">
              {errorMessage}
            </StatusBanner>
          ) : null}

          <SurfaceCard className="chat-surface">
            <div className="message-list">
              {messages.map((message, index) => (
                <article
                  key={`${message.role}-${index}-${message.content}`}
                  className={`message-bubble message-bubble--${message.role}`}
                >
                  <div className="message-bubble__meta">{message.role === "assistant" ? "助手" : "我"}</div>
                  {message.content ? <p>{message.content}</p> : null}
                  {message.action ? (
                    <div className="message-bubble__action">
                      <ChatActionPanel
                        action={message.action}
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
            </div>

            <div className="chat-compose">
              <label className="sr-only" htmlFor="chat-input">
                发送消息
              </label>
              <textarea
                id="chat-input"
                placeholder={INPUT_PLACEHOLDER}
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    submitMessage();
                  }
                }}
              />
              <div className="compose-footer">
                <span className="compose-hint">
                  {latestAction?.type === "ask_param" ? "当前处于补参阶段" : "支持直接输入自然语言需求"}
                </span>
                <button className="primary-button" type="button" onClick={submitMessage} disabled={chatMutation.isPending}>
                  {chatMutation.isPending ? "发送中..." : "发送"}
                </button>
              </div>
            </div>
          </SurfaceCard>
        </div>
      </PageSection>
    </div>
  );
}

function buildVisibleMessages(response: ChatResponse): ChatMessageItem[] {
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
    return [{ role: "assistant", content: response.reply, action: response.action ?? null }];
  }
  return normalized;
}
