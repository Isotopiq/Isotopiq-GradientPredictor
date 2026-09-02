import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { authApi } from '@/api/auth';
import { toast } from 'sonner';
import { Eye, EyeOff } from 'lucide-react';

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    if (newPassword.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }
    setLoading(true);
    try {
      await authApi.resetPassword(token, newPassword);
      setDone(true);
      toast.success('Password reset successfully');
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(msg || 'Reset failed — token may be expired');
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-slate-200 dark:from-slate-950 dark:to-slate-900">
        <div className="max-w-sm rounded-xl border border-border bg-card p-6 text-center shadow-lg">
          <h1 className="text-lg font-semibold">Invalid Reset Link</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            This reset link is missing a token. Please request a new password reset.
          </p>
          <button
            onClick={() => navigate('/login')}
            className="btn-primary mt-4 w-full"
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  if (done) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-slate-200 dark:from-slate-950 dark:to-slate-900">
        <div className="max-w-sm rounded-xl border border-border bg-card p-6 text-center shadow-lg">
          <h1 className="text-lg font-semibold text-success">Password Reset</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Your password has been changed. You can now sign in with your new password.
          </p>
          <button
            onClick={() => navigate('/login')}
            className="btn-primary mt-4 w-full"
          >
            Sign In
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-slate-200 dark:from-slate-950 dark:to-slate-900">
      <div className="w-full max-w-sm px-6">
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
        </div>

        <div className="rounded-xl border border-border bg-card p-6 shadow-lg">
          <h1 className="text-lg font-semibold">Set New Password</h1>
          <p className="mt-1 text-sm text-muted-foreground">Enter your new password below</p>

          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
            <div>
              <label className="label">New password</label>
              <div className="relative mt-1">
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="input pr-10"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                  autoFocus
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
            <div>
              <label className="label">Confirm password</label>
              <input
                type={showPassword ? 'text' : 'password'}
                className="input mt-1"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? 'Please wait...' : 'Reset Password'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
