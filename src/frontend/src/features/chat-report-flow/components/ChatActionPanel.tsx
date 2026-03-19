import { useState } from "react";

import type {
  AskParamAction,
  ChatAction,
  DownloadDocumentAction,
  ReviewParamsAction,
  ShowTemplateCandidatesAction,
} from "../../../entities/chat/types";

type ChatActionPanelProps = {
  action: ChatAction;
  onSubmitParam: (paramId: string, value: string | string[]) => void;
  onSelectTemplate: (templateId: string) => void;
  onCommand: (command: "confirm_generation" | "reset_params" | "edit_param", targetParamId?: string) => void;
  disabled?: boolean;
};

export function ChatActionPanel({
  action,
  onSubmitParam,
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
  onCommand: (command: "confirm_generation" | "reset_params" | "edit_param", targetParamId?: string) => void;
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
          onClick={() => onCommand("confirm_generation")}
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
