import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "./shell/AppShell";
import { ChatPage } from "../pages/ChatPage";
import { ReportCenterPage } from "../pages/ReportCenterPage";
import { ReportDetailPage } from "../pages/ReportDetailPage";
import { SettingsPage } from "../pages/SettingsPage";
import { TemplateDetailPage } from "../pages/TemplateDetailPage";
import { TemplatesPage } from "../pages/TemplatesPage";

export function App() {
  const location = useLocation();

  return (
    <AppShell pathname={location.pathname}>
      <Routes>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/templates" element={<TemplatesPage />} />
        <Route path="/templates/new" element={<TemplateDetailPage />} />
        <Route path="/templates/:templateId" element={<TemplateDetailPage />} />
        <Route path="/reports" element={<ReportCenterPage />} />
        <Route path="/reports/:reportId" element={<ReportDetailPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Routes>
    </AppShell>
  );
}
