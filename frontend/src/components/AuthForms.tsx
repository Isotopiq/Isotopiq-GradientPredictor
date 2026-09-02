import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import { Moon, Sun, Monitor, FlaskConical, BarChart3, Shield, Zap } from 'lucide-react';
import { toast } from 'sonner';

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
        toast.success('Welcome back!');
      } else {
        await register(email, password, fullName || undefined);
        toast.success('Account created successfully!');
      }
      navigate('/dashboard');
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || 'Authentication failed');
      toast.error(msg || 'Authentication failed');
    }
  };

  const themeIcon = theme === 'light' ? <Sun size={16} /> : theme === 'dark' ? <Moon size={16} /> : <Monitor size={16} />;

  return (
    <div className="flex min-h-screen">
      {/* Left branding panel */}
      <div className="relative hidden w-1/2 flex-col justify-between bg-sidebar p-12 text-sidebar-foreground lg:flex">
        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="absolute right-6 top-6 rounded-md p-2 text-sidebar-muted-foreground hover:bg-sidebar-muted hover:text-sidebar-foreground"
          aria-label="Toggle theme"
        >
          {themeIcon}
        </button>

        {/* Logo */}
        <div className="flex items-center">
          <img
            src="/isotopiq-logo-white.png"
            alt="IsotopiQ"
            className="h-10 w-auto"
            style={{ maxHeight: '40px' }}
          />
        </div>

        {/* Tagline + features */}
        <div className="space-y-8">
          <div>
            <h2 className="text-3xl font-bold leading-tight">
              LC-MS Method<br />Prediction Suite
            </h2>
            <p className="mt-3 max-w-md text-sm text-sidebar-muted-foreground">
              Predict chromatographic method parameters from molecular structure.
              Combine chemistry heuristics with trainable retention modeling.
            </p>
          </div>

          <div className="space-y-4">
            <FeatureItem icon={<FlaskConical size={18} />} title="Structure-based prediction" desc="SMILES, InChI, molfile, PubChem & ChemSpider search" />
            <FeatureItem icon={<BarChart3 size={18} />} title="ML-powered retention modeling" desc="XGBoost, LightGBM, ensemble with confidence intervals" />
            <FeatureItem icon={<Shield size={18} />} title="Applicability domain checking" desc="Know when predictions are extrapolating beyond training data" />
            <FeatureItem icon={<Zap size={18} />} title="Interactive gradient optimization" desc="Real-time chromatogram simulation & resolution analysis" />
          </div>
        </div>

        {/* Disclaimer */}
        <p className="text-xs text-sidebar-muted-foreground">
          Predictions are estimates — verify experimentally before production use.
        </p>
      </div>

      {/* Right form panel */}
      <div className="flex w-full items-center justify-center bg-background p-4 lg:w-1/2">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="mb-6 flex justify-center lg:hidden">
            <img
              src="/isotopiq-logo.png"
              alt="IsotopiQ"
              className="h-8 w-auto"
              style={{ maxHeight: '32px' }}
            />
          </div>

          <div className="card-scientific">
            <h1 className="text-xl font-bold">
              {mode === 'login' ? 'Welcome back' : 'Create account'}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {mode === 'login'
                ? 'Sign in to your LC-MS prediction account'
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
            Predictions require experimental verification.
          </p>
        </div>
      </div>
    </div>
  );
}

function FeatureItem({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 shrink-0 rounded-md bg-sidebar-muted p-2 text-accent">{icon}</div>
      <div>
        <p className="text-sm font-medium">{title}</p>
        <p className="text-xs text-sidebar-muted-foreground">{desc}</p>
      </div>
    </div>
  );
}
