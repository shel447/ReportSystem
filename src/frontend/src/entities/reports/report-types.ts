/**
 * 合并模型类型定义
 * 根据《合并模型类型定义.md》文档的章节顺序重新组织
 */

// ============================================================================
// 第2章 - 图表渲染引擎DSL定义
// ============================================================================

/** 组件类型映射 */
export interface ComponentTypeMap {
  text: TextComponent;
  table: TableComponent;
  chart: ChartComponent;
  markdown: MarkdownComponent;
  compositeTable: CompositeTable;
}

/** 渲染引擎组件联合类型 */
export type BIEngineComponent = ComponentTypeMap[keyof ComponentTypeMap];

/** 基础组件信息 */
export interface BasicComponent {
  /** 组件的唯一标识符 */
  id: string;
  /** 组件布局信息 */
  layout?: ComponentLayout;
  /** 组件基础配置信息(具体开放属性待定) */
  basicProperties?: Record<string, unknown>;
  /** 组件高级配置信息(具体开放属性待定)  */
  advanceProperties?: Record<string, unknown>;
  /** 交互配置（组件间联动） */
  interactions?: Interaction[];
}

/** 数据属性基类 */
export interface DataProperty {
  /** 数据类型：静态数据、数据源、api */
  dataType: 'static' | 'datasource' | 'api';
  /** 数据源 id */
  sourceId?: string;
  /** api查询url */
  url?: string;
  /** 查询url方法 */
  method?: 'GET' | 'POST';
  /** 是否自动刷新 */
  autoRefresh?: boolean;
  /** 刷新间隔 */
  refreshInterval?: number;
}

/** 文本数据属性 */
export interface TextDataProperty extends DataProperty {
  /** 标题 */
  title?: string;
  /** 文本静态内容 */
  content: string;
}

/** 表格数据属性 */
export interface TableDataProperty extends DataProperty {
  /** 标题 */
  title?: string;
  /** 数据列配置 */
  columns?: Column[];
  /** 表格静态数据 */
  data?: Record<string, unknown>[];
  /** 列合并配置（将多列数据合并为一列展示） */
  mergeColumns?: MergeColumnInfo[];
  /** 行合并配置（垂直方向合并多行单元格） */
  mergeRows?: MergeRowConfig[];
  /** 是否包含合并单元格标记 */
  hasMerge?: boolean;
}

/** 图表数据属性 */
export interface ChartDataProperty extends DataProperty {
  /** 标题 */
  title?: string;
  /** 数据列配置 */
  columns?: Column[];
  /** 图表静态数据 */
  data?: Record<string, unknown>[];
  /** 图表系列数据配置 */
  series?: Series[];
  /** 平台扩展: 坐标轴分组键值 */
  axisGroup?: string[];
}

/** Markdown数据属性 */
export interface MarkdownDataProperty extends DataProperty {
  /** Markdown文本内容 */
  content: string;
}

/** 组合表格数据属性 */
export interface CompositeTableDataProperty extends DataProperty {
  /** 组合表格标题 */
  title?: string;
}

/** 列合并配置 */
export interface MergeColumnInfo {
  /** 合并后的展示标题 */
  title: string;
  /** 被合并的列键名列表 */
  columns: string[];
}

/** 行合并配置 */
export interface MergeRowConfig {
  /** 合并起始行索引（从0开始） */
  startRowIndex: number;
  /** 合并的行数 */
  rowSpan: number;
  /** 合并的列键名 */
  columnKey: string;
  /** 合并后的单元格展示文本（默认取首行值） */
  mergedText?: string;
}

/** 文本组件 */
export interface TextComponent extends BasicComponent {
  type: 'text';
  dataProperties: TextDataProperty;
}

/** 表格组件 */
export interface TableComponent extends BasicComponent {
  type: 'table';
  dataProperties: TableDataProperty;
}

