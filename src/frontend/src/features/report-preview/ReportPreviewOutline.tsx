import { ChevronLeft, ChevronRight, ListTree } from "lucide-react";

import { listRecords } from "./report-dsl";
import type { PagedPreviewPage } from "./report-workspace";

type ReportPreviewOutlineProps = {
  collapsed: boolean;
  onCollapse: () => void;
  pages?: PagedPreviewPage[];
  report: Record<string, unknown>;
  activePageId?: string;
  onSelectPage?: (pageId: string) => void;
};

export function ReportPreviewOutline({ collapsed, onCollapse, pages, report, activePageId, onSelectPage }: ReportPreviewOutlineProps) {
  return (
    <aside className={`report-preview-outline${collapsed ? " is-collapsed" : ""}`} aria-label="报告大纲">
      <div className="report-preview-outline__header">
        {!collapsed ? <><ListTree size={15} /><strong>大纲</strong></> : null}
        <button type="button" className="icon-button" aria-label={collapsed ? "展开大纲" : "收起大纲"} title={collapsed ? "展开大纲" : "收起大纲"} onClick={onCollapse}>
          {collapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
        </button>
      </div>
      {pages
        ? <PagedOutline pages={pages} activePageId={activePageId} onSelectPage={onSelectPage} />
        : <FlowOutline catalogs={listRecords(report.catalogs)} />}
    </aside>
  );
}

function PagedOutline({ pages, activePageId, onSelectPage }: Pick<ReportPreviewOutlineProps, "pages" | "activePageId" | "onSelectPage">) {
  return (
    <nav className="report-preview-outline__tree" aria-label="幻灯片大纲">
      {(pages ?? []).map((page) => (
        <button
          type="button"
          key={page.id}
          className={`report-preview-outline__item report-preview-outline__item--${page.type}${activePageId === page.id ? " is-active" : ""}`}
          onClick={() => onSelectPage?.(page.id)}
        >
          <span>{page.type === "section-toc" ? "章节" : page.type === "content" ? "页面" : "固定"}</span>
          <strong>{page.label}</strong>
        </button>
      ))}
    </nav>
  );
}

function FlowOutline({ catalogs, level = 1 }: { catalogs: Array<Record<string, unknown>>; level?: number }) {
  return (
    <div className="report-preview-outline__tree">
      {catalogs.flatMap((catalog) => {
        const catalogId = String(catalog.id ?? "");
        return [
          <button type="button" key={catalogId} className={`report-preview-outline__item report-preview-outline__item--level-${Math.min(level, 3)}`} onClick={() => scrollToPreviewNode(`preview-catalog-${catalogId}`)}>
            <span>目录</span>
            <strong>{String(catalog.name ?? catalog.title ?? catalog.id ?? "未命名目录")}</strong>
          </button>,
          ...listRecords(catalog.sections).map((section) => {
            const sectionId = String(section.id ?? "");
            return (
              <button type="button" key={sectionId} className={`report-preview-outline__item report-preview-outline__item--section report-preview-outline__item--level-${Math.min(level + 1, 3)}`} onClick={() => scrollToPreviewNode(`preview-section-${sectionId}`)}>
                <span>章节</span>
                <strong>{String(section.title ?? section.id ?? "未命名章节")}</strong>
              </button>
            );
          }),
          <FlowOutline key={`${catalogId}-children`} catalogs={listRecords(catalog.subCatalogs)} level={level + 1} />,
        ];
      })}
    </div>
  );
}

function scrollToPreviewNode(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}
