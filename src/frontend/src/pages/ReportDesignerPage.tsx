import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { PptEditor, ReportEditor } from "@cloudsop/bi-designer";
import type { EditorStoreApi } from "@cloudsop/bi-designer";

import { fetchReport } from "../entities/reports/api";
import { resolveReportStructureType } from "../features/report-preview/report-dsl";
import { createReportWorkspace, useEditorDocument } from "../features/report-preview/report-workspace";
import { EmptyState } from "../shared/ui/EmptyState";

export function ReportDesignerPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const reportQuery = useQuery({
    queryKey: ["report", reportId],
    queryFn: () => fetchReport(reportId!),
    enabled: Boolean(reportId),
  });

  if (!reportQuery.data) {
    return <EmptyState title="设计器加载中" description="正在读取正式 Report DSL。" />;
  }

  return <ReportDesignerWorkspace reportId={reportQuery.data.reportId} report={reportQuery.data.answer.report} />;
}

function ReportDesignerWorkspace({ reportId, report }: { reportId: string; report: Record<string, unknown> }) {
  const workspace = useMemo(() => createReportWorkspace(report), [report]);
  const { original, store } = workspace;
  const workspaceReport = useEditorDocument(store);
  const structureType = resolveReportStructureType(workspaceReport);
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => store.subscribe(() => setIsDirty(store.getState().isDirty)), [store]);
  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!isDirty) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isDirty]);

  if (!structureType) {
    return <EmptyState title="无法打开设计器" description="报告缺少可识别的 structureType 或 basicInfo.reportType。" />;
  }

  return (
    <div className="report-designer-page">
      <div className="report-designer-toolbar">
        <div>
          <strong>本地设计器</strong>
          <span>{isDirty ? "有未导出的本地修改" : "当前 DSL 未修改"}</span>
        </div>
        <div className="action-row action-row--compact">
          <Link className="ghost-button button-link" to={`/reports/${reportId}`} onClick={(event) => {
            if (isDirty && !window.confirm("存在未导出的本地修改，确定返回报告详情吗？")) {
              event.preventDefault();
            }
          }}>返回详情</Link>
          <button className="ghost-button" type="button" disabled={!isDirty} onClick={() => store.getState().setDoc(original)}>重置</button>
          <button className="primary-button" type="button" onClick={() => downloadDsl(store, reportId)}>下载 DSL JSON</button>
        </div>
      </div>
      <div className="report-designer-canvas">
        {structureType === "paged"
          ? <PptEditor store={store} locale="zh-CN" theme="light" />
          : <ReportEditor store={store} locale="zh-CN" theme="light" />}
      </div>
    </div>
  );
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
