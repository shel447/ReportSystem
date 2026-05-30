import { useSyncExternalStore } from "react";
import { applyAutoLayoutToDoc, createEditorStore } from "@cloudsop/bi-designer";
import type { EditorDoc, EditorStoreApi } from "@cloudsop/bi-designer";
import type { Slide } from "@cloudsop/bi-engine";

import { isRecord, listRecords, resolveReportStructureType } from "./report-dsl";

export type PreviewSlideType = "cover" | "toc" | "section-toc" | "back-cover" | "content";

export type PagedPreviewPage = {
  id: string;
  label: string;
  slide: Slide;
  type: PreviewSlideType;
  sectionContext?: {
    titles: string[];
    sectionTitle: string;
    sectionId: string;
  };
};

export const VIRTUAL_PREVIEW_PAGE_IDS = {
  cover: "__ppt_cover__",
  toc: "__ppt_toc__",
  sectionTocPrefix: "__ppt_section_toc__:",
  backCover: "__ppt_backcover__",
} as const;

const VIRTUAL_LAYOUT = { type: "grid", grid: { cols: 12, rowHeight: 60 } };

export function normalizeReportForWorkspace(report: Record<string, unknown>): EditorDoc {
  const cloned = structuredClone(report);
  return resolveReportStructureType(cloned) === "paged"
    ? applyAutoLayoutToDoc(cloned) as EditorDoc
    : cloned as EditorDoc;
}

export function createReportWorkspace(report: Record<string, unknown>) {
  const original = normalizeReportForWorkspace(report);
  return {
    original,
    store: createEditorStore(original),
  };
}

export function useEditorDocument(store: EditorStoreApi): Record<string, unknown> {
  useSyncExternalStore(
    store.subscribe,
    () => store.getState().docRevision ?? 0,
    () => store.getState().docRevision ?? 0,
  );
  const state = store.getState();
  return (state.doc ?? state.getDoc()) as Record<string, unknown>;
}

export function buildPagedPreviewPages(report: Record<string, unknown>): PagedPreviewPage[] {
  const content = listRecords(report.content);
  const hasContent = content.length > 0;
  const pages: PagedPreviewPage[] = [createVirtualPage(VIRTUAL_PREVIEW_PAGE_IDS.cover, "封面", "cover")];
  if (hasContent) {
    pages.push(createVirtualPage(VIRTUAL_PREVIEW_PAGE_IDS.toc, "目录", "toc"));
  }
  for (const item of content) {
    const slides = listRecords(item.slides) as unknown as Slide[];
    if (slides.length) {
      const sectionId = String(item.id ?? "");
      const sectionTitle = String(item.title ?? "未命名章节");
      pages.push({
        ...createVirtualPage(`${VIRTUAL_PREVIEW_PAGE_IDS.sectionTocPrefix}${sectionId}`, sectionTitle, "section-toc"),
        sectionContext: {
          sectionId,
          sectionTitle,
          titles: slides.map((slide) => String(slide.title ?? "未命名页面")),
        },
      });
      slides.forEach((slide) => pages.push({
        id: slide.id,
        label: String(slide.title ?? "未命名页面"),
        slide,
        type: "content",
      }));
      continue;
    }
    if (isRecord(item)) {
      pages.push({
        id: String(item.id ?? ""),
        label: String(item.title ?? "未命名页面"),
        slide: item as unknown as Slide,
        type: "content",
      });
    }
  }
  pages.push(createVirtualPage(VIRTUAL_PREVIEW_PAGE_IDS.backCover, "封底", "back-cover"));
  return pages;
}

export function buildGlobalTocEntries(report: Record<string, unknown>) {
  return listRecords(report.content).map((item) => {
    const slides = listRecords(item.slides);
    return slides.length
      ? {
          type: "section" as const,
          title: String(item.title ?? "未命名章节"),
          targetSlideId: `${VIRTUAL_PREVIEW_PAGE_IDS.sectionTocPrefix}${String(item.id ?? "")}`,
        }
      : {
          type: "slide" as const,
          title: String(item.title ?? "未命名页面"),
          targetSlideId: String(item.id ?? ""),
        };
  });
}

function createVirtualPage(id: string, label: string, type: PreviewSlideType): PagedPreviewPage {
  return {
    id,
    label,
    type,
    slide: { id, title: label, layout: VIRTUAL_LAYOUT, components: [] } as unknown as Slide,
  };
}
