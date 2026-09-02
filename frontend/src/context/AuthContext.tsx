import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import type { User } from '@/types';
import { authApi } from '@/api/auth';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  setUser: (user: User | null) => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);

  const login = async (email: string, password: string, rememberMe?: boolean) => {
    setLoading(true);
    try {
      const tokens = await authApi.login(email, password, rememberMe);
      localStorage.setItem('access_token', tokens.access_token);
      localStorage.setItem('refresh_token', tokens.refresh_token);
      setUser(tokens.user);
    } finally {
      setLoading(false);
    }
  };

  const register = async (email: string, password: string, fullName?: string) => {
    setLoading(true);
    try {
      const tokens = await authApi.register(email, password, fullName);
      localStorage.setItem('access_token', tokens.access_token);
      localStorage.setItem('refresh_token', tokens.refresh_token);
      setUser(tokens.user);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  // Try to restore session on mount
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    let cancelled = false;
    authApi.me()
      .then((u) => { if (!cancelled) setUser(u); })
      .catch(() => {
        if (cancelled) return;
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      });
    return () => { cancelled = true; };
  }, []);

  // Listen for auth:unauthorized events from the axios interceptor.
  // When a 401 is received, clear the user state so ProtectedRoute
  // can redirect to /login via React Router (no hard page reload).
  useEffect(() => {
    const handleUnauth = () => setUser(null);
    window.addEventListener('auth:unauthorized', handleUnauth);
    return () => window.removeEventListener('auth:unauthorized', handleUnauth);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