/** 图表组件 */
export interface ChartComponent extends BasicComponent {
  type: 'chart';
  dataProperties: ChartDataProperty;
  /** x轴配置 (饼图无此配置) */
  xAxis?: Axis | Axis[];
  /** y轴配置 (饼图无此配置) */
  yAxis?: Axis | Axis[];
  /** 平台扩展: 图表可选配置项 */
  options?: ChartOption;
}

/** Markdown组件 */
export interface MarkdownComponent extends BasicComponent {
  type: 'markdown';
  dataProperties: MarkdownDataProperty;
}

/** 多维表格组合组件（多表格垂直拼接，支持跨表合并） */
export interface CompositeTable extends BasicComponent {
  type: 'compositeTable';
  /** 子表格列表，按顺序垂直拼接 */
  tables: TableComponent[];
  /** 数据属性（可选，用于标题等） */
  dataProperties?: CompositeTableDataProperty;
}

/** 组件布局信息 */
export type ComponentLayout = GridLayout | FlowLayout | AbsoluteLayout;

/** 布局类型枚举 */
export enum LayoutType {
  GRID = 'grid',
  FLOW = 'flow',
  ABSOLUTE = 'absolute',
}

/** 网格布局 */
export interface GridLayout {
  type: LayoutType.GRID;
  // 网格 x 起点
  gx: number;
  // 网格 y 起点
  gy: number;
  // 宽度（格数）
  gw: number;
  // 高度（格数）
  gh: number;
}

/** 流式布局 */
export interface FlowLayout {
  type: LayoutType.FLOW;
}

/** 绝对定位布局 */
export interface AbsoluteLayout {
  type: LayoutType.ABSOLUTE;
  x: number;
  y: number;
  w: number;
  h: number;
  zIndex?: number;
}

/** 页面布局信息 */
export interface PageLayout {
  type: LayoutType;
  grid?: {
    /** 列数 */
    cols: number;
    /** 行高 */
    rowHeight: number;
    /** 间距 */
    gap?: number;
  };
}

/** 交互动作类型 */
export type InteractionAction = 'click' | 'hover' | 'change' | 'select';

/** 交互触发配置 */
export interface InteractionTrigger {
  /** 触发动作 */
  action: InteractionAction;
  /** 触发字段（数据属性名），不指定时默认为组件级触发 */
  field?: string;
}

/** 联动目标配置 */
export interface InteractionTarget {
  /** 目标组件ID */
  componentId: string;
  /** 联动方式 */
  type: 'filter' | 'jump' | 'highlight';
  /** 参数映射：源字段名 → 目标参数名 */
  params?: Record<string, string>;
}

/** 交互配置 */
export interface Interaction {
  /** 触发配置 */
  trigger: InteractionTrigger;
  /** 联动目标列表 */
  targets: InteractionTarget[];
}

// ============================================================================
// 第3章 - 图表系列配置DSL定义
// ============================================================================

/** 坐标轴配置 */
export interface Axis {
  /** 轴类型：类目轴（离散数据）或数值轴（连续数据） */
  type: 'category' | 'value';
  /** 轴名称 */
  name?: string;
}

/** 折线图系列配置 */
export interface LineSeries {
  type: 'line';
  /** 衍生类型：面积图 */
  subType?: 'area';
  /** 数据映射：x轴对应data的key，y轴对应data的key */
  encode: {
    x: string;
    y: string;
    xAxisIndex?: number;
    yAxisIndex?: number;
  };
  /** 系列名称（用于图例） */
  name: string;
}

/** 柱状图系列配置 */
export interface BarSeries {
  type: 'bar';
  /** 衍生类型：条形图（水平柱状图） */
  subType?: 'horizontal';
  /** 数据映射 */
  encode: {
    x: string;
    y: string;
    xAxisIndex?: number;
    yAxisIndex?: number;
  };
  /** 系列名称 */
  name: string;
}

