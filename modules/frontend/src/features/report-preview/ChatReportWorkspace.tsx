import { useEffect, useMemo, useState } from "react";
import { PptEditor, ReportEditor } from "@cloudsop/bi-designer";
import type { EditorStoreApi } from "@cloudsop/bi-designer";
import { Download, ExternalLink, Eye, Info, PanelRightClose, Pencil, RotateCcw } from "lucide-react";
import { Link } from "react-router-dom";

import type { ChatStreamDelta, TemplateInstance } from "../../entities/chat/types";
import { resolveReportStructureType } from "./report-dsl";
import { ReportDslPreview } from "./ReportDslPreview";
import { createReportWorkspace, useEditorDocument } from "./report-workspace";

type WorkspaceTab = "preview" | "edit" | "details";

type ChatReportWorkspaceProps = {
  report: Record<string, unknown>;
  reportId?: string;
  templateInstance: TemplateInstance | null;
  deltas: ChatStreamDelta[];
  status: string;
  editable: boolean;
  mock?: boolean;
  onClose: () => void;
  onDirtyChange: (dirty: boolean) => void;
};

export function ChatReportWorkspace({ report, reportId, templateInstance, deltas, status, editable, mock = false, onClose, onDirtyChange }: ChatReportWorkspaceProps) {
  const [tab, setTab] = useState<WorkspaceTab>("preview");
  const workspace = useMemo(() => createReportWorkspace(report), [report]);
  const { original, store } = workspace;
  const workspaceReport = useEditorDocument(store);
  const structureType = resolveReportStructureType(workspaceReport);
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    setTab("preview");
  }, [reportId]);

  useEffect(() => {
    setIsDirty(false);
    onDirtyChange(false);
    return store.subscribe(() => {
      const nextDirty = store.getState().isDirty;
      setIsDirty(nextDirty);
      onDirtyChange(nextDirty);
    });
  }, [onDirtyChange, store]);

  return (
    <aside className="chat-report-workspace" aria-label="报告预览编辑区">
      <div className="chat-report-workspace__header">
        <div>
          <strong>{readReportName(report)}</strong>
          <span>{status === "running" ? "正在生成报告..." : isDirty ? "有未导出的本地修改" : mock ? "本地演示报告" : "报告已生成"}</span>
        </div>
        <button className="icon-button" type="button" title="收起报告区" aria-label="收起报告区" onClick={onClose}><PanelRightClose size={17} /></button>
      </div>

      <div className="chat-report-workspace__tabs" role="tablist" aria-label="报告工作区">
        <WorkspaceTabButton active={tab === "preview"} icon={<Eye size={15} />} onClick={() => setTab("preview")}>预览</WorkspaceTabButton>
        <WorkspaceTabButton active={tab === "edit"} icon={<Pencil size={15} />} disabled={!editable} onClick={() => setTab("edit")}>编辑</WorkspaceTabButton>
        <WorkspaceTabButton active={tab === "details"} icon={<Info size={15} />} onClick={() => setTab("details")}>详情</WorkspaceTabButton>
        <div className="chat-report-workspace__tab-actions">
          <button className="icon-button" type="button" title="下载 DSL JSON" aria-label="下载 DSL JSON" onClick={() => downloadDsl(store, reportId || "report-demo")}><Download size={16} /></button>
          {editable ? <button className="icon-button" type="button" title="重置本地修改" aria-label="重置本地修改" disabled={!isDirty} onClick={() => store.getState().setDoc(original)}><RotateCcw size={16} /></button> : null}
          {reportId && !mock ? <Link className="icon-button" title="全屏打开设计器" aria-label="全屏打开设计器" to={`/reports/${reportId}/designer`}><ExternalLink size={16} /></Link> : null}
        </div>
      </div>

      <div className="chat-report-workspace__body">
        {tab === "preview" ? <ReportDslPreview store={store} /> : null}
        {tab === "edit" && editable ? (
          structureType === "paged"
            ? <PptEditor store={store} locale="zh-CN" theme="light" />
            : <ReportEditor store={store} locale="zh-CN" theme="light" />
        ) : null}
        {tab === "details" ? (
          <div className="chat-report-details">
            <details open>
              <summary>报告结构</summary>
              <pre>{JSON.stringify(workspaceReport, null, 2)}</pre>
            </details>
            {templateInstance ? <details>
              <summary>模板实例</summary>
              <pre>{JSON.stringify(templateInstance, null, 2)}</pre>
            </details> : null}
            <details>
              <summary>增量事件 ({deltas.length})</summary>
              <pre>{JSON.stringify(deltas, null, 2)}</pre>
            </details>
          </div>
        ) : null}
      </div>
    </aside>
  );
}

function WorkspaceTabButton({ active, disabled, icon, children, onClick }: { active: boolean; disabled?: boolean; icon: React.ReactNode; children: React.ReactNode; onClick: () => void }) {
  return <button className={`chat-report-tab${active ? " is-active" : ""}`} type="button" role="tab" aria-selected={active} disabled={disabled} onClick={onClick}>{icon}<span>{children}</span></button>;
}

function readReportName(report: Record<string, unknown>) {
  const basicInfo = report.basicInfo as Record<string, unknown> | undefined;
  return String(basicInfo?.name ?? basicInfo?.title ?? basicInfo?.id ?? "报告预览");
}

function downloadDsl(store: EditorStoreApi, reportId: string) {
  const blob = new Blob([`${JSON.stringify(store.getState().getDoc(), null, 2)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${reportId}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}
