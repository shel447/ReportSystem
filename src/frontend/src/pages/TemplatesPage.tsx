import { useRef, useState, type ChangeEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";

import { fetchTemplates, previewImportTemplate } from "../entities/templates/api";
import type { TemplateImportPreview } from "../entities/templates/types";
import { ListPageLayout } from "../shared/layouts/ListPageLayout";
import { PageIntroBar } from "../shared/layouts/PageIntroBar";
import { PageSection } from "../shared/ui/PageSection";
import { StatusBanner } from "../shared/ui/StatusBanner";
import { EmptyState } from "../shared/ui/EmptyState";

export function TemplatesPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [importError, setImportError] = useState("");

  const templatesQuery = useQuery({
    queryKey: ["templates"],
    queryFn: fetchTemplates,
  });

  async function handleImportSelection(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }

    try {
      const text = await readFileText(file);
      const content = JSON.parse(text) as Record<string, unknown>;
      const preview = await previewImportTemplate(content);
      openImportDraft(preview);
      setImportError("");
    } catch (error) {
      setImportError(error instanceof Error ? error.message : "模板导入失败。");
    }
  }

  function openImportDraft(preview: TemplateImportPreview) {
    navigate("/templates/new", {
      state: {
        importDraft: preview.normalizedTemplate,
        importWarnings: preview.warnings,
      },
    });
  }

  return (
    <div className="templates-page">
      <PageSection description="模板接口只承载正式静态模板定义，结构固定为 parameters + catalogs。">
        {importError ? (
          <StatusBanner tone="warning" title="导入失败">
            {importError}
          </StatusBanner>
        ) : null}

        <ListPageLayout
          intro={
            <PageIntroBar
              eyebrow="Report Templates"
              description="浏览正式模板资产，并进入模板详情页维护 catalogs -> sections 定义。"
              actions={
                <>
                  <button className="secondary-button" type="button" onClick={() => fileInputRef.current?.click()}>
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
            templatesQuery.data && templatesQuery.data.length > 0 ? (
              <div className="template-catalog-grid">
                {templatesQuery.data.map((template) => (
                  <Link key={template.id} className="template-card" to={`/templates/${template.id}`}>
                    <div className="template-card__header">
                      <strong>{template.name}</strong>
                      <span className="status-chip status-chip--soft">{template.category}</span>
                    </div>
                    <p>{template.description || "暂无模板描述"}</p>
                    <div className="template-card__meta">
                      <span>{template.id}</span>
                      <span>{template.schemaVersion}</span>
                    </div>
                    <div className="template-card__meta">
                      <span>{template.updatedAt ? formatDateTime(template.updatedAt) : "未记录更新时间"}</span>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              !templatesQuery.isLoading && (
                <EmptyState title="暂无模板" description="点击“新建模板”，开始录入新的正式模板定义。" />
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

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", { hour12: false });
}
