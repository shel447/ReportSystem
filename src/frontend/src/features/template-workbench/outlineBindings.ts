import type { WorkbenchSection } from "./state";

export type OutlineSyncStatus = "not_configured" | "stale" | "in_sync" | "compile_error";

export type OutlineBinding = {
  blockId: string;
  targets: string[];
};

export type OutlineSyncSummary = {
  status: OutlineSyncStatus;
  bindings: OutlineBinding[];
  invalidBlockIds: string[];
  availableBlockIds: string[];
};

export function summarizeSectionOutlineBindings(section: WorkbenchSection): OutlineSyncSummary {
  const bindings = new Map<string, Set<string>>();
  const invalidBlockIds = new Set<string>();
  const availableBlockIds = new Set((section.outline?.blocks ?? []).map((block) => block.id.trim()).filter(Boolean));

  visitTextTarget(section.title, "title", bindings, invalidBlockIds, availableBlockIds);
  visitTextTarget(section.description, "description", bindings, invalidBlockIds, availableBlockIds);

  if (section.content) {
    visitTextTarget(section.content.presentation.template, "presentation.template", bindings, invalidBlockIds, availableBlockIds);
    visitTextTarget(section.content.presentation.anchor, "presentation.anchor", bindings, invalidBlockIds, availableBlockIds);
    section.content.datasets.forEach((dataset, index) => {
      const prefix = `datasets.${dataset.id.trim() || index + 1}.source`;
      visitTextTarget(dataset.source.query, `${prefix}.query`, bindings, invalidBlockIds, availableBlockIds);
      visitTextTarget(dataset.source.description, `${prefix}.description`, bindings, invalidBlockIds, availableBlockIds);
      visitTextTarget(dataset.source.prompt, `${prefix}.prompt`, bindings, invalidBlockIds, availableBlockIds);
      visitTextTarget(dataset.source.knowledgeQueryTemplate, `${prefix}.knowledge.query_template`, bindings, invalidBlockIds, availableBlockIds);
      dataset.source.contextQueries.forEach((item, queryIndex) => {
        visitTextTarget(
          item.query,
          `${prefix}.context.queries.${item.id || queryIndex + 1}`,
          bindings,
          invalidBlockIds,
          availableBlockIds,
        );
      });
    });
  }

  const serializedBindings = Array.from(bindings.entries())
    .map(([blockId, targets]) => ({ blockId, targets: Array.from(targets) }))
    .sort((left, right) => left.blockId.localeCompare(right.blockId));

  return {
    status: resolveStatus(section, serializedBindings, invalidBlockIds),
    bindings: serializedBindings,
    invalidBlockIds: Array.from(invalidBlockIds).sort(),
    availableBlockIds: Array.from(availableBlockIds).sort(),
  };
}

function visitTextTarget(
  value: string | undefined,
  target: string,
  bindings: Map<string, Set<string>>,
  invalidBlockIds: Set<string>,
  availableBlockIds: Set<string>,
) {
  const matches = String(value || "").matchAll(/\{@([a-zA-Z0-9_]+)\}/g);
  for (const match of matches) {
    const blockId = match[1]?.trim();
    if (!blockId) {
      continue;
    }
    if (!availableBlockIds.has(blockId)) {
      invalidBlockIds.add(blockId);
      continue;
    }
    if (!bindings.has(blockId)) {
      bindings.set(blockId, new Set());
    }
    bindings.get(blockId)?.add(target);
  }
}

function resolveStatus(
  section: WorkbenchSection,
  bindings: OutlineBinding[],
  invalidBlockIds: Set<string>,
): OutlineSyncStatus {
  if (invalidBlockIds.size) {
    return "compile_error";
  }
  if (!section.outline) {
    return bindings.length ? "compile_error" : "not_configured";
  }
  if (!bindings.length) {
    return "stale";
  }
  return "in_sync";
}
