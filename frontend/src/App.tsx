import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import ChatPage from "./pages/ChatPage";
import DocumentsPage from "./pages/DocumentsPage";
import LearningPage from "./pages/LearningPage";
import SettingsPage from "./pages/SettingsPage";
import VoiceChatPage from "./pages/VoiceChatPage";
import { useAuthStore } from "./store/authStore";

function PrivateRoute({ children }: { children: JSX.Element }) {
  const token = useAuthStore((state) => state.token);
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  const token = useAuthStore((state) => state.token);

  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/chat"
          element={
            <PrivateRoute>
              <Layout title="Chat">
                <ChatPage />
              </Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/voice"
          element={
            <PrivateRoute>
              <Layout title="Voice Chat">
                <VoiceChatPage />
              </Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/documents"
          element={
            <PrivateRoute>
              <Layout title="Documents">
                <DocumentsPage />
              </Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/learning"
          element={
            <PrivateRoute>
              <Layout title="Learning">
                <LearningPage />
              </Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <PrivateRoute>
              <Layout title="Settings">
                <SettingsPage />
              </Layout>
            </PrivateRoute>
          }
        />
        <Route path="*" element={<Navigate to={token ? "/chat" : "/login"} replace />} />
      </Routes>
    </Router>
  );
}
