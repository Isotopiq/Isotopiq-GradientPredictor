import { BrowserRouter, Routes, Route, Navigate, NavLink } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { FlaskConical, Upload, BarChart3, LogOut, LayoutDashboard, BookMarked } from 'lucide-react';
import { ThemeProvider } from '@/context/ThemeContext';
import { AuthProvider, useAuth } from '@/context/AuthContext';
import { ThemeToggle } from '@/components/ThemeToggle';
import { Logo } from '@/components/Logo';
import { PredictorPage } from '@/pages/PredictorPage';
import { LoginPage } from '@/pages/LoginPage';
import { DataUploadPage } from '@/pages/DataUploadPage';
import { ModelsPage } from '@/pages/ModelsPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { MethodLibraryPage } from '@/pages/MethodLibraryPage';
import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

const queryClient = new QueryClient();

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const token = localStorage.getItem('access_token');
  if (!user && !token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function NavLayout({ children }: { children: ReactNode }) {
  const { logout, user } = useAuth();
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-2.5">
          <div className="flex items-center gap-6">
            <Logo />
            <nav className="flex items-center gap-1">
              <NavLink
                to="/dashboard"
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-muted text-foreground'
                      : 'text-muted-foreground hover:text-foreground',
                  )
                }
              >
                <LayoutDashboard size={14} />
                Dashboard
              </NavLink>
              <NavLink
                to="/"
                end
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-muted text-foreground'
                      : 'text-muted-foreground hover:text-foreground',
                  )
                }
              >
                <FlaskConical size={14} />
                Predictor
              </NavLink>
              <NavLink
                to="/methods"
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-muted text-foreground'
                      : 'text-muted-foreground hover:text-foreground',
                  )
                }
              >
                <BookMarked size={14} />
                Methods
              </NavLink>
              <NavLink
                to="/data"
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-muted text-foreground'
                      : 'text-muted-foreground hover:text-foreground',
                  )
                }
              >
                <Upload size={14} />
                Data
              </NavLink>
              <NavLink
                to="/models"
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-muted text-foreground'
                      : 'text-muted-foreground hover:text-foreground',
                  )
                }
              >
                <BarChart3 size={14} />
                Models
              </NavLink>
            </nav>
          </div>
          <div className="flex items-center gap-3">
            {user && (
              <span className="text-xs text-muted-foreground">{user.email}</span>
            )}
            <ThemeToggle />
            <button
              onClick={logout}
              className="text-muted-foreground hover:text-foreground"
              aria-label="Logout"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </header>
      {children}
    </div>
  );
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <NavLayout>
              <DashboardPage />
            </NavLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <NavLayout>
              <PredictorPage />
            </NavLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/methods"
        element={
          <ProtectedRoute>
            <NavLayout>
              <MethodLibraryPage />
            </NavLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/data"
        element={
          <ProtectedRoute>
            <NavLayout>
              <DataUploadPage />
            </NavLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/models"
        element={
          <ProtectedRoute>
            <NavLayout>
              <ModelsPage />
            </NavLayout>
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
        </QueryClientProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
