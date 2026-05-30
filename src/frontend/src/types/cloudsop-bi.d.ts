declare module "@cloudsop/bi-engine" {
  import type { ComponentType, CSSProperties } from "react";

  export type BIEngineComponent = {
    id: string;
    type: string;
    [key: string]: unknown;
  };

  export type Slide = {
    id: string;
    title?: string;
    components?: BIEngineComponent[];
    [key: string]: unknown;
  };

  export const BIEngine: ComponentType<{
    schema: BIEngineComponent;
    mode?: "chat" | "edit" | "view" | "thumbnail";
    theme?: "dark" | "evening" | "light";
    appearance?: { className?: string; style?: CSSProperties };
  }>;
}

declare module "@cloudsop/bi-designer" {
  import type { ComponentType } from "react";
  import type { Slide } from "@cloudsop/bi-engine";

  export type EditorDoc = Record<string, unknown>;

  export type EditorStoreApi = {
    getState: () => {
      doc: EditorDoc | null;
      docRevision: number;
      isDirty: boolean;
      setDoc: (doc: EditorDoc) => void;
      getDoc: () => EditorDoc;
    };
    subscribe: (listener: () => void) => () => void;
  };

  export function createEditorStore(initialDoc?: EditorDoc): EditorStoreApi;
  export function applyAutoLayoutToDoc(doc: Record<string, unknown>): Record<string, unknown>;

  export const PptSlideFrame: ComponentType<{
    store: EditorStoreApi;
    slide: Slide;
    renderMode?: "edit" | "view";
    sectionContext?: { titles: string[]; sectionTitle: string; sectionId: string };
    slideType?: "cover" | "toc" | "section-toc" | "back-cover" | "content";
    globalTocEntries?: ReadonlyArray<{ type: "section" | "slide"; title: string; targetSlideId?: string }>;
    onTocEntryClick?: (index: number) => void;
    onChapterClick?: (index: number) => void;
    onNavigateSlide?: (direction: "prev" | "next") => void;
    cover?: { title?: string; subTitle?: string; author?: string; image?: string };
    backCover?: { image?: string; text?: string };
  }>;

  export const PptEditor: ComponentType<{
    store: EditorStoreApi;
    locale?: string;
    theme?: string;
  }>;

  export const ReportEditor: ComponentType<{
    store: EditorStoreApi;
    locale?: string;
    theme?: string;
  }>;
}

declare module "@cloudsop/bi-signal";
declare module "@cloudsop/bi-signal/react";
