import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createTemplate,
  deleteTemplate,
  fetchTemplate,
  fetchTemplates,
  updateTemplate,
} from "../entities/templates/api";
import type { TemplateDetail, TemplateUpsertPayload } from "../entities/templates/types";
import { safeJsonParse } from "../shared/utils/format";
import { EmptyState } from "../shared/ui/EmptyState";
import { PageSection } from "../shared/ui/PageSection";
import { StatusBanner } from "../shared/ui/StatusBanner";
import { SurfaceCard } from "../shared/ui/SurfaceCard";

type EditorState = {
  templateId?: string;
  name: string;
  description: string;
  reportType: string;
  scenario: string;
  type: string;
  scene: string;
  schemaVersion: string;
  matchKeywordsText: string;
  parametersText: string;
  sectionsText: string;
  contentParamsText: string;
  outlineText: string;
  outputFormatsText: string;
};

const EMPTY_EDITOR: EditorState = {
  name: "",
  description: "",
  reportType: "daily",
  scenario: "",
  type: "",
  scene: "",
  schemaVersion: "v2.0",
  matchKeywordsText: "",
  parametersText: "[]",
  sectionsText: "[]",
  contentParamsText: "[]",
  outlineText: "[]",
  outputFormatsText: "md",
};

export function TemplatesPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string>("");
  const [editor, setEditor] = useState<EditorState>(EMPTY_EDITOR);
  const [saveError, setSaveError] = useState("");

  const templatesQuery = useQuery({
    queryKey: ["templates"],
    queryFn: fetchTemplates,
  });

  useEffect(() => {
    if (!selectedId && templatesQuery.data?.length) {
      setSelectedId(templatesQuery.data[0].template_id);
    }
  }, [selectedId, templatesQuery.data]);

  const selectedTemplateQuery = useQuery({
    queryKey: ["template-detail", selectedId],
    queryFn: () => fetchTemplate(selectedId),
    enabled: Boolean(selectedId),
  });

  useEffect(() => {
    if (!selectedTemplateQuery.data) {
      return;
    }
    setEditor(buildEditorState(selectedTemplateQuery.data));
  }, [selectedTemplateQuery.data]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = serializeTemplate(editor);
      if (editor.templateId) {
        return updateTemplate(editor.templateId, payload);
      }
      return createTemplate(payload);
    },
    onSuccess: async (saved) => {
      setSaveError("");
      await queryClient.invalidateQueries({ queryKey: ["templates"] });
      await queryClient.invalidateQueries({ queryKey: ["template-detail", saved.template_id] });
      setSelectedId(saved.template_id);
      setEditor(buildEditorState(saved));
    },
    onError: (error) => {
      setSaveError(error instanceof Error ? error.message : "模板保存失败。");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (templateId: string) => deleteTemplate(templateId),
    onSuccess: async () => {
      const deletedId = selectedId;
      setSaveError("");
      setSelectedId("");
      setEditor(EMPTY_EDITOR);
      await queryClient.invalidateQueries({ queryKey: ["templates"] });
      queryClient.removeQueries({ queryKey: ["template-detail", deletedId] });
    },
    onError: (error) => {
      setSaveError(error instanceof Error ? error.message : "模板删除失败。");
    },
  });

  const summaryText = useMemo(() => {
    const parameters = safeJsonParse<unknown[]>(editor.parametersText, []);
    const sections = safeJsonParse<unknown[]>(editor.sectionsText, []);
    return `参数 ${parameters.length} 项 / 章节 ${sections.length} 项`;
  }, [editor.parametersText, editor.sectionsText]);

  return (
    <div className="templates-page">
      <PageSection
        title="模板管理"
        description="左侧查看模板清单，右侧维护元信息与 v2 JSON 定义。"
        actions={
          <button
            className="primary-button"
            type="button"
            onClick={() => {
              setSelectedId("");
              setSaveError("");
              setEditor(EMPTY_EDITOR);
            }}
          >
            新建模板
          </button>
        }
      >
        {saveError ? (
          <StatusBanner tone="warning" title="操作未完成">
            {saveError}
          </StatusBanner>
        ) : null}

        <div className="split-layout">
          <SurfaceCard className="split-layout__sidebar">
            <div className="list-header">
              <div>
                <p className="section-kicker">Template Catalog</p>
                <h3>模板列表</h3>
              </div>
              <span className="inline-badge">{templatesQuery.data?.length ?? 0}</span>
            </div>
            <div className="list-stack">
              {templatesQuery.data?.map((template) => (
                <button
                  key={template.template_id}
                  className={`list-item${selectedId === template.template_id ? " active" : ""}`}
                  type="button"
                  onClick={() => setSelectedId(template.template_id)}
                >
                  <strong>{template.name}</strong>
                  <span>{[template.type, template.scene || template.scenario].filter(Boolean).join(" / ")}</span>
                </button>
              ))}
              {!templatesQuery.data?.length && !templatesQuery.isLoading ? (
                <EmptyState title="暂无模板" description="点击“新建模板”，录入最新模板定义。" />
              ) : null}
            </div>
          </SurfaceCard>

          <div className="split-layout__content">
            <SurfaceCard>
              <div className="list-header">
                <div>
                  <p className="section-kicker">Template Editor</p>
                  <h3>{editor.templateId ? "模板详情" : "新建模板"}</h3>
                  <p className="muted-text">{summaryText}</p>
                </div>
                {editor.templateId ? (
                  <button
                    className="danger-button"
                    type="button"
                    onClick={() => deleteMutation.mutate(editor.templateId!)}
                    disabled={deleteMutation.isPending}
                  >
                    删除模板
                  </button>
                ) : null}
              </div>

              <div className="form-grid">
                <label className="field">
                  <span className="field-label">模板名称</span>
                  <input
                    value={editor.name}
                    onChange={(event) => setEditor((current) => ({ ...current, name: event.target.value }))}
                  />
                </label>
                <label className="field">
                  <span className="field-label">模板类型</span>
                  <input
                    value={editor.type}
                    onChange={(event) => setEditor((current) => ({ ...current, type: event.target.value }))}
                  />
                </label>
                <label className="field">
                  <span className="field-label">场景</span>
                  <input
                    value={editor.scene}
                    onChange={(event) => setEditor((current) => ({ ...current, scene: event.target.value }))}
                  />
                </label>
                <label className="field">
                  <span className="field-label">报告类型</span>
                  <input
                    value={editor.reportType}
                    onChange={(event) => setEditor((current) => ({ ...current, reportType: event.target.value }))}
                  />
                </label>
                <label className="field field--full">
                  <span className="field-label">模板描述</span>
                  <textarea
                    rows={3}
                    value={editor.description}
                    onChange={(event) => setEditor((current) => ({ ...current, description: event.target.value }))}
                  />
                </label>
                <label className="field">
                  <span className="field-label">使用场景说明</span>
                  <input
                    value={editor.scenario}
                    onChange={(event) => setEditor((current) => ({ ...current, scenario: event.target.value }))}
                  />
                </label>
                <label className="field">
                  <span className="field-label">Schema 版本</span>
                  <input
                    value={editor.schemaVersion}
                    onChange={(event) => setEditor((current) => ({ ...current, schemaVersion: event.target.value }))}
                  />
                </label>
                <label className="field field--full">
                  <span className="field-label">匹配关键词（逗号分隔）</span>
                  <input
                    value={editor.matchKeywordsText}
                    onChange={(event) =>
                      setEditor((current) => ({ ...current, matchKeywordsText: event.target.value }))
                    }
                  />
                </label>
              </div>
            </SurfaceCard>

            <SurfaceCard>
              <div className="list-header">
                <div>
                  <p className="section-kicker">Advanced JSON</p>
                  <h3>v2 模板定义</h3>
                  <p className="muted-text">按 `parameters / sections` 为主，旧字段保留兼容入口。</p>
                </div>
              </div>
              <div className="form-grid">
                <label className="field field--full">
                  <span className="field-label">parameters</span>
                  <textarea
                    rows={10}
                    value={editor.parametersText}
                    onChange={(event) => setEditor((current) => ({ ...current, parametersText: event.target.value }))}
                  />
                </label>
                <label className="field field--full">
                  <span className="field-label">sections</span>
                  <textarea
                    rows={12}
                    value={editor.sectionsText}
                    onChange={(event) => setEditor((current) => ({ ...current, sectionsText: event.target.value }))}
                  />
                </label>
                <label className="field field--full">
                  <span className="field-label">content_params（旧版兼容）</span>
                  <textarea
                    rows={6}
                    value={editor.contentParamsText}
                    onChange={(event) =>
                      setEditor((current) => ({ ...current, contentParamsText: event.target.value }))
                    }
                  />
                </label>
                <label className="field field--full">
                  <span className="field-label">outline（旧版兼容）</span>
                  <textarea
                    rows={6}
                    value={editor.outlineText}
                    onChange={(event) => setEditor((current) => ({ ...current, outlineText: event.target.value }))}
                  />
                </label>
              </div>

              <div className="action-row">
                <button className="primary-button" type="button" onClick={() => saveMutation.mutate()}>
                  {saveMutation.isPending ? "保存中..." : "保存模板"}
                </button>
              </div>
            </SurfaceCard>
          </div>
        </div>
      </PageSection>
    </div>
  );
}

