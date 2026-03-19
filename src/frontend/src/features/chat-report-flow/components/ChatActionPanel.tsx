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

type ChatCommand =
  | "prepare_outline_review"
  | "reset_params"
  | "edit_param";

type OutlineCommand = "edit_outline" | "confirm_outline_generation";

type ChatActionPanelProps = {
  action: ChatAction;
  onSubmitParam: (paramId: string, value: string | string[]) => void;
  onSubmitOutline: (command: OutlineCommand, outline: OutlineNode[]) => void;
  onSelectTemplate: (templateId: string) => void;
  onCommand: (command: ChatCommand, targetParamId?: string) => void;
  disabled?: boolean;
};

type OutlineRow = {
  node_id: string;
  title: string;
  description: string;
  level: number;
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
  const [rows, setRows] = useState<OutlineRow[]>(() => flattenOutline(action.outline));

  useEffect(() => {
    setRows(flattenOutline(action.outline));
  }, [action]);

  const currentOutline = buildOutlineTree(rows);

  const updateRow = (nodeId: string, patch: Partial<OutlineRow>) => {
    setRows((current) => current.map((row) => (row.node_id === nodeId ? { ...row, ...patch } : row)));
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
      <div className="outline-editor" role="tree">
        {rows.map((row, index) => (
          <div key={row.node_id} className="outline-editor__row" style={{ paddingInlineStart: `${(row.level - 1) * 18}px` }}>
            <div className="outline-editor__fields">
              <label className="field">
                <span className="field-label">章节标题</span>
                <input
                  aria-label={`章节标题 ${row.node_id}`}
                  type="text"
                  value={row.title}
                  disabled={disabled}
                  onChange={(event) => updateRow(row.node_id, { title: event.target.value })}
                />
              </label>
              <label className="field">
                <span className="field-label">章节说明</span>
                <input
                  aria-label={`章节说明 ${row.node_id}`}
                  type="text"
                  value={row.description}
                  disabled={disabled}
                  onChange={(event) => updateRow(row.node_id, { description: event.target.value })}
                />
              </label>
            </div>
            <div className="outline-editor__actions">
              <button type="button" className="ghost-button" disabled={disabled} onClick={() => setRows((current) => addSibling(current, row.node_id))}>
                新增同级
              </button>
              <button type="button" className="ghost-button" disabled={disabled} onClick={() => setRows((current) => addChild(current, row.node_id))}>
                新增子章节
              </button>
              <button type="button" className="ghost-button" disabled={disabled || index === 0} onClick={() => setRows((current) => moveBlock(current, row.node_id, "up"))}>
                上移
              </button>
              <button type="button" className="ghost-button" disabled={disabled || index === rows.length - 1} onClick={() => setRows((current) => moveBlock(current, row.node_id, "down"))}>
                下移
              </button>
              <button type="button" className="ghost-button" disabled={disabled || row.level <= 1} onClick={() => setRows((current) => shiftLevel(current, row.node_id, -1))}>
                提升层级
              </button>
              <button type="button" className="ghost-button" disabled={disabled || index === 0} onClick={() => setRows((current) => shiftLevel(current, row.node_id, 1))}>
                降低层级
              </button>
              <button type="button" className="ghost-button" disabled={disabled || rows.length <= 1} onClick={() => setRows((current) => removeBlock(current, row.node_id))}>
                删除
              </button>
            </div>
          </div>
        ))}
      </div>
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

function flattenOutline(nodes: OutlineNode[]): OutlineRow[] {
  const rows: OutlineRow[] = [];
  const visit = (items: OutlineNode[]) => {
    items.forEach((item) => {
      rows.push({
        node_id: item.node_id,
        title: item.title,
        description: item.description,
        level: item.level,
      });
      visit(item.children ?? []);
    });
  };
  visit(nodes);
  return rows;
}

function buildOutlineTree(rows: OutlineRow[]): OutlineNode[] {
  const roots: OutlineNode[] = [];
  const stack: OutlineNode[] = [];
  rows.forEach((row) => {
    const node: OutlineNode = {
      node_id: row.node_id,
      title: row.title,
      description: row.description,
      level: row.level,
      children: [],
    };
    while (stack.length && stack[stack.length - 1].level >= row.level) {
      stack.pop();
    }
    if (stack.length) {
      stack[stack.length - 1].children.push(node);
    } else {
      roots.push(node);
    }
    stack.push(node);
  });
  return roots;
}

function addSibling(rows: OutlineRow[], nodeId: string): OutlineRow[] {
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

function addChild(rows: OutlineRow[], nodeId: string): OutlineRow[] {
  const index = rows.findIndex((row) => row.node_id === nodeId);
  if (index < 0) {
    return rows;
  }
  const target = rows[index];
  const next = [...rows];
  next.splice(index + 1, 0, createRow(target.level + 1));
  return next;
}

function removeBlock(rows: OutlineRow[], nodeId: string): OutlineRow[] {
  const index = rows.findIndex((row) => row.node_id === nodeId);
  if (index < 0) {
    return rows;
  }
  const end = findSubtreeEnd(rows, index);
  return [...rows.slice(0, index), ...rows.slice(end)];
}

function moveBlock(rows: OutlineRow[], nodeId: string, direction: "up" | "down"): OutlineRow[] {
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

function shiftLevel(rows: OutlineRow[], nodeId: string, delta: -1 | 1): OutlineRow[] {
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

function findSubtreeEnd(rows: OutlineRow[], index: number) {
  const level = rows[index].level;
  let cursor = index + 1;
  while (cursor < rows.length && rows[cursor].level > level) {
    cursor += 1;
  }
  return cursor;
}

function findPreviousSiblingIndex(rows: OutlineRow[], index: number) {
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

function findNextSiblingIndex(rows: OutlineRow[], index: number) {
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

function createRow(level: number): OutlineRow {
  const nodeId = `node-${Math.random().toString(36).slice(2, 10)}`;
  return {
    node_id: nodeId,
    title: "新章节",
    description: "",
    level: Math.max(1, level),
  };
}
