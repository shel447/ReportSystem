import { useRef, useState, type ChangeEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";

import { fetchTemplates, previewImportTemplate } from "../entities/templates/api";
import type { ImportSaveMode, TemplateImportPreview } from "../entities/templates/types";
import { EmptyState } from "../shared/ui/EmptyState";
import { PageSection } from "../shared/ui/PageSection";
import { PageIntroBar } from "../shared/layouts/PageIntroBar";
import { ListPageLayout } from "../shared/layouts/ListPageLayout";
import { StatusBanner } from "../shared/ui/StatusBanner";

export function TemplatesPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [importError, setImportError] = useState("");
  const [pendingImportPreview, setPendingImportPreview] = useState<TemplateImportPreview | null>(null);

  const templatesQuery = useQuery({
    queryKey: ["templates"],
    queryFn: fetchTemplates,
  });

  function beginImportSelection() {
    fileInputRef.current?.click();
  }

  async function handleImportSelection(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }

    try {
      const text = await readFileText(file);
      const payload = JSON.parse(text) as Record<string, unknown>;
      const preview = await previewImportTemplate(payload, file.name);
      setImportError("");
      if (preview.conflict.status === "none") {
        openImportDraft(preview, "create_copy");
        return;
      }
      setPendingImportPreview(preview);
    } catch (error) {
      setPendingImportPreview(null);
      setImportError(error instanceof Error ? error.message : "模板导入失败。");
    }
  }

  function openImportDraft(preview: TemplateImportPreview, saveMode: ImportSaveMode) {
    const matchedTarget = saveMode === "overwrite" ? preview.conflict.matched_templates[0] ?? null : null;
    setPendingImportPreview(null);
    navigate("/templates/new", {
      state: {
        importDraft: preview.normalized_template,
        saveMode,
        targetTemplateId: matchedTarget?.template_id,
        targetTemplateName: matchedTarget?.name,
      },
    });
  }

  return (
    <div className="templates-page">
      <PageSection description="浏览模板目录并进入独立详情页进行配置。">
        {importError ? (
          <StatusBanner tone="warning" title="导入失败">
            {importError}
          </StatusBanner>
        ) : null}

        <ListPageLayout
          intro={
            <PageIntroBar
              eyebrow="Template Catalog"
              description="模板列表只负责浏览和进入，配置工作在独立详情页中完成。"
              actions={
                <>
                  <button className="secondary-button" type="button" onClick={beginImportSelection}>
                    导入模板
                  </button>
                  <Link className="primary-button button-link" to="/templates/new">
                    新建模板
                  </Link>
                </>
              }
              badge={`${templatesQuery.data?.length ?? 0} 个模板`}
            />
          }
          content={
            templatesQuery.data?.length ? (
              <div className="template-catalog-grid">
                {templatesQuery.data.map((template) => (
                  <Link
                    key={template.template_id}
                    className="template-card"
                    to={`/templates/${template.template_id}`}
                  >
                    <div className="template-card__header">
                      <strong>{template.name}</strong>
                      <span className="status-chip status-chip--soft">{template.report_type}</span>
                    </div>
                    <p>{template.description || "暂无模板描述"}</p>
                    <div className="template-card__meta">
                      {[template.category, template.scenario].filter(Boolean).map((item) => (
                        <span key={item}>{item}</span>
                      ))}
                    </div>
                    <div className="template-card__meta">
                      <span>{template.parameter_count ?? 0} 个参数</span>
                      <span>{template.top_level_section_count ?? 0} 个顶层章节</span>
                      {template.schema_version ? <span>{template.schema_version}</span> : null}
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              !templatesQuery.isLoading && (
                <EmptyState title="暂无模板" description="点击“新建模板”，开始录入新版模板定义。" />
              )
            )
          }
        />

        <input
          ref={fileInputRef}
          aria-label="导入模板文件"
          type="file"
          accept=".json,application/json"
          hidden
          onChange={handleImportSelection}
        />

        {pendingImportPreview ? (
          <div className="modal-backdrop" role="presentation" onClick={() => setPendingImportPreview(null)}>
            <div
              className="modal-panel"
              role="dialog"
              aria-modal="true"
              aria-label="处理模板冲突"
              onClick={(event) => event.stopPropagation()}
            >
              <div className="list-header">
                <div>
                  <p className="section-kicker">Template Import</p>
                  <h3>处理模板冲突</h3>
                </div>
                <button className="ghost-button ghost-button--inline" type="button" onClick={() => setPendingImportPreview(null)}>
                  关闭
                </button>
              </div>

              <p className="muted-text">
                {pendingImportPreview.conflict.status === "single_match"
                  ? `检测到同名或同标识模板：${pendingImportPreview.conflict.matched_templates[0]?.name ?? "未知模板"}。`
                  : "检测到多个同名模板，本次导入只允许创建新副本。"}
              </p>

              {pendingImportPreview.conflict.matched_templates.length ? (
                <div className="table-shell">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>模板名称</th>
                        <th>模板 ID</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pendingImportPreview.conflict.matched_templates.map((item) => (
                        <tr key={item.template_id}>
                          <td>{item.name}</td>
                          <td>{item.template_id}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}

              <div className="action-row">
                <button className="primary-button" type="button" onClick={() => openImportDraft(pendingImportPreview, "create_copy")}>
                  新建副本
                </button>
                {pendingImportPreview.conflict.overwrite_supported ? (
                  <button className="secondary-button" type="button" onClick={() => openImportDraft(pendingImportPreview, "overwrite")}>
                    覆盖现有模板
                  </button>
                ) : null}
              </div>
            </div>
          </div>
        ) : null}
      </PageSection>
    </div>
  );
}

async function readFileText(file: File): Promise<string> {
  if (typeof file.text === "function") {
    return file.text();
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("文件读取失败。"));
    reader.onload = () => resolve(typeof reader.result === "string" ? reader.result : "");
    reader.readAsText(file);
  });
}
