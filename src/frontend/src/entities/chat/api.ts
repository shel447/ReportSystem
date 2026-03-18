import { postJson } from "../../shared/api/http";
import type { ChatRequest, ChatResponse } from "./types";

export function sendChatMessage(payload: ChatRequest) {
  return postJson<ChatResponse>("/api/chat", payload);
}