/** 饼图系列配置 */
export interface PieSeries {
  type: 'pie';
  /** 衍生类型：环形图 */
  subType?: 'ring';
  /** 数据映射 */
  encode: { name: string; value: string };
  /** 系列名称 */
  name: string;
}

/** 散点图系列配置 */
export interface ScatterSeries {
  type: 'scatter';
  /** 无衍生类型 */
  subType?: never;
  /** 数据映射 */
  encode: {
    x: string;
    y: string;
    xAxisIndex?: number;
    yAxisIndex?: number;
  };
  /** 系列名称 */
  name: string;
}

/** 雷达图系列配置 (平台独有) */
export interface RadarSeries {
  type: 'radar';
  /** 数据映射 */
  encode: { name: string; value: string };
  /** 系列名称 */
  name: string;
}

/** 仪表盘系列配置 (平台独有) */
export interface GaugeSeries {
  type: 'gauge';
  /** 数值对应data的key */
  encode: { value: string };
  /** 系列名称 */
  name: string;
  /** 仪表盘配置 */
  config?: {
    min?: number;
    max?: number;
    unit?: string;
  };
}

/** 蜡烛图系列配置 (平台独有) */
export interface CandlestickSeries {
  type: 'candlestick';
  /** 数据映射：开盘、收盘、最低、最高 */
  encode: { open: string; close: string; low: string; high: string };
  /** 系列名称 */
  name: string;
}

/** 图表系列配置联合类型 */
export type Series =
  | LineSeries
  | BarSeries
  | PieSeries
  | ScatterSeries
  | RadarSeries
  | GaugeSeries
  | CandlestickSeries;

/** 图表扩展配置  */
export interface ChartOption {
  /** ECharts原生配置 */
  eChartOption?: Record<string, unknown>;
  /** 中心文本 (用于饼图/仪表盘) */
  centerText?: string;
  /** 副中心文本 */
  subCenterText?: string;
}

// ============================================================================
// 第4章 - 智能报告DSL定义
// ============================================================================

/** 报告定义 */
export interface Report {
  /** 报告基础信息 */
  basicInfo: BasicInfo;
  /** 封面 */
  cover?: Cover;
  /** 签字页 */
  signaturePage?: SignaturePage;
  /** 目录&内容 */
  catalogs: Catalog[];
  /** 总结章节 */
  summary?: ReportSummary;
  /** 报告生成元数据(通过id匹配) */
  reportMeta?: Record<string, GenerateMeta>;
  /** 页面布局 */
  layout: PageLayout;
}

/** 报告公共基础信息 */
export interface BasicInfo {
  /** id */
  id: string;
  /** schema版本号 */
  schemaVersion: '1.0.0';
  /** 报告当前模式：草稿&已发布 */
  mode: 'draft' | 'published';
  /** 报告当前状态（取决于当前是否有章节在生成过程中） */
  status?: Status;
  /** 名称/标题 */
  name?: string;
  /** 报告副标题  */
  subTitle?: string;
  /** 报告描述 */
  description?: string;
  /** 模板id */
  templateId?: string;
  /** 模板名称 */
  templateName?: string;
  /** 备注 */
  remark?: string;
  /** 版本号 */
  version?: string;
  /** 创建时间 */
  createDate?: string;
  /** 修改时间 */
  modifyDate?: string;
  /** 创建人 */
  creator?: string;
  /** 修改人 */
  modifier?: string;
  /** 页眉 */
  header?: string;
  /** 页脚 */
  footer?: string;
  /** 报告分类 */
  category?: string;
}

/** 章节定义 */
export interface Section {
  id: string;
  /** 段落标题  */
  title?: string;
  /** 段落顺序 */
  order?: number;
  /** 章节组件列表 */
  components: BIEngineComponent[];
  /** 段落总结  */
  summary?: ReportSummary;
}

/** 目录定义 */
export interface Catalog {
  /** 目录id  */
  id: string;
  /** 目录名称 */
  name: string;
  /** 章节顺序 */
  order?: number;
  /** 子目录  */
  subCatalogs?: Catalog[];
  /** 章节内容  */
  sections?: Section[];
}

