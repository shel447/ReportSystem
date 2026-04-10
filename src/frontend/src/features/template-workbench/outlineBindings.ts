import type { WorkbenchSection } from "./state";

export type OutlineSyncStatus = "not_configured" | "stale" | "in_sync" | "compile_error";

export type OutlineBinding = {
  slotId: string;
  targets: string[];
};

export type OutlineSyncSummary = {
  status: OutlineSyncStatus;
  bindings: OutlineBinding[];
  invalidSlotIds: string[];
  availableSlotIds: string[];
};

export function summarizeSectionOutlineBindings(section: WorkbenchSection): OutlineSyncSummary {
  const bindings = new Map<string, Set<string>>();
  const invalidSlotIds = new Set<string>();
  const availableSlotIds = new Set((section.outline?.slots ?? []).map((slot) => slot.id.trim()).filter(Boolean));

  visitTextTarget(section.title, "title", bindings, invalidSlotIds, availableSlotIds);
  visitTextTarget(section.description, "description", bindings, invalidSlotIds, availableSlotIds);

  if (section.content) {
    visitTextTarget(section.content.presentation.template, "presentation.template", bindings, invalidSlotIds, availableSlotIds);
    visitTextTarget(section.content.presentation.anchor, "presentation.anchor", bindings, invalidSlotIds, availableSlotIds);
    section.content.datasets.forEach((dataset, index) => {
      const prefix = `datasets.${dataset.id.trim() || index + 1}.source`;
      visitTextTarget(dataset.source.query, `${prefix}.query`, bindings, invalidSlotIds, availableSlotIds);
      visitTextTarget(dataset.source.description, `${prefix}.description`, bindings, invalidSlotIds, availableSlotIds);
      visitTextTarget(dataset.source.prompt, `${prefix}.prompt`, bindings, invalidSlotIds, availableSlotIds);
      visitTextTarget(dataset.source.knowledgeQueryTemplate, `${prefix}.knowledge.query_template`, bindings, invalidSlotIds, availableSlotIds);
      dataset.source.contextQueries.forEach((item, queryIndex) => {
        visitTextTarget(
          item.query,
          `${prefix}.context.queries.${item.id || queryIndex + 1}`,
          bindings,
          invalidSlotIds,
          availableSlotIds,
        );
      });
    });
  }

  const serializedBindings = Array.from(bindings.entries())
    .map(([slotId, targets]) => ({ slotId, targets: Array.from(targets) }))
    .sort((left, right) => left.slotId.localeCompare(right.slotId));

  return {
    status: resolveStatus(section, serializedBindings, invalidSlotIds),
    bindings: serializedBindings,
    invalidSlotIds: Array.from(invalidSlotIds).sort(),
    availableSlotIds: Array.from(availableSlotIds).sort(),
  };
}

function visitTextTarget(
  value: string | undefined,
  target: string,
  bindings: Map<string, Set<string>>,
  invalidSlotIds: Set<string>,
  availableSlotIds: Set<string>,
) {
  const matches = String(value || "").matchAll(/\{@([a-zA-Z0-9_]+)\}/g);
  for (const match of matches) {
    const slotId = match[1]?.trim();
    if (!slotId) {
      continue;
    }
    if (!availableSlotIds.has(slotId)) {
      invalidSlotIds.add(slotId);
      continue;
    }
    if (!bindings.has(slotId)) {
      bindings.set(slotId, new Set());
    }
    bindings.get(slotId)?.add(target);
  }
}

function resolveStatus(
  section: WorkbenchSection,
  bindings: OutlineBinding[],
  invalidSlotIds: Set<string>,
): OutlineSyncStatus {
  if (invalidSlotIds.size) {
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
