import { useEffect, useMemo, useState } from "react";
import type { Dispatch, ReactNode, SetStateAction } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Download, FileText, ListTree, Plus, Save, Trash2 } from "lucide-react";

import { createTemplate, deleteTemplate, fetchTemplate, updateTemplate } from "../entities/templates/api";
import type {
  CatalogDefinition,
  ChapterDefinition,
  FlowReportTemplate,
  ParameterValue,
  PresentationBlock,
  ReportTemplate,
  RequirementItemDefinition,
  SectionDefinition,
  TemplateStructureType,
  TemplateParameter,
  WarningItem,
} from "../entities/templates/types";
import { PageSection } from "../shared/ui/PageSection";
import { StatusBanner } from "../shared/ui/StatusBanner";

type LocationState = {
  importDraft?: ReportTemplate;
  importWarnings?: WarningItem[];
};

const EMPTY_PARAMETER_VALUE: ParameterValue = { label: "", value: "", query: "" };

type TemplateSummaryStats = {
  structureType: TemplateStructureType;
  parameters: number;
  catalogs: number;
  chapters: number;
  slides: number;
  sections: number;
};

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
      return { structureType: "flow" as TemplateStructureType, parameters: 0, catalogs: 0, chapters: 0, slides: 0, sections: 0 };
    }
    const structureType = resolveTemplateStructure(activeDraft);
    return {
      structureType,
      parameters: activeDraft.parameters.length,
      catalogs: structureType === "flow" ? countCatalogs(getTemplateCatalogs(activeDraft)) : 0,
      chapters: structureType === "paged" ? getTemplateChapters(activeDraft).length : 0,
      slides: structureType === "paged" ? countSlides(getTemplateChapters(activeDraft)) : 0,
      sections: structureType === "flow" ? countSections(getTemplateCatalogs(activeDraft)) : countPagedSections(getTemplateChapters(activeDraft)),
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
    <div className="template-detail-workbench">
      <header className="template-detail-toolbar">
        <div className="template-detail-toolbar__title">
          <Link className="icon-button button-link" to="/templates" aria-label="返回模板列表" title="返回模板列表">
            <ArrowLeft size={16} aria-hidden="true" />
          </Link>
          <div>
            <p>{isCreateMode ? "新建模板" : activeDraft.id}</p>
            <h1>{activeDraft.name || (isCreateMode ? "新建模板" : "未命名模板")}</h1>
          </div>
          <span className="status-chip status-chip--soft">{summary.structureType === "paged" ? "PPT" : "Flow"}</span>
        </div>
        <div className="template-detail-toolbar__actions">
          {!isCreateMode ? (
            <a className="secondary-button button-link" href={`/rest/chatbi/v1/templates/${encodeURIComponent(activeDraft.id)}/export`}>
              <Download size={16} aria-hidden="true" />
              导出 JSON
            </a>
          ) : null}
          <button className="primary-button" type="button" onClick={() => saveMutation.mutate(activeDraft)}>
            <Save size={16} aria-hidden="true" />
            {saveMutation.isPending ? "保存中..." : "保存模板"}
          </button>
        </div>
      </header>

      {importWarnings.length ? (
        <StatusBanner tone="warning" title="导入提示">
          {importWarnings.map((item) => item.message).join("；")}
        </StatusBanner>
      ) : null}
      {saveError ? <StatusBanner tone="warning" title="操作失败">{saveError}</StatusBanner> : null}

      <div className="template-detail-layout">
        <TemplateWorkspaceNav template={activeDraft} summary={summary} />
        <main className="template-detail-main">
          <section id="template-meta" className="template-panel">
            <PanelHeader kicker="Metadata" title="模板元信息" description="最小必要信息放在同一区域，减少来回滚动。" />
            <div className="template-compact-grid">
              <label className="field"><span className="field-label">模板 ID</span><input value={activeDraft.id} onChange={(e) => setDraftValue(setDraft, (next) => ({ ...next, id: e.target.value }))} /></label>
              <label className="field"><span className="field-label">分类</span><input value={activeDraft.category} onChange={(e) => setDraftValue(setDraft, (next) => ({ ...next, category: e.target.value }))} /></label>
              <label className="field"><span className="field-label">名称</span><input value={activeDraft.name} onChange={(e) => setDraftValue(setDraft, (next) => ({ ...next, name: e.target.value }))} /></label>
              <label className="field"><span className="field-label">Schema Version</span><input value={activeDraft.schemaVersion} onChange={(e) => setDraftValue(setDraft, (next) => ({ ...next, schemaVersion: e.target.value }))} /></label>
              <label className="field"><span className="field-label">模板结构</span><input value={summary.structureType === "paged" ? "PPT / paged" : "Flow"} readOnly /></label>
              <label className="field field--full"><span className="field-label">描述</span><textarea rows={2} value={activeDraft.description} onChange={(e) => setDraftValue(setDraft, (next) => ({ ...next, description: e.target.value }))} /></label>
            </div>
          </section>

          <section id="template-parameters" className="template-panel">
            <PanelHeader
              kicker="Parameters"
              title="根参数"
              description="常用字段一行内编辑，默认值和候选项放到展开区。"
            />
            <ParameterEditorList parameters={activeDraft.parameters} onChange={(parameters) => setDraftValue(setDraft, (next) => ({ ...next, parameters }))} />
          </section>

          <section id="template-structure" className="template-panel">
            <PanelHeader
              kicker={summary.structureType === "paged" ? "Paged" : "Catalogs"}
              title={summary.structureType === "paged" ? "PPT 章节与页面" : "目录与章节树"}
              description={summary.structureType === "paged" ? "分页模板保持完整 JSON 导入保存，当前以结构摘要呈现。" : "目录、子目录和 section 以折叠树方式编辑。"}
              action={summary.structureType === "flow" ? <button className="secondary-button" type="button" onClick={() => appendRootCatalog(setDraft)}><Plus size={16} aria-hidden="true" />新增根目录</button> : undefined}
            />
            {summary.structureType === "paged" ? (
              <PagedTemplateOverview template={activeDraft} />
            ) : (
              <div className="template-tree">
                {getTemplateCatalogs(activeDraft).map((catalog, index) => (
                  <CatalogEditor
                    key={`${catalog.id}-${index}`}
                    catalog={catalog}
                    path={[index]}
                    onChange={(nextCatalog) => updateCatalogAtPath(setDraft, [index], nextCatalog)}
                    onRemove={() => removeRootCatalog(setDraft, index)}
                  />
                ))}
              </div>
            )}
          </section>

          {!isCreateMode ? (
            <section id="template-danger" className="template-panel template-panel--danger">
              <PanelHeader kicker="Danger Zone" title="删除模板" description="删除后模板不可用于新的报告生成。" />
              <div className="template-danger-row">
                <button className="ghost-button ghost-button--inline" type="button" onClick={() => deleteMutation.mutate()}>
                  <Trash2 size={16} aria-hidden="true" />
                  {deleteMutation.isPending ? "删除中..." : "删除模板"}
                </button>
              </div>
            </section>
          ) : null}
        </main>
      </div>
    </div>
  );
}