/** 封面配置 */
export interface Cover {
  /** 封面标题 */
  title: string;
  /** 作者 */
  author?: string;
  /** 时间 */
  date?: string;
  /** 布局模板（模板字符串） */
  layoutTemplate?: string;
  /** 封面图片（base64编码） */
  image?: string;
  /** 封面内容列表 */
  contents?: CoverContent[];
}

/** 封面内容项  */
export interface CoverContent {
  /** 类型 */
  type: 'image' | 'text';
  /** 内容 */
  content: string;
  /** 位置/元素ID */
  elementId: string;
}

/** 签字页配置 */
export interface SignaturePage {
  /** 签字页标题 */
  title?: string;
  /** 签字人列表 */
  signers: Signer[];
  /** 布局模板（模板字符串） */
  layoutTemplate?: string;
}

/** 签字人 */
export interface Signer {
  /** 签字人姓名 */
  name: string;
  /** 签字人角色/职位 */
  role?: string;
  /** 签字图片（base64编码） */
  signature?: string;
  /** 签字日期 */
  date?: string;
}

/** 报告摘要 */
export interface ReportSummary {
  id: string;
  /** 摘要 */
  overview: string;
}

// ============================================================================
// 第5章 - 智能PPT DSL定义
// ============================================================================

/** PPT报告定义 */
export interface PPT {
  /** 报告基础信息 */
  basicInfo: BasicInfo;
  /** 报告生成元数据(通过id匹配) */
  reportMeta?: Record<string, GenerateMeta>;
  /** 幻灯片 */
  content: Slide[] | SlideSection[];
}

/** 幻灯片单一页面 */
export interface Slide {
  id: string;
  layout: PageLayout;
  /** 页面中的组件列表 */
  components: BIEngineComponent[];
}

/** 幻灯片节、子分组 */
export interface SlideSection {
  id: string;
  type: 'section';
  slides: Slide[];
}

// ============================================================================
// 第6章 - 智能Dashboard DSL定义
// ============================================================================

/** Dashboard报告定义 */
export interface Dashboard {
  /** 报告基础信息 */
  basicInfo: BasicInfo;
  /** 报告生成元数据(通过id匹配) */
  reportMeta?: Record<string, GenerateMeta>;
  /** 布局信息 */
  layout: PageLayout;
  /** 页面中的组件列表 */
  content: BIEngineComponent[];
}

// ============================================================================
// 第7章 - 智能问数DSL定义
// ============================================================================

/** 答案类型 */
export enum AnswerType {
  CHART = 'CHART',
  PLAINTEXT = 'PLAINTEXT',
  REPORT = 'REPORT',
  REPORT_DEFINITION = 'REPORT_DEFINITION',
  REPORT_TEMPLATE = 'REPORT_TEMPLATE',
}

/** 内容类型 */
export enum ContentType {
  PLAINTEXT = 'PLAINTEXT',
  MARKDOWN = 'MARKDOWN',
  SQL = 'SQL',
  CODE = 'CODE',
}

/** 会话状态 */
export enum ChatStatus {
  finished = 'finished',
  failed = 'failed',
  running = 'running',
  aborted = 'aborted',
  historyRunning = 'historyRunning',
}

/** 步骤定义 */
export interface Step {
  stepId: string;
  parentStepId?: string;
  title: string;
  contentType?: ContentType;
  status: ChatStatus;
  isStreaming?: boolean;
  content?: string;
  costTime?: number;
  subStep?: Step[];
}

/** 答案定义 */
export interface Answer {
  answerType: AnswerType;
  isStreaming: boolean;
  answer: Array<BIEngineComponent>;
}

/** 智能问数会话 */
export interface Chat {
  question?: string;
  status?: ChatStatus;
  conversationId?: string;
  chatId?: string;
  steps?: Step[];
  answer?: Answer;
  ask?: Record<string, unknown>;
  errors?: Record<string, unknown>;
  usage?: Record<string, unknown>;
  suggestions?: string[];
}

