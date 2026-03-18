import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchSystemSettings,
  rebuildTemplateIndex,
  testSystemSettings,
  updateSystemSettings,
} from "../entities/system-settings/api";
import { DetailPageLayout } from "../shared/layouts/DetailPageLayout";
import { PageIntroBar } from "../shared/layouts/PageIntroBar";
import { PageSection } from "../shared/ui/PageSection";
import { StatusBanner } from "../shared/ui/StatusBanner";
import { SurfaceCard } from "../shared/ui/SurfaceCard";

type SettingsForm = {
  completionBaseUrl: string;
  completionModel: string;
  completionApiKey: string;
  completionTemperature: string;
  completionTimeout: string;
  embeddingBaseUrl: string;
  embeddingModel: string;
  embeddingApiKey: string;
  embeddingTimeout: string;
  useCompletionAuth: boolean;
};

const EMPTY_FORM: SettingsForm = {
  completionBaseUrl: "",
  completionModel: "",
  completionApiKey: "",
  completionTemperature: "0.2",
  completionTimeout: "60",
  embeddingBaseUrl: "",
  embeddingModel: "",
  embeddingApiKey: "",
  embeddingTimeout: "60",
  useCompletionAuth: true,
};

export function SettingsPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<SettingsForm>(EMPTY_FORM);
  const [message, setMessage] = useState("");

  const settingsQuery = useQuery({
    queryKey: ["system-settings"],
    queryFn: fetchSystemSettings,
  });

  useEffect(() => {
    if (!settingsQuery.data) {
      return;
    }
    setForm({
      completionBaseUrl: settingsQuery.data.completion.base_url ?? "",
      completionModel: settingsQuery.data.completion.model ?? "",
      completionApiKey: "",
      completionTemperature: String(settingsQuery.data.completion.temperature ?? 0.2),
      completionTimeout: String(settingsQuery.data.completion.timeout_sec ?? 60),
      embeddingBaseUrl: settingsQuery.data.embedding.base_url ?? "",
      embeddingModel: settingsQuery.data.embedding.model ?? "",
      embeddingApiKey: "",
      embeddingTimeout: String(settingsQuery.data.embedding.timeout_sec ?? 60),
      useCompletionAuth: Boolean(settingsQuery.data.embedding.use_completion_auth ?? true),
    });
  }, [settingsQuery.data]);

  const saveMutation = useMutation({
    mutationFn: () =>
      updateSystemSettings({
        completion: {
          base_url: form.completionBaseUrl,
          model: form.completionModel,
          api_key: form.completionApiKey || undefined,
          temperature: Number(form.completionTemperature || "0.2"),
          timeout_sec: Number(form.completionTimeout || "60"),
        },
        embedding: {
          base_url: form.embeddingBaseUrl,
          model: form.embeddingModel,
          api_key: form.embeddingApiKey || undefined,
          timeout_sec: Number(form.embeddingTimeout || "60"),
          use_completion_auth: form.useCompletionAuth,
        },
      }),
    onSuccess: async () => {
      setMessage("系统设置已保存。");
      await queryClient.invalidateQueries({ queryKey: ["system-settings"] });
    },
    onError: (error) => {
      setMessage(error instanceof Error ? error.message : "系统设置保存失败。");
    },
  });

  const testMutation = useMutation({
    mutationFn: (target: "completion" | "embedding" | "both") => testSystemSettings(target),
    onSuccess: (result) => {
      setMessage(JSON.stringify(result, null, 2));
    },
    onError: (error) => {
      setMessage(error instanceof Error ? error.message : "连接测试失败。");
    },
  });

  const reindexMutation = useMutation({
    mutationFn: rebuildTemplateIndex,
    onSuccess: async (result) => {
      setMessage(result.message);
      await queryClient.invalidateQueries({ queryKey: ["system-settings"] });
    },
    onError: (error) => {
      setMessage(error instanceof Error ? error.message : "重建索引失败。");
    },
  });

  return (
    <div className="settings-page">
      <PageSection description="集中配置 Completion、Embedding 与模板索引状态。">
        {message ? (
          <StatusBanner tone="info" title="操作反馈">
            <span className="pre-wrap">{message}</span>
          </StatusBanner>
        ) : null}

        <DetailPageLayout
          intro={
            <PageIntroBar
              eyebrow="System Settings"
              description="统一维护 Completion、Embedding 与语义索引配置。"
              badge={settingsQuery.data?.is_ready ? "配置完成" : "待完善"}
            />
          }
          summary={
            <SurfaceCard className="summary-strip">
              <div className="summary-strip__item">
                <span>配置完整性</span>
                <strong>{settingsQuery.data?.is_ready ? "已完成" : "未完成"}</strong>
              </div>
              <div className="summary-strip__item">
                <span>Ready 模板数</span>
                <strong>{settingsQuery.data?.index_status?.ready_count ?? 0}</strong>
              </div>
              <div className="summary-strip__item">
                <span>异常模板数</span>
                <strong>{settingsQuery.data?.index_status?.error_count ?? 0}</strong>
              </div>
            </SurfaceCard>
          }
          content={
            <div className="settings-grid">
              <SurfaceCard>
                <div className="list-header">
                  <div>
                    <p className="section-kicker">Completion</p>
                    <h3>Completion 配置</h3>
                  </div>
                </div>
                <div className="form-grid">
                  <label className="field">
                    <span className="field-label">Base URL</span>
                    <input
                      value={form.completionBaseUrl}
                      onChange={(event) =>
                        setForm((current) => ({ ...current, completionBaseUrl: event.target.value }))
                      }
                    />
                  </label>
                  <label className="field">
                    <span className="field-label">Model</span>
                    <input
                      value={form.completionModel}
                      onChange={(event) => setForm((current) => ({ ...current, completionModel: event.target.value }))}
                    />
                  </label>
                  <label className="field field--full">
                    <span className="field-label">API Key</span>
                    <input
                      type="password"
                      placeholder={settingsQuery.data?.completion.masked_api_key || "留空则保留原值"}
                      value={form.completionApiKey}
                      onChange={(event) => setForm((current) => ({ ...current, completionApiKey: event.target.value }))}
                    />
                  </label>
                  <label className="field">
                    <span className="field-label">Temperature</span>
                    <input
                      value={form.completionTemperature}
                      onChange={(event) =>
                        setForm((current) => ({ ...current, completionTemperature: event.target.value }))
                      }
                    />
                  </label>
                  <label className="field">
                    <span className="field-label">Timeout(s)</span>
                    <input
                      value={form.completionTimeout}
                      onChange={(event) => setForm((current) => ({ ...current, completionTimeout: event.target.value }))}
                    />
                  </label>
                </div>
              </SurfaceCard>

              <SurfaceCard>
                <div className="list-header">
                  <div>
                    <p className="section-kicker">Embedding</p>
                    <h3>Embedding 配置</h3>
                  </div>
                </div>
                <div className="form-grid">
                  <label className="field field--full field--checkbox">
                    <span className="field-label">复用 Completion 鉴权</span>
                    <input
                      type="checkbox"
                      checked={form.useCompletionAuth}
                      onChange={(event) =>
                        setForm((current) => ({ ...current, useCompletionAuth: event.target.checked }))
                      }
                    />
                  </label>
                  <label className="field">
                    <span className="field-label">Base URL</span>
                    <input
                      value={form.embeddingBaseUrl}
                      onChange={(event) => setForm((current) => ({ ...current, embeddingBaseUrl: event.target.value }))}
                      disabled={form.useCompletionAuth}
                    />
                  </label>
                  <label className="field">
                    <span className="field-label">Model</span>
                    <input
                      value={form.embeddingModel}
                      onChange={(event) => setForm((current) => ({ ...current, embeddingModel: event.target.value }))}
                    />
                  </label>
                  <label className="field field--full">
                    <span className="field-label">API Key</span>
                    <input
                      type="password"
                      placeholder={settingsQuery.data?.embedding.masked_api_key || "留空则保留原值"}
                      value={form.embeddingApiKey}
                      onChange={(event) => setForm((current) => ({ ...current, embeddingApiKey: event.target.value }))}
                      disabled={form.useCompletionAuth}
                    />
                  </label>
                  <label className="field">
                    <span className="field-label">Timeout(s)</span>
                    <input
                      value={form.embeddingTimeout}
                      onChange={(event) => setForm((current) => ({ ...current, embeddingTimeout: event.target.value }))}
                    />
                  </label>
                </div>
              </SurfaceCard>

              <SurfaceCard className="settings-grid__wide">
                <div className="list-header">
                  <div>
                    <p className="section-kicker">Operations</p>
                    <h3>连接测试与索引</h3>
                  </div>
                </div>

                <div className="action-row">
                  <button className="primary-button" type="button" onClick={() => saveMutation.mutate()}>
                    {saveMutation.isPending ? "保存中..." : "保存设置"}
                  </button>
                  <button className="secondary-button" type="button" onClick={() => testMutation.mutate("both")}>
                    {testMutation.isPending ? "测试中..." : "测试连接"}
                  </button>
                  <button
                    className="ghost-button ghost-button--inline"
                    type="button"
                    onClick={() => reindexMutation.mutate()}
                  >
                    {reindexMutation.isPending ? "重建中..." : "重建模板索引"}
                  </button>
                </div>
              </SurfaceCard>
            </div>
          }
        />
      </PageSection>
    </div>
  );
}
