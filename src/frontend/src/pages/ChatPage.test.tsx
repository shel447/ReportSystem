import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ChatPage, mergeTemplateInstanceParameters } from "./ChatPage";

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

function createSseResponse(events: unknown[]) {
  return {
    ok: true,
    text: async () => events.map((event) => `event: message\ndata: ${JSON.stringify(event)}\n\n`).join(""),
  };
}

function systemSettingsResponse() {
  return {
    ok: true,
    json: async () => ({
      completion: { base_url: "", model: "", timeout_sec: 60, has_api_key: false, masked_api_key: "", configured: false },
      embedding: { base_url: "", model: "", timeout_sec: 60, has_api_key: false, masked_api_key: "", configured: false, use_completion_auth: true },
      is_ready: false,
      index_status: { ready_count: 0, error_count: 0 },
    }),
  };
}

describe("ChatPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("sends a question and renders the returned ask panel", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (url === "/rest/dev/system-settings") {
        return Promise.resolve(systemSettingsResponse());
      }
      if (url === "/rest/chatbi/v1/chat" && !init?.method) {
        return Promise.resolve({ ok: true, json: async () => [] });
      }
      if (url === "/rest/chatbi/v1/chat" && init?.method === "POST") {
        return Promise.resolve(createSseResponse([
          {
            conversationId: "conv_1",
            chatId: "chat_1",
            eventType: "status",
            sequence: 1,
            timestamp: 1713427200000,
            status: "waiting_user",
          },
          {
            conversationId: "conv_1",
            chatId: "chat_1",
            eventType: "ask",
            sequence: 2,
            timestamp: 1713427200001,
            status: "waiting_user",
            ask: {
              status: "pending",
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
          },
          {
            conversationId: "conv_1",
            chatId: "chat_1",
            eventType: "done",
            sequence: 3,
            timestamp: 1713427200002,
            status: "waiting_user",
          },
        ]));
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

  it("renders stream deltas from the sse channel", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (url === "/rest/dev/system-settings") {
        return Promise.resolve(systemSettingsResponse());
      }
      if (url === "/rest/chatbi/v1/chat" && !init?.method) {
        return Promise.resolve({ ok: true, json: async () => [] });
      }
      if (url === "/rest/chatbi/v1/chat" && init?.method === "POST") {
        return Promise.resolve(createSseResponse([
          {
            conversationId: "conv_delta",
            chatId: "chat_delta",
            eventType: "status",
            sequence: 1,
            timestamp: 1713427200000,
            status: "running",
          },
          {
            conversationId: "conv_delta",
            chatId: "chat_delta",
            eventType: "answer",
            sequence: 2,
            timestamp: 1713427200001,
            status: "running",
            delta: [{ action: "init_report", report: { reportId: "rpt_1", title: "网络运行日报" } }],
          },
          {
            conversationId: "conv_delta",
            chatId: "chat_delta",
            eventType: "answer",
            sequence: 3,
            timestamp: 1713427200002,
            status: "running",
            delta: [{ action: "add_section", parentCatalogId: "catalog_1", parentCatalog: [0], sections: [{ sectionId: "section_1", status: "finished", requirement: "总体运行态势" }] }],
          },
          {
            conversationId: "conv_delta",
            chatId: "chat_delta",
            eventType: "answer",
            sequence: 4,
            timestamp: 1713427200003,
            status: "finished",
            answer: {
              answerType: "REPORT",
              answer: {
                reportId: "rpt_1",
                status: "available",
                report: { basicInfo: { id: "rpt_1", schemaVersion: "1.0.0", mode: "published", status: "Success" }, catalogs: [], layout: { type: "grid", grid: { cols: 12, rowHeight: 24 } } },
                templateInstance: {
                  id: "ti_delta",
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
                  conversationId: "conv_delta",
                  status: "completed",
                  captureStage: "report_ready",
                  revision: 2,
                  parameters: [],
                  parameterConfirmation: { missingParameterIds: [], confirmed: true },
                  catalogs: [],
                  createdAt: "2026-04-18T09:00:00Z",
                  updatedAt: "2026-04-18T09:00:00Z",
                },
                documents: [],
                generationProgress: { totalSections: 1, completedSections: 1 },
              },
            },
          },
          {
            conversationId: "conv_delta",
            chatId: "chat_delta",
            eventType: "done",
            sequence: 5,
            timestamp: 1713427200004,
            status: "finished",
          },
        ]));
      }
      if (url === "/rest/chatbi/v1/chat/conv_delta") {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            conversationId: "conv_delta",
            title: "网络运行日报",
            status: "active",
            messages: [],
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    fireEvent.change(screen.getByLabelText("输入问题"), { target: { value: "生成网络运行日报" } });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    expect(await screen.findByText("增量生成进度")).toBeInTheDocument();
    expect(screen.getByText("初始化报告：网络运行日报")).toBeInTheDocument();
    expect(screen.getByText("新增章节：总体运行态势")).toBeInTheDocument();
  });

  it("renders multi-value scoped parameters and merges them back into the nested template instance", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (url === "/rest/dev/system-settings") {
        return Promise.resolve(systemSettingsResponse());
      }
      if (url === "/rest/chatbi/v1/chat" && !init?.method) {
        return Promise.resolve({ ok: true, json: async () => [] });
      }
      if (url === "/rest/chatbi/v1/chat" && init?.method === "POST") {
        const payload = JSON.parse(String(init.body));
        if (!payload.reply) {
          return Promise.resolve(createSseResponse([
            {
              conversationId: "conv_multi",
              chatId: "chat_multi_1",
              eventType: "status",
              sequence: 1,
              timestamp: 1713427200000,
              status: "waiting_user",
            },
            {
              conversationId: "conv_multi",
              chatId: "chat_multi_1",
              eventType: "ask",
              sequence: 2,
              timestamp: 1713427200001,
              status: "waiting_user",
              ask: {
                status: "pending",
                mode: "form",
                type: "fill_params",
                title: "请补充报告参数",
                text: "请补充参数：分析对象",
                parameters: [
                  {
                    id: "scope",
                    label: "分析对象",
                    inputType: "free_text",
                    required: true,
                    multi: true,
                    interactionMode: "form",
                    values: [],
                  },
                ],
                reportContext: {
                  templateInstance: {
                    id: "ti_multi",
                    schemaVersion: "template-instance.vNext-draft",
                    templateId: "tpl_scoped",
                    template: {
                      id: "tpl_scoped",
                      category: "network_operations",
                      name: "作用域参数模板",
                      description: "验证章节参数更新。",
                      schemaVersion: "template.v3",
                      parameters: [],
                      catalogs: [],
                    },
                    conversationId: "conv_multi",
                    status: "collecting_parameters",
                    captureStage: "fill_params",
                    revision: 1,
                    parameters: [],
                    parameterConfirmation: { missingParameterIds: ["scope"], confirmed: false },
                    catalogs: [
                      {
                        id: "catalog_overview",
                        title: "运行概览",
                        renderedTitle: "运行概览",
                        sections: [
                          {
                            id: "section_scope",
                            parameters: [
                              {
                                id: "scope",
                                label: "分析对象",
                                inputType: "free_text",
                                required: true,
                                multi: true,
                                interactionMode: "form",
                                values: [],
                              },
                            ],
                            outline: {
                              requirement: "分析{$scope.display}的总体运行态势。",
                              items: [],
                            },
                            runtimeContext: { bindings: [] },
                            skeletonStatus: "reusable",
                            userEdited: false,
                          },
                        ],
                      },
                    ],
                    createdAt: "2026-04-18T09:00:00Z",
                    updatedAt: "2026-04-18T09:00:00Z",
                  },
                },
              },
            },
            {
              conversationId: "conv_multi",
              chatId: "chat_multi_1",
              eventType: "done",
              sequence: 3,
              timestamp: 1713427200002,
              status: "waiting_user",
            },
          ]));
        }
        return Promise.resolve(createSseResponse([
          {
            conversationId: "conv_multi",
            chatId: "chat_multi_2",
            eventType: "status",
            sequence: 1,
            timestamp: 1713427200001,
            status: "waiting_user",
          },
          {
            conversationId: "conv_multi",
            chatId: "chat_multi_2",
            eventType: "done",
            sequence: 2,
            timestamp: 1713427200002,
            status: "waiting_user",
          },
        ]));
      }
      if (url === "/rest/chatbi/v1/chat/conv_multi") {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            conversationId: "conv_multi",
            title: "作用域参数模板",
            status: "active",
            messages: [
              { chatId: "chat_multi_1", role: "user", content: { question: "生成作用域参数报告" }, createdAt: "2026-04-18T09:00:00Z" },
              {
                chatId: "chat_multi_1a",
                role: "assistant",
                content: {
                  response: {
                    conversationId: "conv_multi",
                    chatId: "chat_multi_1",
                    status: "waiting_user",
                    steps: [],
                    ask: {
                      status: "pending",
                      mode: "form",
                      type: "fill_params",
                      title: "请补充报告参数",
                      text: "请补充参数：分析对象",
                      parameters: [
                        {
                          id: "scope",
                          label: "分析对象",
                          inputType: "free_text",
                          required: true,
                          multi: true,
                          interactionMode: "form",
                          values: [],
                        },
                      ],
                      reportContext: {
                        templateInstance: {
                          id: "ti_multi",
                          schemaVersion: "template-instance.vNext-draft",
                          templateId: "tpl_scoped",
                          template: {
                            id: "tpl_scoped",
                            category: "network_operations",
                            name: "作用域参数模板",
                            description: "验证章节参数更新。",
                            schemaVersion: "template.v3",
                            parameters: [],
                            catalogs: [],
                          },
                          conversationId: "conv_multi",
                          status: "collecting_parameters",
                          captureStage: "fill_params",
                          revision: 1,
                          parameters: [],
                          parameterConfirmation: { missingParameterIds: ["scope"], confirmed: false },
                          catalogs: [
                            {
                              id: "catalog_overview",
                              title: "运行概览",
                              renderedTitle: "运行概览",
                              sections: [
                                {
                                  id: "section_scope",
                                  parameters: [
                                    {
                                      id: "scope",
                                      label: "分析对象",
                                      inputType: "free_text",
                                      required: true,
                                      multi: true,
                                      interactionMode: "form",
                                      values: [],
                                    },
                                  ],
                                  outline: {
                                    requirement: "分析{$scope.display}的总体运行态势。",
                                    items: [],
                                  },
                                  runtimeContext: { bindings: [] },
                                  skeletonStatus: "reusable",
                                  userEdited: false,
                                },
                              ],
                            },
                          ],
                          createdAt: "2026-04-18T09:00:00Z",
                          updatedAt: "2026-04-18T09:00:00Z",
                        },
                      },
                    },
                    answer: null,
                    errors: [],
                    requestId: "req_multi_1",
                    timestamp: 1713427200000,
                    apiVersion: "v1",
                  },
                },
                createdAt: "2026-04-18T09:00:01Z",
              },
            ],
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    fireEvent.change(screen.getByLabelText("输入问题"), { target: { value: "生成作用域参数报告" } });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    expect(await screen.findByPlaceholderText("分析对象（每行一个）")).toBeInTheDocument();

    const updatedInstance = mergeTemplateInstanceParameters(
      {
        id: "ti_multi",
        schemaVersion: "template-instance.vNext-draft",
        templateId: "tpl_scoped",
        template: {
          id: "tpl_scoped",
          category: "network_operations",
          name: "作用域参数模板",
          description: "验证章节参数更新。",
          schemaVersion: "template.v3",
          parameters: [],
          catalogs: [],
        },
        conversationId: "conv_multi",
        status: "collecting_parameters",
        captureStage: "fill_params",
        revision: 1,
        parameters: [],
        parameterConfirmation: { missingParameterIds: ["scope"], confirmed: false },
        catalogs: [
          {
            id: "catalog_overview",
            title: "运行概览",
            renderedTitle: "运行概览",
            sections: [
              {
                id: "section_scope",
                parameters: [
                  {
                    id: "scope",
                    label: "分析对象",
                    inputType: "free_text",
                    required: true,
                    multi: true,
                    interactionMode: "form",
                    values: [],
                  },
                ],
                outline: {
                  requirement: "分析{$scope.display}的总体运行态势。",
                  items: [],
                },
                runtimeContext: { bindings: [] },
                skeletonStatus: "reusable",
                userEdited: false,
              },
            ],
          },
        ],
        createdAt: "2026-04-18T09:00:00Z",
        updatedAt: "2026-04-18T09:00:00Z",
      },
      [{
        id: "scope",
        label: "分析对象",
        inputType: "free_text",
        required: true,
        multi: true,
        interactionMode: "form",
        values: [
          { display: "华东", value: "华东", query: "华东" },
          { display: "华北", value: "华北", query: "华北" },
        ],
      }],
    );

    expect(updatedInstance.catalogs[0].sections?.[0].parameters?.[0].values).toEqual([
      { display: "华东", value: "华东", query: "华东" },
      { display: "华北", value: "华北", query: "华北" },
    ]);
  });

  it("locks replied ask messages and hides the active editor", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url === "/rest/dev/system-settings") {
        return Promise.resolve(systemSettingsResponse());
      }
      if (url === "/rest/chatbi/v1/chat") {
        return Promise.resolve({
          ok: true,
          json: async () => [{ conversationId: "conv_replied", title: "已回复追问", status: "active", lastMessagePreview: "请确认报告诉求" }],
        });
      }
      if (url === "/rest/chatbi/v1/chat/conv_replied") {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            conversationId: "conv_replied",
            title: "已回复追问",
            status: "active",
            messages: [
              {
                chatId: "chat_replied_1",
                role: "assistant",
                createdAt: "2026-04-18T09:00:00Z",
                content: {
                  response: {
                    conversationId: "conv_replied",
                    chatId: "chat_replied_1",
                    status: "waiting_user",
                    steps: [],
                    ask: {
                      status: "replied",
                      mode: "form",
                      type: "confirm_params",
                      title: "请确认报告诉求",
                      text: "请确认报告诉求后开始生成。",
                      parameters: [],
                      reportContext: {
                        templateInstance: {
                          id: "ti_replied",
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
                          conversationId: "conv_replied",
                          status: "ready_for_confirmation",
                          captureStage: "confirm_params",
                          revision: 1,
                          parameters: [],
                          parameterConfirmation: { missingParameterIds: [], confirmed: false },
                          catalogs: [],
                          createdAt: "2026-04-18T09:00:00Z",
                          updatedAt: "2026-04-18T09:00:00Z",
                        },
                      },
                    },
                    answer: null,
                    errors: [],
                    requestId: "req_replied",
                    timestamp: 1713427200000,
                    apiVersion: "v1",
                  },
                },
              },
            ],
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    const buttons = await screen.findAllByRole("button", { name: /已回复追问/i });
    fireEvent.click(buttons[0]);

    expect(await screen.findByText("该追问已被后续回复消费，当前会话中不可继续修改。")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "确认并生成" })).not.toBeInTheDocument();
  });
});
