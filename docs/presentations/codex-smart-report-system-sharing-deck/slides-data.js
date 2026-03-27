"use strict";

const markdownOutput = "../2026-03-24-codex-smart-report-system-sharing.md";
const deckOutput = "../2026-03-27-codex-smart-report-system-sharing.pptx";

const meta = {
  title: "用 Codex 快速搭建并跑通智能报告系统原型",
  audience: "设计、开发团队",
  duration: "30 分钟",
  style: "专业科技评审风",
  markdownOutput,
  deckOutput,
};

const slides = [
  {
    page: 1,
    section: "定位",
    layout: "hero",
    title: "为什么用 Codex 做需求期原型",
    conclusion: "这次分享关注的是如何用 Coding Agent 缩短从需求到原型的距离，而不是直接产出一个生产可交付版本。",
    points: [
      "核心目标是加速需求分析设计，让讨论尽快落在真实系统上。",
      "智能报告系统适合作为案例，因为它同时包含页面、接口、状态流和运行边界。",
      "Codex 的价值不只是写代码，而是串起设计、计划、实现、验证和运行。"
    ],
    notes: [
      "开场先校准预期，不把这次分享讲成“AI 取代工程师”。",
      "第一句话就要把“原型加速”与“交付版本”区分开。"
    ],
    visualHints: [
      "标题页使用系统名与 Coding Agent 主题组合，不需要塞过多细节。",
      "可放系统首页截图；若暂无可用截图，保留抽象化系统总览视觉。"
    ],
    tags: ["需求分析设计", "原型加速", "智能报告系统"]
  },
  {
    page: 2,
    section: "边界",
    layout: "compare",
    title: "背景与边界",
    conclusion: "这套方法优先解决“需求阶段如何避免空对空”，而不是直接替代完整工程交付流程。",
    points: [
      "背景是加速需求分析设计，让设计、开发、需求方围绕真实对象讨论。",
      "重点是尽快把交互、接口、状态和约束跑出来，而不是一开始就追求工程终态。",
      "如果把目标错设为“一次生成可交付版本”，团队会对 agent 形成错误预期。"
    ],
    notes: [
      "这页要主动消除听众防御，告诉他们工程化仍然重要。",
      "强调：agent 在这里先扮演需求验证加速器。"
    ],
    visualHints: [
      "建议用“需求期原型”与“交付版本”双栏对比，突出边界。",
      "右下角可放一句收束话：先原型，后工程化。"
    ],
    compare: {
      leftTitle: "需求期原型",
      leftItems: ["快速形成讨论对象", "暴露真实交互与约束", "支持高频迭代和试错"],
      rightTitle: "交付版本",
      rightItems: ["完整治理与质量门槛", "稳定性、安全、观测、权限", "面向上线与长期维护"]
    }
  },
  {
    page: 3,
    section: "工具理念",
    layout: "split-diagram",
    title: "Codex 基本使用与工具理念",
    conclusion: "Codex 更像一个能读环境、会调用工具、会给出修改方案并执行验证的 agent，而不是传统意义上的代码编辑器。",
    points: [
      "“为什么没有代码编辑区”这个问题的答案是：它优先围绕任务、上下文、工具和结果协作。",
      "典型工作方式不是“我盯着它一行行改”，而是“我给目标和边界，它读仓库、调工具、生成修改并验证”。",
      "人负责方向、范围和判断，agent 负责把方案快速落成可以检查的产物。"
    ],
    notes: [
      "这是帮助设计同学理解 Codex 的关键页。",
      "要把它和“聊天式代码补全工具”区分开。"
    ],
    visualHints: [
      "左边讲理念，右边画出“任务 -> 读环境 -> 调工具 -> 产出修改 -> 验证”的闭环。",
      "可以把“没有代码编辑区”做成醒目的问题标签。"
    ],
    diagramSteps: ["任务与目标", "读取环境", "调用工具", "产出修改", "验证结果"]
  },
  {
    page: 4,
    section: "方法价值",
    layout: "cards",
    title: "为什么适合做需求期 demo",
    conclusion: "当需求还没稳定时，最有价值的不是更快写完代码，而是更快把模糊想法变成可验证对象。",
    points: [
      "文档和口头讨论很容易空转，真实页面、真实接口、真实状态流更容易暴露问题。",
      "需求期的关键不是把所有细节做完，而是判断方向是否对、边界是否清楚。",
      "一旦原型能跑起来，团队讨论会从“想象中的系统”转向“眼前的系统”。"
    ],
    notes: [
      "这页承上启下，说明为什么要用 agent 做 demo。",
      "尽量避免抽象口号，多讲“讨论效率”和“真实约束暴露”。"
    ],
    visualHints: [
      "建议用四张价值卡：对齐上下文、暴露约束、缩短反馈、支撑迭代。"
    ],
    valueCards: ["对齐上下文", "暴露真实约束", "缩短反馈回路", "支撑后续迭代"]
  },
  {
    page: 5,
    section: "输入准备",
    layout: "cards",
    title: "从外网到内网：需要哪些输入",
    conclusion: "做 demo 不是只给一句需求，而是要把目标、上下文、仓库、工具和验证方式一起交给 agent。",
    points: [
      "最少输入包括：需求描述、目标边界、关键成功标准。",
      "还需要：设计上下文、代码仓库、skills 或工具清单、运行环境约束。",
      "最后要补上验证方式，否则 agent 很容易停在“看起来像完成”。"
    ],
    notes: [
      "这里可以顺手教育团队：上下文本身就是生产力。",
      "把“设计上下文”提前埋点，为后面 SDD 过渡。"
    ],
    visualHints: [
      "建议把输入做成 6 张小卡片，像任务启动清单。"
    ],
    valueCards: ["需求目标", "边界与非目标", "设计上下文", "代码仓库", "skills / 工具清单", "验证方式"]
  },
  {
    page: 6,
    section: "新项目",
    layout: "timeline",
    title: "全新项目：从外网到内网的 demo 流程",
    conclusion: "全新项目更适合先在外网把原型拉起来，再通过代码仓库进入公司内网环境继续推进。",
    points: [
      "推荐路径是：外网构思与实现 -> 上传 GitHub -> 公司内下载与继续验证。",
      "这样做的核心是让 agent 先在可用环境里把最小系统跑起来，再进入受限环境。",
      "不推荐也不允许的路径是：个人 PC 放家里，通过内网穿透远程访问。"
    ],
    notes: [
      "这里要明确说：咨询过信息安全管理专员，这条路径不让。",
      "用这个反例提醒大家，企业落地一定要尊重安全边界。"
    ],
    visualHints: [
      "建议做 4 步时间线，并加一个黄色警示卡说明内网穿透不可行。"
    ],
    flowSteps: ["外网准备需求与上下文", "外网生成原型并验证", "代码上传 GitHub", "公司内下载并继续推进"],
    callout: {
      tone: "warning",
      title: "反例提醒",
      body: "个人 PC 放家里、通过内网穿透远程访问的方式，已咨询信息安全管理专员，不允许。"
    }
  },
  {
    page: 7,
    section: "存量项目",
    layout: "timeline",
    title: "存量项目：先外网复刻，再走同样链路",
    conclusion: "存量项目的关键不是直接把内网工程扔给 agent，而是先在外网复刻出可工作的最小上下文。",
    points: [
      "第一步是把项目必要部分在外网复刻出来，让 agent 能理解结构、依赖和主要流程。",
      "后续流程与全新项目类似：外网形成原型 -> 代码入库 -> 公司内继续集成。",
      "这样做的收益是让 agent 先有可操作上下文，而不是一上来卡在企业环境限制里。"
    ],
    notes: [
      "这页要说明：复刻不是复制全部系统，而是复刻讨论所需最小上下文。",
      "可以顺手带一句：复刻的目标是需求验证，不是长期维护。"
    ],
    visualHints: [
      "建议做分层流程图：复刻最小上下文 -> 原型验证 -> 内网继续集成。"
    ],
    flowSteps: ["外网复刻最小项目上下文", "补齐设计与依赖说明", "生成并验证原型", "进入公司内环境集成"]
  },
  {
    page: 8,
    section: "范式",
    layout: "stack",
    title: "设计上下文、SDD 与 superpower skills",
    conclusion: "设计上下文应该成为设计阶段的正式输出，SDD 和 superpower skills 则负责把这份上下文稳定传递给开发与 agent。",
    points: [
      "SDD 的价值在于按设计收敛、计划拆解、实现验证的顺序推进，而不是直接跳到编码。",
      "superpower skills 套件把高频工作流固化下来，减少 agent 每次临场试错。",
      "如果把“设计上下文”交给开发团队和 agent 一起消费，整个需求团队会更容易保持一致语境。"
    ],
    notes: [
      "这是你自己的方法沉淀页，要讲出“为什么上下文本身是交付物”。",
      "设计同学会对这页更敏感，开发同学会对 skills 更敏感。"
    ],
    visualHints: [
      "建议做五层栈：需求 -> 设计上下文 -> SDD -> superpower skills -> 实现与验证。"
    ],
    stackItems: ["需求与目标", "设计上下文", "SDD 实践", "superpower skills", "实现与验证"]
  },
  {
    page: 9,
    section: "案例",
    layout: "split-placeholder",
    title: "为什么选智能报告系统做案例",
    conclusion: "智能报告系统不是单点页面，而是一条完整业务链路，因此很适合展示 Coding Agent 如何把抽象需求推进成可运行原型。",
    points: [
      "系统覆盖 chat、模板、实例、文档、任务、设置，具备完整操作面。",
      "它同时需要交互体验、后端接口、数据模型和本地运行能力。",
      "这类系统最能体现“先跑起来，再围绕真实系统继续讨论”的价值。"
    ],
    notes: [
      "这页是案例入口，要让听众认可案例复杂度足够、有代表性。",
      "不要把它讲成单纯 UI 项目。"
    ],
    visualHints: [
      "左边讲案例价值，右边直接展示当前运行中的真实系统截图。",
      "建议用多页截图并列，体现 chat、模板、文档等完整操作面。"
    ],
    placeholderItems: [
      {
        kind: "ui",
        badge: "真实系统截图",
        title: "当前运行中的真实系统界面",
        desc: "浏览器访问 127.0.0.1:8300 后获取，覆盖对话、模板与文档操作面。",
        gallery: [
          { path: "./assets/chat-page.png", label: "对话助手" },
          { path: "./assets/template-detail-page.png", label: "模板工作台" },
          { path: "./assets/documents-page.png", label: "文档中心" }
        ],
        source: "E:/code/codex_projects/ReportSystemV2/docs/presentations/codex-smart-report-system-sharing-deck/assets/chat-page.png",
        sourceLabel: "截图来源：当前运行 demo http://127.0.0.1:8300/"
      }
    ],
    sources: [
      "E:/code/codex_projects/ReportSystemV2/design/design.md",
      "E:/code/codex_projects/ReportSystemV2/src/frontend/src/app/App.tsx",
      "E:/code/codex_projects/ReportSystemV2/docs/presentations/codex-smart-report-system-sharing-deck/assets/chat-page.png",
      "E:/code/codex_projects/ReportSystemV2/docs/presentations/codex-smart-report-system-sharing-deck/assets/template-detail-page.png",
      "E:/code/codex_projects/ReportSystemV2/docs/presentations/codex-smart-report-system-sharing-deck/assets/documents-page.png"
    ]
  },
  {
    page: 10,
    section: "工作流",
    layout: "workflow",
    title: "设计到计划到实现：Coding Agent 的主工作流",
    conclusion: "真正有价值的不是某一次生成代码，而是把设计、计划、实现、测试和运行连成一条连续链路。",
    points: [
      "第一步先收敛设计：边界、页面形态、关键交互、非目标。",
      "第二步拆实施计划：任务、修改范围、验证命令、预期结果。",
      "第三步落实现并验证，让系统真正跑起来，再承接团队讨论。"
    ],
    notes: [
      "这页是全场方法论核心页。",
      "你可以直接说：我们要的不是一段代码，而是一条可复用的原型生产线。"
    ],
    visualHints: [
      "建议用横向流程图，并标出“人负责判断 / agent 负责执行”的角色切分。"
    ],
    flowSteps: ["设计收敛", "实施计划", "代码实现", "测试验证", "系统跑起来", "团队继续讨论"]
  },
  {
    page: 11,
    section: "证据 1",
    layout: "dual-placeholder",
    title: "证据 1：设计文档如何衔接到实施计划",
    conclusion: "原型并不是直接“上来写代码”，而是先形成可审查的设计，再形成可执行的计划。",
    points: [
      "设计文档负责讲清目标、边界、页面家族与非目标。",
      "实施计划负责把任务拆成具体修改、测试命令和预期结果。",
      "这让 agent 的产出变得可检查、可复用、可回溯。"
    ],
    notes: [
      "这页最好展示文档截图，证明方法不是空喊口号。",
      "如果截图不够清晰，至少放文档标题页和关键段落。"
    ],
    visualHints: [
      "用左右双栏展示真实文档摘录：左边设计文档，右边实施计划。"
    ],
    placeholderItems: [
      {
        kind: "doc",
        badge: "真实设计文档",
        title: "Professional Workbench UX Redesign",
        desc: "直接摘自设计文档中的目标与页面家族定义。",
        excerpt: [
          "## Goals",
          "1. Make the application feel like a coherent professional data product.",
          "3. Give the chat flow a dominant single-column workspace.",
          "4. Split browsing and editing/detail work into separate pages.",
          "",
          "### Page families",
          "1. Conversation pages",
          "2. List pages",
          "3. Detail pages"
        ],
        source: "E:/code/codex_projects/ReportSystemV2/docs/plans/2026-03-18-professional-workbench-ux-design.md",
        sourceLabel: "docs/plans/2026-03-18-professional-workbench-ux-design.md"
      },
      {
        kind: "plan",
        badge: "真实实施计划",
        title: "Implementation Plan",
        desc: "直接摘自实施计划中的目标、架构与首个任务拆解。",
        excerpt: [
          "Goal: Refactor the React frontend into a more polished professional workbench UX.",
          "Architecture: Keep the existing React + Vite app and API contracts.",
          "",
          "### Task 1",
          "Lock in shell hierarchy and route structure",
          "Add /templates/:templateId, /templates/new, /instances/:instanceId",
          "",
          "Run: npm test -- src/app/App.test.tsx",
          "Expected: PASS."
        ],
        source: "E:/code/codex_projects/ReportSystemV2/docs/plans/2026-03-18-professional-workbench-ux-implementation-plan.md",
        sourceLabel: "docs/plans/2026-03-18-professional-workbench-ux-implementation-plan.md"
      }
    ],
    sources: [
      "E:/code/codex_projects/ReportSystemV2/docs/plans/2026-03-18-professional-workbench-ux-design.md",
      "E:/code/codex_projects/ReportSystemV2/docs/plans/2026-03-18-professional-workbench-ux-implementation-plan.md"
    ]
  },
  {
    page: 12,
    section: "证据 2",
    layout: "dual-placeholder",
    title: "证据 2：前后端如何接成可运行系统",
    conclusion: "我们最终拿到的不是若干页面碎片，而是一个前后端打通、可直接启动的系统原型。",
    points: [
      "后端入口统一挂载模板、实例、文档、任务、聊天、设置等路由。",
      "前端路由组织主要页面，并由后端统一托管静态资源。",
      "部署文档把依赖、入口、数据库和启动命令全部落成可执行说明。"
    ],
    notes: [
      "这页要证明“原型能跑”，不是停在好看的页面层面。",
      "如果后续补真实截图，优先放入口代码和部署说明的组合。"
    ],
    visualHints: [
      "左右双栏直接放真实代码摘录：左边后端入口与启动验证，右边前端路由结构。"
    ],
    placeholderItems: [
      {
        kind: "code",
        badge: "真实代码摘录",
        title: "后端入口 + 启动验证",
        desc: "main.py 路由挂载与部署手册中的启动、验证命令。",
        mono: true,
        excerpt: [
          "app.include_router(templates.router, prefix=API_PREFIX)",
          "app.include_router(instances.router, prefix=API_PREFIX)",
          "app.include_router(documents.router, prefix=API_PREFIX)",
          "app.include_router(tasks.router, prefix=API_PREFIX)",
          "app.include_router(chat.router, prefix=API_PREFIX)",
          "@app.get(\"/\")",
          "@app.get(\"/{full_path:path}\")",
          "python -m uvicorn src.backend.main:app --host 0.0.0.0 --port 8300",
          "Invoke-RestMethod -Uri 'http://127.0.0.1:8300/openapi.json'"
        ],
        source: "E:/code/codex_projects/ReportSystemV2/src/backend/main.py",
        sourceLabel: "src/backend/main.py + design/deployment_guide.md"
      },
      {
        kind: "code",
        badge: "真实代码摘录",
        title: "前端路由结构",
        desc: "App.tsx 中当前实际挂载的页面路由。",
        mono: true,
        excerpt: [
          "<Routes>",
          "  <Route path=\"/\" element={<Navigate to=\"/chat\" replace />} />",
          "  <Route path=\"/chat\" element={<ChatPage />} />",
          "  <Route path=\"/templates\" element={<TemplatesPage />} />",
          "  <Route path=\"/templates/:templateId\" element={<TemplateDetailPage />} />",
          "  <Route path=\"/instances\" element={<InstancesPage />} />",
          "  <Route path=\"/instances/:instanceId\" element={<InstanceDetailPage />} />",
          "  <Route path=\"/documents\" element={<DocumentsPage />} />",
          "  <Route path=\"/settings\" element={<SettingsPage />} />",
          "</Routes>"
        ],
        source: "E:/code/codex_projects/ReportSystemV2/src/frontend/src/app/App.tsx",
        sourceLabel: "src/frontend/src/app/App.tsx"
      }
    ],
    sources: [
      "E:/code/codex_projects/ReportSystemV2/src/backend/main.py",
      "E:/code/codex_projects/ReportSystemV2/src/frontend/src/app/App.tsx",
      "E:/code/codex_projects/ReportSystemV2/design/deployment_guide.md"
    ]
  },
  {
    page: 13,
    section: "证据 3",
    layout: "split-placeholder",
    title: "证据 3：为什么这个原型还能持续快速演进",
    conclusion: "Agent 原型的价值不只在第一次搭起来，还在于骨架建立后可以承接高频迭代。",
    points: [
      "最近的提交持续围绕实例更新、Fork、预览等关键交互推进。",
      "这说明原型并不是一次性演示件，而是在真实反馈中继续演进。",
      "一旦主工作流与验证方式稳定，后续细化会明显加速。"
    ],
    notes: [
      "这页可以把最近几条提交直接念出来，增强真实感。",
      "如果没有实际截图，右侧保留提交记录视觉占位也足够。"
    ],
    visualHints: [
      "左边放真实提交列表，右边展示实例详情页真实截图，突出更新 / Fork / 文档产物。"
    ],
    placeholderItems: [
      {
        kind: "git",
        badge: "真实运行界面",
        title: "实例详情：更新 / Fork / Markdown 产物",
        desc: "当前运行中的 Device Inspection Report 实例详情页，已经暴露更新、Fork、章节状态与文档产物。",
        imagePath: "./assets/instance-detail-page.png",
        source: "E:/code/codex_projects/ReportSystemV2/docs/presentations/codex-smart-report-system-sharing-deck/assets/instance-detail-page.png",
        sourceLabel: "截图来源：http://127.0.0.1:8300/instances/9c9475b6-d256-406a-932a-df49782d47b2"
      }
    ],
    commitItems: [
      "351cf41 2026-03-21 feat: visualize instance update outline preview",
      "daf31e4 2026-03-21 feat: preview instance update flow before opening chat",
      "2f9be93 2026-03-21 refactor: separate instance update from fork",
      "8807d8c 2026-03-20 merge: internalize template instances",
      "7de7a21 2026-03-19 feat: add chat fork branches"
    ]
  },
  {
    page: 14,
    section: "协作",
    layout: "trio",
    title: "和其它 coding agent 怎么搭配",
    conclusion: "关键不是比较谁最强，而是按阶段和职责分工，让不同 agent 各自做最合适的事情。",
    points: [
      "Codex 适合作为主执行者，负责读仓库、拆解实现、修改代码和补验证。",
      "Antigravity 更适合做设计 review、方案 challenge 或结构性反馈。",
      "Cursor 适合做局部编辑、快速对照和细节微调。"
    ],
    notes: [
      "这页强调分工，不做竞品评测。",
      "说法上尽量克制，避免把其它工具讲成附庸。"
    ],
    visualHints: [
      "建议做三张角色卡，分别对应 Codex、Antigravity、Cursor。"
    ],
    agentCards: [
      {
        name: "Codex",
        role: "主实现与验证",
        detail: "读仓库、调工具、执行计划、补测试、把系统跑起来"
      },
      {
        name: "Antigravity",
        role: "设计与方案 review",
        detail: "检查设计完整性、挑战假设、补结构化反馈"
      },
      {
        name: "Cursor",
        role: "局部编辑与快速对照",
        detail: "细节微调、局部查看、快速小改"
      }
    ]
  },
  {
    page: 15,
    section: "经验",
    layout: "compare",
    title: "范围控制与 Codex 调教",
    conclusion: "Codex 用得顺不顺，核心取决于两件事：你是否主动控制范围，以及你是否提前给足高频上下文与工具。",
    points: [
      "GPT-5.4 容易给出过满、过完美的方案，因此人必须主动控制需求范围和 YAGNI 边界。",
      "把高频会用到的 skill、环境说明、工具清单提前装好，可以显著减少它反复重试。",
      "如果总让它现猜环境、现试工具，响应时间和稳定性都会变差。"
    ],
    notes: [
      "这是最有操作性的经验页，听众通常会记得很清楚。",
      "可以用“别让它每次都从零摸环境”这句话。"
    ],
    visualHints: [
      "建议做左右双栏：左边范围控制，右边调教与预装清单。"
    ],
    compare: {
      leftTitle: "范围控制",
      leftItems: ["先定最小目标", "明确非目标", "控制 GPT-5.4 的完美化倾向"],
      rightTitle: "Codex 调教",
      rightItems: ["预装高频 skill", "给出环境与工具清单", "减少重复试错与响应时间"]
    }
  },
  {
    page: 16,
    section: "收束",
    layout: "delivery",
    title: "demo 如何继续转成交付件",
    conclusion: "本次分享停在 demo 和原型验证，但下一步完全可以把这条链延伸为正式设计文档、评审胶片和版本交付材料。",
    points: [
      "当前阶段重点是把 demo 跑起来，形成需求讨论和方案验证的基础。",
      "下一步可以叠加 hw-ipd-software-docs、slides 等能力，把原型沉淀为规范设计文档和评审胶片。",
      "cloudsop、netgraph 这类能力在本次分享中只作为未来方向，不作为当前已验证能力。"
    ],
    notes: [
      "最后用一句话收束：先原型，后工程化；先对齐上下文，再交付版本。",
      "这页既是展望，也是边界说明。"
    ],
    visualHints: [
      "建议做“Demo -> 文档包 -> 评审胶片 -> 版本交付件”的链路图，并展示真实生成的 Markdown 报告片段。"
    ],
    flowSteps: ["Demo 原型", "设计文档包", "评审胶片", "版本交付件"],
    placeholderItems: [
      {
        kind: "deliverable",
        badge: "当前已产出",
        title: "Markdown 报告样例",
        excerpt: [
          "# Device Inspection Report",
          "- 实例 ID: 9c9475b6-d256-406a-932a-df49782d47b2",
          "- 状态: draft",
          "## 3. 风险与异常",
          "当前未检测到严重级别的告警事件。"
        ],
        source: "E:/code/codex_projects/ReportSystemV2/docs/presentations/codex-smart-report-system-sharing-deck/assets/sample-generated-report.md",
        sourceLabel: "assets/sample-generated-report.md"
      }
    ],
    callout: {
      tone: "info",
      title: "展望说明",
      body: "cloudsop / netgraph 在本次分享中仅作为后续要叠加的 skill 方向，不作为当前案例已验证能力。"
    },
    sources: [
      "E:/code/codex_projects/ReportSystemV2/docs/presentations/codex-smart-report-system-sharing-deck/assets/sample-generated-report.md",
      "C:/Users/Administrator/.codex/skills/hw-ipd-software-docs/SKILL.md"
    ]
  }
];

module.exports = {
  meta,
  slides,
};
