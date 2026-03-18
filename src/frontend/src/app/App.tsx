import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "./shell/AppShell";
import { DocumentsPage } from "../pages/DocumentsPage";
import { ChatPage } from "../pages/ChatPage";
import { InstancesPage } from "../pages/InstancesPage";
import { SettingsPage } from "../pages/SettingsPage";
import { TasksPage } from "../pages/TasksPage";
import { TemplatesPage } from "../pages/TemplatesPage";

export function App() {
  const location = useLocation();

  return (
    <AppShell pathname={location.pathname}>
      <Routes>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/templates" element={<TemplatesPage />} />
        <Route path="/instances" element={<InstancesPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Routes>
    </AppShell>
  );
}
