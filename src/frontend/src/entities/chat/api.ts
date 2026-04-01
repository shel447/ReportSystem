import { chatbiPath, deleteJson, postJson, requestJson } from "../../shared/api/http";
import type { ChatForkRequest, ChatForkResponse, ChatRequest, ChatResponse, ChatSessionDetail, ChatSessionSummary } from "./types";

export function sendChatMessage(payload: ChatRequest) {
  return postJson<ChatResponse>(chatbiPath("/chat"), payload);
}

export function fetchChatSessions() {
  return requestJson<ChatSessionSummary[]>(chatbiPath("/chat"));
}

export function fetchChatSession(sessionId: string) {
  return requestJson<ChatSessionDetail>(chatbiPath(`/chat/${sessionId}`));
}

export function deleteChatSession(sessionId: string) {
  return deleteJson(chatbiPath(`/chat/${sessionId}`));
}

export function forkChatSession(payload: ChatForkRequest) {
  return postJson<ChatForkResponse>(chatbiPath("/chat/forks"), payload);
}
