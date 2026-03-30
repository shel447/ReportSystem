import { useEffect, useState } from "react";

import type {
  AskParamAction,
  ChatAction,
  DownloadDocumentAction,
  OutlineNode,
  ReviewOutlineAction,
  ReviewParamsAction,
  ShowTemplateCandidatesAction,
} from "../../../entities/chat/types";
import {
  buildCollapsedNodeIds,
  buildDisplayText,
  mapOutlineTree,
  normalizeOutlineTree,
  OutlineDraftNode,
  OutlineTree,
  parseDisplayText,
  serializeOutlineTree,
} from "./OutlineTree";

type ChatCommand =
  | "prepare_outline_review"
  | "reset_params"
  | "edit_param"
  | "confirm_task_switch"
  | "cancel_task_switch";

type OutlineCommand = "edit_outline" | "confirm_outline_generation";

type ChatActionPanelProps = {
  action: ChatAction;
  onSubmitParam: (paramId: string, value: string | string[]) => void;
  onSubmitOutline: (command: OutlineCommand, outline: OutlineNode[]) => void;
  onSelectTemplate: (templateId: string) => void;
  onCommand: (command: ChatCommand, targetParamId?: string) => void;
  disabled?: boolean;
};

type OutlineDraftRow = {
  node_id: string;
  title: string;
  description: string;
  display_text: string;
  level: number;
  ai_generated: boolean;
  node_kind: "group" | "structured_leaf" | "freeform_leaf";
  dynamic_meta?: Record<string, unknown>;
};

export function ChatActionPanel({
  action,
  onSubmitParam,
  onSubmitOutline,
  onSelectTemplate,
  onCommand,
  disabled = false,
}: ChatActionPanelProps) {
  if (action.type === "show_template_candidates") {
    return <CandidatePanel action={action} onSelectTemplate={onSelectTemplate} disabled={disabled} />;
  }
  if (action.type === "ask_param") {
    return <AskParamPanel action={action} onSubmitParam={onSubmitParam} disabled={disabled} />;
  }
  if (action.type === "review_params") {
    return <ReviewPanel action={action} onCommand={onCommand} disabled={disabled} />;
  }
  if (action.type === "review_outline") {
    return (
      <ReviewOutlinePanel
        action={action}
        onSubmitOutline={onSubmitOutline}
        onCommand={onCommand}
        disabled={disabled}
      />
    );
  }
  if (action.type === "download_document") {
    return <DownloadPanel action={action} />;
  }
  if (action.type === "confirm_task_switch") {
    return <ConfirmTaskSwitchPanel action={action} onCommand={onCommand} disabled={disabled} />;
  }
  return null;
}

function CandidatePanel({
  action,
  onSelectTemplate,
  disabled,
}: {
  action: ShowTemplateCandidatesAction;
  onSelectTemplate: (templateId: string) => void;
  disabled: boolean;
}) {
  const [selectedId, setSelectedId] = useState(action.selected_template_id ?? action.candidates[0]?.template_id ?? "");
  const selected = action.candidates.find((item) => item.template_id === selectedId) ?? action.candidates[0];

  return (
    <section className="action-card">
      <p className="section-kicker">候选模板</p>
      <label className="field">
        <span className="field-label">相关模板</span>
        <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)} disabled={disabled}>
          {action.candidates.map((item) => (
            <option key={item.template_id} value={item.template_id}>
              {item.template_name}
            </option>
          ))}
        </select>
      </label>
      {selected ? (
        <div className="inline-panel">
          <strong>{selected.template_name}</strong>
          <p>{[selected.template_type, selected.scenario, selected.description].filter(Boolean).join(" / ")}</p>
          <span className="inline-badge">{selected.score_label ?? "中相关"}</span>
          <div className="reason-list">
            {(selected.match_reasons ?? []).map((reason) => (
              <span key={reason}>{reason}</span>
            ))}
          </div>
        </div>
      ) : null}
      <div className="action-row">
        <button className="primary-button" type="button" onClick={() => onSelectTemplate(selectedId)} disabled={disabled}>
          使用此模板
        </button>
      </div>
    </section>
  );
}