// ============================================================================
// 第8章 - 枚举定义汇总
// ============================================================================

/** 报告状态 */
export enum Status {
  /** 生成中 */
  RUNNING = 'Running',
  /** 已完成 */
  SUCCESS = 'Success',
  /** 已终止 */
  ABORTED = 'Aborted',
  /** 失败 */
  FAILED = 'Failed',
}

/** 字段类型  */
export enum FieldType {
  string = 'string',
  long = 'long',
  int = 'int',
  timestamp = 'timestamp',
  double = 'double',
  float = 'float',
  enum = 'enum',
}

/** 值格式化类型 */
export enum ValueFormatType {
  // 时间类型
  time = 'time',
  // 百分比
  percentage = 'percentage',
  // 数字
  number = 'number',
  // 字节
  byte = 'byte',
}

/** 附加信息类型 */
export enum AdditionalInfoType {
  PROMPT = 'Prompt',
  SUMMARY = 'Summary',
  SQL = 'SQL',
  API = 'API',
  KNOWLEDGE = 'Knowledge',
}

// ============================================================================
// 第9章 - 附加信息与列配置
// ============================================================================

/** 生成元数据 */
export interface GenerateMeta {
  /** 生成状态 */
  status: Status;
  /** 原始问题 */
  question: string;
  /** 附加信息 */
  additionalInfos?: AdditionalInfo[];
}

/** 附加信息 */
export interface AdditionalInfo {
  /** 属性类型 */
  type: AdditionalInfoType;
  /** 属性名称 */
  name?: string;
  /** 属性值 */
  value: string;
  /** 属性扩展字段 */
  appendix?: string;
}

/** 值格式化联合类型 */
export type ValueFormat =
  | { type: ValueFormatType.time; format: string }
  | { type: ValueFormatType.percentage; decimal?: number; unit?: string }
  | { type: ValueFormatType.number; decimal?: number; unit?: string }
  | { type: ValueFormatType.byte; decimal?: number; unit?: string };

/** 字段UI配置  */
export interface FieldUI {
  /**
   * 表格列字段展示优先级；
   * high（优先展示）
   * normal（默认展示，默认值）
   * never（从不展示）
   */
  displayPriority?: 'high' | 'normal' | 'never';
  /** 值格式化配置 */
  valueFormat?: ValueFormat;
  /** 事件配置 */
  event?: UIEvent;
}

/** 字段事件配置 */
export interface UIEvent {
  // string事件触发方式，默认只有click
  trigger: 'click' | 'dblclick' | 'hover';
  // 事件名称
  name: string;
  // 事件触发依赖字段，若依赖字段缺少，表格列不触发事件
  dependency: string[];
}

/** 枚举值配置  */
export interface EnumValue {
  // 匹配值
  value: string;
  // 展示值
  title: string;
}

/** 列配置 */
export interface Column {
  // ========== 通用属性 ==========
  /** 列显示标题 */
  title: string;
  /** 列对应数据源的key */
  key: string;
  /** 字段类型  */
  type?: FieldType;
  /** 字段枚举值配置 */
  enumConfig?: EnumValue[];
  /** 字段UI配置 */
  uiConfig?: FieldUI;
  /** 表头横向合并列数（0=被合并, 2+=跨多列）antd 风格 */
  colSpan?: number;
  /** 子列定义（多级表头）。存在 children 时，当前列为父级表头，自动跨列显示 */
  children?: Column[];
}

/** 聊天列配置（智能问数专用） */
export interface ChatColumn {
  /** 列键名 */
  key: string;
  /** 列标题 */
  title: string;
  /** 数据类型 */
  type?: FieldType;
  /** 枚举配置 */
  enumConfig?: EnumValue[];
  /** UI配置 */
  uiConfig?: FieldUI;
}
