import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ChatPage, mergeTemplateInstanceParameters } from "./ChatPage";

vi.mock("@cloudsop/bi-engine", () => ({
  BIEngine: ({ schema }: { schema: { id: string } }) => <div data-testid="bi-component">{schema.id}</div>,
}));

vi.mock("@cloudsop/bi-designer", () => ({
  applyAutoLayoutToDoc: (report: Record<string, unknown>) => report,
  createEditorStore: (doc: Record<string, unknown>) => ({
    getState: () => ({ doc, docRevision: 1, isDirty: false, setDoc: vi.fn(), getDoc: () => doc }),
    subscribe: () => () => undefined,
  }),
  PptSlideFrame: ({ slide }: { slide: { id: string } }) => <div data-testid="ppt-slide">{slide.id}</div>,
  PptEditor: () => <div data-testid="ppt-editor">PPT Designer</div>,
  ReportEditor: () => <div data-testid="report-editor">Report Designer</div>,
}));

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

function piuContent(answers: Record<string, unknown>) {
  return JSON.stringify({ piuName: "ReportGenerationPIU", answers });
}

describe("ChatPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
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
            records: [{ chatId: "chat_1", question: "生成网络运行日报", askTime: "2026-04-18T09:00:00Z", answers: [] }],
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
    expect(screen.getByText("BI Engine 演示")).toBeInTheDocument();
  });

  it("queues a follow-up question while the current chat is still streaming", async () => {
    let resolveFirstPost: ((value: unknown) => void) | null = null;
    let postCount = 0;
    const postedQuestions: string[] = [];
    const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (url === "/rest/dev/system-settings") {
        return Promise.resolve(systemSettingsResponse());
      }
      if (url === "/rest/chatbi/v1/chat" && !init?.method) {
        return Promise.resolve({ ok: true, json: async () => [] });
      }
      if (url === "/rest/chatbi/v1/chat" && init?.method === "POST") {
        const payload = JSON.parse(String(init.body));
        postedQuestions.push(String(payload.question || ""));
        postCount += 1;
        if (postCount === 1) {
          return new Promise((resolve) => {
            resolveFirstPost = resolve;
          });
        }
        return Promise.resolve(createSseResponse([
          { conversationId: "conv_queue", chatId: payload.chatId, eventType: "status", sequence: 1, timestamp: 1, status: "running" },
          { conversationId: "conv_queue", chatId: payload.chatId, eventType: "done", sequence: 2, timestamp: 2, status: "finished" },
        ]));
      }
      if (url === "/rest/chatbi/v1/chat/conv_queue") {
        return Promise.resolve({ ok: true, json: async () => ({ conversationId: "conv_queue", title: "队列测试", status: "active", records: [] }) });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    fireEvent.change(screen.getByLabelText("输入问题"), { target: { value: "第一条" } });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));
    await waitFor(() => expect(postCount).toBe(1));

    fireEvent.change(screen.getByLabelText("输入问题"), { target: { value: "第二条" } });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    expect(await screen.findByText(/排队中 1 条/)).toBeInTheDocument();
    expect(postCount).toBe(1);

    await act(async () => {
      resolveFirstPost?.(createSseResponse([
        { conversationId: "conv_queue", chatId: "chat_first", eventType: "status", sequence: 1, timestamp: 1, status: "running" },
        { conversationId: "conv_queue", chatId: "chat_first", eventType: "done", sequence: 2, timestamp: 2, status: "finished" },
      ]));
    });

    await waitFor(() => expect(postCount).toBe(2));
    expect(postedQuestions).toEqual(["第一条", "第二条"]);
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
            delta: [{ action: "add_catalog", parentCatalogId: null, parentCatalog: null, catalogs: [{ catalogId: "catalog_1", title: "运行概览" }] }],
          },
          {
            conversationId: "conv_delta",
            chatId: "chat_delta",
            eventType: "answer",
            sequence: 4,
            timestamp: 1713427200003,
            status: "running",
            delta: [{ action: "add_section", parentCatalogId: "catalog_1", parentCatalog: [0], sections: [{ sectionId: "section_1", status: "finished", requirement: "总体运行态势" }] }],
          },
          {
            conversationId: "conv_delta",
            chatId: "chat_delta",
            eventType: "answer",
            sequence: 5,
            timestamp: 1713427200004,
            status: "finished",
            answer: {
              answerType: "REPORT",
              answer: {
                reportId: "rpt_1",
                status: "available",
                report: { structureType: "flow", basicInfo: { id: "rpt_1", schemaVersion: "1.0.0", mode: "published", status: "Success", name: "网络运行日报" }, catalogs: [{ id: "catalog_1", name: "运行概览", sections: [{ id: "section_1", title: "总体运行态势", components: [] }] }], layout: { type: "grid", grid: { cols: 12, rowHeight: 24 } } },
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
            sequence: 6,
            timestamp: 1713427200005,
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
            records: [],
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    fireEvent.change(screen.getByLabelText("输入问题"), { target: { value: "生成网络运行日报" } });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    await waitFor(() => expect(screen.getByLabelText("报告预览编辑区")).toBeInTheDocument());
    expect(screen.getByRole("tab", { name: "预览" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "详情" }));
    expect(await screen.findByText("报告结构")).toBeInTheDocument();
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
        const requestChatId = String(payload.chatId);
        if (!payload.reply) {
          return Promise.resolve(createSseResponse([
            {
              conversationId: "conv_multi",
              chatId: requestChatId,
              eventType: "status",
              sequence: 1,
              timestamp: 1713427200000,
              status: "waiting_user",
            },
            {
              conversationId: "conv_multi",
              chatId: requestChatId,
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
                              requirement: "分析{$scope.label}的总体运行态势。",
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
              chatId: requestChatId,
              eventType: "done",
              sequence: 3,
              timestamp: 1713427200002,
              status: "waiting_user",
            },
          ]));
        }
        expect(payload.reply.sourceChatId).toBeTruthy();
        expect(payload.reply.parameters.scope).toEqual(["华东", "华北"]);
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
            records: [
              {
                chatId: "chat_multi_1",
                question: "生成作用域参数报告",
                askTime: "2026-04-18T09:00:00Z",
                answers: [
                  {
                    type: "TEXT",
                    answerTime: "2026-04-18T09:00:00Z",
                    content: "已收到请求，正在分析网络质量。",
                  },
                  {
                    type: "PIU",
                    answerTime: "2026-04-18T09:00:01Z",
                    content: piuContent({
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
                                    requirement: "分析{$scope.label}的总体运行态势。",
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
                      delta: [],
                      answer: null,
                      errors: [],
                    }),
                  },
                ],
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
                  requirement: "分析{$scope.label}的总体运行态势。",
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
          { label: "华东", value: "华东", query: "华东" },
          { label: "华北", value: "华北", query: "华北" },
        ],
      }],
    );

    expect(updatedInstance.catalogs[0].sections?.[0].parameters?.[0].values).toEqual([
      { label: "华东", value: "华东", query: "华东" },
      { label: "华北", value: "华北", query: "华北" },
    ]);
  });

  it("locks replied ask messages and hides the active editor", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (url === "/rest/dev/system-settings") {
        return Promise.resolve(systemSettingsResponse());
      }
      if (url === "/rest/chatbi/v1/chat" && init?.method === "POST") {
        const payload = JSON.parse(String(init.body));
        expect(payload.reply.type).toBe("fill_params");
        expect(payload.question).toBe("补充参数：区域=华北");
        return Promise.resolve(createSseResponse([
          { conversationId: "conv_dynamic_options", chatId: payload.chatId, eventType: "status", sequence: 1, timestamp: 1, status: "waiting_user" },
          { conversationId: "conv_dynamic_options", chatId: payload.chatId, eventType: "done", sequence: 2, timestamp: 2, status: "waiting_user" },
        ]));
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
            records: [
              {
                chatId: "chat_replied_1",
                question: "请确认报告诉求",
                askTime: "2026-04-18T09:00:00Z",
                answers: [
                  {
                    type: "PIU",
                    answerTime: "2026-04-18T09:00:00Z",
                    content: piuContent({
                      steps: [],
                      ask: {
                        status: "replied",
                        mode: "form",
                        type: "confirm_params",
                        title: "请确认报告诉求",
                        text: "请确认报告诉求后开始生成。",
                        parameters: [
                          {
                            id: "reportDate",
                            label: "统计日期",
                            inputType: "date",
                            required: true,
                            multi: false,
                            interactionMode: "form",
                            values: [{ label: "2026-04-18", value: "2026-04-18", query: "dt='2026-04-18'" }],
                          },
                        ],
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
                            parameters: [
                              {
                                id: "reportDate",
                                label: "统计日期",
                                inputType: "date",
                                required: true,
                                multi: false,
                                interactionMode: "form",
                                values: [{ label: "2026-04-18", value: "2026-04-18", query: "dt='2026-04-18'" }],
                              },
                            ],
                            parameterConfirmation: { missingParameterIds: [], confirmed: false },
                            catalogs: [],
                            createdAt: "2026-04-18T09:00:00Z",
                            updatedAt: "2026-04-18T09:00:00Z",
                          },
                        },
                      },
                      delta: [],
                      answer: null,
                      errors: [],
                    }),
                  },
                ],
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

    expect(await screen.findByText("已回复")).toBeInTheDocument();
    expect(screen.getByLabelText("统计日期")).toBeDisabled();
    expect(screen.getByDisplayValue("2026-04-18")).toBeDisabled();
    expect(screen.queryByRole("button", { name: "确认并生成" })).not.toBeInTheDocument();
  });

  it("renders confirm generation as a new user and assistant turn", async () => {
    const templateInstance = {
      id: "ti_confirm",
      schemaVersion: "template-instance.vNext-draft",
      templateId: "tpl_network_status",
      template: {
        id: "tpl_network_status",
        category: "network_operations",
        name: "网络运行状态报告",
        description: "网络运行状态报告模板。",
        schemaVersion: "template.v3",
        parameters: [],
        catalogs: [],
      },
      conversationId: "conv_confirm",
      status: "ready_for_confirmation",
      captureStage: "confirm_params",
      revision: 1,
      parameters: [],
      parameterConfirmation: { missingParameterIds: [], confirmed: false },
      catalogs: [],
      createdAt: "2026-04-18T09:00:00Z",
      updatedAt: "2026-04-18T09:00:00Z",
    };
    const reportAnswer = {
      answerType: "REPORT",
      answer: {
        reportId: "rpt_confirm",
        status: "available",
        report: {
          structureType: "flow",
          basicInfo: { id: "rpt_confirm", schemaVersion: "1.0.0", mode: "published", status: "Success", name: "网络运行状态报告" },
          catalogs: [],
          layout: { type: "grid", grid: { cols: 12, rowHeight: 24 } },
        },
        templateInstance: { ...templateInstance, status: "completed", captureStage: "report_ready" },
        documents: [],
        generationProgress: { totalSections: 0, completedSections: 0 },
      },
    };
    let confirmChatId = "";
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
            { conversationId: "conv_confirm", chatId: payload.chatId, eventType: "status", sequence: 1, timestamp: 1, status: "waiting_user" },
            {
              conversationId: "conv_confirm",
              chatId: payload.chatId,
              eventType: "ask",
              sequence: 2,
              timestamp: 2,
              status: "waiting_user",
              ask: {
                status: "pending",
                mode: "form",
                type: "confirm_params",
                title: "请确认报告诉求",
                text: "请确认报告诉求后开始生成。",
                parameters: [],
                reportContext: { templateInstance },
              },
            },
            { conversationId: "conv_confirm", chatId: payload.chatId, eventType: "done", sequence: 3, timestamp: 3, status: "waiting_user" },
          ]));
        }
        expect(payload.reply.sourceChatId).toBeTruthy();
        expect(payload.question).toBe("确认并生成报告");
        expect(payload.reply.reportContext.templateInstance.id).toBe("ti_confirm");
        confirmChatId = payload.chatId;
        return Promise.resolve(createSseResponse([
          { conversationId: "conv_confirm", chatId: payload.chatId, eventType: "status", sequence: 1, timestamp: 4, status: "running" },
          {
            conversationId: "conv_confirm",
            chatId: payload.chatId,
            eventType: "answer",
            sequence: 2,
            timestamp: 5,
            status: "finished",
            answer: reportAnswer,
          },
          { conversationId: "conv_confirm", chatId: payload.chatId, eventType: "done", sequence: 3, timestamp: 6, status: "finished" },
        ]));
      }
      if (url === "/rest/chatbi/v1/chat/conv_confirm") {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            conversationId: "conv_confirm",
            title: "网络运行状态报告",
            status: "active",
            records: confirmChatId
              ? [
                {
                  chatId: confirmChatId,
                  question: "",
                  askTime: "2026-04-18T09:01:00Z",
                  answers: [
                    {
                      type: "PIU",
                      answerTime: "2026-04-18T09:01:01Z",
                      content: piuContent({ steps: [], ask: null, delta: [], answer: reportAnswer, errors: [] }),
                    },
                  ],
                },
              ]
              : [],
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderPage();

    fireEvent.change(screen.getByLabelText("输入问题"), { target: { value: "做一份网络运行状态报告，用word" } });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    expect(await screen.findByText("请确认报告诉求")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "确认并生成" })).not.toBeDisabled());
    fireEvent.click(screen.getByRole("button", { name: "确认并生成" }));

    await waitFor(() => {
      const confirmPost = fetchMock.mock.calls.find(([, init]) => {
        if ((init as RequestInit | undefined)?.method !== "POST") return false;
        const payload = JSON.parse(String((init as RequestInit).body));
        return payload.reply?.type === "confirm_params";
      });
      expect(confirmPost).toBeTruthy();
    });
    expect(await screen.findByText("确认并生成报告")).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText("报告已生成").length).toBeGreaterThanOrEqual(1));
    const entries = Array.from(container.querySelectorAll(".message-entry"));
    const confirmQuestionIndex = entries.findIndex((entry) => entry.textContent?.includes("确认并生成报告"));
    const reportAnswerIndex = entries.findIndex((entry) => entry.textContent?.includes("报告已生成"));
    expect(confirmQuestionIndex).toBeGreaterThanOrEqual(0);
    expect(reportAnswerIndex).toBeGreaterThan(confirmQuestionIndex);
    expect(screen.getByRole("link", { name: "打开报告详情" })).toHaveAttribute("href", "/reports/rpt_confirm");
  });

  it("aggregates multiple PIU answers in one conversation record into one assistant response with a step tree", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url === "/rest/dev/system-settings") {
        return Promise.resolve(systemSettingsResponse());
      }
      if (url === "/rest/chatbi/v1/chat") {
        return Promise.resolve({
          ok: true,
          json: async () => [{ conversationId: "conv_piu_merge", title: "聚合 PIU", status: "active", lastMessagePreview: "已完成" }],
        });
      }
      if (url === "/rest/chatbi/v1/chat/conv_piu_merge") {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            conversationId: "conv_piu_merge",
            title: "聚合 PIU",
            status: "active",
            records: [
              {
                chatId: "chat_piu_merge",
                question: "分析本周网络质量",
                askTime: "2026-04-18T09:00:00Z",
                answers: [
                  {
                    type: "TEXT",
                    answerTime: "2026-04-18T09:00:00Z",
                    content: "已收到请求，正在分析网络质量。",
                  },
                  {
                    type: "PIU",
                    answerTime: "2026-04-18T09:00:01Z",
                    content: piuContent({
                      steps: [
                        { code: "report", stepId: "report", title: "生成报告", status: "running" },
                        { code: "report.collect", stepId: "report.collect", parentStepId: "report", title: "收集数据", status: "running" },
                      ],
                      delta: [{ step: { code: "report.plan", stepId: "report.plan", parentStepId: "report", title: "规划章节", status: "running" } }],
                      ask: null,
                      answer: null,
                      errors: [],
                    }),
                  },
                  {
                    type: "PIU",
                    answerTime: "2026-04-18T09:00:02Z",
                    content: piuContent({
                      steps: [
                        { code: "report.collect", stepId: "report.collect", parentStepId: "report", title: "收集数据", status: "finished" },
                        { code: "report.render", stepId: "report.render", parentStepId: "report", title: "渲染报告", status: "running" },
                      ],
                      ask: null,
                      answer: {
                        answerType: "DATA_ANALYSIS",
                        answer: {
                          summary: "网络质量整体稳定。",
                          querySpec: {},
                          sql: "select 1",
                          data: { columns: {}, results: [] },
                          visualizations: { components: [] },
                          warnings: [],
                        },
                      },
                      errors: [{ message: "非阻断提示" }],
                    }),
                  },
                ],
              },
            ],
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = renderPage();

    fireEvent.click(await screen.findByRole("button", { name: /聚合 PIU/ }));

    expect(await screen.findByText("已收到请求，正在分析网络质量。")).toBeInTheDocument();
    expect(await screen.findByText("智能问数已完成")).toBeInTheDocument();
    expect(screen.getByText("网络质量整体稳定。")).toBeInTheDocument();
    expect(screen.getAllByText("智能问数已完成")).toHaveLength(1);
    expect(container.querySelectorAll(".message-entry--assistant")).toHaveLength(1);
    expect(screen.getByRole("list", { name: "生成进度" })).toBeInTheDocument();
    expect(screen.getByText("生成报告")).toBeInTheDocument();
    expect(screen.getByText("收集数据")).toBeInTheDocument();
    expect(screen.getByText("规划章节")).toBeInTheDocument();
    expect(screen.getByText("渲染报告")).toBeInTheDocument();
    expect(container.querySelector(".step-status-icon--finished")).toBeInTheDocument();
    expect(screen.getAllByLabelText("已完成").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByLabelText("进行中").length).toBeGreaterThanOrEqual(1);
    fireEvent.click(screen.getByRole("button", { name: "收起生成报告子步骤" }));
    expect(screen.queryByText("收集数据")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "展开生成报告子步骤" }));
    expect(screen.getByText("收集数据")).toBeInTheDocument();
  });

  it("uses ask parameter options and defaults without calling parameter option resolve", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url === "/rest/dev/system-settings") {
        return Promise.resolve(systemSettingsResponse());
      }
      if (url === "/rest/chatbi/v1/chat") {
        return Promise.resolve({
          ok: true,
          json: async () => [{ conversationId: "conv_dynamic_options", title: "动态参数", status: "active", lastMessagePreview: "请选择区域" }],
        });
      }
      if (url === "/rest/chatbi/v1/chat/conv_dynamic_options") {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            conversationId: "conv_dynamic_options",
            title: "动态参数",
            status: "active",
            records: [
              {
                chatId: "chat_dynamic_options",
                question: "生成区域日报",
                askTime: "2026-04-18T09:00:00Z",
                answers: [
                  {
                    type: "PIU",
                    answerTime: "2026-04-18T09:00:01Z",
                    content: piuContent({
                      steps: [],
                      ask: {
                        status: "pending",
                        mode: "form",
                        type: "fill_params",
                        title: "请补充报告参数",
                        text: "请选择区域。",
                        parameters: [
                          {
                            id: "region",
                            label: "区域",
                            inputType: "dynamic",
                            required: true,
                            multi: false,
                            interactionMode: "form",
                            source: "region_source",
                            options: [
                              { label: "华东", value: "east", query: "region=east" },
                              { label: "华北", value: "north", query: "region=north" },
                            ],
                            defaultValue: [{ label: "华东", value: "east", query: "region=east" }],
                          },
                        ],
                        reportContext: {
                          templateInstance: {
                            id: "ti_dynamic",
                            schemaVersion: "template-instance.vNext-draft",
                            templateId: "tpl_dynamic",
                            template: {
                              id: "tpl_dynamic",
                              category: "network_operations",
                              name: "区域日报",
                              description: "区域日报模板。",
                              schemaVersion: "template.v3",
                              parameters: [],
                              catalogs: [],
                            },
                            conversationId: "conv_dynamic_options",
                            status: "collecting_parameters",
                            captureStage: "fill_params",
                            revision: 1,
                            parameters: [],
                            parameterConfirmation: { missingParameterIds: ["region"], confirmed: false },
                            catalogs: [],
                            createdAt: "2026-04-18T09:00:00Z",
                            updatedAt: "2026-04-18T09:00:00Z",
                          },
                        },
                      },
                      answer: null,
                      errors: [],
                    }),
                  },
                ],
              },
            ],
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: /动态参数/ }));

    const select = await screen.findByLabelText("区域") as HTMLSelectElement;
    expect(select.value).toBe("华东");
    expect(screen.getByRole("option", { name: "华北" })).toBeInTheDocument();
    fireEvent.change(select, { target: { value: "华北" } });
    fireEvent.click(screen.getByRole("button", { name: "提交参数" }));
    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([, init]) => {
        if ((init as RequestInit | undefined)?.method !== "POST") return false;
        const payload = JSON.parse(String((init as RequestInit).body));
        return payload.question === "补充参数：区域=华北";
      })).toBe(true);
    });
    expect(fetchMock).not.toHaveBeenCalledWith(expect.stringContaining("parameter-options"), expect.anything());
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("parameter-options"))).toBe(false);
  });

  it("streams a local flow demo into the BI Engine report workspace", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn(async (url: string) => url === "/rest/dev/system-settings"
      ? systemSettingsResponse()
      : ({ ok: true, json: async () => [] })));

    renderPage();
    fireEvent.click(screen.getByRole("button", { name: /经营分析综合报告/ }));
    await act(async () => vi.runAllTimersAsync());

    expect(screen.getByLabelText("报告预览编辑区")).toBeInTheDocument();
    expect(screen.getAllByText("经营总览").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole("tab", { name: "编辑" })).toBeEnabled();
  });

  it("streams a local paged demo into the PPT preview", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn(async (url: string) => url === "/rest/dev/system-settings"
      ? systemSettingsResponse()
      : ({ ok: true, json: async () => [] })));

    renderPage();
    fireEvent.click(screen.getByRole("button", { name: /经营复盘演示汇报/ }));
    await act(async () => vi.runAllTimersAsync());

    expect(screen.getByTestId("ppt-slide")).toHaveTextContent("__ppt_cover__");
    expect(screen.getByText("1 / 9")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "编辑" }));
    expect(screen.getByTestId("ppt-editor")).toBeInTheDocument();
  });
});
