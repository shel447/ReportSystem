import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { fetchReport, generateReportDocuments } from "../entities/reports/api";
import type { DocumentGenerationResponse } from "../entities/reports/types";
import { DetailPageLayout } from "../shared/layouts/DetailPageLayout";
import { PageIntroBar } from "../shared/layouts/PageIntroBar";
import { EmptyState } from "../shared/ui/EmptyState";
import { PageSection } from "../shared/ui/PageSection";
import { SurfaceCard } from "../shared/ui/SurfaceCard";
import { prettyJson } from "../shared/utils/format";

const EXPORT_FORMATS = ["word", "ppt", "pdf"] as const;
type ExportFormat = (typeof EXPORT_FORMATS)[number];

export function ReportDetailPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const queryClient = useQueryClient();
  const [selectedFormats, setSelectedFormats] = useState<ExportFormat[]>(["word", "ppt", "pdf"]);
  const [pdfSource, setPdfSource] = useState<"word" | "ppt">("word");

  const reportQuery = useQuery({
    queryKey: ["report", reportId],
    queryFn: () => fetchReport(reportId!),
    enabled: Boolean(reportId),
  });

  const documentMutation = useMutation({
    mutationFn: () =>
      generateReportDocuments(reportId!, {
        formats: selectedFormats,
        pdfSource,
        theme: "default",
        strictValidation: true,
        regenerateIfExists: false,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["report", reportId] });
    },
  });

  const report = reportQuery.data;
  const basicInfo = useMemo(
    () => (((report?.answer.report.basicInfo as Record<string, unknown> | undefined) ?? {}) as Record<string, unknown>),
    [report],
  );
  const mutationResult = documentMutation.data as DocumentGenerationResponse | undefined;

  return (
    <div className="report-detail-page">
      <PageSection description="报告详情页按正式 Report DSL、TemplateInstance 和导出产物三层聚合展示。">
        {!report ? (
          <EmptyState title="报告加载中" description="正在获取报告详情。" />
        ) : (
          <DetailPageLayout
            intro={(
              <PageIntroBar
                eyebrow="Reports"
                description={String(basicInfo.name ?? report.reportId)}
                badge={report.status}
                actions={(
                  <>
                    <Link className="ghost-button button-link" to="/reports">
                      返回报告中心
                    </Link>
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => documentMutation.mutate()}
                      disabled={!selectedFormats.length || documentMutation.isPending}
                    >
                      {documentMutation.isPending ? "生成中..." : "生成文档"}
                    </button>
                  </>
                )}
              />
            )}
            summary={(
              <SurfaceCard className="summary-strip">
                <div className="summary-strip__item">
                  <span>报告 ID</span>
                  <strong>{report.reportId}</strong>
                </div>
                <div className="summary-strip__item">
                  <span>状态</span>
                  <strong>{report.status}</strong>
                </div>
                <div className="summary-strip__item">
                  <span>模板实例</span>
                  <strong>{report.answer.templateInstance.id}</strong>
                </div>
                <div className="summary-strip__item">
                  <span>章节完成度</span>
                  <strong>
                    {report.answer.generationProgress.completedSections}/{report.answer.generationProgress.totalSections}
                  </strong>
                </div>
              </SurfaceCard>
            )}
            content={(
              <div className="template-detail-grid">
                <SurfaceCard>
                  <div className="list-header">
                    <div>
                      <p className="section-kicker">Documents</p>
                      <h3>文档导出</h3>
                    </div>
                  </div>
                  <div className="stack-list">
                    <div className="template-inline-group">
                      <div className="template-inline-group__header">
                        <strong>导出格式</strong>
                        <span>Java Office Exporter</span>
                      </div>
                      <div className="action-row action-row--compact">
                        {EXPORT_FORMATS.map((format) => {
                          const active = selectedFormats.includes(format);
                          return (
                            <button
                              key={format}
                              type="button"
                              className={active ? "primary-button" : "ghost-button ghost-button--inline"}
                              onClick={() => setSelectedFormats((current) => toggleFormat(current, format))}
                            >
                              {format}
                            </button>
                          );
                        })}
                      </div>
                      {selectedFormats.includes("pdf") ? (
                        <label className="field">
                          <span className="field-label">PDF 来源</span>
                          <select value={pdfSource} onChange={(event) => setPdfSource(event.target.value as "word" | "ppt")}>
                            <option value="word">word</option>
                            <option value="ppt">ppt</option>
                          </select>
                        </label>
                      ) : null}
                    </div>

                    {mutationResult?.jobs?.length ? (
                      <div className="template-inline-group">
                        <div className="template-inline-group__header">
                          <strong>最近任务</strong>
                          <span>{mutationResult.jobs.length} 个</span>
                        </div>
                        {mutationResult.jobs.map((job) => (
                          <div key={job.jobId} className="template-inline-row template-inline-row--wide">
                            <strong>{job.format}</strong>
                            <span>{job.status}</span>
                            <span>{job.dependsOn ?? "无依赖"}</span>
                          </div>
                        ))}
                      </div>
                    ) : null}

                    {report.answer.documents.length ? (
                      <div className="template-inline-group">
                        <div className="template-inline-group__header">
                          <strong>可下载产物</strong>
                          <span>{report.answer.documents.length} 个</span>
                        </div>
                        {report.answer.documents.map((item) => (
                          <div key={item.id} className="template-inline-row template-inline-row--wide">
                            <strong>{item.fileName}</strong>
                            <span>{item.format}</span>
                            <span>{item.status}</span>
                            <a className="secondary-button button-link" href={item.downloadUrl}>
                              下载
                            </a>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <EmptyState title="暂无文档" description="选择导出格式后，点击“生成文档”即可获取 Word/PPT/PDF 产物。" />
                    )}
                  </div>
                </SurfaceCard>

                <SurfaceCard>
                  <div className="list-header">
                    <div>
                      <p className="section-kicker">Report DSL</p>
                      <h3>正式报告内容</h3>
                    </div>
                  </div>
                  <div className="stack-list">
                    <div className="template-inline-group">
                      <div className="template-inline-group__header">
                        <strong>基础信息</strong>
                        <span>{String(basicInfo.category ?? "")}</span>
                      </div>
                      <p>{String(basicInfo.description ?? "暂无描述")}</p>
                    </div>
                    {readCatalogs(report.answer.report).map((catalog) => (
                      <div key={catalog.id} className="template-editor-subcard">
                        <div className="template-inline-group__header">
                          <strong>{catalog.name}</strong>
                          <span>{catalog.sections.length} 个章节</span>
                        </div>
                        {catalog.sections.map((section) => (
                          <div key={section.id} className="template-inline-group">
                            <div className="template-inline-group__header">
                              <strong>{section.title}</strong>
                              <span>{section.components.length} 个组件</span>
                            </div>
                            <p>{section.summary || "无摘要"}</p>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </SurfaceCard>

                <SurfaceCard>
                  <div className="list-header">
                    <div>
                      <p className="section-kicker">Template Instance</p>
                      <h3>模板实例快照</h3>
                    </div>
                  </div>
                  <div className="stack-list">
                    <div className="template-inline-group">
                      <div className="template-inline-group__header">
                        <strong>参数生效值</strong>
                        <span>{Object.keys(report.answer.templateInstance.parameterValues).length} 项</span>
                      </div>
                      {Object.entries(report.answer.templateInstance.parameterValues).map(([key, values]) => (
                        <div key={key} className="template-inline-row template-inline-row--wide">
                          <strong>{key}</strong>
                          <span>{values.map((item) => String(item.display)).join("、") || "未设置"}</span>
                        </div>
                      ))}
                    </div>
                    {report.answer.templateInstance.catalogs.map((catalog) => (
                      <div key={catalog.id} className="template-editor-subcard">
                        <div className="template-inline-group__header">
                          <strong>{catalog.name}</strong>
                          <span>{catalog.sections.length} 个章节</span>
                        </div>
                        {catalog.sections.map((section) => (
                          <div key={section.id} className="template-inline-group">
                            <div className="template-inline-group__header">
                              <strong>{section.title}</strong>
                              <span>{section.skeletonStatus}</span>
                            </div>
                            <p>{section.requirementInstance.text}</p>
                          </div>
                        ))}
                      </div>
                    ))}
                    <details>
                      <summary>查看原始 JSON</summary>
                      <pre>{prettyJson(report.answer.templateInstance)}</pre>
                    </details>
                  </div>
                </SurfaceCard>
              </div>
            )}
          />
        )}
      </PageSection>
    </div>
  );
}

function toggleFormat(current: ExportFormat[], format: ExportFormat) {
  return current.includes(format) ? current.filter((item) => item !== format) : [...current, format];
}

function readCatalogs(report: Record<string, unknown>) {
  const catalogs = Array.isArray(report.catalogs) ? report.catalogs : [];
  return catalogs.map((catalog) => {
    const value = catalog as Record<string, unknown>;
    const sections = Array.isArray(value.sections) ? value.sections : [];
    return {
      id: String(value.id ?? ""),
      name: String(value.name ?? "未命名目录"),
      sections: sections.map((section) => {
        const sectionValue = section as Record<string, unknown>;
        const summary = sectionValue.summary as Record<string, unknown> | undefined;
        const components = Array.isArray(sectionValue.components) ? sectionValue.components : [];
        return {
          id: String(sectionValue.id ?? ""),
          title: String(sectionValue.title ?? "未命名章节"),
          summary: String(summary?.overview ?? ""),
          components,
        };
      }),
    };
  });
}
