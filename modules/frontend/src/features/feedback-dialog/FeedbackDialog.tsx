import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { submitFeedback } from "../../entities/feedback/api";

type FeedbackDialogProps = {
  open: boolean;
  onClose: () => void;
};

export function FeedbackDialog({ open, onClose }: FeedbackDialogProps) {
  const [submitter, setSubmitter] = useState("");
  const [content, setContent] = useState("");
  const [priority, setPriority] = useState("medium");
  const [errorMessage, setErrorMessage] = useState("");

  const mutation = useMutation({
    mutationFn: submitFeedback,
    onSuccess: () => {
      setErrorMessage("");
      setSubmitter("");
      setContent("");
      setPriority("medium");
      onClose();
    },
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : "意见提交失败。");
    },
  });

  if (!open) {
    return null;
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="feedback-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="list-header">
          <div>
            <p className="section-kicker">Feedback</p>
            <h3 id="feedback-title">提交意见</h3>
          </div>
          <button className="ghost-button ghost-button--inline" type="button" onClick={onClose}>
            关闭
          </button>
        </div>

        <div className="form-grid">
          <label className="field">
            <span className="field-label">提交人</span>
            <input value={submitter} onChange={(event) => setSubmitter(event.target.value)} />
          </label>
          <label className="field">
            <span className="field-label">优先级</span>
            <select value={priority} onChange={(event) => setPriority(event.target.value)}>
              <option value="high">高</option>
              <option value="medium">中</option>
              <option value="low">低</option>
            </select>
          </label>
          <label className="field field--full">
            <span className="field-label">问题描述</span>
            <textarea rows={6} value={content} onChange={(event) => setContent(event.target.value)} />
          </label>
        </div>

        {errorMessage ? <p className="error-text">{errorMessage}</p> : null}

        <div className="action-row">
          <button
            className="primary-button"
            type="button"
            disabled={!content.trim() || mutation.isPending}
            onClick={() =>
              mutation.mutate({
                submitter,
                content,
                priority,
                images: [],
              })
            }
          >
            {mutation.isPending ? "提交中..." : "提交反馈"}
          </button>
        </div>
      </div>
    </div>
  );
}
