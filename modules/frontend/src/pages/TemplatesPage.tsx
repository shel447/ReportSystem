import { useMemo, useRef, useState, type ChangeEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { FileJson, Filter, Plus, Search, Upload } from "lucide-react";

import { fetchTemplates, previewImportTemplate } from "../entities/templates/api";
import type { TemplateImportPreview, TemplateStructureType } from "../entities/templates/types";
import { StatusBanner } from "../shared/ui/StatusBanner";
import { EmptyState } from "../shared/ui/EmptyState";

export function TemplatesPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [importError, setImportError] = useState("");
  const [query, setQuery] = useState("");
  const [structureFilter, setStructureFilter] = useState<"all" | TemplateStructureType>("all");
  const [categoryFilter, setCategoryFilter] = useState("all");

  const templatesQuery = useQuery({
    queryKey: ["templates"],
    queryFn: fetchTemplates,
  });

  const templates = templatesQuery.data ?? [];
  const categories = useMemo(
    () => Array.from(new Set(templates.map((template) => template.category).filter(Boolean))).sort(),
    [templates],
  );
  const visibleTemplates = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return templates.filter((template) => {
      const structureType = template.structureType === "paged" ? "paged" : "flow";
      const matchesStructure = structureFilter === "all" || structureType === structureFilter;
      const matchesCategory = categoryFilter === "all" || template.category === categoryFilter;
      const searchable = `${template.id} ${template.name} ${template.description} ${template.category}`.toLowerCase();
      const matchesQuery = !normalizedQuery || searchable.includes(normalizedQuery);
      return matchesStructure && matchesCategory && matchesQuery;
    });
  }, [categoryFilter, query, structureFilter, templates]);
  const flowCount = templates.filter((template) => template.structureType !== "paged").length;
  const pagedCount = templates.filter((template) => template.structureType === "paged").length;

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
    <div className="templates-workbench">
      <section className="template-list-shell">
        <div className="template-list-toolbar">
          <div className="template-list-toolbar__title">
            <FileJson size={18} aria-hidden="true" />
            <div>
              <h1>报告模板</h1>
              <p>{templates.length} 个模板 · Flow {flowCount} · PPT {pagedCount}</p>
            </div>
          </div>
          <div className="template-list-toolbar__actions">
            <button className="secondary-button" type="button" onClick={() => fileInputRef.current?.click()}>
              <Upload size={16} aria-hidden="true" />
              导入
            </button>
            <Link className="primary-button button-link" to="/templates/new">
              <Plus size={16} aria-hidden="true" />
              新建
            </Link>
          </div>
        </div>

        {importError ? (
          <StatusBanner tone="warning" title="导入失败">
            {importError}
          </StatusBanner>
        ) : null}

        <div className="template-list-filters" aria-label="模板筛选">
          <label className="template-search-field">
            <Search size={16} aria-hidden="true" />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索 ID、名称、描述或分类" />
          </label>
          <label className="template-filter-select">
            <Filter size={15} aria-hidden="true" />
            <select value={structureFilter} onChange={(event) => setStructureFilter(event.target.value as "all" | TemplateStructureType)} aria-label="结构类型筛选">
              <option value="all">全部结构</option>
              <option value="flow">Flow</option>
              <option value="paged">PPT</option>
            </select>
          </label>
          <label className="template-filter-select">
            <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)} aria-label="分类筛选">
              <option value="all">全部分类</option>
              {categories.map((category) => <option key={category} value={category}>{category}</option>)}
            </select>
          </label>
        </div>

        {templatesQuery.isLoading ? (
          <div className="template-list-loading">正在加载模板...</div>
        ) : visibleTemplates.length > 0 ? (
          <div className="template-table" role="table" aria-label="报告模板列表">
            <div className="template-table__head" role="row">
              <span role="columnheader">模板</span>
              <span role="columnheader">结构</span>
              <span role="columnheader">分类</span>
              <span role="columnheader">版本</span>
              <span role="columnheader">更新时间</span>
            </div>
            {visibleTemplates.map((template) => (
              <Link key={template.id} className="template-table__row" to={`/templates/${template.id}`}>
                <span className="template-table__main" role="cell">
                  <strong>{template.name}</strong>
                  <small>{template.id}</small>
                  <em>{template.description || "暂无模板描述"}</em>
                </span>
                <span role="cell"><span className="status-chip status-chip--soft">{template.structureType === "paged" ? "PPT" : "Flow"}</span></span>
                <span role="cell">{template.category}</span>
                <span role="cell">{template.schemaVersion}</span>
                <span role="cell">{template.updatedAt ? formatDateTime(template.updatedAt) : "未记录"}</span>
              </Link>
            ))}
          </div>
        ) : (
          <EmptyState title={templates.length ? "没有匹配的模板" : "暂无模板"} description={templates.length ? "调整搜索或筛选条件后再试。" : "点击“新建”，开始录入新的正式模板定义。"} />
        )}

        <input
          ref={fileInputRef}
          aria-label="导入模板文件"
          type="file"
          accept=".json,application/json"
          hidden
          onChange={handleImportSelection}
        />
      </section>
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
