import { useMemo } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { fetchConversation, fetchConversations } from "../entities/chat/api";
import type { ChatResponse, ConversationDetail } from "../entities/chat/types";
import { EmptyState } from "../shared/ui/EmptyState";
import { PageSection } from "../shared/ui/PageSection";
import { SurfaceCard } from "../shared/ui/SurfaceCard";

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
      <PageSection description="报告中心不依赖独立实例接口，而是从对话沉淀中聚合最近生成的正式报告。">
        {recentReports.length ? (
          <div className="template-catalog-grid">
            {recentReports.map((report) => (
              <Link key={report.reportId} className="template-card" to={`/reports/${report.reportId}`}>
                <div className="template-card__header">
                  <strong>{report.reportName}</strong>
                  <span className="status-chip status-chip--soft">{report.status}</span>
                </div>
                <p>来源会话：{report.conversationTitle || report.conversationId}</p>
                <div className="template-card__meta">
                  <span>{report.reportId}</span>
                  <span>{report.createdAt ? formatDateTime(report.createdAt) : "未记录时间"}</span>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <SurfaceCard>
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
          </SurfaceCard>
        )}
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

  for (const message of [...conversation.messages].reverse()) {
    const response = readChatResponse(message.content);
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
      createdAt: message.createdAt ?? undefined,
    });
  }

  return items;
}

function readChatResponse(content: Record<string, unknown>): ChatResponse | null {
  const value = content.response;
  if (!value || typeof value !== "object") {
    return null;
  }
  return value as ChatResponse;
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", { hour12: false });
}
