import { deleteJson, postJson, requestJson } from "../../shared/api/http";
import type { ChatForkRequest, ChatForkResponse, ChatRequest, ChatResponse, ChatSessionDetail, ChatSessionSummary } from "./types";

export function sendChatMessage(payload: ChatRequest) {
  return postJson<ChatResponse>("/api/chat", payload);
}

export function fetchChatSessions() {
  return requestJson<ChatSessionSummary[]>("/api/chat");
}

export function fetchChatSession(sessionId: string) {
  return requestJson<ChatSessionDetail>(`/api/chat/${sessionId}`);
}

export function deleteChatSession(sessionId: string) {
  return deleteJson(`/api/chat/${sessionId}`);
}

export function forkChatSession(payload: ChatForkRequest) {
  return postJson<ChatForkResponse>("/api/chat/forks", payload);
}
