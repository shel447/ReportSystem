import type { TemplateWorkbenchState, WorkbenchSection } from "./state";

export type StructuralPreview = {
  sections: Array<{
    title: string;
    description: string;
    content: string;
    level: number;
  }>;
};

export function buildRequirementPreview(state: TemplateWorkbenchState): StructuralPreview {
  const sections = state.sections.flatMap((section) => renderSection(section, state.previewSamples, {}, 1, "requirement"));
  return { sections };
}

export function buildStructuralPreview(state: TemplateWorkbenchState): StructuralPreview {
  const sections = state.sections.flatMap((section) => renderSection(section, state.previewSamples, {}, 1, "execution"));
  return { sections };
}

function renderSection(
  section: WorkbenchSection,
  samples: Record<string, string | string[]>,
  locals: Record<string, string>,
  level: number,
  mode: "requirement" | "execution",
): StructuralPreview["sections"] {
  if (section.foreachEnabled && section.foreachParam) {
    const values = normalizeSampleList(samples[section.foreachParam]);
    return values.flatMap((value) =>
      renderSection(
        { ...section, foreachEnabled: false },
        samples,
        { ...locals, [section.foreachAlias || "item"]: value },
        level,
        mode,
      ),
    );
  }

  const outlineValues = resolveOutlineValues(section, samples, locals);
  const title = renderText(section.title, samples, locals, outlineValues);
  const description = renderText(section.description, samples, locals, outlineValues);

  if (section.kind === "group") {
    return [
      { title, description, content: "", level },
      ...section.children.flatMap((child) => renderSection(child, samples, locals, level + 1, mode)),
    ];
  }

  return [
    {
      title,
      description,
      content: mode === "requirement" ? renderRequirementContent(section, samples, locals, outlineValues) : renderContent(section, samples, locals, outlineValues),
      level,
    },
  ];
}

function renderContent(
  section: WorkbenchSection,
  samples: Record<string, string | string[]>,
  locals: Record<string, string>,
  outlineValues: Record<string, string>,
): string {
  const presentation = section.content?.presentation;
  if (!presentation) {
    return "内容预览";
  }
  if (presentation.type === "text") {
    return renderText(presentation.template, samples, locals, outlineValues);
  }
  if (presentation.type === "value") {
    return renderText(presentation.anchor || "{$value}", samples, { ...locals, value: "值预览" }, outlineValues);
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

function renderRequirementContent(
  section: WorkbenchSection,
  samples: Record<string, string | string[]>,
  locals: Record<string, string>,
  outlineValues: Record<string, string>,
): string {
  if (!section.outline) {
    return "未配置诉求句子";
  }
  return renderText(section.outline.requirement, samples, locals, outlineValues);
}

function renderText(
  template: string,
  samples: Record<string, string | string[]>,
  locals: Record<string, string>,
  outlineValues: Record<string, string> = {},
): string {
  return String(template || "")
    .replace(/\{\$([a-zA-Z0-9_]+)\}/g, (_match, alias: string) => locals[alias] ?? "")
    .replace(/\{@([a-zA-Z0-9_]+)\}/g, (_match, itemId: string) => outlineValues[itemId] ?? "")
    .replace(/\{([a-zA-Z0-9_]+)\}/g, (_match, key: string) => stringifySample(samples[key]));
}

function resolveOutlineValues(
  section: WorkbenchSection,
  samples: Record<string, string | string[]>,
  locals: Record<string, string>,
): Record<string, string> {
  const resolved: Record<string, string> = {};
  for (const item of section.outline?.items ?? []) {
    const itemId = item.id.trim();
    if (!itemId) {
      continue;
    }
    if (item.paramId.trim()) {
      resolved[itemId] = stringifySample(samples[item.paramId.trim()]);
      continue;
    }
    if (typeof samples[itemId] !== "undefined") {
      resolved[itemId] = stringifySample(samples[itemId]);
      continue;
    }
    if (item.defaultValue.trim()) {
      resolved[itemId] = renderText(item.defaultValue, samples, locals, resolved);
      continue;
    }
    resolved[itemId] = item.hint || itemId;
  }
  return resolved;
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
