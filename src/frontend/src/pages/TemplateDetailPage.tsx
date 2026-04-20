import { useEffect, useMemo, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { createTemplate, deleteTemplate, fetchTemplate, updateTemplate } from "../entities/templates/api";
import type {
  CatalogDefinition,
  ParameterValue,
  PresentationBlock,
  ReportTemplate,
  RequirementItemDefinition,
  SectionDefinition,
  TemplateParameter,
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

const EMPTY_PARAMETER_VALUE: ParameterValue = { label: "", value: "", query: "" };

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
    return {
      parameters: activeDraft.parameters.length,
      catalogs: countCatalogs(activeDraft.catalogs),
      sections: countSections(activeDraft.catalogs),
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
      <PageSection description="模板详情页直接编辑正式 ReportTemplate 对象。目录使用 title，章节使用 outline.requirement，不再维护旧的 section.title/order 结构。">
        <DetailPageLayout
          intro={(
            <PageIntroBar
              eyebrow="Template Detail"
              description="维护模板元信息、统一参数、递归目录与章节诉求。保存时直接提交正式模板对象。"
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
              <div className="summary-strip__item"><span>参数数</span><strong>{summary.parameters}</strong></div>
              <div className="summary-strip__item"><span>目录数</span><strong>{summary.catalogs}</strong></div>
              <div className="summary-strip__item"><span>章节数</span><strong>{summary.sections}</strong></div>
            </SurfaceCard>
          )}
          content={(
            <div className="settings-grid">
              {importWarnings.length ? (
                <StatusBanner tone="warning" title="导入提示">
                  {importWarnings.map((item) => item.message).join("；")}
                </StatusBanner>
              ) : null}
              {saveError ? <StatusBanner tone="warning" title="操作失败">{saveError}</StatusBanner> : null}

              <SurfaceCard className="settings-grid__wide">
                <div className="list-header"><div><p className="section-kicker">Metadata</p><h3>模板元信息</h3></div></div>
                <div className="form-grid">
                  <label className="field"><span className="field-label">模板 ID</span><input value={activeDraft.id} onChange={(e) => setDraftValue(setDraft, (next) => ({ ...next, id: e.target.value }))} /></label>
                  <label className="field"><span className="field-label">分类</span><input value={activeDraft.category} onChange={(e) => setDraftValue(setDraft, (next) => ({ ...next, category: e.target.value }))} /></label>
                  <label className="field"><span className="field-label">名称</span><input value={activeDraft.name} onChange={(e) => setDraftValue(setDraft, (next) => ({ ...next, name: e.target.value }))} /></label>
                  <label className="field"><span className="field-label">Schema Version</span><input value={activeDraft.schemaVersion} onChange={(e) => setDraftValue(setDraft, (next) => ({ ...next, schemaVersion: e.target.value }))} /></label>
                  <label className="field field--full"><span className="field-label">描述</span><textarea rows={3} value={activeDraft.description} onChange={(e) => setDraftValue(setDraft, (next) => ({ ...next, description: e.target.value }))} /></label>
                  <label className="field field--full"><span className="field-label">标签（逗号分隔）</span><input value={(activeDraft.tags ?? []).join(", ")} onChange={(e) => setDraftValue(setDraft, (next) => ({ ...next, tags: e.target.value.split(",").map((item) => item.trim()).filter(Boolean) }))} /></label>
                </div>
              </SurfaceCard>

              <SurfaceCard className="settings-grid__wide">
                <div className="list-header">
                  <div><p className="section-kicker">Parameters</p><h3>根参数定义</h3></div>
                  <button className="secondary-button" type="button" onClick={() => setDraftValue(setDraft, (next) => ({ ...next, parameters: [...next.parameters, createEmptyParameter()] }))}>新增参数</button>
                </div>
                <ParameterEditorList parameters={activeDraft.parameters} onChange={(parameters) => setDraftValue(setDraft, (next) => ({ ...next, parameters }))} />
              </SurfaceCard>

              <SurfaceCard className="settings-grid__wide">
                <div className="list-header">
                  <div><p className="section-kicker">Catalogs</p><h3>递归目录与章节</h3></div>
                  <button className="secondary-button" type="button" onClick={() => appendRootCatalog(setDraft)}>新增根目录</button>
                </div>
                <div className="stack-list">
                  {activeDraft.catalogs.map((catalog, index) => (
                    <CatalogEditor
                      key={`${catalog.id}-${index}`}
                      catalog={catalog}
                      path={[index]}
                      onChange={(nextCatalog) => updateCatalogAtPath(setDraft, [index], nextCatalog)}
                      onRemove={() => removeRootCatalog(setDraft, index)}
                    />
                  ))}
                </div>
              </SurfaceCard>

              {!isCreateMode ? (
                <SurfaceCard className="settings-grid__wide">
                  <div className="list-header"><div><p className="section-kicker">Danger Zone</p><h3>删除模板</h3></div></div>
                  <div className="action-row">
                    <button className="ghost-button ghost-button--inline" type="button" onClick={() => deleteMutation.mutate()}>{deleteMutation.isPending ? "删除中..." : "删除模板"}</button>
                    <Link className="secondary-button button-link" to="/templates">返回模板列表</Link>
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

type CatalogEditorProps = {
  catalog: CatalogDefinition;
  path: number[];
  onChange: (catalog: CatalogDefinition) => void;
  onRemove: () => void;
};

function CatalogEditor({ catalog, onChange, onRemove, path }: CatalogEditorProps) {
  return (
    <article className="template-editor-card">
      <div className="template-editor-card__header">
        <strong>{catalog.title || `目录 ${path.join(".") || 1}`}</strong>
        <div className="action-row action-row--compact">
          <button className="secondary-button" type="button" onClick={() => onChange({ ...catalog, subCatalogs: [...(catalog.subCatalogs ?? []), createEmptyCatalog()] })}>新增子目录</button>
          <button className="secondary-button" type="button" onClick={() => onChange({ ...catalog, sections: [...(catalog.sections ?? []), createEmptySection()] })}>新增章节</button>
          <button className="ghost-button ghost-button--inline" type="button" onClick={onRemove}>删除目录</button>
        </div>
      </div>
      <div className="form-grid">
        <label className="field"><span className="field-label">目录 ID</span><input value={catalog.id} onChange={(e) => onChange({ ...catalog, id: e.target.value })} /></label>
        <label className="field"><span className="field-label">目录标题</span><input value={catalog.title} onChange={(e) => onChange({ ...catalog, title: e.target.value })} /></label>
        <label className="field field--full"><span className="field-label">目录描述</span><textarea rows={2} value={catalog.description ?? ""} onChange={(e) => onChange({ ...catalog, description: e.target.value || undefined })} /></label>
        <label className="field"><span className="field-label">Foreach 参数</span><input value={catalog.foreach?.parameterId ?? ""} onChange={(e) => onChange({ ...catalog, foreach: normalizeForeach(e.target.value, catalog.foreach?.as ?? "item") })} /></label>
        <label className="field"><span className="field-label">Foreach 别名</span><input value={catalog.foreach?.as ?? ""} onChange={(e) => onChange({ ...catalog, foreach: normalizeForeach(catalog.foreach?.parameterId ?? "", e.target.value) })} /></label>
      </div>

      <div className="template-inline-group">
        <div className="template-inline-group__header"><strong>目录级参数</strong></div>
        <ParameterEditorList parameters={catalog.parameters ?? []} onChange={(parameters) => onChange({ ...catalog, parameters: parameters.length ? parameters : undefined })} />
      </div>

      {(catalog.subCatalogs ?? []).length ? (
        <div className="stack-list">
          {(catalog.subCatalogs ?? []).map((subCatalog, index) => (
            <CatalogEditor
              key={`${subCatalog.id}-${index}`}
              catalog={subCatalog}
              path={[...path, index]}
              onChange={(nextCatalog) => {
                const subCatalogs = [...(catalog.subCatalogs ?? [])];
                subCatalogs[index] = nextCatalog;
                onChange({ ...catalog, subCatalogs });
              }}
              onRemove={() => {
                const subCatalogs = [...(catalog.subCatalogs ?? [])];
                subCatalogs.splice(index, 1);
                onChange({ ...catalog, subCatalogs: subCatalogs.length ? subCatalogs : undefined });
              }}
            />
          ))}
        </div>
      ) : null}

      {(catalog.sections ?? []).map((section, index) => (
        <SectionEditor
          key={`${section.id}-${index}`}
          section={section}
          onChange={(nextSection) => {
            const sections = [...(catalog.sections ?? [])];
            sections[index] = nextSection;
            onChange({ ...catalog, sections });
          }}
          onRemove={() => {
            const sections = [...(catalog.sections ?? [])];
            sections.splice(index, 1);
            onChange({ ...catalog, sections: sections.length ? sections : undefined });
          }}
        />
      ))}
    </article>
  );
}

type SectionEditorProps = {
  section: SectionDefinition;
  onChange: (section: SectionDefinition) => void;
  onRemove: () => void;
};

function SectionEditor({ section, onChange, onRemove }: SectionEditorProps) {
  return (
    <article className="template-editor-subcard">
      <div className="template-editor-card__header">
        <strong>{section.id || "章节"}</strong>
        <button className="ghost-button ghost-button--inline" type="button" onClick={onRemove}>删除章节</button>
      </div>
      <div className="form-grid">
        <label className="field"><span className="field-label">章节 ID</span><input value={section.id} onChange={(e) => onChange({ ...section, id: e.target.value })} /></label>
        <label className="field field--full"><span className="field-label">章节描述</span><textarea rows={2} value={section.description ?? ""} onChange={(e) => onChange({ ...section, description: e.target.value || undefined })} /></label>
        <label className="field field--full"><span className="field-label">诉求文本</span><textarea rows={3} value={section.outline.requirement} onChange={(e) => onChange({ ...section, outline: { ...section.outline, requirement: e.target.value } })} /></label>
        <label className="field"><span className="field-label">Foreach 参数</span><input value={section.foreach?.parameterId ?? ""} onChange={(e) => onChange({ ...section, foreach: normalizeForeach(e.target.value, section.foreach?.as ?? "item") })} /></label>
        <label className="field"><span className="field-label">Foreach 别名</span><input value={section.foreach?.as ?? ""} onChange={(e) => onChange({ ...section, foreach: normalizeForeach(section.foreach?.parameterId ?? "", e.target.value) })} /></label>
        <label className="field"><span className="field-label">展示种类</span><select value={section.content.presentation.kind} onChange={(e) => onChange({ ...section, content: { ...section.content, presentation: { ...section.content.presentation, kind: e.target.value as SectionDefinition["content"]["presentation"]["kind"] } } })}><option value="narrative">narrative</option><option value="table">table</option><option value="chart">chart</option><option value="mixed">mixed</option></select></label>
      </div>

      <div className="template-inline-group"><div className="template-inline-group__header"><strong>章节级参数</strong></div><ParameterEditorList parameters={section.parameters ?? []} onChange={(parameters) => onChange({ ...section, parameters: parameters.length ? parameters : undefined })} /></div>

      <div className="template-inline-group">
        <div className="template-inline-group__header"><strong>诉求项</strong><button className="secondary-button" type="button" onClick={() => onChange({ ...section, outline: { ...section.outline, items: [...section.outline.items, createEmptyRequirementItem()] } })}>新增诉求项</button></div>
        {section.outline.items.map((item, index) => (
          <div key={`${item.id}-${index}`} className="template-inline-row template-inline-row--wide">
            <input value={item.id} onChange={(e) => updateRequirementItem(section, index, { id: e.target.value }, onChange)} placeholder="id" />
            <input value={item.label} onChange={(e) => updateRequirementItem(section, index, { label: e.target.value }, onChange)} placeholder="标签" />
            <select value={item.kind} onChange={(e) => updateRequirementItem(section, index, { kind: e.target.value as RequirementItemDefinition["kind"] }, onChange)}>
              <option value="search_target">search_target</option><option value="search_condition">search_condition</option><option value="metric">metric</option><option value="time_range">time_range</option><option value="filter">filter</option><option value="threshold">threshold</option><option value="sort">sort</option><option value="free_text">free_text</option><option value="parameter_ref">parameter_ref</option>
            </select>
            <input value={item.sourceParameterId ?? ""} onChange={(e) => updateRequirementItem(section, index, { sourceParameterId: e.target.value || undefined }, onChange)} placeholder="sourceParameterId" />
            <label className="template-inline-toggle"><input type="checkbox" checked={item.required} onChange={(e) => updateRequirementItem(section, index, { required: e.target.checked }, onChange)} />必填</label>
            <button className="ghost-button ghost-button--inline" type="button" onClick={() => onChange({ ...section, outline: { ...section.outline, items: removeAtIndex(section.outline.items, index) } })}>删除</button>
          </div>
        ))}
      </div>

      <div className="template-inline-group">
        <div className="template-inline-group__header"><strong>数据集</strong><button className="secondary-button" type="button" onClick={() => onChange({ ...section, content: { ...section.content, datasets: [...(section.content.datasets ?? []), createEmptyDataset()] } })}>新增数据集</button></div>
        {(section.content.datasets ?? []).map((dataset, index) => (
          <div key={`${dataset.id}-${index}`} className="template-inline-row template-inline-row--wide">
            <input value={dataset.id} onChange={(e) => updateDataset(section, index, { id: e.target.value }, onChange)} placeholder="dataset id" />
            <select value={dataset.sourceType} onChange={(e) => updateDataset(section, index, { sourceType: e.target.value as "sql" | "api" | "llm" | "compose" }, onChange)}><option value="sql">sql</option><option value="api">api</option><option value="llm">llm</option><option value="compose">compose</option></select>
            <input value={dataset.sourceRef} onChange={(e) => updateDataset(section, index, { sourceRef: e.target.value }, onChange)} placeholder="sourceRef" />
            <input value={dataset.name ?? ""} onChange={(e) => updateDataset(section, index, { name: e.target.value || undefined }, onChange)} placeholder="名称" />
            <button className="ghost-button ghost-button--inline" type="button" onClick={() => onChange({ ...section, content: { ...section.content, datasets: removeAtIndex(section.content.datasets ?? [], index) } })}>删除</button>
          </div>
        ))}
      </div>

      <div className="template-inline-group">
        <div className="template-inline-group__header"><strong>展示块</strong><button className="secondary-button" type="button" onClick={() => onChange({ ...section, content: { ...section.content, presentation: { ...section.content.presentation, blocks: [...section.content.presentation.blocks, createEmptyBlock()] } } })}>新增展示块</button></div>
        {section.content.presentation.blocks.map((block, index) => (
          <div key={`${block.id}-${index}`} className="template-inline-row template-inline-row--wide">
            <input value={block.id} onChange={(e) => updateBlock(section, index, { id: e.target.value }, onChange)} placeholder="block id" />
            <select value={block.type} onChange={(e) => updateBlock(section, index, { type: e.target.value as PresentationBlock["type"] }, onChange)}><option value="paragraph">paragraph</option><option value="bullet">bullet</option><option value="kpi">kpi</option><option value="table">table</option><option value="chart">chart</option><option value="markdown">markdown</option></select>
            <input value={block.title ?? ""} onChange={(e) => updateBlock(section, index, { title: e.target.value || undefined }, onChange)} placeholder="标题" />
            <input value={block.datasetId ?? ""} onChange={(e) => updateBlock(section, index, { datasetId: e.target.value || undefined }, onChange)} placeholder="datasetId" />
            <button className="ghost-button ghost-button--inline" type="button" onClick={() => onChange({ ...section, content: { ...section.content, presentation: { ...section.content.presentation, blocks: removeAtIndex(section.content.presentation.blocks, index) } } })}>删除</button>
          </div>
        ))}
      </div>
    </article>
  );
}

function ParameterEditorList({ parameters, onChange }: { parameters: TemplateParameter[]; onChange: (parameters: TemplateParameter[]) => void }) {
  return (
    <div className="stack-list">
      <button className="secondary-button" type="button" onClick={() => onChange([...parameters, createEmptyParameter()])}>新增参数</button>
      {parameters.map((parameter, index) => (
        <article key={`${parameter.id}-${index}`} className="template-editor-card">
          <div className="template-editor-card__header">
            <strong>{parameter.label || `参数 ${index + 1}`}</strong>
            <button className="ghost-button ghost-button--inline" type="button" onClick={() => onChange(removeAtIndex(parameters, index))}>删除</button>
          </div>
          <div className="form-grid">
            <label className="field"><span className="field-label">ID</span><input value={parameter.id} onChange={(e) => updateParameter(parameters, index, { id: e.target.value }, onChange)} /></label>
            <label className="field"><span className="field-label">标签</span><input value={parameter.label} onChange={(e) => updateParameter(parameters, index, { label: e.target.value }, onChange)} /></label>
            <label className="field"><span className="field-label">输入类型</span><select value={parameter.inputType} onChange={(e) => updateParameter(parameters, index, { inputType: e.target.value as TemplateParameter["inputType"] }, onChange)}><option value="free_text">free_text</option><option value="date">date</option><option value="enum">enum</option><option value="dynamic">dynamic</option></select></label>
            <label className="field"><span className="field-label">追问方式</span><select value={parameter.interactionMode} onChange={(e) => updateParameter(parameters, index, { interactionMode: e.target.value as TemplateParameter["interactionMode"] }, onChange)}><option value="form">form</option><option value="natural_language">natural_language</option></select></label>
            <label className="field field--checkbox"><span className="field-label">必填</span><input type="checkbox" checked={parameter.required} onChange={(e) => updateParameter(parameters, index, { required: e.target.checked }, onChange)} /></label>
            <label className="field field--checkbox"><span className="field-label">多值</span><input type="checkbox" checked={parameter.multi} onChange={(e) => updateParameter(parameters, index, { multi: e.target.checked }, onChange)} /></label>
            <label className="field field--full"><span className="field-label">描述</span><textarea rows={2} value={parameter.description ?? ""} onChange={(e) => updateParameter(parameters, index, { description: e.target.value || undefined }, onChange)} /></label>
            <label className="field field--full"><span className="field-label">默认值（JSON ParameterValue[]）</span><textarea rows={4} value={formatJson(parameter.defaultValue ?? [])} onChange={(e) => updateParameterJson(parameters, index, "defaultValue", e.target.value, onChange)} /></label>
            {parameter.inputType === "enum" ? <label className="field field--full"><span className="field-label">候选项（JSON ParameterValue[]）</span><textarea rows={5} value={formatJson(parameter.options ?? [EMPTY_PARAMETER_VALUE])} onChange={(e) => updateParameterJson(parameters, index, "options", e.target.value, onChange)} /></label> : null}
            {parameter.inputType === "dynamic" ? <label className="field field--full"><span className="field-label">候选值来源 URL</span><input value={parameter.source ?? ""} onChange={(e) => updateParameter(parameters, index, { source: e.target.value || undefined }, onChange)} /></label> : null}
          </div>
        </article>
      ))}
    </div>
  );
}

function createEmptyTemplate(): ReportTemplate {
  return { id: "", category: "", name: "", description: "", schemaVersion: "template.v3", tags: [], parameters: [], catalogs: [] };
}

function createEmptyParameter(): TemplateParameter {
  return {
    id: `param_${Date.now()}`,
    label: "",
    inputType: "free_text",
    required: false,
    multi: false,
    interactionMode: "form",
    description: "",
    defaultValue: [],
  };
}

function createEmptyCatalog(): CatalogDefinition {
  return { id: `catalog_${Date.now()}`, title: "", sections: [] };
}

function createEmptySection(): SectionDefinition {
  return {
    id: `section_${Date.now()}`,
    outline: { requirement: "", items: [] },
    content: { datasets: [], presentation: { kind: "mixed", blocks: [] } },
  };
}

function createEmptyRequirementItem(): RequirementItemDefinition {
  return { id: `item_${Date.now()}`, label: "", kind: "parameter_ref", required: true, multi: false, widget: "input", defaultValue: [] };
}

function createEmptyDataset() {
  return { id: `dataset_${Date.now()}`, sourceType: "sql" as const, sourceRef: "", name: "" };
}

function createEmptyBlock(): PresentationBlock {
  return { id: `block_${Date.now()}`, type: "paragraph", title: "", datasetId: "" };
}

function cloneTemplate(template: ReportTemplate): ReportTemplate {
  return JSON.parse(JSON.stringify(template)) as ReportTemplate;
}

function setDraftValue(setDraft: Dispatch<SetStateAction<ReportTemplate | null>>, updater: (draft: ReportTemplate) => ReportTemplate) {
  setDraft((current) => (current ? updater(current) : current));
}

function appendRootCatalog(setDraft: Dispatch<SetStateAction<ReportTemplate | null>>) {
  setDraftValue(setDraft, (draft) => ({ ...cloneTemplate(draft), catalogs: [...draft.catalogs, createEmptyCatalog()] }));
}

function removeRootCatalog(setDraft: Dispatch<SetStateAction<ReportTemplate | null>>, index: number) {
  setDraftValue(setDraft, (draft) => ({ ...cloneTemplate(draft), catalogs: removeAtIndex(draft.catalogs, index) }));
}

function updateCatalogAtPath(setDraft: Dispatch<SetStateAction<ReportTemplate | null>>, path: number[], nextCatalog: CatalogDefinition) {
  setDraftValue(setDraft, (draft) => {
    const next = cloneTemplate(draft);
    next.catalogs = replaceCatalogAtPath(next.catalogs, path, nextCatalog);
    return next;
  });
}

function replaceCatalogAtPath(catalogs: CatalogDefinition[], path: number[], nextCatalog: CatalogDefinition): CatalogDefinition[] {
  if (!path.length) {
    return catalogs;
  }
  const [head, ...tail] = path;
  const nextCatalogs = [...catalogs];
  if (!tail.length) {
    nextCatalogs[head] = nextCatalog;
    return nextCatalogs;
  }
  const target = nextCatalogs[head];
  nextCatalogs[head] = {
    ...target,
    subCatalogs: replaceCatalogAtPath(target.subCatalogs ?? [], tail, nextCatalog),
  };
  return nextCatalogs;
}

function updateParameter(parameters: TemplateParameter[], index: number, patch: Partial<TemplateParameter>, onChange: (parameters: TemplateParameter[]) => void) {
  const next = [...parameters];
  next[index] = { ...next[index], ...patch };
  onChange(next);
}

function updateParameterJson(parameters: TemplateParameter[], index: number, key: "defaultValue" | "options", raw: string, onChange: (parameters: TemplateParameter[]) => void) {
  try {
    const parsed = JSON.parse(raw) as ParameterValue[];
    updateParameter(parameters, index, { [key]: parsed } as Partial<TemplateParameter>, onChange);
  } catch {
    // Ignore invalid intermediate JSON while typing.
  }
}

function updateRequirementItem(section: SectionDefinition, index: number, patch: Partial<RequirementItemDefinition>, onChange: (section: SectionDefinition) => void) {
  const items = [...section.outline.items];
  items[index] = { ...items[index], ...patch };
  onChange({ ...section, outline: { ...section.outline, items } });
}

function updateDataset(section: SectionDefinition, index: number, patch: Record<string, unknown>, onChange: (section: SectionDefinition) => void) {
  const datasets = [...(section.content.datasets ?? [])];
  datasets[index] = { ...datasets[index], ...patch };
  onChange({ ...section, content: { ...section.content, datasets } });
}

function updateBlock(section: SectionDefinition, index: number, patch: Partial<PresentationBlock>, onChange: (section: SectionDefinition) => void) {
  const blocks = [...section.content.presentation.blocks];
  blocks[index] = { ...blocks[index], ...patch };
  onChange({ ...section, content: { ...section.content, presentation: { ...section.content.presentation, blocks } } });
}

function removeAtIndex<T>(items: T[], index: number): T[] {
  const next = [...items];
  next.splice(index, 1);
  return next;
}

function normalizeForeach(parameterId: string, asValue: string) {
  if (!parameterId.trim()) {
    return undefined;
  }
  return { parameterId: parameterId.trim(), as: asValue.trim() || "item" };
}

function countCatalogs(catalogs: CatalogDefinition[]): number {
  return catalogs.reduce((sum, catalog) => sum + 1 + countCatalogs(catalog.subCatalogs ?? []), 0);
}

function countSections(catalogs: CatalogDefinition[]): number {
  return catalogs.reduce((sum, catalog) => sum + (catalog.sections?.length ?? 0) + countSections(catalog.subCatalogs ?? []), 0);
}

function formatJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}
