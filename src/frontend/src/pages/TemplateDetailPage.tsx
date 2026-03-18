import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  createTemplate,
  deleteTemplate,
  fetchTemplate,
  updateTemplate,
} from "../entities/templates/api";
import type { TemplateDetail, TemplateUpsertPayload } from "../entities/templates/types";
import { safeJsonParse } from "../shared/utils/format";
import { DetailPageLayout } from "../shared/layouts/DetailPageLayout";
import { PageIntroBar } from "../shared/layouts/PageIntroBar";
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

export function TemplateDetailPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { templateId } = useParams<{ templateId: string }>();
  const [editor, setEditor] = useState<EditorState>(EMPTY_EDITOR);
  const [saveError, setSaveError] = useState("");

  const isCreateMode = !templateId;

  const selectedTemplateQuery = useQuery({
    queryKey: ["template-detail", templateId],
    queryFn: () => fetchTemplate(templateId!),
    enabled: Boolean(templateId),
  });

  useEffect(() => {
    if (selectedTemplateQuery.data) {
      setEditor(buildEditorState(selectedTemplateQuery.data));
      return;
    }
    if (isCreateMode) {
      setEditor(EMPTY_EDITOR);
    }
  }, [isCreateMode, selectedTemplateQuery.data]);

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
      setEditor(buildEditorState(saved));
      navigate(`/templates/${saved.template_id}`, { replace: true });
    },
    onError: (error) => {
      setSaveError(error instanceof Error ? error.message : "模板保存失败。");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => deleteTemplate(editor.templateId!),
    onSuccess: async () => {
      setSaveError("");
      await queryClient.invalidateQueries({ queryKey: ["templates"] });
      navigate("/templates", { replace: true });
    },
    onError: (error) => {
      setSaveError(error instanceof Error ? error.message : "模板删除失败。");
    },
  });

  const summary = useMemo(() => {
    const parameters = safeJsonParse<unknown[]>(editor.parametersText, []);
    const sections = safeJsonParse<unknown[]>(editor.sectionsText, []);
    return {
      parameterCount: parameters.length,
      sectionCount: sections.length,
    };
  }, [editor.parametersText, editor.sectionsText]);

  return (
    <div className="template-detail-page">
      <PageSection description={isCreateMode ? "创建新的模板定义。" : "在独立详情页中查看和编辑模板。"}>
        {saveError ? (
          <StatusBanner tone="warning" title="操作未完成">
            {saveError}
          </StatusBanner>
        ) : null}

        <DetailPageLayout
          intro={
            <PageIntroBar
              eyebrow="Template Detail"
              description={isCreateMode ? "新建模板" : editor.name || "模板详情"}
              badge={editor.schemaVersion || "v2.0"}
              actions={
                <>
                  <Link className="ghost-button button-link" to="/templates">
                    返回列表
                  </Link>
                  {editor.templateId ? (
                    <button
                      className="danger-button"
                      type="button"
                      onClick={() => deleteMutation.mutate()}
                      disabled={deleteMutation.isPending}
                    >
                      删除模板
                    </button>
                  ) : null}
                </>
              }
            />
          }
          summary={
            <SurfaceCard className="summary-strip">
              <div className="summary-strip__item">
                <span>模板类型</span>
                <strong>{editor.type || "未设置"}</strong>
              </div>
              <div className="summary-strip__item">
                <span>场景</span>
                <strong>{editor.scene || editor.scenario || "未设置"}</strong>
              </div>
              <div className="summary-strip__item">
                <span>参数数量</span>
                <strong>{summary.parameterCount}</strong>
              </div>
              <div className="summary-strip__item">
                <span>章节数量</span>
                <strong>{summary.sectionCount}</strong>
              </div>
            </SurfaceCard>
          }
          content={
            <div className="template-detail-grid">
              <SurfaceCard>
                <div className="list-header">
                  <div>
                    <p className="section-kicker">Basic Information</p>
                    <h3>基础信息</h3>
                    <p className="muted-text">维护模板标识、用途和匹配信息。</p>
                  </div>
                </div>
                <div className="form-grid">
                  <label className="field">
                    <span className="field-label">模板名称</span>
                    <input
                      aria-label="模板名称"
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
                      onChange={(event) =>
                        setEditor((current) => ({ ...current, schemaVersion: event.target.value }))
                      }
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
                    <p className="section-kicker">Parameters</p>
                    <h3>参数定义</h3>
                    <p className="muted-text">按最新版模板规范维护 `parameters`。</p>
                  </div>
                </div>
                <div className="json-editor-block">
                  <label className="field field--full">
                    <span className="field-label">parameters</span>
                    <textarea
                      rows={10}
                      value={editor.parametersText}
                      onChange={(event) =>
                        setEditor((current) => ({ ...current, parametersText: event.target.value }))
                      }
                    />
                  </label>
                </div>
              </SurfaceCard>

              <SurfaceCard>
                <div className="list-header">
                  <div>
                    <p className="section-kicker">Sections</p>
                    <h3>章节结构</h3>
                    <p className="muted-text">维护 `sections`，作为新版模板主结构。</p>
                  </div>
                </div>
                <div className="json-editor-block">
                  <label className="field field--full">
                    <span className="field-label">sections</span>
                    <textarea
                      rows={12}
                      value={editor.sectionsText}
                      onChange={(event) => setEditor((current) => ({ ...current, sectionsText: event.target.value }))}
                    />
                  </label>
                </div>
              </SurfaceCard>

              <SurfaceCard>
                <div className="list-header">
                  <div>
                    <p className="section-kicker">Compatibility</p>
                    <h3>高级 JSON</h3>
                    <p className="muted-text">旧版字段保留兼容入口，便于逐步迁移。</p>
                  </div>
                </div>
                <div className="form-grid">
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
          }
        />
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
