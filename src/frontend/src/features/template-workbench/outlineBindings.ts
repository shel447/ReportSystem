import type { WorkbenchSection } from "./state";

export type OutlineSyncStatus = "not_configured" | "stale" | "in_sync" | "compile_error";

export type OutlineBinding = {
  itemId: string;
  targets: string[];
};

export type OutlineSyncSummary = {
  status: OutlineSyncStatus;
  bindings: OutlineBinding[];
  invalidItemIds: string[];
  availableItemIds: string[];
};

export function summarizeSectionOutlineBindings(section: WorkbenchSection): OutlineSyncSummary {
  const bindings = new Map<string, Set<string>>();
  const invalidItemIds = new Set<string>();
  const availableItemIds = new Set((section.outline?.items ?? []).map((item) => item.id.trim()).filter(Boolean));

  visitTextTarget(section.title, "title", bindings, invalidItemIds, availableItemIds);
  visitTextTarget(section.description, "description", bindings, invalidItemIds, availableItemIds);

  if (section.content) {
    visitTextTarget(section.content.presentation.template, "presentation.template", bindings, invalidItemIds, availableItemIds);
    visitTextTarget(section.content.presentation.anchor, "presentation.anchor", bindings, invalidItemIds, availableItemIds);
    section.content.datasets.forEach((dataset, index) => {
      const prefix = `datasets.${dataset.id.trim() || index + 1}.source`;
      visitTextTarget(dataset.source.query, `${prefix}.query`, bindings, invalidItemIds, availableItemIds);
      visitTextTarget(dataset.source.description, `${prefix}.description`, bindings, invalidItemIds, availableItemIds);
      visitTextTarget(dataset.source.prompt, `${prefix}.prompt`, bindings, invalidItemIds, availableItemIds);
      visitTextTarget(dataset.source.knowledgeQueryTemplate, `${prefix}.knowledge.query_template`, bindings, invalidItemIds, availableItemIds);
      dataset.source.contextQueries.forEach((item, queryIndex) => {
        visitTextTarget(
          item.query,
          `${prefix}.context.queries.${item.id || queryIndex + 1}`,
          bindings,
          invalidItemIds,
          availableItemIds,
        );
      });
    });
  }

  const serializedBindings = Array.from(bindings.entries())
    .map(([itemId, targets]) => ({ itemId, targets: Array.from(targets) }))
    .sort((left, right) => left.itemId.localeCompare(right.itemId));

  return {
    status: resolveStatus(section, serializedBindings, invalidItemIds),
    bindings: serializedBindings,
    invalidItemIds: Array.from(invalidItemIds).sort(),
    availableItemIds: Array.from(availableItemIds).sort(),
  };
}

function visitTextTarget(
  value: string | undefined,
  target: string,
  bindings: Map<string, Set<string>>,
  invalidItemIds: Set<string>,
  availableItemIds: Set<string>,
) {
  const matches = String(value || "").matchAll(/\{@([a-zA-Z0-9_]+)\}/g);
  for (const match of matches) {
    const itemId = match[1]?.trim();
    if (!itemId) {
      continue;
    }
    if (!availableItemIds.has(itemId)) {
      invalidItemIds.add(itemId);
      continue;
    }
    if (!bindings.has(itemId)) {
      bindings.set(itemId, new Set());
    }
    bindings.get(itemId)?.add(target);
  }
}

function resolveStatus(
  section: WorkbenchSection,
  bindings: OutlineBinding[],
  invalidItemIds: Set<string>,
): OutlineSyncStatus {
  if (invalidItemIds.size) {
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