function PanelHeader({ kicker, title, description, action }: { kicker: string; title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="template-panel__header">
      <div>
        <p className="section-kicker">{kicker}</p>
        <h2>{title}</h2>
        {description ? <p>{description}</p> : null}
      </div>
      {action ? <div className="template-panel__action">{action}</div> : null}
    </div>
  );
}

function TemplateWorkspaceNav({ template, summary }: { template: ReportTemplate; summary: TemplateSummaryStats }) {
  const flowCatalogs = getTemplateCatalogs(template);
  const pagedChapters = getTemplateChapters(template);
  return (
    <aside className="template-workspace-nav" aria-label="模板结构导航">
      <div className="template-workspace-nav__card">
        <div className="template-workspace-nav__title">
          <FileText size={16} aria-hidden="true" />
          <strong>模板概览</strong>
        </div>
        <div className="template-workspace-nav__stats">
          <span><strong>{summary.parameters}</strong><small>参数</small></span>
          <span><strong>{summary.structureType === "paged" ? summary.chapters : summary.catalogs}</strong><small>{summary.structureType === "paged" ? "章节" : "目录"}</small></span>
          <span><strong>{summary.structureType === "paged" ? summary.slides : summary.sections}</strong><small>{summary.structureType === "paged" ? "页面" : "Section"}</small></span>
        </div>
      </div>
      <nav className="template-workspace-nav__links">
        <a href="#template-meta">模板元信息</a>
        <a href="#template-parameters">根参数</a>
        <a href="#template-structure">{summary.structureType === "paged" ? "PPT 结构" : "目录树"}</a>
      </nav>
      <div className="template-workspace-nav__outline">
        <div className="template-workspace-nav__title">
          <ListTree size={16} aria-hidden="true" />
          <strong>{summary.structureType === "paged" ? "章节页面" : "目录结构"}</strong>
        </div>
        {summary.structureType === "paged" ? (
          <div className="template-workspace-nav__tree">
            {pagedChapters.map((chapter, index) => (
              <span key={`${chapter.id}-${index}`}>{chapter.title || chapter.id || `章节 ${index + 1}`}</span>
            ))}
          </div>
        ) : (
          <div className="template-workspace-nav__tree">
            {flowCatalogs.map((catalog, index) => (
              <span key={`${catalog.id}-${index}`}>{catalog.title || catalog.id || `目录 ${index + 1}`}</span>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}

type CatalogEditorProps = {
  catalog: CatalogDefinition;
  path: number[];
  onChange: (catalog: CatalogDefinition) => void;
  onRemove: () => void;
};

function CatalogEditor({ catalog, onChange, onRemove, path }: CatalogEditorProps) {
  const pathLabel = path.map((item) => item + 1).join(".");
  return (
    <details className="template-tree-node" open>
      <summary>
        <span className="template-tree-node__index">{pathLabel}</span>
        <strong>{catalog.title || catalog.id || `目录 ${pathLabel}`}</strong>
        <small>{catalog.subCatalogs?.length ?? 0} 子目录 · {catalog.sections?.length ?? 0} section</small>
      </summary>
      <div className="template-tree-node__body">
        <div className="template-node-actions">
          <button className="secondary-button" type="button" onClick={() => onChange({ ...catalog, subCatalogs: [...(catalog.subCatalogs ?? []), createEmptyCatalog()] })}><Plus size={16} aria-hidden="true" />新增子目录</button>
          <button className="secondary-button" type="button" onClick={() => onChange({ ...catalog, sections: [...(catalog.sections ?? []), createEmptySection()] })}><Plus size={16} aria-hidden="true" />新增章节</button>
          <button className="ghost-button ghost-button--inline" type="button" onClick={onRemove}><Trash2 size={16} aria-hidden="true" />删除目录</button>
        </div>
        <div className="template-compact-grid">
        <label className="field"><span className="field-label">目录 ID</span><input value={catalog.id} onChange={(e) => onChange({ ...catalog, id: e.target.value })} /></label>
        <label className="field"><span className="field-label">目录标题</span><input value={catalog.title} onChange={(e) => onChange({ ...catalog, title: e.target.value })} /></label>
        <label className="field field--full"><span className="field-label">目录描述</span><textarea rows={2} value={catalog.description ?? ""} onChange={(e) => onChange({ ...catalog, description: e.target.value || undefined })} /></label>
        <label className="field"><span className="field-label">Dynamic Foreach 参数</span><input value={getForeachDynamic(catalog.dynamic)?.parameterId ?? ""} onChange={(e) => onChange({ ...catalog, dynamic: normalizeForeachDynamic(e.target.value, getForeachDynamic(catalog.dynamic)?.as ?? "item") })} /></label>
        <label className="field"><span className="field-label">Dynamic Foreach 别名</span><input value={getForeachDynamic(catalog.dynamic)?.as ?? ""} onChange={(e) => onChange({ ...catalog, dynamic: normalizeForeachDynamic(getForeachDynamic(catalog.dynamic)?.parameterId ?? "", e.target.value) })} /></label>
        </div>

      <div className="template-inline-group template-inline-group--compact">
        <div className="template-inline-group__header"><strong>目录级参数</strong></div>
        <ParameterEditorList parameters={catalog.parameters ?? []} onChange={(parameters) => onChange({ ...catalog, parameters: parameters.length ? parameters : undefined })} />
      </div>

      {(catalog.subCatalogs ?? []).length ? (
        <div className="template-tree-node__children">
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
      </div>
    </details>
  );
}

type SectionEditorProps = {
  section: SectionDefinition;
  onChange: (section: SectionDefinition) => void;
  onRemove: () => void;
};

function SectionEditor({ section, onChange, onRemove }: SectionEditorProps) {
  return (
    <details className="template-section-node" open>
      <summary>
        <span className="template-tree-node__index">S</span>
        <strong>{section.id || "章节"}</strong>
        <small>{section.content.presentation.kind} · {section.content.presentation.blocks.length} blocks</small>
      </summary>
      <div className="template-tree-node__body">
        <div className="template-node-actions">
          <button className="ghost-button ghost-button--inline" type="button" onClick={onRemove}><Trash2 size={16} aria-hidden="true" />删除章节</button>
        </div>
      <div className="template-compact-grid">
        <label className="field"><span className="field-label">章节 ID</span><input value={section.id} onChange={(e) => onChange({ ...section, id: e.target.value })} /></label>
        <label className="field field--full"><span className="field-label">章节描述</span><textarea rows={2} value={section.description ?? ""} onChange={(e) => onChange({ ...section, description: e.target.value || undefined })} /></label>
        <label className="field field--full"><span className="field-label">诉求文本</span><textarea rows={3} value={section.outline.requirement} onChange={(e) => onChange({ ...section, outline: { ...section.outline, requirement: e.target.value } })} /></label>
        <label className="field"><span className="field-label">Dynamic Foreach 参数</span><input value={getForeachDynamic(section.dynamic)?.parameterId ?? ""} onChange={(e) => onChange({ ...section, dynamic: normalizeForeachDynamic(e.target.value, getForeachDynamic(section.dynamic)?.as ?? "item") })} /></label>
        <label className="field"><span className="field-label">Dynamic Foreach 别名</span><input value={getForeachDynamic(section.dynamic)?.as ?? ""} onChange={(e) => onChange({ ...section, dynamic: normalizeForeachDynamic(getForeachDynamic(section.dynamic)?.parameterId ?? "", e.target.value) })} /></label>
        <label className="field"><span className="field-label">展示种类</span><select value={section.content.presentation.kind} onChange={(e) => onChange({ ...section, content: { ...section.content, presentation: { ...section.content.presentation, kind: e.target.value as SectionDefinition["content"]["presentation"]["kind"] } } })}><option value="text">text</option><option value="table">table</option><option value="chart">chart</option><option value="mixed">mixed</option></select></label>
      </div>

      <div className="template-inline-group template-inline-group--compact"><div className="template-inline-group__header"><strong>章节级参数</strong></div><ParameterEditorList parameters={section.parameters ?? []} onChange={(parameters) => onChange({ ...section, parameters: parameters.length ? parameters : undefined })} /></div>

      <div className="template-inline-group template-inline-group--compact">
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

      <div className="template-inline-group template-inline-group--compact">
        <div className="template-inline-group__header"><strong>数据集</strong><button className="secondary-button" type="button" onClick={() => onChange({ ...section, content: { ...section.content, datasets: [...(section.content.datasets ?? []), createEmptyDataset()] } })}>新增数据集</button></div>
        {(section.content.datasets ?? []).map((dataset, index) => (
          <div key={`${dataset.id}-${index}`} className="template-inline-row template-inline-row--wide">
            <input value={dataset.id} onChange={(e) => updateDataset(section, index, { id: e.target.value }, onChange)} placeholder="dataset id" />
            <select value={dataset.sourceType} onChange={(e) => updateDataset(section, index, { sourceType: e.target.value as "sql" | "api" | "llm" | "compose" }, onChange)}><option value="sql">sql</option><option value="api">api</option><option value="llm">llm</option><option value="compose">compose</option></select>
            <input value={dataset.source ?? dataset.sourceRef ?? ""} onChange={(e) => updateDataset(section, index, { source: e.target.value }, onChange)} placeholder="source" />
            <input value={dataset.name ?? ""} onChange={(e) => updateDataset(section, index, { name: e.target.value || undefined }, onChange)} placeholder="名称" />
            <button className="ghost-button ghost-button--inline" type="button" onClick={() => onChange({ ...section, content: { ...section.content, datasets: removeAtIndex(section.content.datasets ?? [], index) } })}>删除</button>
          </div>
        ))}
      </div>

      <div className="template-inline-group template-inline-group--compact">
        <div className="template-inline-group__header"><strong>展示块</strong><button className="secondary-button" type="button" onClick={() => onChange({ ...section, content: { ...section.content, presentation: { ...section.content.presentation, blocks: [...section.content.presentation.blocks, createEmptyBlock()] } } })}>新增展示块</button></div>
        {section.content.presentation.blocks.map((block, index) => (
          <div key={`${block.id}-${index}`} className="template-inline-row template-inline-row--wide">
            <input value={block.id} onChange={(e) => updateBlock(section, index, { id: e.target.value }, onChange)} placeholder="block id" />
            <select value={block.type} onChange={(e) => updateBlock(section, index, { type: e.target.value as PresentationBlock["type"] }, onChange)}><option value="text">text</option><option value="table">table</option><option value="chart">chart</option><option value="composite_table">composite_table</option></select>
            <input value={block.title ?? ""} onChange={(e) => updateBlock(section, index, { title: e.target.value || undefined }, onChange)} placeholder="标题" />
            <input value={block.datasetId ?? ""} onChange={(e) => updateBlock(section, index, { datasetId: e.target.value || undefined }, onChange)} placeholder="datasetId" />
            {block.type === "text" ? <input value={block.properties?.template ?? ""} onChange={(e) => updateBlock(section, index, { properties: { ...(block.properties ?? {}), template: e.target.value || undefined } }, onChange)} placeholder="文本模板" /> : null}
            <button className="ghost-button ghost-button--inline" type="button" onClick={() => onChange({ ...section, content: { ...section.content, presentation: { ...section.content.presentation, blocks: removeAtIndex(section.content.presentation.blocks, index) } } })}>删除</button>
          </div>
        ))}
      </div>
      </div>
    </details>
  );
}

function PagedTemplateOverview({ template }: { template: ReportTemplate }) {
  const chapters = getTemplateChapters(template);
  return (
    <div className="paged-template-overview">
      <StatusBanner tone="info" title="分页模板当前以导入保存为主">
        这类模板会完整保留 chapters、slides、dynamic、layout 和 presentation 配置；当前页面先提供结构摘要和 JSON 查看，不做细粒度可视化编辑。
      </StatusBanner>
      <div className="paged-template-overview__chapters">
        {chapters.map((chapter, chapterIndex) => (
          <article key={`${chapter.id}-${chapterIndex}`} className="paged-template-overview__chapter">
            <div className="paged-template-overview__chapter-head">
              <strong>{chapter.title || chapter.id || `章节 ${chapterIndex + 1}`}</strong>
              <span className="status-chip status-chip--soft">{chapter.slides?.length ?? 0} 页</span>
            </div>
            {(chapter.slides ?? []).map((slide, slideIndex) => (
              <div key={`${slide.id}-${slideIndex}`} className="template-inline-row template-inline-row--wide">
                <strong>{slide.title || slide.id || `页面 ${slideIndex + 1}`}</strong>
                <span>{slide.sections?.length ?? 0} 个 section</span>
                {slide.layout?.layoutId ? <span>layout: {slide.layout.layoutId}</span> : null}
              </div>
            ))}
          </article>
        ))}
      </div>
      <details className="json-details">
        <summary>查看完整模板 JSON</summary>
        <pre>{formatJson(template)}</pre>
      </details>
    </div>
  );
}

function ParameterEditorList({ parameters, onChange }: { parameters: TemplateParameter[]; onChange: (parameters: TemplateParameter[]) => void }) {
  return (
    <div className="template-parameter-list">
      <div className="template-parameter-list__toolbar">
        <span>{parameters.length ? `${parameters.length} 个参数` : "暂无参数"}</span>
        <button className="secondary-button" type="button" onClick={() => onChange([...parameters, createEmptyParameter()])}><Plus size={16} aria-hidden="true" />新增参数</button>
      </div>
      {parameters.map((parameter, index) => (
        <details key={`${parameter.id}-${index}`} className="template-parameter-row" open>
          <summary>
            <strong>{parameter.label || `参数 ${index + 1}`}</strong>
            <small>{parameter.id || "未设置 ID"} · {parameter.inputType} · {parameter.required ? "必填" : "可选"}</small>
          </summary>
          <div className="template-parameter-row__body">
            <div className="template-node-actions">
              <button className="ghost-button ghost-button--inline" type="button" onClick={() => onChange(removeAtIndex(parameters, index))}><Trash2 size={16} aria-hidden="true" />删除参数</button>
            </div>
          <div className="template-compact-grid">
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
          </div>
        </details>
      ))}
    </div>
  );
}

function createEmptyTemplate(): ReportTemplate {
  return { id: "", category: "", name: "", description: "", schemaVersion: "template.v3", structureType: "flow", parameters: [], catalogs: [] };
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
  return { id: `dataset_${Date.now()}`, sourceType: "sql" as const, source: "", name: "" };
}

function createEmptyBlock(): PresentationBlock {
  return { id: `block_${Date.now()}`, type: "text", title: "", properties: { template: "" } };
}

function cloneTemplate(template: ReportTemplate): ReportTemplate {
  return JSON.parse(JSON.stringify(template)) as ReportTemplate;
}

function setDraftValue(setDraft: Dispatch<SetStateAction<ReportTemplate | null>>, updater: (draft: ReportTemplate) => ReportTemplate) {
  setDraft((current) => (current ? updater(current) : current));
}

function appendRootCatalog(setDraft: Dispatch<SetStateAction<ReportTemplate | null>>) {
  setDraftValue(setDraft, (draft) => {
    const flow = asFlowTemplate(cloneTemplate(draft));
    return { ...flow, catalogs: [...flow.catalogs, createEmptyCatalog()] };
  });
}

function removeRootCatalog(setDraft: Dispatch<SetStateAction<ReportTemplate | null>>, index: number) {
  setDraftValue(setDraft, (draft) => {
    const flow = asFlowTemplate(cloneTemplate(draft));
    return { ...flow, catalogs: removeAtIndex(flow.catalogs, index) };
  });
}

function updateCatalogAtPath(setDraft: Dispatch<SetStateAction<ReportTemplate | null>>, path: number[], nextCatalog: CatalogDefinition) {
  setDraftValue(setDraft, (draft) => {
    const next = asFlowTemplate(cloneTemplate(draft));
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

function getForeachDynamic(dynamic: CatalogDefinition["dynamic"] | SectionDefinition["dynamic"]) {
  return dynamic?.type === "foreach" ? dynamic : undefined;
}

function normalizeForeachDynamic(parameterId: string, asValue: string) {
  if (!parameterId.trim()) {
    return undefined;
  }
  return { type: "foreach" as const, parameterId: parameterId.trim(), as: asValue.trim() || "item" };
}

function resolveTemplateStructure(template: ReportTemplate): TemplateStructureType {
  return template.structureType === "paged" ? "paged" : "flow";
}

function getTemplateCatalogs(template: ReportTemplate): CatalogDefinition[] {
  return Array.isArray((template as { catalogs?: CatalogDefinition[] }).catalogs)
    ? ((template as { catalogs?: CatalogDefinition[] }).catalogs ?? [])
    : [];
}

function getTemplateChapters(template: ReportTemplate): ChapterDefinition[] {
  return Array.isArray((template as { chapters?: ChapterDefinition[] }).chapters)
    ? ((template as { chapters?: ChapterDefinition[] }).chapters ?? [])
    : [];
}

function asFlowTemplate(template: ReportTemplate): FlowReportTemplate {
  const { chapters: _chapters, ...rest } = template as ReportTemplate & { chapters?: ChapterDefinition[] };
  return { ...rest, structureType: "flow", catalogs: getTemplateCatalogs(template) };
}

function countCatalogs(catalogs: CatalogDefinition[]): number {
  return catalogs.reduce((sum, catalog) => sum + 1 + countCatalogs(catalog.subCatalogs ?? []), 0);
}

function countSections(catalogs: CatalogDefinition[]): number {
  return catalogs.reduce((sum, catalog) => sum + (catalog.sections?.length ?? 0) + countSections(catalog.subCatalogs ?? []), 0);
}

function countSlides(chapters: ChapterDefinition[]): number {
  return chapters.reduce((sum, chapter) => sum + (chapter.slides?.length ?? 0), 0);
}

function countPagedSections(chapters: ChapterDefinition[]): number {
  return chapters.reduce(
    (sum, chapter) => sum + (chapter.slides ?? []).reduce((slideSum, slide) => slideSum + (slide.sections?.length ?? 0), 0),
    0,
  );
}

function formatJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}
