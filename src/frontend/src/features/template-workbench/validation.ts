import type { TemplateWorkbenchState, WorkbenchSection } from "./state";
import { summarizeSectionOutlineBindings } from "./outlineBindings";

export function validateWorkbench(state: TemplateWorkbenchState): string[] {
  const errors: string[] = [];
  const paramIds = new Map<string, number>();
  const parametersById = new Map(state.parameters.map((parameter) => [parameter.id, parameter]));

  state.parameters.forEach((parameter) => {
    const id = parameter.id.trim();
    if (!id) {
      errors.push(`参数标识不能为空：${parameter.label || "未命名参数"}`);
      return;
    }
    paramIds.set(id, (paramIds.get(id) ?? 0) + 1);
    if (parameter.inputType === "enum" && !parameter.options.length) {
      errors.push(`固定选项参数至少需要一个候选项：${parameter.label || id}`);
    }
    if (parameter.inputType === "dynamic" && !parameter.source.trim()) {
      errors.push(`动态参数必须配置来源：${parameter.label || id}`);
    }
    if (parameter.inputType === "date" && parameter.multi) {
      errors.push(`日期参数不支持多值：${parameter.label || id}`);
    }
  });

  for (const [id, count] of paramIds.entries()) {
    if (count > 1) {
      errors.push(`参数标识不能重复：${id}`);
    }
  }

  state.sections.forEach((section) => validateSection(section, parametersById, errors, false));

  return [...new Set(errors)];
}

export function collectParameterReferences(state: TemplateWorkbenchState, parameterId: string): string[] {
  const references: string[] = [];
  const token = `{${parameterId}}`;

  function visit(section: WorkbenchSection, path: string[]) {
    const title = section.title || "未命名章节";
    const nextPath = [...path, title];
    const breadcrumb = nextPath.join(" / ");

    if (section.foreachEnabled && section.foreachParam === parameterId) {
      references.push(`${breadcrumb}（foreach）`);
    }

    if (containsToken(section.title, token) || containsToken(section.description, token)) {
      references.push(`${breadcrumb}（标题或说明）`);
    }

    if (section.outline) {
      if (containsToken(section.outline.document, token)) {
        references.push(`${breadcrumb}（诉求文稿）`);
      }
      if (section.outline.blocks.some((block) => block.paramId === parameterId)) {
        references.push(`${breadcrumb}（诉求要素）`);
      }
    }

    if (section.content) {
      const presentation = section.content.presentation;
      if (containsToken(presentation.template, token) || containsToken(presentation.anchor, token)) {
        references.push(`${breadcrumb}（展示方式）`);
      }
      section.content.datasets.forEach((dataset) => {
        if (
          containsToken(dataset.source.query, token) ||
          containsToken(dataset.source.description, token) ||
          containsToken(dataset.source.prompt, token) ||
          containsToken(dataset.source.knowledgeQueryTemplate, token)
        ) {
          references.push(`${breadcrumb}（数据集 ${dataset.id || "未命名"}）`);
        }
      });
    }

    section.children.forEach((child) => visit(child, nextPath));
  }

  state.sections.forEach((section) => visit(section, []));
  return [...new Set(references)];
}

function validateSection(
  section: WorkbenchSection,
  parametersById: Map<string, TemplateWorkbenchState["parameters"][number]>,
  errors: string[],
  ancestorForeach: boolean,
) {
  const sectionTitle = section.title || "未命名章节";
  validateOutline(section, sectionTitle, parametersById, errors);

  if (section.foreachEnabled) {
    if (ancestorForeach) {
      errors.push(`不支持嵌套 foreach：${sectionTitle}`);
    }
    const parameter = parametersById.get(section.foreachParam);
    if (!parameter) {
      errors.push(`foreach 来源参数不存在：${sectionTitle}`);
    } else if (!parameter.multi) {
      errors.push(`foreach 只能绑定多值参数：${sectionTitle}`);
    }
  }

  if (section.kind === "group") {
    section.children.forEach((child) => validateSection(child, parametersById, errors, ancestorForeach || section.foreachEnabled));
    return;
  }

  if (!section.content) {
    errors.push(`内容章节缺少内容定义：${sectionTitle}`);
    return;
  }

  validateContentSection(section, errors);
  section.children.forEach((child) => validateSection(child, parametersById, errors, ancestorForeach || section.foreachEnabled));
}

