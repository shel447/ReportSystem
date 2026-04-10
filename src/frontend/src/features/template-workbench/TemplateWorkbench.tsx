import { useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { resolveParameterOptions } from "../../entities/parameter-options/api";
import { EmptyState } from "../../shared/ui/EmptyState";
import { StatusBanner } from "../../shared/ui/StatusBanner";
import { SurfaceCard } from "../../shared/ui/SurfaceCard";
import { prettyJson } from "../../shared/utils/format";
import { summarizeSectionOutlineBindings } from "./outlineBindings";
import { buildBlueprintPreview, buildStructuralPreview } from "./preview";
import type {
  DatasetSourceKind,
  LayoutType,
  OutlineBlockType,
  ParameterInputType,
  TemplateWorkbenchState,
  WorkbenchCompositeSection,
  WorkbenchDataset,
  WorkbenchLayout,
  WorkbenchOutlineBlock,
  WorkbenchParameter,
  WorkbenchSection,
} from "./state";
import { toTemplatePayload } from "./state";
import { collectParameterReferences, validateWorkbench } from "./validation";
import "./templateWorkbench.css";

type Props = {
  value: TemplateWorkbenchState;
  onChange: (next: TemplateWorkbenchState) => void;
  onSave: () => void;
  savePending?: boolean;
};

const PARAM_TYPE_LABELS: Record<ParameterInputType, string> = {
  free_text: "文本输入",
  date: "日期选择",
  enum: "固定选项",
  dynamic: "动态选项",
};

const DATASET_KIND_LABELS: Record<DatasetSourceKind, string> = {
  sql: "SQL 查询",
  nl2sql: "自然语言查询",
  ai_synthesis: "智能总结",
};

const LAYOUT_LABELS: Record<LayoutType, string> = {
  kv_grid: "键值网格",
  tabular: "表格布局",
};

const PRESENTATION_LABELS: Record<string, string> = {
  text: "文本",
  value: "单值",
  simple_table: "简单表格",
  chart: "图表占位",
  composite_table: "复合表",
};

const OUTLINE_BLOCK_LABELS: Record<OutlineBlockType, string> = {
  indicator: "指标",
  time_range: "时间范围",
  scope: "范围",
  threshold: "阈值",
  operator: "运算符",
  enum_select: "枚举选择",
  number: "数值",
  boolean: "布尔",
  free_text: "自由文本",
  param_ref: "参数引用",
};

const TIME_RANGE_WIDGET_LABELS = {
  date: "单日期",
  date_range: "日期区间",
  relative_range: "相对时间",
} as const;

const OPERATOR_OPTIONS = [">=", ">", "<=", "<", "=", "!=", "包含", "不包含"] as const;

const SELECTABLE_OUTLINE_BLOCK_TYPES = new Set<OutlineBlockType>(["indicator", "scope", "enum_select"]);

const OUTLINE_SYNC_STATUS_LABELS = {
  not_configured: "未启用蓝图",
  stale: "待同步",
  in_sync: "已同步",
  compile_error: "引用异常",
} as const;

export function TemplateWorkbench({ value, onChange, onSave, savePending = false }: Props) {
  const [selectedParamKey, setSelectedParamKey] = useState("");
  const [selectedSectionKey, setSelectedSectionKey] = useState("");
  const [selectedDatasetKey, setSelectedDatasetKey] = useState("");
  const [selectedCompositeKey, setSelectedCompositeKey] = useState("");
  const [selectedSectionTab, setSelectedSectionTab] = useState<"outline" | "execution" | "sync">("outline");
  const [previewTab, setPreviewTab] = useState<"blueprint" | "execution" | "json">("blueprint");
  const [feedbackMessage, setFeedbackMessage] = useState("");
  const [dynamicQuery, setDynamicQuery] = useState("");

  const validationErrors = useMemo(() => validateWorkbench(value), [value]);

  useEffect(() => {
    if (!selectedParamKey || !value.parameters.some((item) => item.uiKey === selectedParamKey)) {
      setSelectedParamKey(value.parameters[0]?.uiKey ?? "");
    }
  }, [selectedParamKey, value.parameters]);

  useEffect(() => {
    if (!selectedSectionKey || !findSection(value.sections, selectedSectionKey)) {
      setSelectedSectionKey(value.sections[0]?.uiKey ?? "");
    }
  }, [selectedSectionKey, value.sections]);

  const selectedParameter = value.parameters.find((item) => item.uiKey === selectedParamKey) ?? null;
  const selectedSection = useMemo(() => findSection(value.sections, selectedSectionKey), [selectedSectionKey, value.sections]);
  const selectedDataset = selectedSection?.content?.datasets.find((item) => item.uiKey === selectedDatasetKey) ?? null;
  const selectedCompositeSection = selectedSection?.content?.presentation.sections.find((item) => item.uiKey === selectedCompositeKey) ?? null;
  const blueprintPreview = useMemo(() => buildBlueprintPreview(value), [value]);
  const executionPreview = useMemo(() => buildStructuralPreview(value), [value]);
  const exportJson = useMemo(() => prettyJson(toTemplatePayload(value)), [value]);
  const foreachDisabled = selectedSection ? hasForeachAncestor(value.sections, selectedSection.uiKey) : false;
  const selectedOutlineSummary = useMemo(
    () => (selectedSection ? summarizeSectionOutlineBindings(selectedSection) : null),
    [selectedSection],
  );
  const saveDisabled = savePending || validationErrors.length > 0;
  const dynamicOptionsMutation = useMutation({
    mutationFn: () =>
      resolveParameterOptions({
        template_id: value.meta.templateId,
        param_id: selectedParameter?.id ?? "",
        source: selectedParameter?.source ?? "",
        query: dynamicQuery.trim() || undefined,
        selected_params: buildSelectedParams(value),
      }),
  });

  useEffect(() => {
    const datasets = selectedSection?.content?.datasets ?? [];
    if (!selectedDatasetKey || !datasets.some((item) => item.uiKey === selectedDatasetKey)) {
      setSelectedDatasetKey(datasets[0]?.uiKey ?? "");
    }
  }, [selectedDatasetKey, selectedSection]);

  useEffect(() => {
    const items = selectedSection?.content?.presentation.sections ?? [];
    if (!selectedCompositeKey || !items.some((item) => item.uiKey === selectedCompositeKey)) {
      setSelectedCompositeKey(items[0]?.uiKey ?? "");
    }
  }, [selectedCompositeKey, selectedSection]);

  useEffect(() => {
    if (!feedbackMessage) {
      return;
    }
    const timer = window.setTimeout(() => setFeedbackMessage(""), 3000);
    return () => window.clearTimeout(timer);
  }, [feedbackMessage]);

  useEffect(() => {
    setDynamicQuery("");
    dynamicOptionsMutation.reset();
  }, [selectedParamKey]);

  function updateState(mutator: (draft: TemplateWorkbenchState) => void) {
    const draft = JSON.parse(JSON.stringify(value)) as TemplateWorkbenchState;
    mutator(draft);
    onChange(draft);
  }

  function updateStateWithResult(mutator: (draft: TemplateWorkbenchState) => boolean) {
    let changed = false;
    updateState((draft) => {
      changed = mutator(draft);
    });
    return changed;
  }

  function updateParameter(field: keyof WorkbenchParameter, nextValue: string | boolean | string[]) {
    if (!selectedParameter) {
      return;
    }
    updateState((draft) => {
      const current = draft.parameters.find((item) => item.uiKey === selectedParameter.uiKey);
      if (!current) {
        return;
      }
      if (field === "inputType") {
        current.inputType = nextValue as ParameterInputType;
        if (current.inputType === "date") {
          current.multi = false;
        }
        if (current.inputType !== "enum") {
          current.options = [];
        }
        if (current.inputType !== "dynamic") {
          current.source = "";
        }
        return;
      }
      if (field === "multi") {
        current.multi = Boolean(nextValue);
        return;
      }
      if (field === "interactionMode") {
        current.interactionMode = nextValue as "form" | "chat";
        return;
      }
      if (field === "required") {
        current.required = Boolean(nextValue);
        return;
      }
      if (field === "options") {
        current.options = nextValue as string[];
        return;
      }
      if (field === "source") {
        current.source = String(nextValue);
        return;
      }
      if (field === "id") {
        const previousId = current.id;
        current.id = String(nextValue);
        if (previousId && previousId !== current.id && draft.previewSamples[previousId] !== undefined) {
          draft.previewSamples[current.id] = draft.previewSamples[previousId];
          delete draft.previewSamples[previousId];
        }
        return;
      }
      if (field === "label") {
        current.label = String(nextValue);
      }
    });
  }

  function updatePreviewSample(parameter: WorkbenchParameter, rawValue: string) {
    updateState((draft) => {
      draft.previewSamples[parameter.id] = parameter.multi
        ? rawValue.split(",").map((item) => item.trim()).filter(Boolean)
        : rawValue;
    });
  }

  function addParameter() {
    const item: WorkbenchParameter = {
      uiKey: createUiKey("param"),
      id: suggestId(value.parameters.map((entry) => entry.id), "param"),
      label: "新参数",
      required: true,
      inputType: "free_text",
      interactionMode: "form",
      multi: false,
      options: [],
      source: "",
    };
    updateState((draft) => {
      draft.parameters.push(item);
    });
    setSelectedParamKey(item.uiKey);
  }

  function cloneParameter() {
    if (!selectedParameter) {
      return;
    }
    const item = {
      ...selectedParameter,
      uiKey: createUiKey("param"),
      id: suggestId(value.parameters.map((entry) => entry.id), selectedParameter.id || "param"),
      label: selectedParameter.label ? `${selectedParameter.label} 副本` : "新参数副本",
    };
    updateState((draft) => {
      const index = draft.parameters.findIndex((entry) => entry.uiKey === selectedParameter.uiKey);
      draft.parameters.splice(index + 1, 0, item);
    });
    setSelectedParamKey(item.uiKey);
  }

  function deleteParameter() {
    if (!selectedParameter) {
      return;
    }
    const references = collectParameterReferences(value, selectedParameter.id);
    if (references.length) {
      setFeedbackMessage(`参数仍被引用：${references[0]}`);
      return;
    }
    updateState((draft) => {
      draft.parameters = draft.parameters.filter((item) => item.uiKey !== selectedParameter.uiKey);
      delete draft.previewSamples[selectedParameter.id];
    });
    setSelectedParamKey("");
  }

  function moveParameter(delta: number) {
    if (!selectedParameter) {
      return;
    }
    updateState((draft) => {
      moveArrayItemByKey(draft.parameters, selectedParameter.uiKey, delta);
    });
  }

  function updateSelectedDataset(mutator: (dataset: WorkbenchDataset) => void) {
    if (!selectedSection?.content || !selectedDataset) {
      return;
    }
    updateSelectedSection((section) => {
      const current = section.content?.datasets.find((item) => item.uiKey === selectedDataset.uiKey);
      if (!current || !section.content) {
        return;
      }
      const previousId = current.id;
      mutator(current);
      if (previousId && previousId !== current.id) {
        section.content.datasets.forEach((dataset) => {
          dataset.dependsOn = dataset.dependsOn.map((dependency) => (dependency === previousId ? current.id : dependency));
          dataset.source.contextRefs = dataset.source.contextRefs.map((dependency) => (dependency === previousId ? current.id : dependency));
        });
        if (section.content.presentation.datasetId === previousId) {
          section.content.presentation.datasetId = current.id;
        }
        section.content.presentation.sections.forEach((item) => {
          if (item.datasetId === previousId) {
            item.datasetId = current.id;
          }
        });
      }
    });
  }

  function updateSelectedComposite(mutator: (section: WorkbenchCompositeSection) => void) {
    if (!selectedSection?.content || !selectedCompositeSection) {
      return;
    }
    updateSelectedSection((section) => {
      const current = section.content?.presentation.sections.find((item) => item.uiKey === selectedCompositeSection.uiKey);
      if (current) {
        mutator(current);
      }
    });
  }

  function updatePresentation(mutator: (presentation: NonNullable<WorkbenchSection["content"]>["presentation"]) => void) {
    updateSelectedSection((section) => {
      if (section.content) {
        mutator(section.content.presentation);
      }
    });
  }

  function addDataset() {
    if (!selectedSection?.content) {
      return;
    }
    const item = createDataset(selectedSection.content.datasets);
    updateSelectedSection((section) => {
      section.content?.datasets.push(item);
    });
    setSelectedDatasetKey(item.uiKey);
  }

  function duplicateDataset() {
    if (!selectedDataset) {
      return;
    }
    const item = cloneDataset(selectedDataset, selectedSection?.content?.datasets ?? []);
    updateSelectedSection((section) => {
      if (!section.content) {
        return;
      }
      const index = section.content.datasets.findIndex((entry) => entry.uiKey === selectedDataset.uiKey);
      section.content.datasets.splice(index + 1, 0, item);
    });
    setSelectedDatasetKey(item.uiKey);
  }

  function deleteDataset() {
    if (!selectedSection?.content || !selectedDataset) {
      return;
    }
    updateSelectedSection((section) => {
      if (!section.content) {
        return;
      }
      section.content.datasets = section.content.datasets.filter((item) => item.uiKey !== selectedDataset.uiKey);
      section.content.datasets.forEach((dataset) => {
        dataset.dependsOn = dataset.dependsOn.filter((dependency) => dependency !== selectedDataset.id);
        dataset.source.contextRefs = dataset.source.contextRefs.filter((dependency) => dependency !== selectedDataset.id);
      });
      if (section.content.presentation.datasetId === selectedDataset.id) {
        section.content.presentation.datasetId = "";
      }
      section.content.presentation.sections.forEach((item) => {
        if (item.datasetId === selectedDataset.id) {
          item.datasetId = "";
        }
      });
    });
    setSelectedDatasetKey("");
  }

  function moveDataset(delta: number) {
    if (!selectedDataset) {
      return;
    }
    updateSelectedSection((section) => {
      if (section.content) {
        moveArrayItemByKey(section.content.datasets, selectedDataset.uiKey, delta);
      }
    });
  }

  function addRootSection() {
    const item = createSection();
    updateState((draft) => {
      draft.sections.push(item);
    });
    setSelectedSectionKey(item.uiKey);
  }

  function addChildSection() {
    if (!selectedSection) {
      return;
    }
    const item = createSection();
    updateState((draft) => {
      const current = findSection(draft.sections, selectedSection.uiKey);
      if (!current) {
        return;
      }
      current.kind = "group";
      current.content = null;
      current.children.push(item);
    });
    setSelectedSectionKey(item.uiKey);
  }

  function duplicateSection() {
    if (!selectedSection) {
      return;
    }
    const item = cloneSection(selectedSection);
    updateState((draft) => {
      insertSiblingAfter(draft.sections, selectedSection.uiKey, item);
    });
    setSelectedSectionKey(item.uiKey);
  }

  function deleteSection() {
    if (!selectedSection) {
      return;
    }
    updateState((draft) => {
      draft.sections = removeSection(draft.sections, selectedSection.uiKey);
    });
    setSelectedSectionKey("");
  }

  function moveSection(delta: number) {
    if (!selectedSection) {
      return;
    }
    updateState((draft) => {
      moveSectionByKey(draft.sections, selectedSection.uiKey, delta);
    });
  }

  function indentSection() {
    if (!selectedSection) {
      return;
    }
    const changed = updateStateWithResult((draft) => indentSectionByKey(draft.sections, selectedSection.uiKey));
    if (!changed) {
      setFeedbackMessage("当前章节无法缩进，请先选择前一个目录章节。");
    }
  }

  function outdentSection() {
    if (!selectedSection) {
      return;
    }
    const changed = updateStateWithResult((draft) => outdentSectionByKey(draft.sections, selectedSection.uiKey));
    if (!changed) {
      setFeedbackMessage("当前章节已经位于顶层，无法继续取消缩进。");
    }
  }

  function updateSelectedSection(mutator: (section: WorkbenchSection) => void) {
    if (!selectedSection) {
      return;
    }
    updateState((draft) => {
      const current = findSection(draft.sections, selectedSection.uiKey);
      if (current) {
        mutator(current);
      }
    });
  }

  return (
    <div className="template-workbench">
      {feedbackMessage ? (
        <StatusBanner tone="info" title="已阻止当前操作">
          {feedbackMessage}
        </StatusBanner>
      ) : null}
      <div className="template-workbench__grid">
        <SurfaceCard className="template-workbench__parameters">
          <div className="list-header">
            <div>
              <p className="section-kicker">Parameters</p>
              <h3>参数工作台</h3>
              <p className="muted-text">维护参数定义和预览示例值。</p>
            </div>
            <div className="action-row action-row--compact">
              <button className="secondary-button" type="button" onClick={addParameter}>新增参数</button>
              <button className="ghost-button" type="button" onClick={cloneParameter} disabled={!selectedParameter}>复制</button>
              <button className="ghost-button" type="button" onClick={() => moveParameter(-1)} disabled={!selectedParameter}>上移</button>
              <button className="ghost-button" type="button" onClick={() => moveParameter(1)} disabled={!selectedParameter}>下移</button>
              <button className="danger-button" type="button" onClick={deleteParameter} disabled={!selectedParameter}>删除</button>
            </div>
          </div>
          <div className="workbench-split">
            <div className="workbench-pane">
              <div className="list-stack">
                {value.parameters.map((item) => (
                  <button
                    key={item.uiKey}
                    type="button"
                    className={`list-item ${item.uiKey === selectedParamKey ? "active" : ""}`}
                    onClick={() => setSelectedParamKey(item.uiKey)}
                  >
                    <strong>{item.label || "未命名参数"}</strong>
                    <span>
                      {[
                        item.id,
                        PARAM_TYPE_LABELS[item.inputType],
                        item.required ? "必填" : "可选",
                        item.multi ? "多值" : "单值",
                        item.interactionMode === "chat" ? "自然语言追问" : "结构化表单",
                      ]
                        .filter(Boolean)
                        .join(" / ")}
                    </span>
                  </button>
                ))}
              </div>
            </div>
            <div className="workbench-pane">
              {selectedParameter ? (
                <div className="form-grid">
                  <label className="field">
                    <span className="field-label">参数名称</span>
                    <input value={selectedParameter.label} onChange={(event) => updateParameter("label", event.target.value)} />
                  </label>
                  <label className="field">
                    <span className="field-label">参数标识</span>
                    <input value={selectedParameter.id} onChange={(event) => updateParameter("id", event.target.value)} />
                  </label>
                  <label className="field">
                    <span className="field-label">输入方式</span>
                    <select value={selectedParameter.inputType} onChange={(event) => updateParameter("inputType", event.target.value as ParameterInputType)}>
                      {Object.entries(PARAM_TYPE_LABELS).map(([key, label]) => (
                        <option key={key} value={key}>{label}</option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span className="field-label">追问模式</span>
                    <select
                      aria-label="追问模式"
                      value={selectedParameter.interactionMode}
                      onChange={(event) => updateParameter("interactionMode", event.target.value as "form" | "chat")}
                    >
                      <option value="form">结构化表单</option>
                      <option value="chat">自然语言追问</option>
                    </select>
                  </label>
                  <label className="field field--checkbox">
                    <span className="field-label">是否必填</span>
                    <label className="choice-chip active">
                      <input type="checkbox" checked={selectedParameter.required} onChange={(event) => updateParameter("required", event.target.checked)} />
                      <span>必填</span>
                    </label>
                  </label>
                  {(selectedParameter.inputType === "enum" || selectedParameter.inputType === "dynamic") && (
                    <label className="field field--checkbox">
                      <span className="field-label">是否多值</span>
                      <label className="choice-chip active">
                        <input type="checkbox" checked={selectedParameter.multi} onChange={(event) => updateParameter("multi", event.target.checked)} />
                        <span>允许多项</span>
                      </label>
                    </label>
                  )}
                  {selectedParameter.inputType === "enum" && (
                    <label className="field field--full">
                      <span className="field-label">固定选项（逗号分隔）</span>
                      <input value={selectedParameter.options.join(", ")} onChange={(event) => updateParameter("options", splitCsv(event.target.value))} />
                    </label>
                  )}
                  {selectedParameter.inputType === "dynamic" && (
                    <>
                      <label className="field field--full">
                        <span className="field-label">动态来源</span>
                        <input value={selectedParameter.source} onChange={(event) => updateParameter("source", event.target.value)} />
                      </label>
                      <div className="field field--full">
                        <div className="workbench-inline-header">
                          <span className="field-label">动态选项解析</span>
                          <button
                            className="ghost-button"
                            type="button"
                            onClick={() => dynamicOptionsMutation.mutate()}
                            disabled={!selectedParameter.source.trim() || dynamicOptionsMutation.isPending}
                          >
                            {dynamicOptionsMutation.isPending ? "解析中..." : "解析动态选项"}
                          </button>
                        </div>
                        <input
                          aria-label="动态选项查询"
                          value={dynamicQuery}
                          onChange={(event) => setDynamicQuery(event.target.value)}
                          placeholder="可选：输入查询词以过滤外部参数源"
                        />
                        {dynamicOptionsMutation.error ? (
                          <p className="muted-text">解析失败：{dynamicOptionsMutation.error instanceof Error ? dynamicOptionsMutation.error.message : "请求失败"}</p>
                        ) : null}
                        {dynamicOptionsMutation.data ? (
                          <div className="inline-panel">
                            <strong>解析结果</strong>
                            <div className="reason-list">
                              {dynamicOptionsMutation.data.items.length
                                ? dynamicOptionsMutation.data.items.map((item) => (
                                    <span key={`${item.label}-${item.value}`}>{item.label}（{item.value}）</span>
                                  ))
                                : [<span key="empty">暂无可选值</span>]}
                            </div>
                            <p className="muted-text">
                              返回 {dynamicOptionsMutation.data.meta.returned} 项
                              {dynamicOptionsMutation.data.meta.retryable ? "，当前错误可重试。" : ""}
                            </p>
                          </div>
                        ) : null}
                      </div>
                    </>
                  )}
                  <label className="field field--full">
                    <span className="field-label">{`${selectedParameter.label || "参数"}预览值`}</span>
                    <input
                      aria-label={`${selectedParameter.label || "参数"}预览值`}
                      value={formatPreviewSample(value.previewSamples[selectedParameter.id])}
                      placeholder={selectedParameter.multi ? "使用逗号分隔多项" : "输入预览值"}
                      onChange={(event) => updatePreviewSample(selectedParameter, event.target.value)}
                    />
                  </label>
                </div>
              ) : (
                <EmptyState title="暂无参数" description="点击“新增参数”开始配置。" />
              )}
            </div>
          </div>
        </SurfaceCard>
        <SurfaceCard className="template-workbench__sections">
          <div className="list-header">
            <div>
              <p className="section-kicker">Sections</p>
              <h3>章节工作台</h3>
              <p className="muted-text">维护章节树、foreach 和内容展示方式。</p>
            </div>
            <div className="action-row action-row--compact">
              <button className="secondary-button" type="button" onClick={addRootSection}>新增顶层章节</button>
              <button className="ghost-button" type="button" onClick={addChildSection} disabled={!selectedSection}>新增子章节</button>
              <button className="ghost-button" type="button" onClick={duplicateSection} disabled={!selectedSection}>复制</button>
              <button className="ghost-button" type="button" onClick={indentSection} disabled={!selectedSection}>缩进</button>
              <button className="ghost-button" type="button" onClick={outdentSection} disabled={!selectedSection}>取消缩进</button>
              <button className="ghost-button" type="button" onClick={() => moveSection(-1)} disabled={!selectedSection}>上移</button>
              <button className="ghost-button" type="button" onClick={() => moveSection(1)} disabled={!selectedSection}>下移</button>
              <button className="danger-button" type="button" onClick={deleteSection} disabled={!selectedSection}>删除</button>
            </div>
          </div>
          <div className="workbench-split workbench-split--wide">
            <div className="workbench-pane">
              <div className="list-stack">
                {value.sections.length ? (
                  value.sections.map((section) => (
                    <SectionTreeItem key={section.uiKey} section={section} selectedKey={selectedSectionKey} depth={0} onSelect={setSelectedSectionKey} />
                  ))
                ) : (
                  <EmptyState title="暂无章节" description="点击“新增顶层章节”开始配置。" />
                )}
              </div>
            </div>
            <div className="workbench-pane">
              {selectedSection ? (
                <div className="template-workbench__detail">
                  <div className="section-detail-tabs" role="tablist" aria-label="章节配置切换">
                    <button
                      type="button"
                      role="tab"
                      aria-selected={selectedSectionTab === "outline"}
                      className={`preview-tab ${selectedSectionTab === "outline" ? "is-active" : ""}`}
                      onClick={() => setSelectedSectionTab("outline")}
                    >
                      蓝图
                    </button>
                    <button
                      type="button"
                      role="tab"
                      aria-selected={selectedSectionTab === "execution"}
                      className={`preview-tab ${selectedSectionTab === "execution" ? "is-active" : ""}`}
                      onClick={() => setSelectedSectionTab("execution")}
                    >
                      执行链路
                    </button>
                    <button
                      type="button"
                      role="tab"
                      aria-selected={selectedSectionTab === "sync"}
                      className={`preview-tab ${selectedSectionTab === "sync" ? "is-active" : ""}`}
                      onClick={() => setSelectedSectionTab("sync")}
                    >
                      同步状态
                    </button>
                  </div>

                  {selectedSectionTab === "outline" ? (
                    <div className="template-workbench__detail" role="tabpanel" aria-label="蓝图">
                      <div className="form-grid">
                        <label className="field">
                          <span className="field-label">章节标题</span>
                          <input value={selectedSection.title} onChange={(event) => updateSelectedSection((section) => { section.title = event.target.value; })} />
                        </label>
                        <label className="field">
                          <span className="field-label">章节模式</span>
                          <select value={selectedSection.kind} onChange={(event) => updateSelectedSection((section) => { section.kind = event.target.value as WorkbenchSection["kind"]; if (section.kind === "group") { section.content = null; } else if (!section.content) { section.content = createSection().content; } })}>
                            <option value="content">内容章节</option>
                            <option value="group">目录章节</option>
                          </select>
                        </label>
                        <label className="field field--full">
                          <span className="field-label">章节说明</span>
                          <textarea rows={3} value={selectedSection.description} onChange={(event) => updateSelectedSection((section) => { section.description = event.target.value; })} />
                        </label>
                      </div>
                      <div className="inline-panel">
                        <label className="field field--checkbox">
                          <span className="field-label">按参数重复生成章节</span>
                          <label className="choice-chip active">
                            <input type="checkbox" checked={selectedSection.foreachEnabled} onChange={(event) => updateSelectedSection((section) => { section.foreachEnabled = event.target.checked; if (!event.target.checked) { section.foreachParam = ""; section.foreachAlias = "item"; } })} />
                            <span>开启 foreach</span>
                          </label>
                        </label>
                        {selectedSection.foreachEnabled ? (
                          <div className="form-grid">
                            <label className="field">
                              <span className="field-label">来源参数</span>
                              <select value={selectedSection.foreachParam} onChange={(event) => updateSelectedSection((section) => { section.foreachParam = event.target.value; })}>
                                <option value="">请选择多值参数</option>
                                {value.parameters.filter((item) => item.multi).map((item) => (
                                  <option key={item.uiKey} value={item.id}>{item.label || item.id}</option>
                                ))}
                              </select>
                            </label>
                            <label className="field">
                              <span className="field-label">循环别名</span>
                              <input value={selectedSection.foreachAlias} onChange={(event) => updateSelectedSection((section) => { section.foreachAlias = event.target.value; })} />
                            </label>
                          </div>
                        ) : null}
                      </div>
                      {selectedSection.outline ? (
                        <div className="editor-block">
                          <div className="list-header">
                            <div>
                              <p className="section-kicker">Outline</p>
                              <h4>蓝图定义</h4>
                              <p className="muted-text">面向用户的章节文稿，支持插入 {`{@block_id}`} 与全局参数占位符。</p>
                            </div>
                            <div className="action-row action-row--compact">
                              <button className="secondary-button" type="button" onClick={() => updateSelectedSection((section) => { if (section.outline) { section.outline.blocks.push(createOutlineBlock(section.outline.blocks)); } })}>新增区块</button>
                              <button className="ghost-button" type="button" onClick={() => updateSelectedSection((section) => { section.outline = null; })}>移除蓝图</button>
                            </div>
                          </div>
                          <div className="form-grid">
                            <label className="field field--full">
                              <span className="field-label">蓝图文稿</span>
                              <textarea aria-label="蓝图文稿" rows={4} value={selectedSection.outline.document} onChange={(event) => updateSelectedSection((section) => { if (section.outline) { section.outline.document = event.target.value; } })} />
                            </label>
                          </div>
                          <FieldArrayEditor
                            title="蓝图区块"
                            actionLabel="新增区块"
                            items={selectedSection.outline.blocks}
                            onAdd={() => updateSelectedSection((section) => { if (section.outline) { section.outline.blocks.push(createOutlineBlock(section.outline.blocks)); } })}
                            onRemove={(index) => updateSelectedSection((section) => { if (section.outline) { section.outline.blocks.splice(index, 1); } })}
                            renderRow={(item, index) => (
                              <OutlineBlockEditor
                                block={item}
                                parameters={value.parameters}
                                onChange={(mutator) => updateSelectedSection((section) => {
                                  const current = section.outline?.blocks[index];
                                  if (current) {
                                    mutator(current);
                                  }
                                })}
                              />
                            )}
                          />
                        </div>
                      ) : (
                        <div className="inline-panel">
                          <p>当前章节尚未启用蓝图。启用后可配置 document + blocks[] 作为用户侧大纲抽象。</p>
                          <button className="secondary-button" type="button" onClick={() => updateSelectedSection((section) => { section.outline = createOutlineBlueprint(); })}>启用蓝图</button>
                        </div>
                      )}
                    </div>
                  ) : null}

                  {selectedSectionTab === "execution" ? (
                    <div role="tabpanel" aria-label="执行链路">
                      <div className="inline-panel">
                        <p>执行链路面向系统内部生成。这里可以继续使用 {`{param}`}、{`{$var}`} 与 {`{@block_id}`} 引用蓝图值。</p>
                      </div>
                  {selectedSection.kind === "content" && selectedSection.content ? (
                    <div className="template-workbench__detail">
                      <div className="editor-block">
                        <div className="list-header">
                          <div>
                            <p className="section-kicker">Datasets</p>
                            <h4>数据准备</h4>
                            <p className="muted-text">维护章节内的数据集、依赖关系和数据源配置。</p>
                          </div>
                          <div className="action-row action-row--compact">
                            <button className="secondary-button" type="button" onClick={addDataset}>新增数据集</button>
                            <button className="ghost-button" type="button" onClick={duplicateDataset} disabled={!selectedDataset}>复制数据集</button>
                            <button className="ghost-button" type="button" onClick={() => moveDataset(-1)} disabled={!selectedDataset}>上移</button>
                            <button className="ghost-button" type="button" onClick={() => moveDataset(1)} disabled={!selectedDataset}>下移</button>
                            <button className="danger-button" type="button" onClick={deleteDataset} disabled={!selectedDataset}>删除数据集</button>
                          </div>
                        </div>
                        <div className="workbench-split">
                          <div className="workbench-pane">
                            {selectedSection.content.datasets.length ? (
                              <div className="list-stack">
                                {selectedSection.content.datasets.map((dataset) => (
                                  <button
                                    key={dataset.uiKey}
                                    type="button"
                                    className={`list-item ${dataset.uiKey === selectedDatasetKey ? "active" : ""}`}
                                    onClick={() => setSelectedDatasetKey(dataset.uiKey)}
                                  >
                                    <strong>{dataset.id || "未命名数据集"}</strong>
                                    <span>{[DATASET_KIND_LABELS[dataset.source.kind], dataset.dependsOn.length ? `依赖 ${dataset.dependsOn.join(", ")}` : null].filter(Boolean).join(" / ")}</span>
                                  </button>
                                ))}
                              </div>
                            ) : (
                              <EmptyState title="暂无数据集" description="点击“新增数据集”开始配置。" />
                            )}
                          </div>
                          <div className="workbench-pane">
                            {selectedDataset ? (
                              <div className="form-grid">
                                <label className="field">
                                  <span className="field-label">数据集 ID</span>
                                  <input aria-label="数据集 ID" value={selectedDataset.id} onChange={(event) => updateSelectedDataset((dataset) => { dataset.id = event.target.value; })} />
                                </label>
                                <label className="field">
                                  <span className="field-label">数据源类型</span>
                                  <select aria-label="数据源类型" value={selectedDataset.source.kind} onChange={(event) => updateSelectedDataset((dataset) => { dataset.source.kind = event.target.value as DatasetSourceKind; })}>
                                    {Object.entries(DATASET_KIND_LABELS).map(([key, label]) => (
                                      <option key={key} value={key}>{label}</option>
                                    ))}
                                  </select>
                                </label>
                                <label className="field field--full">
                                  <span className="field-label">依赖数据集</span>
                                  <div className="chip-grid">
                                    {selectedSection.content.datasets.filter((item) => item.uiKey !== selectedDataset.uiKey && item.id).map((item) => (
                                      <label key={item.uiKey} className={`choice-chip ${selectedDataset.dependsOn.includes(item.id) ? "active" : ""}`}>
                                        <input
                                          type="checkbox"
                                          checked={selectedDataset.dependsOn.includes(item.id)}
                                          onChange={(event) => updateSelectedDataset((dataset) => {
                                            dataset.dependsOn = toggleInArray(dataset.dependsOn, item.id, event.target.checked);
                                          })}
                                        />
                                        <span>{item.id}</span>
                                      </label>
                                    ))}
                                  </div>
                                </label>
                                <label className="field field--full">
                                  <span className="field-label">查询说明</span>
                                  <input value={selectedDataset.source.description} onChange={(event) => updateSelectedDataset((dataset) => { dataset.source.description = event.target.value; })} />
                                </label>
                                {selectedDataset.source.kind === "sql" ? (
                                  <label className="field field--full">
                                    <span className="field-label">SQL 文本</span>
                                    <textarea aria-label="SQL 文本" rows={6} value={selectedDataset.source.query} onChange={(event) => updateSelectedDataset((dataset) => { dataset.source.query = event.target.value; })} />
                                  </label>
                                ) : null}
                                {selectedDataset.source.kind === "nl2sql" ? (
                                  <label className="field field--full">
                                    <span className="field-label">自然语言查询</span>
                                    <textarea rows={5} value={selectedDataset.source.query} onChange={(event) => updateSelectedDataset((dataset) => { dataset.source.query = event.target.value; })} />
                                  </label>
                                ) : null}
                                {selectedDataset.source.kind === "ai_synthesis" ? (
                                  <>
                                    <label className="field field--full">
                                      <span className="field-label">引用数据集（逗号分隔）</span>
                                      <input value={selectedDataset.source.contextRefs.join(", ")} onChange={(event) => updateSelectedDataset((dataset) => { dataset.source.contextRefs = splitCsv(event.target.value); })} />
                                    </label>
                                    <label className="field field--full">
                                      <span className="field-label">附加查询（每行一条，id: query）</span>
                                      <textarea rows={4} value={selectedDataset.source.contextQueries.map((item) => `${item.id}: ${item.query}`).join("\n")} onChange={(event) => updateSelectedDataset((dataset) => { dataset.source.contextQueries = event.target.value.split("\n").map((line) => line.trim()).filter(Boolean).map((line, index) => { const [id, ...rest] = line.split(":"); return { id: (id || `query_${index + 1}`).trim(), query: rest.join(":").trim() }; }); })} />
                                    </label>
                                    <label className="field field--full">
                                      <span className="field-label">知识模板</span>
                                      <textarea rows={4} value={selectedDataset.source.knowledgeQueryTemplate} onChange={(event) => updateSelectedDataset((dataset) => { dataset.source.knowledgeQueryTemplate = event.target.value; })} />
                                    </label>
                                    <div className="form-grid">
                                      <label className="field"><span className="field-label">知识主题</span><input value={selectedDataset.source.knowledgeParams.subject} onChange={(event) => updateSelectedDataset((dataset) => { dataset.source.knowledgeParams.subject = event.target.value; })} /></label>
                                      <label className="field"><span className="field-label">症状</span><input value={selectedDataset.source.knowledgeParams.symptoms} onChange={(event) => updateSelectedDataset((dataset) => { dataset.source.knowledgeParams.symptoms = event.target.value; })} /></label>
                                      <label className="field"><span className="field-label">目标</span><input value={selectedDataset.source.knowledgeParams.objective} onChange={(event) => updateSelectedDataset((dataset) => { dataset.source.knowledgeParams.objective = event.target.value; })} /></label>
                                    </div>
                                    <label className="field field--full">
                                      <span className="field-label">提示词</span>
                                      <textarea rows={5} value={selectedDataset.source.prompt} onChange={(event) => updateSelectedDataset((dataset) => { dataset.source.prompt = event.target.value; })} />
                                    </label>
                                  </>
                                ) : null}
                              </div>
                            ) : (
                              <EmptyState title="未选择数据集" description="从左侧选择一个数据集进行编辑。" />
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="editor-block">
                        <div className="list-header">
                          <div>
                            <p className="section-kicker">Presentation</p>
                            <h4>展示方式</h4>
                            <p className="muted-text">按数据集结果配置文本、表格、图表占位或复合表。</p>
                          </div>
                        </div>
                        <div className="form-grid">
                          <label className="field">
                            <span className="field-label">展示类型</span>
                            <select aria-label="展示类型" value={selectedSection.content.presentation.type} onChange={(event) => updatePresentation((presentation) => { presentation.type = event.target.value as typeof presentation.type; })}>
                              <option value="text">文本</option>
                              <option value="value">单值</option>
                              <option value="simple_table">简单表格</option>
                              <option value="chart">图表占位</option>
                              <option value="composite_table">复合表</option>
                            </select>
                          </label>
                          {(selectedSection.content.presentation.type === "value" || selectedSection.content.presentation.type === "simple_table" || selectedSection.content.presentation.type === "chart") ? (
                            <label className="field">
                              <span className="field-label">绑定数据集</span>
                              <select aria-label="绑定数据集" value={selectedSection.content.presentation.datasetId} onChange={(event) => updatePresentation((presentation) => { presentation.datasetId = event.target.value; })}>
                                <option value="">请选择数据集</option>
                                {selectedSection.content.datasets.filter((item) => item.id).map((item) => (
                                  <option key={item.uiKey} value={item.id}>{item.id}</option>
                                ))}
                              </select>
                            </label>
                          ) : null}
                          {selectedSection.content.presentation.type === "text" ? (
                            <label className="field field--full">
                              <span className="field-label">模板文本</span>
                              <textarea rows={4} value={selectedSection.content.presentation.template} onChange={(event) => updatePresentation((presentation) => { presentation.template = event.target.value; })} />
                            </label>
                          ) : null}
                          {selectedSection.content.presentation.type === "value" ? (
                            <label className="field">
                              <span className="field-label">锚点模板</span>
                              <input value={selectedSection.content.presentation.anchor} onChange={(event) => updatePresentation((presentation) => { presentation.anchor = event.target.value; })} />
                            </label>
                          ) : null}
                          {selectedSection.content.presentation.type === "composite_table" ? (
                            <>
                              <label className="field">
                                <span className="field-label">总列数</span>
                                <input type="number" min={1} value={selectedSection.content.presentation.columns ?? 2} onChange={(event) => updatePresentation((presentation) => { presentation.columns = Number(event.target.value) || 2; })} />
                              </label>
                              <FieldArrayEditor
                                title="复合表分区"
                                actionLabel="新增分区"
                                items={selectedSection.content.presentation.sections}
                                onAdd={() => updatePresentation((presentation) => { presentation.sections.push(createCompositeSection(presentation.sections)); })}
                                onRemove={(index) => updatePresentation((presentation) => { presentation.sections.splice(index, 1); })}
                                renderRow={(item, index) => (
                                  <div className="array-editor__stack">
                                    <div className="array-editor__inline-grid array-editor__inline-grid--triple">
                                      <input value={item.id} onChange={(event) => updatePresentation((presentation) => { const current = presentation.sections[index]; if (current) { current.id = event.target.value; } })} placeholder="分区 ID" />
                                      <input value={item.band} onChange={(event) => updatePresentation((presentation) => { const current = presentation.sections[index]; if (current) { current.band = event.target.value; } })} placeholder="Band" />
                                      <select value={item.layout.type} onChange={(event) => updatePresentation((presentation) => { const current = presentation.sections[index]; if (current) { current.layout = createLayout(event.target.value as LayoutType); } })}>
                                        {Object.entries(LAYOUT_LABELS).map(([key, label]) => (
                                          <option key={key} value={key}>{label}</option>
                                        ))}
                                      </select>
                                    </div>
                                    <input value={item.datasetId} onChange={(event) => updatePresentation((presentation) => { const current = presentation.sections[index]; if (current) { current.datasetId = event.target.value; } })} placeholder="绑定数据集" />
                                    {item.layout.type === "kv_grid" ? (
                                      <input value={item.layout.fields.map((field) => field.key).join(", ")} onChange={(event) => updatePresentation((presentation) => { const current = presentation.sections[index]; if (current) { current.layout.fields = splitCsv(event.target.value).map((field) => ({ key: field, value: field })); } })} placeholder="字段列表（逗号分隔）" />
                                    ) : (
                                      <>
                                        <input value={item.layout.headers.map((header) => header.label).join(", ")} onChange={(event) => updatePresentation((presentation) => { const current = presentation.sections[index]; if (current) { current.layout.headers = splitCsv(event.target.value).map((label) => ({ label, span: 1 })); } })} placeholder="表头（逗号分隔）" />
                                        <input value={item.layout.columns.map((column) => column.field).join(", ")} onChange={(event) => updatePresentation((presentation) => { const current = presentation.sections[index]; if (current) { current.layout.columns = splitCsv(event.target.value).map((field) => ({ field, span: 1 })); } })} placeholder="列字段（逗号分隔）" />
                                      </>
                                    )}
                                  </div>
                                )}
                              />
                            </>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="inline-panel"><p>当前为目录章节，仅维护子章节结构。</p></div>
                  )}
                    </div>
                  ) : null}

                  {selectedSectionTab === "sync" ? (
                    <div className="inline-panel sync-panel" role="tabpanel" aria-label="同步状态">
                      <div className="sync-panel__header">
                        <span className={`status-chip status-chip--${selectedOutlineSummary?.status ?? "not_configured"}`}>{OUTLINE_SYNC_STATUS_LABELS[selectedOutlineSummary?.status ?? "not_configured"]}</span>
                        <span className="muted-text">
                          {selectedOutlineSummary?.status === "in_sync" ? `执行链路已引用 ${selectedOutlineSummary.bindings.length} 个蓝图区块。` : null}
                          {selectedOutlineSummary?.status === "stale" ? "已配置蓝图，但执行链路还没有使用任何蓝图区块引用。" : null}
                          {selectedOutlineSummary?.status === "not_configured" ? "当前章节尚未启用蓝图。执行链路仍可独立维护。" : null}
                          {selectedOutlineSummary?.status === "compile_error" ? "执行链路中存在无法解析的 {@block_id} 引用。" : null}
                        </span>
                      </div>
                      {selectedOutlineSummary?.bindings.length ? (
                        <div className="sync-panel__group">
                          <strong>已引用区块</strong>
                          <ul className="validation-list">
                            {selectedOutlineSummary.bindings.map((binding) => (
                              <li key={binding.blockId}>{binding.blockId} · {binding.targets.join(" / ")}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                      {selectedOutlineSummary?.invalidBlockIds.length ? (
                        <div className="sync-panel__group">
                          <strong>异常引用</strong>
                          <ul className="validation-list">
                            {selectedOutlineSummary.invalidBlockIds.map((item) => (
                              <li key={item}>{item}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                      {selectedSection.outline?.blocks.length ? (
                        <div className="sync-panel__group">
                          <strong>当前蓝图区块</strong>
                          <div className="chip-grid">
                            {selectedSection.outline.blocks.map((block) => (
                              <span key={block.uiKey} className="inline-badge">{block.id || "未命名区块"}</span>
                            ))}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ) : (
                <EmptyState title="未选择章节" description="从左侧选择一个章节进行编辑。" />
              )}
            </div>
          </div>
        </SurfaceCard>
        <SurfaceCard className="template-workbench__preview">
          <div className="list-header">
            <div>
              <p className="section-kicker">Preview</p>
              <h3>结构预览</h3>
              <p className="muted-text">切换查看蓝图层、执行层和模板 JSON。</p>
            </div>
          </div>
          <div className="preview-tabs" role="tablist" aria-label="结构预览切换">
            <button
              type="button"
              role="tab"
              aria-selected={previewTab === "blueprint"}
              className={`preview-tab ${previewTab === "blueprint" ? "is-active" : ""}`}
              onClick={() => setPreviewTab("blueprint")}
            >
              蓝图预览
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={previewTab === "execution"}
              className={`preview-tab ${previewTab === "execution" ? "is-active" : ""}`}
              onClick={() => setPreviewTab("execution")}
            >
              执行预览
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={previewTab === "json"}
              className={`preview-tab ${previewTab === "json" ? "is-active" : ""}`}
              onClick={() => setPreviewTab("json")}
            >
              模板 JSON
            </button>
          </div>
          {previewTab === "blueprint" ? (
            <div className="preview-stack" role="tabpanel" aria-label="蓝图预览">
              {blueprintPreview.sections.length ? (
                blueprintPreview.sections.map((item, index) => (
                  <article key={`${item.title}-${index}`} className="preview-section" data-level={item.level}>
                    <strong>{item.title || `章节 ${index + 1}`}</strong>
                    {item.description ? <p>{item.description}</p> : null}
                    {item.content ? <div className="preview-section__content">{item.content}</div> : null}
                  </article>
                ))
              ) : (
                <EmptyState title="蓝图预览为空" description="请先添加蓝图文稿或示例值。" />
              )}
            </div>
          ) : null}
          {previewTab === "execution" ? (
            <div className="preview-stack" role="tabpanel" aria-label="执行预览">
              {executionPreview.sections.length ? (
                executionPreview.sections.map((item, index) => (
                  <article key={`${item.title}-${index}`} className="preview-section" data-level={item.level}>
                    <strong>{item.title || `章节 ${index + 1}`}</strong>
                    {item.description ? <p>{item.description}</p> : null}
                    {item.content ? <div className="preview-section__content">{item.content}</div> : null}
                  </article>
                ))
              ) : (
                <EmptyState title="执行预览为空" description="请先添加章节或示例值。" />
              )}
            </div>
          ) : null}
          {previewTab === "json" ? (
            <div className="inline-panel" role="tabpanel" aria-label="模板 JSON">
              <p>{value.meta.compatibility.migratedFromLegacy ? "该模板来自旧版结构，保存后将按新版结构维护。" : "当前模板已按新版结构维护。"}</p>
              {validationErrors.length ? (
                <ul className="validation-list">
                  {validationErrors.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : null}
              <pre>{exportJson}</pre>
            </div>
          ) : null}
        </SurfaceCard>
      </div>
      <div className="template-workbench__footer">
        <div className="action-row">
          <button className="primary-button" type="button" onClick={onSave} disabled={saveDisabled}>{savePending ? "保存中..." : "保存模板"}</button>
        </div>
      </div>
    </div>
  );
}

function SectionTreeItem({ section, selectedKey, depth, onSelect }: { section: WorkbenchSection; selectedKey: string; depth: number; onSelect: (uiKey: string) => void; }) {
  return (
    <div className="section-tree-item" style={{ paddingLeft: depth * 14 }}>
      <button type="button" className={`list-item ${section.uiKey === selectedKey ? "active" : ""}`} onClick={() => onSelect(section.uiKey)}>
        <strong>{section.title || "未命名章节"}</strong>
        <span>{[
          section.foreachEnabled ? `foreach: ${section.foreachParam || "未设置"}` : null,
          section.kind === "group"
            ? `目录章节 / ${section.children.length} 个子章节`
            : `内容章节 / ${section.content?.datasets.length ?? 0} 个数据集 / ${PRESENTATION_LABELS[section.content?.presentation.type ?? "text"]}`,
        ].filter(Boolean).join(" / ")}</span>
      </button>
      {section.children.length ? <div className="section-tree-item__children">{section.children.map((child) => <SectionTreeItem key={child.uiKey} section={child} selectedKey={selectedKey} depth={depth + 1} onSelect={onSelect} />)}</div> : null}
    </div>
  );
}

function FieldArrayEditor<T>({
  title,
  actionLabel,
  items,
  onAdd,
  onRemove,
  renderRow,
}: {
  title: string;
  actionLabel: string;
  items: T[];
  onAdd: () => void;
  onRemove: (index: number) => void;
  renderRow: (item: T, index: number) => JSX.Element;
}) {
  return (
    <div className="array-editor field field--full">
      <div className="workbench-inline-header">
        <strong>{title}</strong>
        <button className="ghost-button" type="button" onClick={onAdd}>{actionLabel}</button>
      </div>
      <div className="array-editor__stack">
        {items.length ? items.map((item, index) => (
          <div key={index} className="array-editor__row">
            {renderRow(item, index)}
            <button className="danger-button" type="button" onClick={() => onRemove(index)}>删除</button>
          </div>
        )) : <p className="muted-text">暂无配置项。</p>}
      </div>
    </div>
  );
}

function OutlineBlockEditor({
  block,
  parameters,
  onChange,
}: {
  block: WorkbenchOutlineBlock;
  parameters: WorkbenchParameter[];
  onChange: (mutator: (block: WorkbenchOutlineBlock) => void) => void;
}) {
  const blockLabel = block.id || block.uiKey;
  const optionsMode = getOutlineBlockOptionsMode(block);

  return (
    <div className="outline-block-editor">
      <div className="array-editor__inline-grid array-editor__inline-grid--triple">
        <label className="field">
          <span className="field-label">区块 ID</span>
          <input
            aria-label={`区块 ID ${blockLabel}`}
            value={block.id}
            onChange={(event) => onChange((current) => {
              current.id = event.target.value;
            })}
            placeholder="区块 ID"
          />
        </label>
        <label className="field">
          <span className="field-label">区块类型</span>
          <select
            aria-label={`区块类型 ${blockLabel}`}
            value={block.type}
            onChange={(event) => onChange((current) => {
              applyOutlineBlockType(current, event.target.value as OutlineBlockType);
            })}
          >
            {Object.entries(OUTLINE_BLOCK_LABELS).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span className="field-label">提示语</span>
          <input
            aria-label={`提示语 ${blockLabel}`}
            value={block.hint}
            onChange={(event) => onChange((current) => {
              current.hint = event.target.value;
            })}
            placeholder="提示语"
          />
        </label>
      </div>

      <div className="outline-block-editor__typed">
        <label className="field">
          <span className="field-label">默认值</span>
          <input
            aria-label={`默认值 ${blockLabel}`}
            value={block.defaultValue}
            onChange={(event) => onChange((current) => {
              current.defaultValue = event.target.value;
            })}
            placeholder="默认值"
          />
        </label>

        {block.type === "time_range" ? (
          <label className="field">
            <span className="field-label">时间控件</span>
            <select
              aria-label={`时间控件 ${blockLabel}`}
              value={normalizeTimeRangeWidget(block.widget)}
              onChange={(event) => onChange((current) => {
                current.widget = event.target.value;
              })}
            >
              {Object.entries(TIME_RANGE_WIDGET_LABELS).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </label>
        ) : null}

        {block.type === "param_ref" ? (
          <>
            <label className="field">
              <span className="field-label">绑定参数</span>
              <select
                aria-label={`绑定参数 ${blockLabel}`}
                value={block.paramId}
                onChange={(event) => onChange((current) => {
                  current.paramId = event.target.value;
                })}
              >
                <option value="">绑定参数</option>
                {parameters.map((parameter) => (
                  <option key={parameter.uiKey} value={parameter.id}>{parameter.label || parameter.id}</option>
                ))}
              </select>
            </label>
            <p className="outline-block-editor__hint">该区块的取值直接来自全局参数，不在章节蓝图内重复配置选项。</p>
          </>
        ) : null}

        {SELECTABLE_OUTLINE_BLOCK_TYPES.has(block.type) ? (
          <>
            <label className="field">
              <span className="field-label">选项来源</span>
              <select
                aria-label={`选项来源 ${blockLabel}`}
                value={optionsMode}
                onChange={(event) => onChange((current) => {
                  applyOutlineBlockOptionsMode(current, event.target.value as "options" | "source");
                })}
              >
                <option value="options">固定选项</option>
                <option value="source">动态来源</option>
              </select>
            </label>
            {optionsMode === "options" ? (
              <label className="field field--full">
                <span className="field-label">固定选项</span>
                <input
                  aria-label={`固定选项 ${blockLabel}`}
                  value={block.options.join(", ")}
                  onChange={(event) => onChange((current) => {
                    current.options = splitCsv(event.target.value);
                  })}
                  placeholder="候选项（逗号分隔）"
                />
              </label>
            ) : (
              <label className="field field--full">
                <span className="field-label">动态来源</span>
                <input
                  aria-label={`动态来源 ${blockLabel}`}
                  value={block.source}
                  onChange={(event) => onChange((current) => {
                    current.source = event.target.value;
                  })}
                  placeholder="动态来源"
                />
              </label>
            )}
          </>
        ) : null}

        {(block.type === "number" || block.type === "threshold") ? (
          <label className="field">
            <span className="field-label">数值默认值</span>
            <input
              aria-label={`数值默认值 ${blockLabel}`}
              type="number"
              value={block.defaultValue}
              onChange={(event) => onChange((current) => {
                current.defaultValue = event.target.value;
              })}
              placeholder="默认数值"
            />
          </label>
        ) : null}

        {block.type === "boolean" ? (
          <label className="field">
            <span className="field-label">布尔默认值</span>
            <select
              aria-label={`布尔默认值 ${blockLabel}`}
              value={normalizeBooleanValue(block.defaultValue)}
              onChange={(event) => onChange((current) => {
                current.defaultValue = event.target.value;
              })}
            >
              <option value="false">否</option>
              <option value="true">是</option>
            </select>
          </label>
        ) : null}

        {block.type === "operator" ? (
          <label className="field">
            <span className="field-label">运算符默认值</span>
            <select
              aria-label={`运算符默认值 ${blockLabel}`}
              value={normalizeOperatorValue(block.defaultValue)}
              onChange={(event) => onChange((current) => {
                current.defaultValue = event.target.value;
              })}
            >
              {OPERATOR_OPTIONS.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </label>
        ) : null}

        {!SELECTABLE_OUTLINE_BLOCK_TYPES.has(block.type)
          && block.type !== "param_ref"
          && block.type !== "time_range"
          && block.type !== "number"
          && block.type !== "threshold"
          && block.type !== "boolean"
          && block.type !== "operator" ? (
          <label className="field">
            <span className="field-label">控件形态</span>
            <input
              aria-label={`控件形态 ${blockLabel}`}
              value={block.widget}
              onChange={(event) => onChange((current) => {
                current.widget = event.target.value;
              })}
              placeholder="控件形态"
            />
          </label>
        ) : null}

        {block.type === "free_text" ? (
          <label className="field field--checkbox">
            <input
              aria-label={`允许多值 ${blockLabel}`}
              type="checkbox"
              checked={block.multi}
              onChange={(event) => onChange((current) => {
                current.multi = event.target.checked;
              })}
            />
            <span>允许多值</span>
          </label>
        ) : null}
      </div>
    </div>
  );
}

function createSection(): WorkbenchSection {
  return {
    uiKey: createUiKey("section"),
    title: "新章节",
    description: "",
    foreachEnabled: false,
    foreachParam: "",
    foreachAlias: "item",
    kind: "content",
    outline: null,
    content: {
      datasets: [],
      presentation: {
        type: "text",
        template: "",
        anchor: "{$value}",
        datasetId: "",
        chartType: "bar",
        sections: [],
      },
    },
    children: [],
  };
}

function createOutlineBlueprint() {
  return {
    document: "",
    blocks: [createOutlineBlock([])],
  };
}

function createOutlineBlock(existing: WorkbenchOutlineBlock[]): WorkbenchOutlineBlock {
  return {
    uiKey: createUiKey("outline-block"),
    id: suggestId(existing.map((item) => item.id), "block"),
    type: "free_text",
    hint: "",
    defaultValue: "",
    options: [],
    source: "",
    paramId: "",
    multi: false,
    widget: "",
  };
}

function applyOutlineBlockType(block: WorkbenchOutlineBlock, nextType: OutlineBlockType) {
  block.type = nextType;
  block.multi = false;

  if (nextType === "param_ref") {
    block.options = [];
    block.source = "";
    block.widget = "";
    return;
  }

  block.paramId = "";

  if (nextType === "time_range") {
    block.options = [];
    block.source = "";
    block.widget = normalizeTimeRangeWidget(block.widget);
    return;
  }

  if (SELECTABLE_OUTLINE_BLOCK_TYPES.has(nextType)) {
    if (block.source.trim()) {
      block.options = [];
      block.widget = "dynamic_source";
    } else {
      block.source = "";
      if (!block.widget.trim() || block.widget === "dynamic_source") {
        block.widget = "select";
      }
    }
    return;
  }
}

function getOutlineBlockOptionsMode(block: WorkbenchOutlineBlock): "options" | "source" {
  return block.widget === "dynamic_source" || block.source.trim() ? "source" : "options";
}

function applyOutlineBlockOptionsMode(block: WorkbenchOutlineBlock, mode: "options" | "source") {
  if (mode === "options") {
    block.source = "";
    block.widget = "select";
    return;
  }
  block.options = [];
  block.widget = "dynamic_source";
}

function normalizeTimeRangeWidget(widget: string) {
  if (widget === "date" || widget === "relative_range" || widget === "date_range") {
    return widget;
  }
  return "date_range";
}

function normalizeBooleanValue(value: string) {
  return value === "true" ? "true" : "false";
}

function normalizeOperatorValue(value: string) {
  return OPERATOR_OPTIONS.includes(value as (typeof OPERATOR_OPTIONS)[number]) ? value : ">=";
}

function cloneSection(section: WorkbenchSection): WorkbenchSection {
  const copy = JSON.parse(JSON.stringify(section)) as WorkbenchSection;
  assignSectionKeys(copy);
  return copy;
}

function createDataset(existing: WorkbenchDataset[]): WorkbenchDataset {
  return {
    uiKey: createUiKey("dataset"),
    id: suggestId(existing.map((item) => item.id), "dataset"),
    dependsOn: [],
    source: {
      kind: "sql",
      query: "",
      description: "",
      keyCol: "",
      valueCol: "",
      prompt: "",
      contextRefs: [],
      contextQueries: [],
      knowledgeQueryTemplate: "",
      knowledgeParams: {
        subject: "",
        symptoms: "",
        objective: "",
      },
    },
  };
}

function cloneDataset(dataset: WorkbenchDataset, existing: WorkbenchDataset[]): WorkbenchDataset {
  const copy = JSON.parse(JSON.stringify(dataset)) as WorkbenchDataset;
  copy.uiKey = createUiKey("dataset");
  copy.id = suggestId(existing.map((item) => item.id), dataset.id || "dataset");
  return copy;
}

function createCompositeSection(existing: WorkbenchCompositeSection[]): WorkbenchCompositeSection {
  return {
    uiKey: createUiKey("composite"),
    id: suggestId(existing.map((item) => item.id), "band"),
    band: "",
    datasetId: "",
    layout: createLayout("kv_grid"),
  };
}

function createLayout(type: LayoutType): WorkbenchLayout {
  return type === "kv_grid"
    ? {
        type,
        colsPerRow: 2,
        keySpan: 1,
        valueSpan: 1,
        fields: [{ key: "", value: "" }],
        headers: [],
        columns: [],
      }
    : {
        type,
        fields: [],
        headers: [{ label: "", span: 1 }],
        columns: [{ field: "", span: 1 }],
      };
}

function assignSectionKeys(section: WorkbenchSection) {
  section.uiKey = createUiKey("section");
  section.outline?.blocks.forEach((block) => {
    block.uiKey = createUiKey("outline-block");
  });
  section.children.forEach(assignSectionKeys);
  section.content?.datasets.forEach((dataset) => {
    dataset.uiKey = createUiKey("dataset");
  });
  section.content?.presentation.sections.forEach((item) => {
    item.uiKey = createUiKey("composite");
  });
}

function findSection(sections: WorkbenchSection[], uiKey: string): WorkbenchSection | null {
  for (const section of sections) {
    if (section.uiKey === uiKey) {
      return section;
    }
    const nested = findSection(section.children, uiKey);
    if (nested) {
      return nested;
    }
  }
  return null;
}

function removeSection(sections: WorkbenchSection[], uiKey: string): WorkbenchSection[] {
  return sections.filter((section) => section.uiKey !== uiKey).map((section) => ({ ...section, children: removeSection(section.children, uiKey) }));
}

function insertSiblingAfter(sections: WorkbenchSection[], targetKey: string, nextSection: WorkbenchSection): boolean {
  const index = sections.findIndex((section) => section.uiKey === targetKey);
  if (index >= 0) {
    sections.splice(index + 1, 0, nextSection);
    return true;
  }
  return sections.some((section) => insertSiblingAfter(section.children, targetKey, nextSection));
}

function moveSectionByKey(sections: WorkbenchSection[], targetKey: string, delta: number): boolean {
  const index = sections.findIndex((section) => section.uiKey === targetKey);
  if (index >= 0) {
    const nextIndex = index + delta;
    if (nextIndex < 0 || nextIndex >= sections.length) {
      return true;
    }
    const [item] = sections.splice(index, 1);
    sections.splice(nextIndex, 0, item);
    return true;
  }
  return sections.some((section) => moveSectionByKey(section.children, targetKey, delta));
}

function hasForeachAncestor(sections: WorkbenchSection[], uiKey: string, ancestorForeach = false): boolean {
  for (const section of sections) {
    if (section.uiKey === uiKey) {
      return ancestorForeach;
    }
    if (hasForeachAncestor(section.children, uiKey, ancestorForeach || section.foreachEnabled)) {
      return true;
    }
  }
  return false;
}

function indentSectionByKey(sections: WorkbenchSection[], targetKey: string): boolean {
  const index = sections.findIndex((section) => section.uiKey === targetKey);
  if (index > 0) {
    const previous = sections[index - 1];
    if (previous.kind !== "group") {
      return false;
    }
    const [item] = sections.splice(index, 1);
    previous.children.push(item);
    return true;
  }
  return sections.some((section) => indentSectionByKey(section.children, targetKey));
}

function outdentSectionByKey(sections: WorkbenchSection[], targetKey: string): boolean {
  return outdentWithin(sections, targetKey, null, -1);
}

function outdentWithin(
  sections: WorkbenchSection[],
  targetKey: string,
  parentSections: WorkbenchSection[] | null,
  parentIndex: number,
): boolean {
  const index = sections.findIndex((section) => section.uiKey === targetKey);
  if (index >= 0) {
    if (!parentSections || parentIndex < 0) {
      return false;
    }
    const [item] = sections.splice(index, 1);
    parentSections.splice(parentIndex + 1, 0, item);
    return true;
  }
  for (let currentIndex = 0; currentIndex < sections.length; currentIndex += 1) {
    if (outdentWithin(sections[currentIndex].children, targetKey, sections, currentIndex)) {
      return true;
    }
  }
  return false;
}

function moveArrayItemByKey<T extends { uiKey: string }>(items: T[], uiKey: string, delta: number) {
  const index = items.findIndex((item) => item.uiKey === uiKey);
  if (index < 0) {
    return;
  }
  const nextIndex = index + delta;
  if (nextIndex < 0 || nextIndex >= items.length) {
    return;
  }
  const [item] = items.splice(index, 1);
  items.splice(nextIndex, 0, item);
}

function splitCsv(value: string): string[] {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function toggleInArray(items: string[], value: string, checked: boolean) {
  if (checked) {
    return Array.from(new Set([...items, value]));
  }
  return items.filter((item) => item !== value);
}

function formatPreviewSample(value: string | string[] | undefined): string {
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  return value ?? "";
}

function buildSelectedParams(state: TemplateWorkbenchState): Record<string, unknown> {
  return Object.fromEntries(
    state.parameters
      .filter((parameter) => parameter.id)
      .map((parameter) => [parameter.id, state.previewSamples[parameter.id] ?? ""]),
  );
}

function suggestId(existingIds: string[], prefix: string) {
  const normalizedPrefix = prefix.trim() || "item";
  let index = 1;
  let candidate = normalizedPrefix;
  while (!candidate || existingIds.includes(candidate)) {
    candidate = `${normalizedPrefix}_${index}`;
    index += 1;
  }
  return candidate;
}

let uiCounter = 0;
function createUiKey(prefix: string) {
  uiCounter += 1;
  return `${prefix}-${uiCounter}`;
}
