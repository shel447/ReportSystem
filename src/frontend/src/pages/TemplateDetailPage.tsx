import { useEffect, useMemo, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { createTemplate, deleteTemplate, fetchTemplate, updateTemplate } from "../entities/templates/api";
import type {
  CatalogDefinition,
  PresentationBlock,
  ReportTemplate,
  RequirementItemDefinition,
  SectionDefinition,
  TemplateParameter,
  TrioValue,
  WarningItem,
} from "../entities/templates/types";
import { DetailPageLayout } from "../shared/layouts/DetailPageLayout";
import { PageIntroBar } from "../shared/layouts/PageIntroBar";
import { PageSection } from "../shared/ui/PageSection";
import { StatusBanner } from "../shared/ui/StatusBanner";
import { SurfaceCard } from "../shared/ui/SurfaceCard";

type LocationState = {
  importDraft?: ReportTemplate;
  importWarnings?: WarningItem[];
};

const EMPTY_TRIO: TrioValue = { display: "", value: "", query: "" };

export function TemplateDetailPage() {
  const { templateId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const locationState = (location.state as LocationState | null) ?? null;
  const isCreateMode = !templateId;
  const [draft, setDraft] = useState<ReportTemplate | null>(
    locationState?.importDraft ?? (isCreateMode ? createEmptyTemplate() : null),
  );
  const [saveError, setSaveError] = useState("");
  const [importWarnings] = useState<WarningItem[]>(locationState?.importWarnings ?? []);

  const templateQuery = useQuery({
    queryKey: ["template", templateId],
    queryFn: () => fetchTemplate(templateId ?? ""),
    enabled: Boolean(templateId),
    staleTime: 0,
  });

  useEffect(() => {
    if (templateQuery.data) {
      setDraft(templateQuery.data);
    }
  }, [templateQuery.data]);

  const saveMutation = useMutation({
    mutationFn: async (payload: ReportTemplate) => {
      if (isCreateMode) {
        return createTemplate(payload);
      }
      return updateTemplate(templateId ?? payload.id, payload);
    },
    onSuccess: async (payload) => {
      setDraft(payload);
      setSaveError("");
      await queryClient.invalidateQueries({ queryKey: ["templates"] });
      await queryClient.invalidateQueries({ queryKey: ["template", payload.id] });
      if (isCreateMode) {
        navigate(`/templates/${payload.id}`, { replace: true });
      }
    },
    onError: (error) => {
      setSaveError(error instanceof Error ? error.message : "模板保存失败。");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      if (!templateId) {
        return;
      }
      return deleteTemplate(templateId);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["templates"] });
      navigate("/templates");
    },
    onError: (error) => {
      setSaveError(error instanceof Error ? error.message : "模板删除失败。");
    },
  });

  const activeDraft = draft;
  const summary = useMemo(() => {
    if (!activeDraft) {
      return { parameters: 0, catalogs: 0, sections: 0 };
    }
    const sections = activeDraft.catalogs.reduce((count, catalog) => count + catalog.sections.length, 0);
    return {
      parameters: activeDraft.parameters.length,
      catalogs: activeDraft.catalogs.length,
      sections,
    };
  }, [activeDraft]);

  if (!activeDraft) {
    return (
      <PageSection description="模板不存在或加载失败。">
        <StatusBanner tone="warning" title="无法加载模板详情">
          {saveError || "未找到模板。"}
        </StatusBanner>
      </PageSection>
    );
  }

  return (
    <div className="template-detail-page">
      <PageSection description="模板详情页直接编辑正式 ReportTemplate 对象，不再存在旧 sections 根结构或兼容映射。">
        <DetailPageLayout
          intro={(
            <PageIntroBar
              eyebrow="Template Detail"
              description="维护模板元信息、参数定义、目录与章节诉求。保存时直接提交正式模板对象。"
              badge={isCreateMode ? "新建模板" : activeDraft.id}
              actions={(
                <>
                  {!isCreateMode ? (
                    <a
                      className="secondary-button button-link"
                      href={`/rest/chatbi/v1/templates/${encodeURIComponent(activeDraft.id)}/export`}
                    >
                      导出 JSON
                    </a>
                  ) : null}
                  <button className="primary-button" type="button" onClick={() => saveMutation.mutate(activeDraft)}>
                    {saveMutation.isPending ? "保存中..." : "保存模板"}
                  </button>
                </>
              )}
            />
          )}
          summary={(
            <SurfaceCard className="summary-strip">
              <div className="summary-strip__item">
                <span>参数数</span>
                <strong>{summary.parameters}</strong>
              </div>
              <div className="summary-strip__item">
                <span>目录数</span>
                <strong>{summary.catalogs}</strong>
              </div>
              <div className="summary-strip__item">
                <span>章节数</span>
                <strong>{summary.sections}</strong>
              </div>
            </SurfaceCard>
          )}
          content={(
            <div className="settings-grid">
              {importWarnings.length ? (
                <StatusBanner tone="warning" title="导入提示">
                  {importWarnings.map((item) => item.message).join("；")}
                </StatusBanner>
              ) : null}
              {saveError ? (
                <StatusBanner tone="warning" title="操作失败">
                  {saveError}
                </StatusBanner>
              ) : null}

              <SurfaceCard className="settings-grid__wide">
                <div className="list-header">
                  <div>
                    <p className="section-kicker">Metadata</p>
                    <h3>模板元信息</h3>
                  </div>
                </div>
                <div className="form-grid">
                  <label className="field">
                    <span className="field-label">模板 ID</span>
                    <input value={activeDraft.id} onChange={(event) => setDraftValue(setDraft, (next) => ({ ...next, id: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span className="field-label">分类</span>
                    <input value={activeDraft.category} onChange={(event) => setDraftValue(setDraft, (next) => ({ ...next, category: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span className="field-label">名称</span>
                    <input value={activeDraft.name} onChange={(event) => setDraftValue(setDraft, (next) => ({ ...next, name: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span className="field-label">Schema Version</span>
                    <input value={activeDraft.schemaVersion} onChange={(event) => setDraftValue(setDraft, (next) => ({ ...next, schemaVersion: event.target.value }))} />
                  </label>
                  <label className="field field--full">
                    <span className="field-label">描述</span>
                    <textarea rows={3} value={activeDraft.description} onChange={(event) => setDraftValue(setDraft, (next) => ({ ...next, description: event.target.value }))} />
                  </label>
                  <label className="field field--full">
                    <span className="field-label">标签（逗号分隔）</span>
                    <input
                      value={(activeDraft.tags ?? []).join(", ")}
                      onChange={(event) =>
                        setDraftValue(setDraft, (next) => ({
                          ...next,
                          tags: event.target.value.split(",").map((item) => item.trim()).filter(Boolean),
                        }))}
                    />
                  </label>
                </div>
              </SurfaceCard>

              <SurfaceCard className="settings-grid__wide">
                <div className="list-header">
                  <div>
                    <p className="section-kicker">Parameters</p>
                    <h3>参数定义</h3>
                  </div>
                  <button className="secondary-button" type="button" onClick={() => appendParameter(setDraft)}>
                    新增参数
                  </button>
                </div>
                <div className="stack-list">
                  {activeDraft.parameters.map((parameter, index) => (
                    <article key={`${parameter.id}-${index}`} className="template-editor-card">
                      <div className="template-editor-card__header">
                        <strong>{parameter.label || `参数 ${index + 1}`}</strong>
                        <button className="ghost-button ghost-button--inline" type="button" onClick={() => removeAt(setDraft, ["parameters"], index)}>
                          删除
                        </button>
                      </div>
                      <div className="form-grid">
                        <label className="field">
                          <span className="field-label">ID</span>
                          <input value={parameter.id} onChange={(event) => updateParameter(setDraft, index, { id: event.target.value })} />
                        </label>
                        <label className="field">
                          <span className="field-label">标签</span>
                          <input value={parameter.label} onChange={(event) => updateParameter(setDraft, index, { label: event.target.value })} />
                        </label>
                        <label className="field">
                          <span className="field-label">输入类型</span>
                          <select value={parameter.inputType} onChange={(event) => updateParameter(setDraft, index, { inputType: event.target.value as TemplateParameter["inputType"] })}>
                            <option value="free_text">free_text</option>
                            <option value="date">date</option>
                            <option value="enum">enum</option>
                            <option value="dynamic">dynamic</option>
                          </select>
                        </label>
                        <label className="field">
                          <span className="field-label">追问方式</span>
                          <select value={parameter.interactionMode} onChange={(event) => updateParameter(setDraft, index, { interactionMode: event.target.value as TemplateParameter["interactionMode"] })}>
                            <option value="form">form</option>
                            <option value="natural_language">natural_language</option>
                          </select>
                        </label>
                        <label className="field">
                          <span className="field-label">取值模式</span>
                          <select value={parameter.valueMode} onChange={(event) => updateParameter(setDraft, index, { valueMode: event.target.value as TemplateParameter["valueMode"] })}>
                            <option value="display">display</option>
                            <option value="value">value</option>
                            <option value="query">query</option>
                          </select>
                        </label>
                        <label className="field field--checkbox">
                          <span className="field-label">必填</span>
                          <input type="checkbox" checked={parameter.required} onChange={(event) => updateParameter(setDraft, index, { required: event.target.checked })} />
                        </label>
                        <label className="field field--checkbox">
                          <span className="field-label">多值</span>
                          <input type="checkbox" checked={parameter.multi} onChange={(event) => updateParameter(setDraft, index, { multi: event.target.checked })} />
                        </label>
                        <label className="field field--full">
                          <span className="field-label">描述</span>
                          <textarea rows={2} value={parameter.description ?? ""} onChange={(event) => updateParameter(setDraft, index, { description: event.target.value || undefined })} />
                        </label>
                        <label className="field field--full">
                          <span className="field-label">默认值（JSON TrioValue[]）</span>
                          <textarea rows={4} value={formatJson(parameter.defaultValue ?? [])} onChange={(event) => updateParameterJson(setDraft, index, "defaultValue", event.target.value)} />
                        </label>
                        {parameter.inputType === "enum" ? (
                          <label className="field field--full">
                            <span className="field-label">枚举选项（JSON TrioValue[]）</span>
                            <textarea rows={5} value={formatJson(parameter.options ?? [EMPTY_TRIO])} onChange={(event) => updateParameterJson(setDraft, index, "options", event.target.value)} />
                          </label>
                        ) : null}
                        {parameter.inputType === "dynamic" ? (
                          <label className="field field--full">
                            <span className="field-label">开放数据源 URL</span>
                            <input value={parameter.openSource?.url ?? ""} onChange={(event) => updateParameter(setDraft, index, { openSource: { url: event.target.value } })} />
                          </label>
                        ) : null}
                      </div>
                    </article>
                  ))}
                </div>
              </SurfaceCard>

              <SurfaceCard className="settings-grid__wide">
                <div className="list-header">
                  <div>
                    <p className="section-kicker">Catalogs</p>
                    <h3>目录与章节</h3>
                  </div>
                  <button className="secondary-button" type="button" onClick={() => appendCatalog(setDraft)}>
                    新增目录
                  </button>
                </div>
                <div className="stack-list">
                  {activeDraft.catalogs.map((catalog, catalogIndex) => (
                    <article key={`${catalog.id}-${catalogIndex}`} className="template-editor-card">
                      <div className="template-editor-card__header">
                        <strong>{catalog.name || `目录 ${catalogIndex + 1}`}</strong>
                        <div className="action-row action-row--compact">
                          <button className="secondary-button" type="button" onClick={() => appendSection(setDraft, catalogIndex)}>
                            新增章节
                          </button>
                          <button className="ghost-button ghost-button--inline" type="button" onClick={() => removeAt(setDraft, ["catalogs"], catalogIndex)}>
                            删除目录
                          </button>
                        </div>
                      </div>
                      <div className="form-grid">
                        <label className="field">
                          <span className="field-label">目录 ID</span>
                          <input value={catalog.id} onChange={(event) => updateCatalog(setDraft, catalogIndex, { id: event.target.value })} />
                        </label>
                        <label className="field">
                          <span className="field-label">目录名称</span>
                          <input value={catalog.name} onChange={(event) => updateCatalog(setDraft, catalogIndex, { name: event.target.value })} />
                        </label>
                        <label className="field">
                          <span className="field-label">排序</span>
                          <input value={String(catalog.order ?? catalogIndex + 1)} onChange={(event) => updateCatalog(setDraft, catalogIndex, { order: Number(event.target.value || 1) })} />
                        </label>
                        <label className="field field--full">
                          <span className="field-label">目录描述</span>
                          <textarea rows={2} value={catalog.description ?? ""} onChange={(event) => updateCatalog(setDraft, catalogIndex, { description: event.target.value || undefined })} />
                        </label>
                      </div>

                      <div className="stack-list">
                        {catalog.sections.map((section, sectionIndex) => (
                          <article key={`${section.id}-${sectionIndex}`} className="template-editor-subcard">
                            <div className="template-editor-card__header">
                              <strong>{section.title || `章节 ${sectionIndex + 1}`}</strong>
                              <button className="ghost-button ghost-button--inline" type="button" onClick={() => removeSection(setDraft, catalogIndex, sectionIndex)}>
                                删除章节
                              </button>
                            </div>
                            <div className="form-grid">
                              <label className="field">
                                <span className="field-label">章节 ID</span>
                                <input value={section.id} onChange={(event) => updateSection(setDraft, catalogIndex, sectionIndex, { id: event.target.value })} />
                              </label>
                              <label className="field">
                                <span className="field-label">章节标题</span>
                                <input value={section.title} onChange={(event) => updateSection(setDraft, catalogIndex, sectionIndex, { title: event.target.value })} />
                              </label>
                              <label className="field">
                                <span className="field-label">排序</span>
                                <input value={String(section.order ?? sectionIndex + 1)} onChange={(event) => updateSection(setDraft, catalogIndex, sectionIndex, { order: Number(event.target.value || 1) })} />
                              </label>
                              <label className="field field--full">
                                <span className="field-label">章节描述</span>
                                <textarea rows={2} value={section.description ?? ""} onChange={(event) => updateSection(setDraft, catalogIndex, sectionIndex, { description: event.target.value || undefined })} />
                              </label>
                              <label className="field field--full">
                                <span className="field-label">诉求文本</span>
                                <textarea rows={3} value={section.outline.requirement} onChange={(event) => updateSection(setDraft, catalogIndex, sectionIndex, { outline: { ...section.outline, requirement: event.target.value } })} />
                              </label>
                              <label className="field">
                                <span className="field-label">Foreach 参数</span>
                                <input value={section.foreach?.parameterId ?? ""} onChange={(event) => updateSection(setDraft, catalogIndex, sectionIndex, { foreach: normalizeForeach(event.target.value, section.foreach?.as ?? "item") })} />
                              </label>
                              <label className="field">
                                <span className="field-label">Foreach 别名</span>
                                <input value={section.foreach?.as ?? ""} onChange={(event) => updateSection(setDraft, catalogIndex, sectionIndex, { foreach: normalizeForeach(section.foreach?.parameterId ?? "", event.target.value) })} />
                              </label>
                              <label className="field">
                                <span className="field-label">展示种类</span>
                                <select value={section.content.presentation.kind} onChange={(event) => updateSection(setDraft, catalogIndex, sectionIndex, { content: { ...section.content, presentation: { ...section.content.presentation, kind: event.target.value as SectionDefinition["content"]["presentation"]["kind"] } } })}>
                                  <option value="narrative">narrative</option>
                                  <option value="table">table</option>
                                  <option value="chart">chart</option>
                                  <option value="mixed">mixed</option>
                                </select>
                              </label>
                            </div>

                            <div className="template-inline-group">
                              <div className="template-inline-group__header">
                                <strong>诉求项</strong>
                                <button className="secondary-button" type="button" onClick={() => appendRequirementItem(setDraft, catalogIndex, sectionIndex)}>
                                  新增诉求项
                                </button>
                              </div>
                              {section.outline.items.map((item, itemIndex) => (
                                <div key={`${item.id}-${itemIndex}`} className="template-inline-row template-inline-row--wide">
                                  <input value={item.id} onChange={(event) => updateRequirementItem(setDraft, catalogIndex, sectionIndex, itemIndex, { id: event.target.value })} placeholder="id" />
                                  <input value={item.label} onChange={(event) => updateRequirementItem(setDraft, catalogIndex, sectionIndex, itemIndex, { label: event.target.value })} placeholder="标签" />
                                  <select value={item.kind} onChange={(event) => updateRequirementItem(setDraft, catalogIndex, sectionIndex, itemIndex, { kind: event.target.value as RequirementItemDefinition["kind"] })}>
                                    <option value="search_target">search_target</option>
                                    <option value="search_condition">search_condition</option>
                                    <option value="metric">metric</option>
                                    <option value="time_range">time_range</option>
                                    <option value="filter">filter</option>
                                    <option value="threshold">threshold</option>
                                    <option value="sort">sort</option>
                                    <option value="free_text">free_text</option>
                                    <option value="parameter_ref">parameter_ref</option>
                                  </select>
                                  <input value={item.sourceParameterId ?? ""} onChange={(event) => updateRequirementItem(setDraft, catalogIndex, sectionIndex, itemIndex, { sourceParameterId: event.target.value || undefined })} placeholder="sourceParameterId" />
                                  <label className="template-inline-toggle">
                                    <input type="checkbox" checked={item.required} onChange={(event) => updateRequirementItem(setDraft, catalogIndex, sectionIndex, itemIndex, { required: event.target.checked })} />
                                    必填
                                  </label>
                                  <button className="ghost-button ghost-button--inline" type="button" onClick={() => removeRequirementItem(setDraft, catalogIndex, sectionIndex, itemIndex)}>
                                    删除
                                  </button>
                                </div>
                              ))}
                            </div>

                            <div className="template-inline-group">
                              <div className="template-inline-group__header">
                                <strong>数据集</strong>
                                <button className="secondary-button" type="button" onClick={() => appendDataset(setDraft, catalogIndex, sectionIndex)}>
                                  新增数据集
                                </button>
                              </div>
                              {(section.content.datasets ?? []).map((dataset, datasetIndex) => (
                                <div key={`${dataset.id}-${datasetIndex}`} className="template-inline-row template-inline-row--wide">
                                  <input value={dataset.id} onChange={(event) => updateDataset(setDraft, catalogIndex, sectionIndex, datasetIndex, { id: event.target.value })} placeholder="dataset id" />
                                  <select value={dataset.sourceType} onChange={(event) => updateDataset(setDraft, catalogIndex, sectionIndex, datasetIndex, { sourceType: event.target.value as "sql" | "api" | "llm" | "compose" })}>
                                    <option value="sql">sql</option>
                                    <option value="api">api</option>
                                    <option value="llm">llm</option>
                                    <option value="compose">compose</option>
                                  </select>
                                  <input value={dataset.sourceRef} onChange={(event) => updateDataset(setDraft, catalogIndex, sectionIndex, datasetIndex, { sourceRef: event.target.value })} placeholder="sourceRef" />
                                  <input value={dataset.name ?? ""} onChange={(event) => updateDataset(setDraft, catalogIndex, sectionIndex, datasetIndex, { name: event.target.value || undefined })} placeholder="名称" />
                                  <button className="ghost-button ghost-button--inline" type="button" onClick={() => removeDataset(setDraft, catalogIndex, sectionIndex, datasetIndex)}>
                                    删除
                                  </button>
                                </div>
                              ))}
                            </div>

                            <div className="template-inline-group">
                              <div className="template-inline-group__header">
                                <strong>展示块</strong>
                                <button className="secondary-button" type="button" onClick={() => appendBlock(setDraft, catalogIndex, sectionIndex)}>
                                  新增展示块
                                </button>
                              </div>
                              {section.content.presentation.blocks.map((block, blockIndex) => (
                                <div key={`${block.id}-${blockIndex}`} className="template-inline-row template-inline-row--wide">
                                  <input value={block.id} onChange={(event) => updateBlock(setDraft, catalogIndex, sectionIndex, blockIndex, { id: event.target.value })} placeholder="block id" />
                                  <select value={block.type} onChange={(event) => updateBlock(setDraft, catalogIndex, sectionIndex, blockIndex, { type: event.target.value as PresentationBlock["type"] })}>
                                    <option value="paragraph">paragraph</option>
                                    <option value="bullet">bullet</option>
                                    <option value="kpi">kpi</option>
                                    <option value="table">table</option>
                                    <option value="chart">chart</option>
                                    <option value="markdown">markdown</option>
                                  </select>
                                  <input value={block.title ?? ""} onChange={(event) => updateBlock(setDraft, catalogIndex, sectionIndex, blockIndex, { title: event.target.value || undefined })} placeholder="标题" />
                                  <input value={block.datasetId ?? ""} onChange={(event) => updateBlock(setDraft, catalogIndex, sectionIndex, blockIndex, { datasetId: event.target.value || undefined })} placeholder="datasetId" />
                                  <button className="ghost-button ghost-button--inline" type="button" onClick={() => removeBlock(setDraft, catalogIndex, sectionIndex, blockIndex)}>
                                    删除
                                  </button>
                                </div>
                              ))}
                            </div>
                          </article>
                        ))}
                      </div>
                    </article>
                  ))}
                </div>
              </SurfaceCard>

              {!isCreateMode ? (
                <SurfaceCard className="settings-grid__wide">
                  <div className="list-header">
                    <div>
                      <p className="section-kicker">Danger Zone</p>
                      <h3>删除模板</h3>
                    </div>
                  </div>
                  <div className="action-row">
                    <button className="ghost-button ghost-button--inline" type="button" onClick={() => deleteMutation.mutate()}>
                      {deleteMutation.isPending ? "删除中..." : "删除模板"}
                    </button>
                    <Link className="secondary-button button-link" to="/templates">
                      返回模板列表
                    </Link>
                  </div>
                </SurfaceCard>
              ) : null}
            </div>
          )}
        />
      </PageSection>
    </div>
  );
}

function createEmptyTemplate(): ReportTemplate {
  return {
    id: "",
    category: "",
    name: "",
    description: "",
    schemaVersion: "template.v3",
    tags: [],
    parameters: [],
    catalogs: [],
  };
}

function createEmptyParameter(): TemplateParameter {
  return {
    id: `param_${Date.now()}`,
    label: "",
    inputType: "free_text",
    required: false,
    multi: false,
    interactionMode: "form",
    valueMode: "value",
    description: "",
    defaultValue: [],
  };
}

function createEmptyCatalog(): CatalogDefinition {
  return {
    id: `catalog_${Date.now()}`,
    name: "",
    order: 1,
    sections: [],
  };
}

function createEmptySection(): SectionDefinition {
  return {
    id: `section_${Date.now()}`,
    title: "",
    order: 1,
    outline: {
      requirement: "",
      items: [],
    },
    content: {
      datasets: [],
      presentation: {
        kind: "mixed",
        blocks: [],
      },
    },
  };
}

function createEmptyRequirementItem(): RequirementItemDefinition {
  return {
    id: `item_${Date.now()}`,
    label: "",
    kind: "parameter_ref",
    required: true,
    multi: false,
    widget: "input",
    defaultValue: [],
  };
}

function createEmptyDataset() {
  return {
    id: `dataset_${Date.now()}`,
    sourceType: "sql" as const,
    sourceRef: "",
    name: "",
  };
}

function createEmptyBlock(): PresentationBlock {
  return {
    id: `block_${Date.now()}`,
    type: "paragraph",
    title: "",
    datasetId: "",
  };
}

function cloneTemplate(template: ReportTemplate): ReportTemplate {
  return JSON.parse(JSON.stringify(template)) as ReportTemplate;
}

function setDraftValue(
  setDraft: Dispatch<SetStateAction<ReportTemplate | null>>,
  updater: (draft: ReportTemplate) => ReportTemplate,
) {
  setDraft((current) => (current ? updater(current) : current));
}

function appendParameter(setDraft: Dispatch<SetStateAction<ReportTemplate | null>>) {
  setDraftValue(setDraft, (draft) => ({ ...cloneTemplate(draft), parameters: [...draft.parameters, createEmptyParameter()] }));
}

function updateParameter(
  setDraft: Dispatch<SetStateAction<ReportTemplate | null>>,
  index: number,
  patch: Partial<TemplateParameter>,
) {
  setDraftValue(setDraft, (draft) => {
    const next = cloneTemplate(draft);
    next.parameters[index] = { ...next.parameters[index], ...patch };
    return next;
  });
}

function updateParameterJson(
  setDraft: Dispatch<SetStateAction<ReportTemplate | null>>,
  index: number,
  key: "defaultValue" | "options",
  raw: string,
) {
  try {
    const parsed = JSON.parse(raw) as TrioValue[];
    updateParameter(setDraft, index, { [key]: parsed } as Partial<TemplateParameter>);
  } catch {
    // Ignore invalid intermediate JSON while typing.
  }
}

function appendCatalog(setDraft: Dispatch<SetStateAction<ReportTemplate | null>>) {
  setDraftValue(setDraft, (draft) => ({ ...cloneTemplate(draft), catalogs: [...draft.catalogs, createEmptyCatalog()] }));
}

function updateCatalog(
  setDraft: Dispatch<SetStateAction<ReportTemplate | null>>,
  catalogIndex: number,
  patch: Partial<CatalogDefinition>,
) {
  setDraftValue(setDraft, (draft) => {
    const next = cloneTemplate(draft);
    next.catalogs[catalogIndex] = { ...next.catalogs[catalogIndex], ...patch };
    return next;
  });
}

function appendSection(setDraft: Dispatch<SetStateAction<ReportTemplate | null>>, catalogIndex: number) {
  setDraftValue(setDraft, (draft) => {
    const next = cloneTemplate(draft);
    next.catalogs[catalogIndex].sections.push(createEmptySection());
    return next;
  });
}

function updateSection(
  setDraft: Dispatch<SetStateAction<ReportTemplate | null>>,
  catalogIndex: number,
  sectionIndex: number,
  patch: Partial<SectionDefinition>,
) {
  setDraftValue(setDraft, (draft) => {
    const next = cloneTemplate(draft);
    next.catalogs[catalogIndex].sections[sectionIndex] = { ...next.catalogs[catalogIndex].sections[sectionIndex], ...patch };
    return next;
  });
}

function appendRequirementItem(
  setDraft: Dispatch<SetStateAction<ReportTemplate | null>>,
  catalogIndex: number,
  sectionIndex: number,
) {
  setDraftValue(setDraft, (draft) => {
    const next = cloneTemplate(draft);
    next.catalogs[catalogIndex].sections[sectionIndex].outline.items.push(createEmptyRequirementItem());
    return next;
  });
}

function updateRequirementItem(
  setDraft: Dispatch<SetStateAction<ReportTemplate | null>>,
  catalogIndex: number,
  sectionIndex: number,
  itemIndex: number,
  patch: Partial<RequirementItemDefinition>,
) {
  setDraftValue(setDraft, (draft) => {
    const next = cloneTemplate(draft);
    next.catalogs[catalogIndex].sections[sectionIndex].outline.items[itemIndex] = {
      ...next.catalogs[catalogIndex].sections[sectionIndex].outline.items[itemIndex],
      ...patch,
    };
    return next;
  });
}

function appendDataset(
  setDraft: Dispatch<SetStateAction<ReportTemplate | null>>,
  catalogIndex: number,
  sectionIndex: number,
) {
  setDraftValue(setDraft, (draft) => {
    const next = cloneTemplate(draft);
    next.catalogs[catalogIndex].sections[sectionIndex].content.datasets = [
      ...(next.catalogs[catalogIndex].sections[sectionIndex].content.datasets ?? []),
      createEmptyDataset(),
    ];
    return next;
  });
}

function updateDataset(
  setDraft: Dispatch<SetStateAction<ReportTemplate | null>>,
  catalogIndex: number,
  sectionIndex: number,
  datasetIndex: number,
  patch: Record<string, unknown>,
) {
  setDraftValue(setDraft, (draft) => {
    const next = cloneTemplate(draft);
    const datasets = next.catalogs[catalogIndex].sections[sectionIndex].content.datasets ?? [];
    datasets[datasetIndex] = { ...datasets[datasetIndex], ...patch };
    next.catalogs[catalogIndex].sections[sectionIndex].content.datasets = datasets;
    return next;
  });
}

function appendBlock(
  setDraft: Dispatch<SetStateAction<ReportTemplate | null>>,
  catalogIndex: number,
  sectionIndex: number,
) {
  setDraftValue(setDraft, (draft) => {
    const next = cloneTemplate(draft);
    next.catalogs[catalogIndex].sections[sectionIndex].content.presentation.blocks.push(createEmptyBlock());
    return next;
  });
}

function updateBlock(
  setDraft: Dispatch<SetStateAction<ReportTemplate | null>>,
  catalogIndex: number,
  sectionIndex: number,
  blockIndex: number,
  patch: Partial<PresentationBlock>,
) {
  setDraftValue(setDraft, (draft) => {
    const next = cloneTemplate(draft);
    next.catalogs[catalogIndex].sections[sectionIndex].content.presentation.blocks[blockIndex] = {
      ...next.catalogs[catalogIndex].sections[sectionIndex].content.presentation.blocks[blockIndex],
      ...patch,
    };
    return next;
  });
}

function removeAt(
  setDraft: Dispatch<SetStateAction<ReportTemplate | null>>,
  path: ["parameters"] | ["catalogs"],
  index: number,
) {
  setDraftValue(setDraft, (draft) => {
    const next = cloneTemplate(draft);
    next[path[0]].splice(index, 1);
    return next;
  });
}

function removeSection(
  setDraft: Dispatch<SetStateAction<ReportTemplate | null>>,
  catalogIndex: number,
  sectionIndex: number,
) {
  setDraftValue(setDraft, (draft) => {
    const next = cloneTemplate(draft);
    next.catalogs[catalogIndex].sections.splice(sectionIndex, 1);
    return next;
  });
}

function removeRequirementItem(
  setDraft: Dispatch<SetStateAction<ReportTemplate | null>>,
  catalogIndex: number,
  sectionIndex: number,
  itemIndex: number,
) {
  setDraftValue(setDraft, (draft) => {
    const next = cloneTemplate(draft);
    next.catalogs[catalogIndex].sections[sectionIndex].outline.items.splice(itemIndex, 1);
    return next;
  });
}

function removeDataset(
  setDraft: Dispatch<SetStateAction<ReportTemplate | null>>,
  catalogIndex: number,
  sectionIndex: number,
  datasetIndex: number,
) {
  setDraftValue(setDraft, (draft) => {
    const next = cloneTemplate(draft);
    (next.catalogs[catalogIndex].sections[sectionIndex].content.datasets ?? []).splice(datasetIndex, 1);
    return next;
  });
}

function removeBlock(
  setDraft: Dispatch<SetStateAction<ReportTemplate | null>>,
  catalogIndex: number,
  sectionIndex: number,
  blockIndex: number,
) {
  setDraftValue(setDraft, (draft) => {
    const next = cloneTemplate(draft);
    next.catalogs[catalogIndex].sections[sectionIndex].content.presentation.blocks.splice(blockIndex, 1);
    return next;
  });
}

function normalizeForeach(parameterId: string, asValue: string) {
  if (!parameterId.trim()) {
    return undefined;
  }
  return {
    parameterId: parameterId.trim(),
    as: asValue.trim() || "item",
  };
}

function formatJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}
