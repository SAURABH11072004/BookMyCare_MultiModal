import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import Layout from "./components/Layout";
import { Spinner } from "./components/ui";
import { useAuth } from "./lib/auth";
import AnalysesPage from "./pages/Analyses";
import AnalysisResultPage from "./pages/AnalysisResult";
import DashboardPage from "./pages/Dashboard";
import HistoryPage from "./pages/History";
import LibraryPage from "./pages/Library";
import { LoginPage, RegisterPage } from "./pages/Auth";
import NewAnalysisPage from "./pages/NewAnalysis";
import NotFoundPage from "./pages/NotFound";
import ProfilePage from "./pages/Profile";
import ReportDetailPage from "./pages/ReportDetail";
import ReportsPage from "./pages/Reports";

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <Spinner />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <>{children}</>;
}

function GuestOnly({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation() as { pathname: string; state?: { from?: string } };
  if (loading) return <Spinner />;
  if (user) {
    // Newly registered users go to their profile; returning users go back where they were.
    if (location.pathname === "/register") return <Navigate to="/profile" replace state={{ welcome: true }} />;
    return <Navigate to={location.state?.from ?? "/"} replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<GuestOnly><LoginPage /></GuestOnly>} />
      <Route path="/register" element={<GuestOnly><RegisterPage /></GuestOnly>} />
      <Route element={<RequireAuth><Layout /></RequireAuth>}>
        <Route index element={<DashboardPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="reports/:id" element={<ReportDetailPage />} />
        <Route path="analyses" element={<AnalysesPage />} />
        <Route path="analyses/new" element={<NewAnalysisPage />} />
        <Route path="analyses/:id" element={<AnalysisResultPage />} />
        <Route path="library" element={<LibraryPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
