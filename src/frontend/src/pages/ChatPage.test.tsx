import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ChatPage } from "./ChatPage";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ChatPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("sends a question and renders the returned ask panel", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (url === "/rest/dev/system-settings") {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            completion: { base_url: "", model: "", timeout_sec: 60, has_api_key: false, masked_api_key: "", configured: false },
            embedding: { base_url: "", model: "", timeout_sec: 60, has_api_key: false, masked_api_key: "", configured: false, use_completion_auth: true },
            is_ready: false,
            index_status: { ready_count: 0, error_count: 0 },
          }),
        });
      }
      if (url === "/rest/chatbi/v1/chat" && !init?.method) {
        return Promise.resolve({ ok: true, json: async () => [] });
      }
      if (url === "/rest/chatbi/v1/chat" && init?.method === "POST") {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            conversationId: "conv_1",
            chatId: "chat_1",
            status: "waiting_user",
            steps: [],
            ask: {
              mode: "form",
              type: "fill_params",
              title: "请补充报告参数",
              text: "请补充参数：报告日期",
              parameters: [
                {
                  id: "report_date",
                  label: "报告日期",
                  inputType: "date",
                  required: true,
                  multi: false,
                  interactionMode: "form",
                  values: [],
                },
              ],
              reportContext: {
                templateInstance: {
                  id: "ti_1",
                  schemaVersion: "template-instance.vNext-draft",
                  templateId: "tpl_network_daily",
                  template: {
                    id: "tpl_network_daily",
                    category: "network_operations",
                    name: "网络运行日报",
                    description: "面向网络运维中心的统一日报模板。",
                    schemaVersion: "template.v3",
                    parameters: [],
                    catalogs: [],
                  },
                  conversationId: "conv_1",
                  status: "collecting_parameters",
                  captureStage: "fill_params",
                  revision: 1,
                  parameters: [],
                  parameterConfirmation: { missingParameterIds: ["report_date"], confirmed: false },
                  catalogs: [],
                  createdAt: "2026-04-18T09:00:00Z",
                  updatedAt: "2026-04-18T09:00:00Z",
                },
              },
            },
            answer: null,
            errors: [],
            requestId: "req_1",
            timestamp: 1713427200000,
            apiVersion: "v1",
          }),
        });
      }
      if (url === "/rest/chatbi/v1/chat/conv_1") {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            conversationId: "conv_1",
            title: "网络运行日报",
            status: "active",
            messages: [{ chatId: "chat_1", role: "user", content: { question: "生成网络运行日报" }, createdAt: "2026-04-18T09:00:00Z" }],
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    fireEvent.change(screen.getByLabelText("输入问题"), { target: { value: "生成网络运行日报" } });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    expect(await screen.findByText("请补充报告参数")).toBeInTheDocument();
    expect(screen.getByLabelText("报告日期")).toBeInTheDocument();
    expect(screen.getByText("当前模板实例")).toBeInTheDocument();
  });
});
