import type { TemplateWorkbenchState, WorkbenchSection } from "./state";

export type StructuralPreview = {
  sections: Array<{
    title: string;
    description: string;
    content: string;
    level: number;
  }>;
};

export function buildStructuralPreview(state: TemplateWorkbenchState): StructuralPreview {
  const sections = state.sections.flatMap((section) => renderSection(section, state.previewSamples, {}, 1));
  return { sections };
}

function renderSection(
  section: WorkbenchSection,
  samples: Record<string, string | string[]>,
  locals: Record<string, string>,
  level: number,
): StructuralPreview["sections"] {
  if (section.foreachEnabled && section.foreachParam) {
    const values = normalizeSampleList(samples[section.foreachParam]);
    return values.flatMap((value) =>
      renderSection(
        { ...section, foreachEnabled: false },
        samples,
        { ...locals, [section.foreachAlias || "item"]: value },
        level,
      ),
    );
  }

  const title = renderText(section.title, samples, locals);
  const description = renderText(section.description, samples, locals);

  if (section.kind === "group") {
    return [
      { title, description, content: "", level },
      ...section.children.flatMap((child) => renderSection(child, samples, locals, level + 1)),
    ];
  }

  return [
    {
      title,
      description,
      content: renderContent(section, samples, locals),
      level,
    },
  ];
}

function renderContent(
  section: WorkbenchSection,
  samples: Record<string, string | string[]>,
  locals: Record<string, string>,
): string {
  const presentation = section.content?.presentation;
  if (!presentation) {
    return "内容预览";
  }
  if (presentation.type === "text") {
    return renderText(presentation.template, samples, locals);
  }
  if (presentation.type === "value") {
    return (presentation.anchor || "{$value}").replace("{$value}", "值预览");
  }
  if (presentation.type === "simple_table") {
    return "表格预览";
  }
  if (presentation.type === "chart") {
    return "图表预览";
  }
  if (presentation.type === "composite_table") {
    return "复合表预览";
  }
  return "内容预览";
}

function renderText(
  template: string,
  samples: Record<string, string | string[]>,
  locals: Record<string, string>,
): string {
  return String(template || "")
    .replace(/\{\$([a-zA-Z0-9_]+)\}/g, (_match, alias: string) => locals[alias] ?? "")
    .replace(/\{([a-zA-Z0-9_]+)\}/g, (_match, key: string) => stringifySample(samples[key]));
}

function stringifySample(value: string | string[] | undefined): string {
  if (Array.isArray(value)) {
    return value.join("、");
  }
  return value ?? "";
}

function normalizeSampleList(value: string | string[] | undefined): string[] {
  if (Array.isArray(value)) {
    return value;
  }
  if (typeof value === "string" && value) {
    return [value];
  }
  return [];
}