function validateOutline(
  section: WorkbenchSection,
  sectionTitle: string,
  parametersById: Map<string, TemplateWorkbenchState["parameters"][number]>,
  errors: string[],
) {
  if (!section.outline) {
    const summaryWithoutOutline = summarizeSectionOutlineBindings(section);
    summaryWithoutOutline.invalidBlockIds.forEach((blockId) => {
      errors.push(`执行链路引用了不存在的诉求要素：${sectionTitle} / ${blockId}`);
    });
    return;
  }

  const blockIds = new Map<string, number>();
  section.outline.blocks.forEach((block) => {
    const blockId = block.id.trim();
    if (!blockId) {
      errors.push(`诉求要素标识不能为空：${sectionTitle}`);
      return;
    }
    blockIds.set(blockId, (blockIds.get(blockId) ?? 0) + 1);
    if (block.type === "param_ref" && !parametersById.has(block.paramId.trim())) {
      errors.push(`诉求要素 param_ref 必须绑定已有参数：${sectionTitle} / ${blockId}`);
    }
    if (["indicator", "scope", "enum_select"].includes(block.type) && !block.options.length && !block.source.trim()) {
      errors.push(`诉求要素需要配置选项或来源：${sectionTitle} / ${blockId}`);
    }
  });

  for (const [blockId, count] of blockIds.entries()) {
    if (count > 1) {
      errors.push(`诉求要素标识不能重复：${sectionTitle} / ${blockId}`);
    }
  }

  const summary = summarizeSectionOutlineBindings(section);
  summary.invalidBlockIds.forEach((blockId) => {
    errors.push(`执行链路引用了不存在的诉求要素：${sectionTitle} / ${blockId}`);
  });
}

function validateContentSection(section: WorkbenchSection, errors: string[]) {
  if (!section.content) {
    return;
  }
  const sectionTitle = section.title || "未命名章节";
  const datasetsById = new Map<string, (typeof section.content.datasets)[number]>();

  section.content.datasets.forEach((dataset) => {
    const datasetId = dataset.id.trim();
    if (!datasetId) {
      errors.push(`数据集 ID 不能为空：${sectionTitle}`);
      return;
    }
    if (datasetsById.has(datasetId)) {
      errors.push(`数据集 ID 不能重复：${sectionTitle} / ${datasetId}`);
    }
    datasetsById.set(datasetId, dataset);
    dataset.dependsOn.forEach((dependency) => {
      if (dependency && dependency === datasetId) {
        errors.push(`数据集不能依赖自身：${sectionTitle} / ${datasetId}`);
      }
    });
  });

  section.content.datasets.forEach((dataset) => {
    dataset.dependsOn.forEach((dependency) => {
      if (dependency && !datasetsById.has(dependency)) {
        errors.push(`数据集依赖不存在：${sectionTitle} / ${dataset.id || "未命名"} -> ${dependency}`);
      }
    });
  });

  if (hasDatasetCycle(section.content.datasets)) {
    errors.push(`数据集依赖存在环：${sectionTitle}`);
  }

  const presentation = section.content.presentation;
  if (["value", "simple_table", "chart"].includes(presentation.type) && presentation.datasetId && !datasetsById.has(presentation.datasetId)) {
    errors.push(`展示方式引用了不存在的数据集：${sectionTitle} / ${presentation.datasetId}`);
  }
  if (presentation.type === "composite_table") {
    if (!presentation.sections.length) {
      errors.push(`复合表至少需要一个分区：${sectionTitle}`);
    }
    presentation.sections.forEach((item, index) => {
      if (!item.layout.type) {
        errors.push(`复合表分区缺少布局类型：${sectionTitle} / 分区 ${index + 1}`);
      }
      if (item.datasetId && !datasetsById.has(item.datasetId)) {
        errors.push(`复合表分区引用了不存在的数据集：${sectionTitle} / ${item.datasetId}`);
      }
      if (item.layout.type === "kv_grid" && !item.layout.fields.length) {
        errors.push(`KV 分区至少需要一个字段：${sectionTitle} / ${item.id || `分区 ${index + 1}`}`);
      }
      if (item.layout.type === "tabular" && !item.layout.columns.length) {
        errors.push(`表格分区至少需要一列：${sectionTitle} / ${item.id || `分区 ${index + 1}`}`);
      }
    });
  }
}

function hasDatasetCycle(datasets: Array<{ id: string; dependsOn: string[] }>) {
  const graph = new Map<string, string[]>();
  datasets.forEach((dataset) => {
    if (dataset.id.trim()) {
      graph.set(dataset.id.trim(), dataset.dependsOn.filter(Boolean));
    }
  });

  const visiting = new Set<string>();
  const visited = new Set<string>();

  function visit(node: string): boolean {
    if (visited.has(node)) {
      return false;
    }
    if (visiting.has(node)) {
      return true;
    }
    visiting.add(node);
    const dependencies = graph.get(node) ?? [];
    for (const dependency of dependencies) {
      if (graph.has(dependency) && visit(dependency)) {
        return true;
      }
    }
    visiting.delete(node);
    visited.add(node);
    return false;
  }

  for (const node of graph.keys()) {
    if (visit(node)) {
      return true;
    }
  }
  return false;
}

function containsToken(value: string | undefined, token: string) {
  return Boolean(value && value.includes(token));
}
