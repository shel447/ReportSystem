import { useEffect, useMemo, useState } from "react";
import { BIEngine } from "@cloudsop/bi-engine";
import type { BIEngineComponent } from "@cloudsop/bi-engine";
import { PptSlideFrame } from "@cloudsop/bi-designer";
import type { EditorStoreApi } from "@cloudsop/bi-designer";

import { listRecords, resolveReportStructureType } from "./report-dsl";
import { ReportPreviewOutline } from "./ReportPreviewOutline";
import {
  buildGlobalTocEntries,
  buildPagedPreviewPages,
  createReportWorkspace,
  useEditorDocument,
} from "./report-workspace";

type ReportDslPreviewProps = {
  report?: Record<string, unknown>;
  store?: EditorStoreApi;
  compact?: boolean;
};

export function ReportDslPreview({ report, store: providedStore, compact = false }: ReportDslPreviewProps) {
  const standaloneWorkspace = useMemo(() => createReportWorkspace(report ?? {}), [report]);
  const store = providedStore ?? standaloneWorkspace.store;
  const workspaceReport = useEditorDocument(store);
  const structureType = resolveReportStructureType(workspaceReport);
  if (structureType === "flow") {
    return <FlowReportPreview report={workspaceReport} compact={compact} />;
  }
  if (structureType === "paged") {
    return <PagedReportPreview report={workspaceReport} store={store} compact={compact} />;
  }
  return <div className="bi-preview-empty">无法识别报告结构，请检查 structureType 或 basicInfo.reportType。</div>;
}

function FlowReportPreview({ report, compact }: { report: Record<string, unknown>; compact: boolean }) {
  const [outlineCollapsed, setOutlineCollapsed] = useState(false);
  const catalogs = listRecords(report.catalogs);
  return (
    <div className={`bi-report-preview bi-report-preview--flow${compact ? " is-compact" : ""}`}>
      <ReportPreviewOutline report={report} collapsed={outlineCollapsed} onCollapse={() => setOutlineCollapsed((current) => !current)} />
      <div className="bi-report-preview__content">
        {catalogs.length ? catalogs.map((catalog) => <CatalogPreview key={String(catalog.id ?? "")} catalog={catalog} level={1} />) : (
          <div className="bi-preview-empty">报告正在生成，暂时还没有可展示的目录内容。</div>
        )}
      </div>
    </div>
  );
}

function CatalogPreview({ catalog, level }: { catalog: Record<string, unknown>; level: number }) {
  const sections = listRecords(catalog.sections);
  const subCatalogs = listRecords(catalog.subCatalogs);
  const Heading = level <= 1 ? "h2" : level === 2 ? "h3" : "h4";
  return (
    <section id={`preview-catalog-${String(catalog.id ?? "")}`} className={`bi-preview-catalog bi-preview-catalog--level-${Math.min(level, 3)}`}>
      <Heading>{String(catalog.name ?? catalog.title ?? catalog.id ?? "未命名目录")}</Heading>
      {sections.map((section) => <SectionPreview key={String(section.id ?? "")} section={section} />)}
      {subCatalogs.map((child) => <CatalogPreview key={String(child.id ?? "")} catalog={child} level={level + 1} />)}
    </section>
  );
}

function SectionPreview({ section }: { section: Record<string, unknown> }) {
  const components = listRecords(section.components) as unknown as BIEngineComponent[];
  return (
    <section id={`preview-section-${String(section.id ?? "")}`} className="bi-preview-section">
      {section.title ? <h4>{String(section.title)}</h4> : null}
      {components.length ? components.map((component) => (
        <div className="bi-preview-component" key={component.id}>
          <BIEngine schema={component} mode="view" theme="light" appearance={{ style: { width: "100%" } }} />
        </div>
      )) : <div className="bi-preview-empty">章节内容生成中...</div>}
    </section>
  );
}

function PagedReportPreview({ report, store, compact }: { report: Record<string, unknown>; store: EditorStoreApi; compact: boolean }) {
  const [outlineCollapsed, setOutlineCollapsed] = useState(false);
  const pages = useMemo(() => buildPagedPreviewPages(report), [report]);
  const globalTocEntries = useMemo(() => buildGlobalTocEntries(report), [report]);
  const [activePageId, setActivePageId] = useState(() => pages[0]?.id ?? "");
  const activeIndex = Math.max(pages.findIndex((page) => page.id === activePageId), 0);
  const activePage = pages[activeIndex];

  useEffect(() => {
    if (!pages.some((page) => page.id === activePageId)) {
      setActivePageId(pages[0]?.id ?? "");
    }
  }, [activePageId, pages]);

  if (!activePage) {
    return <div className="bi-preview-empty">报告正在生成，暂时还没有可展示的幻灯片。</div>;
  }

  function navigate(offset: number) {
    setActivePageId(pages[Math.min(Math.max(activeIndex + offset, 0), pages.length - 1)]?.id ?? activePage.id);
  }

  return (
    <div className={`bi-report-preview bi-report-preview--paged${compact ? " is-compact" : ""}`}>
      <ReportPreviewOutline report={report} pages={pages} activePageId={activePage.id} collapsed={outlineCollapsed} onCollapse={() => setOutlineCollapsed((current) => !current)} onSelectPage={setActivePageId} />
      <div className="bi-report-preview__content">
        <div className="bi-paged-preview__toolbar">
          <strong>{activePage.label}</strong>
          <span>{activeIndex + 1} / {pages.length}</span>
          <button type="button" aria-label="上一页" disabled={activeIndex === 0} onClick={() => navigate(-1)}>‹</button>
          <button type="button" aria-label="下一页" disabled={activeIndex >= pages.length - 1} onClick={() => navigate(1)}>›</button>
        </div>
        <div className="bi-paged-preview__canvas">
          <PptSlideFrame
            store={store}
            slide={activePage.slide}
            renderMode="view"
            slideType={activePage.type}
            sectionContext={activePage.sectionContext}
            globalTocEntries={activePage.type === "toc" ? globalTocEntries : undefined}
            cover={activePage.type === "cover" ? readCover(report.cover) : undefined}
            backCover={activePage.type === "back-cover" ? readBackCover(report.backCover) : undefined}
            onTocEntryClick={(index) => setActivePageId(globalTocEntries[index]?.targetSlideId ?? activePage.id)}
            onChapterClick={(index) => {
              const sectionSlide = pages.filter((page) => page.type === "content")[index];
              setActivePageId(sectionSlide?.id ?? activePage.id);
            }}
            onNavigateSlide={(direction) => navigate(direction === "prev" ? -1 : 1)}
          />
        </div>
      </div>
    </div>
  );
}

function readCover(value: unknown) {
  return value && typeof value === "object" ? value as { title?: string; subTitle?: string; author?: string; image?: string } : undefined;
}

function readBackCover(value: unknown) {
  return value && typeof value === "object" ? value as { image?: string; text?: string } : undefined;
}
