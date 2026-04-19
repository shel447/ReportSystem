import { ApiError, chatbiPath, deleteJson, postJson, requestJson } from "../../shared/api/http";
import type { ChatForkRequest, ChatRequest, ChatResponse, ChatStreamEvent, ConversationDetail, ConversationSummary } from "./types";

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

export async function sendChatMessageStream(
  payload: ChatRequest,
  options: {
    onEvent?: (event: ChatStreamEvent) => void;
  } = {},
) {
  const requestPayload = {
    chatId: payload.chatId ?? buildChatId(),
    instruction: payload.instruction ?? "generate_report",
    attachments: payload.attachments ?? [],
    histories: payload.histories ?? [],
    requestId: payload.requestId ?? buildRequestId(),
    apiVersion: payload.apiVersion ?? "v1",
    ...payload,
  };
  const response = await fetch(chatbiPath("/chat"), {
    method: "POST",
    headers: {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
      "X-User-Id": "default",
    },
    body: JSON.stringify(requestPayload),
  });
  if (!response.ok) {
    let message = `请求失败 (${response.status})`;
    try {
      const payload = await response.json();
      if (typeof payload?.detail === "string") {
        message = payload.detail;
      }
    } catch {
      // 保持默认错误文本。
    }
    throw new ApiError(message, response.status);
  }

  const finalResponse = createEmptyChatResponse(requestPayload);
  await consumeChatEventStream(response, (event) => {
    applyStreamEvent(finalResponse, event);
    options.onEvent?.(event);
  });
  return finalResponse;
}

function buildChatId() {
  return `chat_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function buildRequestId() {
  return `req_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function createEmptyChatResponse(payload: Record<string, unknown>): ChatResponse {
  return {
    conversationId: String(payload.conversationId ?? ""),
    chatId: String(payload.chatId ?? ""),
    status: "running",
    steps: [],
    ask: null,
    answer: null,
    errors: [],
    requestId: typeof payload.requestId === "string" ? payload.requestId : undefined,
    timestamp: Date.now(),
    apiVersion: typeof payload.apiVersion === "string" ? payload.apiVersion : "v1",
  };
}

function applyStreamEvent(target: ChatResponse, event: ChatStreamEvent) {
  target.conversationId = event.conversationId;
  target.chatId = event.chatId;
  target.status = event.status;
  target.timestamp = event.timestamp;
  if (event.ask !== undefined) {
    target.ask = event.ask;
  }
  if (event.answer !== undefined) {
    target.answer = event.answer;
  }
  if (event.steps !== undefined) {
    target.steps = event.steps;
  }
}

async function consumeChatEventStream(response: Response, onEvent: (event: ChatStreamEvent) => void) {
  if (!response.body) {
    const text = typeof response.text === "function" ? await response.text() : "";
    for (const event of parseSsePayload(text)) {
      onEvent(event);
    }
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const event = parseSseFrame(frame);
      if (event) {
        onEvent(event);
      }
    }
  }
  buffer += decoder.decode();
  for (const event of parseSsePayload(buffer)) {
    onEvent(event);
  }
}

export function parseSsePayload(payload: string): ChatStreamEvent[] {
  return payload
    .split("\n\n")
    .map((frame) => parseSseFrame(frame))
    .filter((event): event is ChatStreamEvent => Boolean(event));
}

function parseSseFrame(frame: string): ChatStreamEvent | null {
  const lines = frame
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) {
    return null;
  }
  const data = lines
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim())
    .join("\n");
  if (!data) {
    return null;
  }
  return JSON.parse(data) as ChatStreamEvent;
}
