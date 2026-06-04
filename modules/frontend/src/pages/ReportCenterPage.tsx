import { useMemo } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { fetchConversation, fetchConversations } from "../entities/chat/api";
import type { ChatResponse, ConversationAnswer, ConversationDetail, ConversationRecord } from "../entities/chat/types";
import { EmptyState } from "../shared/ui/EmptyState";
import { ListPageLayout } from "../shared/layouts/ListPageLayout";
import { PageIntroBar } from "../shared/layouts/PageIntroBar";
import { PageSection } from "../shared/ui/PageSection";

export function ReportCenterPage() {
  const conversationsQuery = useQuery({
    queryKey: ["conversations"],
    queryFn: fetchConversations,
  });

  const recentConversationIds = useMemo(
    () => (conversationsQuery.data ?? []).slice(0, 8).map((item) => item.conversationId),
    [conversationsQuery.data],
  );

  const conversationQueries = useQueries({
    queries: recentConversationIds.map((conversationId) => ({
      queryKey: ["conversation", conversationId],
      queryFn: () => fetchConversation(conversationId),
      enabled: Boolean(conversationId),
    })),
  });

  const recentReports = useMemo(() => {
    const items: Array<{
      reportId: string;
      reportName: string;
      status: string;
      conversationId: string;
      conversationTitle: string;
      createdAt?: string;
    }> = [];
    const seen = new Set<string>();
    for (let index = 0; index < conversationQueries.length; index += 1) {
      const conversation = conversationQueries[index].data;
      if (!conversation) {
        continue;
      }
      const reports = extractReportsFromConversation(conversation);
      for (const report of reports) {
        if (seen.has(report.reportId)) {
          continue;
        }
        seen.add(report.reportId);
        items.push(report);
      }
    }
    return items;
  }, [conversationQueries]);

  return (
    <div className="reports-page">
      <PageSection>
        <ListPageLayout
          intro={<PageIntroBar title="报告中心" badge={`${recentReports.length} 份报告`} actions={<Link className="primary-button button-link" to="/chat">生成报告</Link>} />}
          content={recentReports.length ? (
          <div className="asset-list">
            {recentReports.map((report) => (
              <Link key={report.reportId} className="asset-list__row" to={`/reports/${report.reportId}`}>
                <div className="asset-list__main">
                  <strong>{report.reportName}</strong>
                  <p>来源会话：{report.conversationTitle || report.conversationId}</p>
                </div>
                <div className="asset-list__meta">
                  <span className="status-chip status-chip--soft">{report.status}</span>
                  <span>{report.createdAt ? formatDateTime(report.createdAt) : "未记录时间"}</span>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="empty-state-panel">
            <EmptyState
              title={conversationsQuery.isLoading ? "正在聚合报告" : "报告中心"}
              description="当前没有已生成的报告。通过对话生成后，这里会自动展示最近的报告。"
            />
            <div className="action-row action-row--compact">
              <Link className="primary-button button-link" to="/chat">
                前往对话助手
              </Link>
              <Link className="ghost-button button-link" to="/templates">
                查看模板
              </Link>
            </div>
          </div>
        )}
        />
      </PageSection>
    </div>
  );
}

function extractReportsFromConversation(conversation: ConversationDetail) {
  const items: Array<{
    reportId: string;
    reportName: string;
    status: string;
    conversationId: string;
    conversationTitle: string;
    createdAt?: string;
  }> = [];

  for (const record of [...conversation.records].reverse()) {
    const response = readReportResponse(record);
    if (!response || response.answer?.answerType !== "REPORT") {
      continue;
    }
    const payload = response.answer.answer;
    const basicInfo = (payload.report.basicInfo ?? {}) as Record<string, unknown>;
    items.push({
      reportId: payload.reportId,
      reportName: String(basicInfo.name ?? payload.reportId),
      status: payload.status,
      conversationId: conversation.conversationId,
      conversationTitle: conversation.title ?? conversation.conversationId,
      createdAt: normalizeRecordTime(record.askTime),
    });
  }

  return items;
}

function readReportResponse(record: ConversationRecord): ChatResponse | null {
  for (const answer of [...record.answers].reverse()) {
    const response = readPiuResponse(record, answer);
    if (response?.answer?.answerType === "REPORT") {
      return response;
    }
  }
  return null;
}

function readPiuResponse(record: ConversationRecord, answer: ConversationAnswer): ChatResponse | null {
  if (answer.type !== "PIU") {
    return null;
  }
  try {
    const parsed = JSON.parse(answer.content);
    const answers = parsed?.answers;
    if (!answers || typeof answers !== "object") {
      return null;
    }
    return {
      conversationId: "",
      chatId: record.chatId,
      status: answers.answer ? "finished" : "running",
      steps: Array.isArray(answers.steps) ? answers.steps : [],
      ask: answers.ask ?? null,
      answer: answers.answer ?? null,
      errors: Array.isArray(answers.errors) ? answers.errors : [],
      timestamp: typeof answer.answerTime === "number" ? answer.answerTime : Date.now(),
      apiVersion: "v1",
    };
  } catch {
    return null;
  }
}

function normalizeRecordTime(value: string | number | null | undefined): string | undefined {
  if (value === null || value === undefined || value === "") {
    return undefined;
  }
  if (typeof value === "number") {
    return new Date(value).toISOString();
  }
  return value;
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", { hour12: false });
}