function AskParamPanel({
  action,
  onSubmitParam,
  disabled,
}: {
  action: AskParamAction;
  onSubmitParam: (paramId: string, value: string | string[]) => void;
  disabled: boolean;
}) {
  const initialValue = action.selected_values?.[0] ?? "";
  const initialList = action.selected_values ?? [];
  const [value, setValue] = useState(initialValue);
  const [values, setValues] = useState<string[]>(initialList);
  const progress = action.progress ?? { collected: 0, required: 0 };

  const submit = () => {
    if (action.widget.kind === "multi_select") {
      onSubmitParam(action.param.id, values);
      return;
    }
    onSubmitParam(action.param.id, value);
  };

  return (
    <section className="action-card">
      <div className="card-heading">
        <div>
          <p className="section-kicker">补充参数</p>
          {action.template_name ? (
            <p className="template-hint">
              <span>已匹配模板：</span>
              <strong>{action.template_name}</strong>
            </p>
          ) : null}
        </div>
        <span className="inline-badge">
          {progress.collected}/{progress.required}
        </span>
      </div>
      <label className="field">
        <span className="field-label">{action.param.label}</span>
        {action.widget.kind === "date" ? (
          <input
            aria-label={action.param.label}
            type="date"
            value={value}
            disabled={disabled}
            onChange={(event) => setValue(event.target.value)}
          />
        ) : null}
        {action.widget.kind === "text" ? (
          <input
            aria-label={action.param.label}
            type="text"
            value={value}
            disabled={disabled}
            onChange={(event) => setValue(event.target.value)}
          />
        ) : null}
        {action.widget.kind === "single_select" ? (
          <select
            aria-label={action.param.label}
            value={value}
            disabled={disabled}
            onChange={(event) => setValue(event.target.value)}
          >
            <option value="">请选择</option>
            {(action.param.options ?? []).map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        ) : null}
        {action.widget.kind === "multi_select" ? (
          <div className="chip-grid" aria-label={action.param.label}>
            {(action.param.options ?? []).map((option) => {
              const checked = values.includes(option);
              return (
                <label key={option} className={`choice-chip${checked ? " active" : ""}`}>
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={disabled}
                    onChange={(event) => {
                      setValues((current) =>
                        event.target.checked ? [...current, option] : current.filter((item) => item !== option),
                      );
                    }}
                  />
                  <span>{option}</span>
                </label>
              );
            })}
          </div>
        ) : null}
      </label>
      <div className="action-row">
        <button className="primary-button" type="button" onClick={submit} disabled={disabled}>
          提交
        </button>
      </div>
    </section>
  );
}

function ReviewPanel({
  action,
  onCommand,
  disabled,
}: {
  action: ReviewParamsAction;
  onCommand: (command: ChatCommand, targetParamId?: string) => void;
  disabled: boolean;
}) {
  return (
    <section className="action-card">
      <p className="section-kicker">参数确认</p>
      {action.template_name ? (
        <p className="template-hint">
          <span>已匹配模板：</span>
          <strong>{action.template_name}</strong>
        </p>
      ) : null}
      <div className="review-list">
        {action.params.map((param) => (
          <div key={param.id} className="review-item">
            <div>
              <strong>{param.label}</strong>
              <p>{formatParamValue(param.value)}</p>
            </div>
            <button
              className="secondary-button"
              type="button"
              disabled={disabled}
              onClick={() => onCommand("edit_param", param.id)}
            >
              编辑
            </button>
          </div>
        ))}
      </div>
      <div className="action-row">
        <button className="secondary-button" type="button" disabled={disabled} onClick={() => onCommand("reset_params")}>
          重置参数
        </button>
        <button
          className="primary-button"
          type="button"
          disabled={disabled}
          onClick={() => onCommand("prepare_outline_review")}
        >
          确认参数并生成大纲
        </button>
      </div>
    </section>
  );
}

function ReviewOutlinePanel({
  action,
  onSubmitOutline,
  onCommand,
  disabled,
}: {
  action: ReviewOutlineAction;
  onSubmitOutline: (command: OutlineCommand, outline: OutlineNode[]) => void;
  onCommand: (command: ChatCommand, targetParamId?: string) => void;
  disabled: boolean;
}) {
  const [outlineTree, setOutlineTree] = useState<OutlineDraftNode[]>(() => normalizeOutlineTree(action.outline));
  const [collapsedNodeIds, setCollapsedNodeIds] = useState<Set<string>>(() => buildCollapsedNodeIds(action.outline));
  const [editingNodeId, setEditingNodeId] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [draftDisplayText, setDraftDisplayText] = useState("");

  useEffect(() => {
    setOutlineTree(normalizeOutlineTree(action.outline));
    setCollapsedNodeIds(buildCollapsedNodeIds(action.outline));
    setEditingNodeId(null);
    setSelectedNodeId(null);
    setDraftDisplayText("");
  }, [action]);

  const currentOutline = serializeOutlineTree(outlineTree);

  const updateTree = (updater: (rows: OutlineDraftRow[]) => OutlineDraftRow[]) => {
    setOutlineTree((current) => buildOutlineTree(updater(flattenOutlineTree(current))));
  };

  const commitInlineEdit = (nodeId: string) => {
    const { title, description } = parseDisplayText(draftDisplayText);
    setOutlineTree((current) =>
      mapOutlineTree(current, nodeId, (node) => ({
        ...node,
        title,
        description,
        display_text: buildDisplayText(title, description),
      })),
    );
    setEditingNodeId(null);
    setDraftDisplayText("");
  };

  const cancelInlineEdit = () => {
    setEditingNodeId(null);
    setDraftDisplayText("");
  };

  return (
    <section className="action-card">
      <div className="card-heading">
        <div>
          <p className="section-kicker">大纲确认</p>
          {action.template_name ? (
            <p className="template-hint">
              <span>已匹配模板：</span>
              <strong>{action.template_name}</strong>
            </p>
          ) : null}
        </div>
      </div>
      {action.params_snapshot.length ? (
        <div className="inline-panel">
          <strong>已确认参数</strong>
          <div className="reason-list">
            {action.params_snapshot.map((item) => (
              <span key={item.id}>
                {item.label}：{formatParamValue(item.value)}
              </span>
            ))}
          </div>
        </div>
      ) : null}
      {action.warnings.length ? (
        <div className="inline-panel">
          <strong>展开提示</strong>
          <div className="reason-list">
            {action.warnings.map((warning) => (
              <span key={warning}>{warning}</span>
            ))}
          </div>
        </div>
      ) : null}
      <OutlineTree
        mode="editable"
        nodes={outlineTree}
        collapsedNodeIds={collapsedNodeIds}
        editingNodeId={editingNodeId}
        selectedNodeId={selectedNodeId}
        draftDisplayText={draftDisplayText}
        disabled={disabled}
        onToggleCollapse={(nodeId) =>
          setCollapsedNodeIds((current) => {
            const next = new Set(current);
            if (next.has(nodeId)) {
              next.delete(nodeId);
            } else {
              next.add(nodeId);
            }
            return next;
          })
        }
        onSelectNode={setSelectedNodeId}
        onBeginEdit={(node) => {
          setSelectedNodeId(node.node_id);
          setEditingNodeId(node.node_id);
          setDraftDisplayText(node.display_text);
        }}
        onDraftChange={setDraftDisplayText}
        onCommitEdit={commitInlineEdit}
        onCancelEdit={cancelInlineEdit}
        onAddSibling={(nodeId) => updateTree((rows) => addSibling(rows, nodeId))}
        onAddChild={(nodeId) => {
          updateTree((rows) => addChild(rows, nodeId));
          setCollapsedNodeIds((current) => {
            const next = new Set(current);
            next.delete(nodeId);
            return next;
          });
        }}
        onMoveUp={(nodeId) => updateTree((rows) => moveBlock(rows, nodeId, "up"))}
        onMoveDown={(nodeId) => updateTree((rows) => moveBlock(rows, nodeId, "down"))}
        onPromote={(nodeId) => updateTree((rows) => shiftLevel(rows, nodeId, -1))}
        onDemote={(nodeId) => updateTree((rows) => shiftLevel(rows, nodeId, 1))}
        onDelete={(nodeId) => updateTree((rows) => removeBlock(rows, nodeId))}
      />
      <div className="action-row">
        <button className="secondary-button" type="button" disabled={disabled} onClick={() => onCommand("edit_param")}>
          返回改参数
        </button>
        <button
          className="secondary-button"
          type="button"
          disabled={disabled}
          onClick={() => onSubmitOutline("edit_outline", currentOutline)}
        >
          保存大纲
        </button>
        <button
          className="primary-button"
          type="button"
          disabled={disabled}
          onClick={() => onSubmitOutline("confirm_outline_generation", currentOutline)}
        >
          确认生成
        </button>
      </div>
    </section>
  );
}

function ConfirmTaskSwitchPanel({
  action,
  onCommand,
  disabled,
}: {
  action: Extract<ChatAction, { type: "confirm_task_switch" }>;
  onCommand: (command: ChatCommand, targetParamId?: string) => void;
  disabled: boolean;
}) {
  return (
    <section className="action-card">
      <p className="section-kicker">任务切换确认</p>
      <p>{action.reason}</p>
      <div className="reason-list">
        <span>{capabilityLabel(action.from_capability)}</span>
        <span>→</span>
        <span>{capabilityLabel(action.to_capability)}</span>
      </div>
      <div className="action-row">
        <button
          className="secondary-button"
          type="button"
          disabled={disabled}
          onClick={() => onCommand("cancel_task_switch")}
        >
          留在当前任务
        </button>
        <button
          className="primary-button"
          type="button"
          disabled={disabled}
          onClick={() => onCommand("confirm_task_switch")}
        >
          继续切换
        </button>
      </div>
    </section>
  );
}

function DownloadPanel({ action }: { action: DownloadDocumentAction }) {
  return (
    <section className="action-card">
      <p className="section-kicker">文档已生成</p>
      <strong>{action.document.file_name ?? "Markdown 文档"}</strong>
      {action.document.download_url ? (
        <div className="action-row">
          <a className="primary-button button-link" href={action.document.download_url}>
            下载 Markdown
          </a>
        </div>
      ) : null}
    </section>
  );
}

function formatParamValue(value: string | string[]) {
  return Array.isArray(value) ? value.join("、") : value;
}

function capabilityLabel(capability: "report_generation" | "smart_query" | "fault_diagnosis") {
  switch (capability) {
    case "report_generation":
      return "制作报告";
    case "smart_query":
      return "智能问数";
    case "fault_diagnosis":
      return "智能故障";
    default:
      return capability;
  }
}

function flattenOutlineTree(nodes: OutlineDraftNode[]): OutlineDraftRow[] {
  const rows: OutlineDraftRow[] = [];
  const visit = (items: OutlineDraftNode[]) => {
    items.forEach((item) => {
      rows.push({
        node_id: item.node_id,
        title: item.title,
        description: item.description,
        display_text: item.display_text ?? buildDisplayText(item.title, item.description),
        level: item.level,
        ai_generated: Boolean(item.ai_generated),
        node_kind: item.node_kind ?? (item.children?.length ? "group" : "freeform_leaf"),
        ...(item.dynamic_meta ? { dynamic_meta: item.dynamic_meta } : {}),
      });
      visit(item.children ?? []);
    });
  };
  visit(nodes);
  return rows;
}

function buildOutlineTree(rows: OutlineDraftRow[]): OutlineDraftNode[] {
  const roots: OutlineDraftNode[] = [];
  const stack: OutlineDraftNode[] = [];
  rows.forEach((row) => {
    const node: OutlineDraftNode = {
      node_id: row.node_id,
      title: row.title,
      description: row.description,
      display_text: row.display_text,
      level: row.level,
      children: [],
      ai_generated: row.ai_generated,
      node_kind: row.node_kind,
      ...(row.dynamic_meta ? { dynamic_meta: row.dynamic_meta } : {}),
    };
    while (stack.length && stack[stack.length - 1].level >= row.level) {
      stack.pop();
    }
    if (stack.length) {
      stack[stack.length - 1].children.push(node);
      stack[stack.length - 1].node_kind = "group";
      stack[stack.length - 1].ai_generated = false;
    } else {
      roots.push(node);
    }
    stack.push(node);
  });
  return normalizeOutlineTree(roots);
}

function addSibling(rows: OutlineDraftRow[], nodeId: string): OutlineDraftRow[] {
  const index = rows.findIndex((row) => row.node_id === nodeId);
  if (index < 0) {
    return rows;
  }
  const insertAt = findSubtreeEnd(rows, index);
  const target = rows[index];
  const next = [...rows];
  next.splice(insertAt, 0, createRow(target.level));
  return next;
}

function addChild(rows: OutlineDraftRow[], nodeId: string): OutlineDraftRow[] {
  const index = rows.findIndex((row) => row.node_id === nodeId);
  if (index < 0) {
    return rows;
  }
  const target = rows[index];
  const next = [...rows];
  next.splice(index + 1, 0, createRow(target.level + 1));
  return next;
}

function removeBlock(rows: OutlineDraftRow[], nodeId: string): OutlineDraftRow[] {
  const index = rows.findIndex((row) => row.node_id === nodeId);
  if (index < 0) {
    return rows;
  }
  const end = findSubtreeEnd(rows, index);
  return [...rows.slice(0, index), ...rows.slice(end)];
}

function moveBlock(rows: OutlineDraftRow[], nodeId: string, direction: "up" | "down"): OutlineDraftRow[] {
  const index = rows.findIndex((row) => row.node_id === nodeId);
  if (index < 0) {
    return rows;
  }
  const end = findSubtreeEnd(rows, index);
  const block = rows.slice(index, end);
  if (direction === "up") {
    const previous = findPreviousSiblingIndex(rows, index);
    if (previous < 0) {
      return rows;
    }
    return [...rows.slice(0, previous), ...block, ...rows.slice(previous, index), ...rows.slice(end)];
  }
  const nextSibling = findNextSiblingIndex(rows, index);
  if (nextSibling < 0) {
    return rows;
  }
  const nextEnd = findSubtreeEnd(rows, nextSibling);
  return [...rows.slice(0, index), ...rows.slice(end, nextEnd), ...block, ...rows.slice(nextEnd)];
}

function shiftLevel(rows: OutlineDraftRow[], nodeId: string, delta: -1 | 1): OutlineDraftRow[] {
  const index = rows.findIndex((row) => row.node_id === nodeId);
  if (index < 0) {
    return rows;
  }
  if (delta === 1 && index === 0) {
    return rows;
  }
  const end = findSubtreeEnd(rows, index);
  const next = [...rows];
  const maxLevel = delta === 1 ? Math.max(1, next[index - 1].level + 1) : undefined;
  for (let cursor = index; cursor < end; cursor += 1) {
    if (delta === -1) {
      next[cursor] = { ...next[cursor], level: Math.max(1, next[cursor].level - 1) };
    } else {
      const proposed = next[cursor].level + 1;
      next[cursor] = { ...next[cursor], level: Math.min(proposed, maxLevel ?? proposed) };
    }
  }
  return next;
}

function findSubtreeEnd(rows: OutlineDraftRow[], index: number) {
  const level = rows[index].level;
  let cursor = index + 1;
  while (cursor < rows.length && rows[cursor].level > level) {
    cursor += 1;
  }
  return cursor;
}

function findPreviousSiblingIndex(rows: OutlineDraftRow[], index: number) {
  const level = rows[index].level;
  for (let cursor = index - 1; cursor >= 0; cursor -= 1) {
    if (rows[cursor].level === level) {
      return cursor;
    }
    if (rows[cursor].level < level) {
      return -1;
    }
  }
  return -1;
}

function findNextSiblingIndex(rows: OutlineDraftRow[], index: number) {
  const level = rows[index].level;
  const end = findSubtreeEnd(rows, index);
  for (let cursor = end; cursor < rows.length; cursor += 1) {
    if (rows[cursor].level === level) {
      return cursor;
    }
    if (rows[cursor].level < level) {
      return -1;
    }
  }
  return -1;
}

function createRow(level: number): OutlineDraftRow {
  const nodeId = `node-${Math.random().toString(36).slice(2, 10)}`;
  const title = "新章节";
  return {
    node_id: nodeId,
    title,
    description: "",
    display_text: title,
    level: Math.max(1, level),
    ai_generated: false,
    node_kind: "freeform_leaf",
  };
}
