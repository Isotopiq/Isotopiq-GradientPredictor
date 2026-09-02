import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import { Moon, Sun, Monitor, Eye, EyeOff } from 'lucide-react';
import { toast } from 'sonner';

type Mode = 'login' | 'register' | 'forgot';

export function AuthForms() {
  const [mode, setMode] = useState<Mode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [forgotSent, setForgotSent] = useState(false);
  const { login, register, loading } = useAuth();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      if (mode === 'login') {
        await login(email, password, rememberMe);
        toast.success('Welcome back!');
        navigate('/dashboard');
      } else if (mode === 'register') {
        await register(email, password, fullName || undefined);
        toast.success('Account created successfully!');
        navigate('/dashboard');
      } else if (mode === 'forgot') {
        const { authApi } = await import('@/api/auth');
        await authApi.forgotPassword(email);
        setForgotSent(true);
        toast.success('Reset link sent if account exists');
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || 'Something went wrong');
      toast.error(msg || 'Something went wrong');
    }
  };

  const themeIcon = theme === 'light' ? <Sun size={16} /> : theme === 'dark' ? <Moon size={16} /> : <Monitor size={16} />;

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-slate-200 dark:from-slate-950 dark:to-slate-900">
      {/* Theme toggle — top right */}
      <button
        onClick={toggleTheme}
        className="absolute right-5 top-5 rounded-lg border border-border bg-card/80 p-2 text-muted-foreground backdrop-blur transition-colors hover:text-foreground"
        aria-label="Toggle theme"
      >
        {themeIcon}
      </button>

      {/* Auth card */}
      <div className="w-full max-w-sm px-6">
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center">
          <img
            src="/isotopiq-logo.png"
            alt="IsotopiQ"
            className="h-12 w-auto dark:hidden"
            style={{ maxHeight: '48px' }}
          />
          <img
            src="/isotopiq-logo-white.png"
            alt="IsotopiQ"
            className="hidden h-12 w-auto dark:block"
            style={{ maxHeight: '48px' }}
          />
          <p className="mt-3 text-xs font-medium tracking-wide text-muted-foreground uppercase">
            LC-MS Method Prediction Suite
          </p>
        </div>

        {/* Form card */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-lg">
          <h1 className="text-lg font-semibold text-foreground">
            {mode === 'login' && 'Sign in'}
            {mode === 'register' && 'Create account'}
            {mode === 'forgot' && 'Reset password'}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {mode === 'login' && 'Enter your credentials to continue'}
            {mode === 'register' && 'Start predicting LC-MS methods'}
            {mode === 'forgot' && 'Enter your email for a reset link'}
          </p>

          {mode === 'forgot' && forgotSent ? (
            <div className="mt-6 rounded-lg border border-success/30 bg-success/5 p-4 text-sm">
              <p className="font-medium text-success">Check your inbox</p>
              <p className="mt-1 text-muted-foreground">
                If an account exists for <span className="font-medium">{email}</span>,
                you'll receive a reset link shortly. The link expires in 1 hour.
              </p>
              <button
                onClick={() => { setMode('login'); setForgotSent(false); }}
                className="mt-3 text-xs font-medium text-accent hover:underline"
              >
                Back to sign in
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="mt-5 space-y-4">
              {mode === 'register' && (
                <div>
                  <label className="label">Full name <span className="text-muted-foreground">(optional)</span></label>
                  <input
                    className="input mt-1"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Jane Doe"
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
                  placeholder="you@lab.com"
                  required
                  autoFocus
                />
              </div>

              {mode !== 'forgot' && (
                <div>
                  <div className="flex items-center justify-between">
                    <label className="label">Password</label>
                    {mode === 'login' && (
                      <button
                        type="button"
                        onClick={() => setMode('forgot')}
                        className="text-xs text-muted-foreground hover:text-accent hover:underline"
                      >
                        Forgot password?
                      </button>
                    )}
                  </div>
                  <div className="relative mt-1">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      className="input pr-10"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      minLength={8}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      tabIndex={-1}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
              )}

              {/* Remember me — login only */}
              {mode === 'login' && (
                <label className="flex cursor-pointer items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="h-4 w-4 rounded border-input accent-accent"
                  />
                  <span className="text-muted-foreground">Remember me for 30 days</span>
                </label>
              )}

              {error && (
                <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                  {error}
                </p>
              )}

              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? 'Please wait...' : (
                  mode === 'login' ? 'Sign in' :
                  mode === 'register' ? 'Create account' :
                  'Send reset link'
                )}
              </button>
            </form>
          )}

          {/* Mode switcher */}
          {mode !== 'forgot' && (
            <div className="mt-5 border-t border-border pt-4 text-center text-sm">
              {mode === 'login' ? (
                <span className="text-muted-foreground">
                  No account?{' '}
                  <button
                    onClick={() => setMode('register')}
                    className="font-medium text-accent hover:underline"
                  >
                    Register
                  </button>
                </span>
              ) : (
                <span className="text-muted-foreground">
                  Already registered?{' '}
                  <button
                    onClick={() => setMode('login')}
                    className="font-medium text-accent hover:underline"
                  >
                    Sign in
                  </button>
                </span>
              )}
            </div>
          )}

          {mode === 'forgot' && !forgotSent && (
            <div className="mt-5 border-t border-border pt-4 text-center text-sm">
              <button
                onClick={() => setMode('login')}
                className="font-medium text-accent hover:underline"
              >
                Back to sign in
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <p className="mt-6 text-center text-xs text-muted-foreground">
          Predictions are estimates — verify experimentally.
        </p>
      </div>
    </div>
  );
}
