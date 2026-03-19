import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import { createTemplate, deleteTemplate, fetchTemplate, updateTemplate } from "../entities/templates/api";
import { TemplateWorkbench } from "../features/template-workbench/TemplateWorkbench";
import { createEmptyWorkbenchState, toTemplatePayload, toWorkbenchState, type TemplateWorkbenchState } from "../features/template-workbench/state";
import { DetailPageLayout } from "../shared/layouts/DetailPageLayout";
import { PageIntroBar } from "../shared/layouts/PageIntroBar";
import { PageSection } from "../shared/ui/PageSection";
import { StatusBanner } from "../shared/ui/StatusBanner";
import { SurfaceCard } from "../shared/ui/SurfaceCard";

export function TemplateDetailPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { templateId } = useParams<{ templateId: string }>();
  const [editor, setEditor] = useState<TemplateWorkbenchState>(createEmptyWorkbenchState());
  const [saveError, setSaveError] = useState("");

  const isCreateMode = !templateId;

  const selectedTemplateQuery = useQuery({
    queryKey: ["template-detail", templateId],
    queryFn: () => fetchTemplate(templateId!),
    enabled: Boolean(templateId),
  });

  useEffect(() => {
    if (selectedTemplateQuery.data) {
      setEditor(toWorkbenchState(selectedTemplateQuery.data));
      return;
    }
    if (isCreateMode) {
      setEditor(createEmptyWorkbenchState());
    }
  }, [isCreateMode, selectedTemplateQuery.data]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = toTemplatePayload(editor);
      if (editor.meta.templateId) {
        return updateTemplate(editor.meta.templateId, payload);
      }
      return createTemplate(payload);
    },
    onSuccess: async (saved) => {
      setSaveError("");
      await queryClient.invalidateQueries({ queryKey: ["templates"] });
      await queryClient.invalidateQueries({ queryKey: ["template-detail", saved.template_id] });
      setEditor(toWorkbenchState(saved));
      navigate(`/templates/${saved.template_id}`, { replace: true });
    },
    onError: (error) => {
      setSaveError(error instanceof Error ? error.message : "模板保存失败。");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => deleteTemplate(editor.meta.templateId!),
    onSuccess: async () => {
      setSaveError("");
      await queryClient.invalidateQueries({ queryKey: ["templates"] });
      navigate("/templates", { replace: true });
    },
    onError: (error) => {
      setSaveError(error instanceof Error ? error.message : "模板删除失败。");
    },
  });

  const summary = useMemo(
    () => ({
      parameterCount: editor.parameters.length,
      sectionCount: editor.sections.length,
    }),
    [editor.parameters.length, editor.sections.length],
  );

  function updateMeta(field: keyof TemplateWorkbenchState["meta"], nextValue: unknown) {
    setEditor((current) => ({
      ...current,
      meta: {
        ...current.meta,
        [field]: nextValue,
      },
    }));
  }

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
              description={isCreateMode ? "新建模板" : editor.meta.name || "模板详情"}
              badge={editor.meta.schemaVersion || "v2.0"}
              actions={
                <>
                  <Link className="ghost-button button-link" to="/templates">
                    返回列表
                  </Link>
                  {editor.meta.templateId ? (
                    <a className="secondary-button button-link" href={`/api/templates/${editor.meta.templateId}/export`}>
                      导出 JSON
                    </a>
                  ) : null}
                  {editor.meta.templateId ? (
                    <button className="danger-button" type="button" onClick={() => deleteMutation.mutate()} disabled={deleteMutation.isPending}>
                      删除模板
                    </button>
                  ) : null}
                </>
              }
            />
          }
          summary={
            <SurfaceCard className="summary-strip">
              <div className="summary-strip__item"><span>模板类型</span><strong>{editor.meta.type || "未设置"}</strong></div>
              <div className="summary-strip__item"><span>场景</span><strong>{editor.meta.scene || editor.meta.scenario || "未设置"}</strong></div>
              <div className="summary-strip__item"><span>参数数量</span><strong>{summary.parameterCount}</strong></div>
              <div className="summary-strip__item"><span>章节数量</span><strong>{summary.sectionCount}</strong></div>
            </SurfaceCard>
          }
          content={
            <div className="template-detail-grid">
              <SurfaceCard>
                <div className="list-header">
                  <div>
                    <p className="section-kicker">Basic Information</p>
                    <h3>基础信息</h3>
                    <p className="muted-text">维护模板名称、用途和匹配信息。</p>
                  </div>
                </div>
                <div className="form-grid">
                  <label className="field"><span className="field-label">模板名称</span><input aria-label="模板名称" value={editor.meta.name} onChange={(event) => updateMeta("name", event.target.value)} /></label>
                  <label className="field"><span className="field-label">模板类型</span><input value={editor.meta.type} onChange={(event) => updateMeta("type", event.target.value)} /></label>
                  <label className="field"><span className="field-label">场景</span><input value={editor.meta.scene} onChange={(event) => updateMeta("scene", event.target.value)} /></label>
                  <label className="field"><span className="field-label">报告类型</span><input value={editor.meta.reportType} onChange={(event) => updateMeta("reportType", event.target.value)} /></label>
                  <label className="field field--full"><span className="field-label">模板描述</span><textarea rows={3} value={editor.meta.description} onChange={(event) => updateMeta("description", event.target.value)} /></label>
                  <label className="field"><span className="field-label">使用场景说明</span><input value={editor.meta.scenario} onChange={(event) => updateMeta("scenario", event.target.value)} /></label>
                  <label className="field"><span className="field-label">Schema 版本</span><input value={editor.meta.schemaVersion} onChange={(event) => updateMeta("schemaVersion", event.target.value)} /></label>
                  <label className="field field--full"><span className="field-label">匹配关键词（逗号分隔）</span><input value={editor.meta.matchKeywords.join(", ")} onChange={(event) => updateMeta("matchKeywords", event.target.value.split(",").map((item) => item.trim()).filter(Boolean))} /></label>
                </div>
              </SurfaceCard>

              <TemplateWorkbench value={editor} onChange={setEditor} onSave={() => saveMutation.mutate()} savePending={saveMutation.isPending} />
            </div>
          }
        />
      </PageSection>
    </div>
  );
}