function buildEditorState(template: TemplateDetail): EditorState {
  return {
    templateId: template.template_id,
    name: template.name,
    description: template.description ?? "",
    reportType: template.report_type ?? "daily",
    scenario: template.scenario ?? "",
    type: template.type ?? "",
    scene: template.scene ?? "",
    schemaVersion: template.schema_version || "v2.0",
    matchKeywordsText: (template.match_keywords ?? []).join(", "),
    parametersText: JSON.stringify(template.parameters ?? [], null, 2),
    sectionsText: JSON.stringify(template.sections ?? [], null, 2),
    contentParamsText: JSON.stringify(template.content_params ?? [], null, 2),
    outlineText: JSON.stringify(template.outline ?? [], null, 2),
    outputFormatsText: (template.output_formats ?? []).join(", "),
  };
}

function serializeTemplate(editor: EditorState): TemplateUpsertPayload {
  return {
    name: editor.name.trim(),
    description: editor.description.trim(),
    report_type: editor.reportType.trim() || "daily",
    scenario: editor.scenario.trim(),
    type: editor.type.trim(),
    scene: editor.scene.trim(),
    match_keywords: editor.matchKeywordsText
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
    content_params: safeJsonParse(editor.contentParamsText, []),
    parameters: safeJsonParse(editor.parametersText, []),
    outline: safeJsonParse(editor.outlineText, []),
    sections: safeJsonParse(editor.sectionsText, []),
    schema_version: editor.schemaVersion.trim() || "v2.0",
    output_formats: editor.outputFormatsText
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
  };
}
