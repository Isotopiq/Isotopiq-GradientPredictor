import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { Logo } from '@/components/Logo';
import { useTheme } from '@/context/ThemeContext';
import { Moon, Sun } from 'lucide-react';

export function AuthForms() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const { login, register, loading } = useAuth();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      if (mode === 'login') {
        await login(email, password);
      } else {
        await register(email, password, fullName || undefined);
      }
      navigate('/');
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || 'Authentication failed');
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-background p-4">
      {/* Theme toggle in corner */}
      <button
        onClick={toggleTheme}
        className="absolute right-4 top-4 rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground"
        aria-label="Toggle theme"
      >
        {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
      </button>

      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-6 flex justify-center">
          <Logo />
        </div>

        <div className="card">
          <h1 className="text-xl font-bold">
            {mode === 'login' ? 'Welcome back' : 'Create account'}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {mode === 'login'
              ? 'Sign in to your LC-MS Method Prediction account'
              : 'Register to start predicting LC-MS methods'}
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            {mode === 'register' && (
              <div>
                <label className="label">Full name (optional)</label>
                <input
                  className="input mt-1"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </div>
            )}
            <div>
              <label className="label">Email</label>
              <input
                type="email"
                className="input mt-1"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="label">Password</label>
              <input
                type="password"
                className="input mt-1"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Register'}
            </button>
          </form>

          <button
            onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
            className="mt-4 text-xs text-muted-foreground hover:text-foreground"
          >
            {mode === 'login'
              ? "Don't have an account? Register"
              : 'Already have an account? Sign in'}
          </button>
        </div>

        <p className="mt-4 text-center text-xs text-muted-foreground">
          Predictions are estimates — verify experimentally before production use.
        </p>
      </div>
    </div>
  );
}
