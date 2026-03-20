import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "./shell/AppShell";
import { DocumentsPage } from "../pages/DocumentsPage";
import { ChatPage } from "../pages/ChatPage";
import { InstanceDetailPage } from "../pages/InstanceDetailPage";
import { InstancesPage } from "../pages/InstancesPage";
import { SettingsPage } from "../pages/SettingsPage";
import { TasksPage } from "../pages/TasksPage";
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
        <Route path="/template-instances" element={<Navigate to="/instances" replace />} />
        <Route path="/instances" element={<InstancesPage />} />
        <Route path="/instances/:instanceId" element={<InstanceDetailPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Routes>
    </AppShell>
  );
}
