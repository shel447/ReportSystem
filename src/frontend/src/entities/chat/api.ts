import { chatbiPath, deleteJson, postJson, requestJson } from "../../shared/api/http";
import type { ChatForkRequest, ChatRequest, ChatResponse, ConversationDetail, ConversationSummary } from "./types";

export function fetchConversations() {
  return requestJson<ConversationSummary[]>(chatbiPath("/chat"));
}

export function fetchConversation(conversationId: string) {
  return requestJson<ConversationDetail>(chatbiPath(`/chat/${encodeURIComponent(conversationId)}`));
}

export function deleteConversation(conversationId: string) {
  return deleteJson(chatbiPath(`/chat/${encodeURIComponent(conversationId)}`));
}

export function forkConversation(payload: ChatForkRequest) {
  return postJson<{ conversationId: string }>(chatbiPath("/chat/forks"), payload);
}

export function sendChatMessage(payload: ChatRequest) {
  return postJson<ChatResponse>(chatbiPath("/chat"), {
    chatId: payload.chatId ?? buildChatId(),
    instruction: payload.instruction ?? "generate_report",
    attachments: payload.attachments ?? [],
    histories: payload.histories ?? [],
    requestId: payload.requestId ?? buildRequestId(),
    apiVersion: payload.apiVersion ?? "v1",
    ...payload,
  });
}

function buildChatId() {
  return `chat_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function buildRequestId() {
  return `req_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}
