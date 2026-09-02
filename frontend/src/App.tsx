import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { ThemeProvider } from '@/context/ThemeContext';
import { AuthProvider, useAuth } from '@/context/AuthContext';
import { AppShell } from '@/components/AppShell';
import { PredictorPage } from '@/pages/PredictorPage';
import { LoginPage } from '@/pages/LoginPage';
import { DataUploadPage } from '@/pages/DataUploadPage';
import { ModelsPage } from '@/pages/ModelsPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { MethodLibraryPage } from '@/pages/MethodLibraryPage';
import { BatchAnalysisPage } from '@/pages/BatchAnalysisPage';
import { MethodComparisonPage } from '@/pages/MethodComparisonPage';
import { ColumnDatabasePage } from '@/pages/ColumnDatabasePage';
import { TemplatesPage } from '@/pages/TemplatesPage';
import { SharedMethodPage } from '@/pages/SharedMethodPage';
import { ResetPasswordPage } from '@/pages/ResetPasswordPage';
import { AdminPage } from '@/pages/AdminPage';
import { ProfilePage } from '@/pages/ProfilePage';
import type { ReactNode } from 'react';

const queryClient = new QueryClient();

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const token = localStorage.getItem('access_token');
  if (!user && !token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/shared/:token" element={<SharedMethodPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <AppShell>
              <DashboardPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppShell>
              <PredictorPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/methods"
        element={
          <ProtectedRoute>
            <AppShell>
              <MethodLibraryPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/data"
        element={
          <ProtectedRoute>
            <AppShell>
              <DataUploadPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/models"
        element={
          <ProtectedRoute>
            <AppShell>
              <ModelsPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/batch"
        element={
          <ProtectedRoute>
            <AppShell>
              <BatchAnalysisPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/compare"
        element={
          <ProtectedRoute>
            <AppShell>
              <MethodComparisonPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/columns"
        element={
          <ProtectedRoute>
            <AppShell>
              <ColumnDatabasePage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/templates"
        element={
          <ProtectedRoute>
            <AppShell>
              <TemplatesPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            <AppShell>
              <AdminPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <AppShell>
              <ProfilePage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
          <Toaster position="bottom-right" richColors closeButton />
        </QueryClientProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
