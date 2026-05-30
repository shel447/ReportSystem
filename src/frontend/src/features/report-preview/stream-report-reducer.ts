import type { ChatStreamDelta } from "../../entities/chat/types";
import { listRecords, resolveReportStructureType } from "./report-dsl";

export type StreamReportState = Record<string, unknown> | null;

export function reduceStreamReport(deltas: ChatStreamDelta[]): StreamReportState {
  return deltas.reduce<StreamReportState>((state, delta) => applyStreamReportDelta(state, delta), null);
}

export function applyStreamReportDelta(current: StreamReportState, delta: ChatStreamDelta): StreamReportState {
  if (delta.action === "init_report") {
    const structureType = delta.report.structureType ?? "flow";
    return structureType === "paged"
      ? { structureType, basicInfo: { id: delta.report.reportId, name: delta.report.title }, content: [] }
      : { structureType, basicInfo: { id: delta.report.reportId, name: delta.report.title }, catalogs: [], layout: { type: "flow" } };
  }

  const report = structuredClone(current ?? emptyReportForDelta(delta));
  if (delta.action === "add_catalog") {
    const target = findCatalogChildren(report, delta.parentCatalogId);
    mergeById(target, delta.catalogs.map((catalog) => ({
      id: catalog.catalogId,
      name: catalog.title,
      sections: [],
      subCatalogs: [],
    })));
  } else if (delta.action === "add_chapter") {
    const content = ensureRecords(report, "content");
    mergeById(content, delta.chapters.map((chapter) => ({ id: chapter.id, type: "section", title: chapter.title, slides: [] })));
  } else if (delta.action === "add_slide") {
    const content = ensureRecords(report, "content");
    const chapter = content.find((item) => item.id === delta.chapterId);
    const target = chapter ? ensureRecords(chapter, "slides") : content;
    mergeById(target, delta.slides.map((slide) => ({ ...slide, components: [] })));
  } else if (delta.action === "add_section") {
    if (delta.structureType === "paged") {
      const slide = findSlide(report, delta.slideId);
      if (slide) {
        mergeComponents(slide, delta.sections);
      }
    } else {
      const catalog = findCatalog(report, delta.parentCatalogId);
      if (catalog) {
        const sections = ensureRecords(catalog, "sections");
        mergeById(sections, delta.sections.map(toFlowSection));
      }
    }
  }
  return report;
}

function emptyReportForDelta(delta: ChatStreamDelta): Record<string, unknown> {
  const structureType = "structureType" in delta ? delta.structureType : "flow";
  return structureType === "paged"
    ? { structureType: "paged", basicInfo: {}, content: [] }
    : { structureType: "flow", basicInfo: {}, catalogs: [], layout: { type: "flow" } };
}

function toFlowSection(section: { sectionId: string; requirement: string; components?: Array<Record<string, unknown>> }) {
  return { id: section.sectionId, title: section.requirement, components: section.components ?? [] };
}

function mergeComponents(slide: Record<string, unknown>, sections: Array<{ components?: Array<Record<string, unknown>> }>) {
  const components = ensureRecords(slide, "components");
  for (const section of sections) {
    mergeById(components, section.components ?? []);
  }
}

function findCatalogChildren(report: Record<string, unknown>, parentId: string | null) {
  if (!parentId) {
    return ensureRecords(report, "catalogs");
  }
  const parent = findCatalog(report, parentId);
  return parent ? ensureRecords(parent, "subCatalogs") : ensureRecords(report, "catalogs");
}

function findCatalog(report: Record<string, unknown>, catalogId: string | null) {
  if (!catalogId) return null;
  const stack = [...listRecords(report.catalogs)];
  while (stack.length) {
    const current = stack.shift()!;
    if (current.id === catalogId) return current;
    stack.push(...listRecords(current.subCatalogs));
  }
  return null;
}

function findSlide(report: Record<string, unknown>, slideId: string | null | undefined) {
  if (!slideId) return null;
  for (const item of listRecords(report.content)) {
    if (item.id === slideId) return item;
    const slide = listRecords(item.slides).find((candidate) => candidate.id === slideId);
    if (slide) return slide;
  }
  return null;
}

function ensureRecords(target: Record<string, unknown>, key: string) {
  const current = listRecords(target[key]);
  target[key] = current;
  return current;
}

function mergeById(target: Array<Record<string, unknown>>, next: Array<Record<string, unknown>>) {
  for (const item of next) {
    const existing = target.find((candidate) => candidate.id === item.id);
    if (existing) {
      Object.assign(existing, item);
    } else {
      target.push(item);
    }
  }
}

export function canPreviewStreamReport(report: StreamReportState) {
  if (!report) return false;
  return resolveReportStructureType(report) === "paged"
    ? listRecords(report.content).length > 0
    : listRecords(report.catalogs).length > 0;
}
