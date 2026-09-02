import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useAuth } from '@/context/AuthContext';
import { methodsApi } from '@/api/methods';
import { GradientChart } from '@/components/GradientChart';
import { Logo } from '@/components/Logo';
import { Skeleton } from '@/components/Skeleton';
import { Copy, BookMarked } from 'lucide-react';
import { toast } from 'sonner';

export function SharedMethodPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const { data: method, isLoading, error } = useQuery({
    queryKey: ['shared-method', token],
    queryFn: () => methodsApi.getShared(token!),
    enabled: !!token,
  });

  const forkMutation = useMutation({
    mutationFn: () => methodsApi.fork(method!.id),
    onSuccess: () => {
      toast.success('Method copied to your library');
      navigate('/methods');
    },
    onError: () => toast.error('Failed to copy method — try logging in first'),
  });

  if (isLoading) return <div className="p-6"><Skeleton className="h-96" /></div>;
  if (error || !method) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6">
        <Logo />
        <p className="text-sm text-muted-foreground">Shared method not found or no longer available.</p>
        <button className="btn-primary" onClick={() => navigate('/login')}>Go to Login</button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-3">
          <Logo />
          {user ? (
            <button
              className="btn-primary btn-sm"
              onClick={() => forkMutation.mutate()}
              disabled={forkMutation.isPending}
            >
              <Copy size={14} className="mr-1" /> Fork to My Library
            </button>
          ) : (
            <button className="btn-primary btn-sm" onClick={() => navigate('/login')}>
              <BookMarked size={14} className="mr-1" /> Log in to Fork
            </button>
          )}
        </div>
      </header>

      {/* Content */}
      <div className="mx-auto max-w-4xl p-6">
        <div className="mb-6">
          <h1 className="text-xl font-bold">{method.name || 'Shared Method'}</h1>
          <p className="text-sm text-muted-foreground">
            Shared via IsotopiQ LC-MS Suite
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="card-scientific">
            <h2 className="mb-3 text-sm font-semibold">Method Parameters</h2>
            <div className="space-y-2 text-xs">
              <Row label="Column Type" value={method.column_type} />
              <Row label="pH" value={method.ph?.toFixed(1)} />
              <Row label="Flow Rate" value={`${method.flow_rate_ml_min?.toFixed(2)} mL/min`} />
              <Row label="Temperature" value={`${method.temperature_c?.toFixed(0)} °C`} />
              <Row label="Additive" value={method.additive} />
              <Row label="Mobile Phase A" value={method.mobile_phase_a} />
              <Row label="Mobile Phase B" value={method.mobile_phase_b} />
            </div>
          </div>

          <div className="card-scientific">
            <h2 className="mb-3 text-sm font-semibold">Gradient Profile</h2>
            <GradientChart gradientTable={method.gradient_table || []} />
          </div>
        </div>

        <div className="mt-4 card-scientific">
          <h2 className="mb-3 text-sm font-semibold">Gradient Table</h2>
          <table className="data-table">
            <thead>
              <tr>
                <th>Step</th>
                <th>Time (min)</th>
                <th>%B</th>
              </tr>
            </thead>
            <tbody>
              {(method.gradient_table || []).map((p, i) => (
                <tr key={i}>
                  <td className="text-muted-foreground">{i + 1}</td>
                  <td>{(p.time_s / 60).toFixed(2)}</td>
                  <td>{p.percent_b.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="mt-4 text-center text-xs text-muted-foreground">
          Predictions are estimates — verify experimentally before production use.
        </p>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="flex justify-between border-b border-border pb-1 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value || '—'}</span>
    </div>
  );
}
