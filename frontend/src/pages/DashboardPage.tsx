import { useEffect, useState } from 'react';
import {
  Database,
  FlaskConical,
  BarChart3,
  TrendingUp,
  Activity,
  Cpu,
  Target,
  Zap,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  RadialBarChart,
  RadialBar,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { apiClient } from '@/api/client';

interface ModelStats {
  totals: {
    models: number;
    compounds: number;
    methods: number;
    runs: number;
    predictions: number;
  };
  avg_confidence: number;
  models_by_type: Record<string, number>;
  models_by_column: Record<string, number>;
  best_by_column: Record<string, {
    model_type: string;
    version: number;
    r2: number;
    rmse: number | null;
    n_samples: number;
  }>;
  recent_models: Array<{
    id: string;
    column_type: string;
    model_type: string;
    version: number;
    n_samples: number;
    r2: number | null;
    rmse: number | null;
    trained_at: string | null;
  }>;
}

const PIE_COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export function DashboardPage() {
  const [stats, setStats] = useState<ModelStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await apiClient.get<ModelStats>('/ml/stats');
        setStats(data);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-5">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="card h-28 animate-pulse" />
          ))}
        </div>
      </main>
    );
  }

  if (!stats) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6">
        <div className="card text-center text-sm text-muted-foreground">
          Unable to load statistics. Make sure the backend is running.
        </div>
      </main>
    );
  }

  const typeData = Object.entries(stats.models_by_type).map(([name, value]) => ({
    name,
    value,
  }));
  const columnData = Object.entries(stats.models_by_column).map(([name, value]) => ({
    name,
    models: value,
  }));
  const confidencePct = Math.round(stats.avg_confidence * 100);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6">
      <h1 className="mb-4 text-xl font-bold">Dashboard</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-5">
        <StatCard
          icon={<Cpu size={18} />}
          label="Models"
          value={stats.totals.models}
          color="text-indigo-500"
        />
        <StatCard
          icon={<FlaskConical size={18} />}
          label="Compounds"
          value={stats.totals.compounds}
          color="text-emerald-500"
        />
        <StatCard
          icon={<Database size={18} />}
          label="Methods"
          value={stats.totals.methods}
          color="text-amber-500"
        />
        <StatCard
          icon={<Activity size={18} />}
          label="Runs"
          value={stats.totals.runs}
          color="text-rose-500"
        />
        <StatCard
          icon={<Target size={18} />}
          label="Predictions"
          value={stats.totals.predictions}
          color="text-violet-500"
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Confidence gauge */}
        <div className="card">
          <h3 className="text-sm font-semibold">Avg. Prediction Confidence</h3>
          <ResponsiveContainer width="100%" height={180} className="mt-2">
            <RadialBarChart
              innerRadius="60%"
              outerRadius="100%"
              data={[{ name: 'confidence', value: confidencePct, fill: '#6366f1' }]}
              startAngle={90}
              endAngle={-270}
            >
              <RadialBar dataKey="value" cornerRadius={8} fill="#6366f1" background />
              <text
                x="50%"
                y="50%"
                textAnchor="middle"
                dominantBaseline="middle"
                className="fill-foreground text-2xl font-bold"
              >
                {confidencePct}%
              </text>
            </RadialBarChart>
          </ResponsiveContainer>
          <p className="text-center text-xs text-muted-foreground">
            Across {stats.totals.predictions} predictions
          </p>
        </div>

        {/* Models by type pie */}
        <div className="card">
          <h3 className="text-sm font-semibold">Models by Type</h3>
          {typeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180} className="mt-2">
              <PieChart>
                <Pie
                  data={typeData}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={70}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}`}
                  labelLine={false}
                  fontSize={10}
                >
                  {typeData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[180px] items-center justify-center text-sm text-muted-foreground">
              No models trained yet
            </div>
          )}
        </div>

        {/* Models by column bar */}
        <div className="card">
          <h3 className="text-sm font-semibold">Models by Column Type</h3>
          {columnData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180} className="mt-2">
              <BarChart data={columnData}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis dataKey="name" fontSize={10} stroke="hsl(var(--muted-foreground))" />
                <YAxis fontSize={10} stroke="hsl(var(--muted-foreground))" allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="models" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[180px] items-center justify-center text-sm text-muted-foreground">
              No models trained yet
            </div>
          )}
        </div>
      </div>

      {/* Best model per column */}
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="card">
          <div className="flex items-center gap-2">
            <TrendingUp size={16} className="text-accent" />
            <h3 className="text-sm font-semibold">Best Model per Column Type</h3>
          </div>
          <div className="mt-3 space-y-2">
            {Object.entries(stats.best_by_column).length > 0 ? (
              Object.entries(stats.best_by_column).map(([col, info]) => (
                <div
                  key={col}
                  className="flex items-center justify-between rounded-md border border-border p-3"
                >
                  <div>
                    <p className="text-sm font-medium">{col}</p>
                    <p className="text-xs text-muted-foreground">
                      {info.model_type} v{info.version} · {info.n_samples} samples
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold tabular-nums text-accent">
                      R² = {info.r2?.toFixed(3) ?? '—'}
                    </p>
                    {info.rmse !== null && (
                      <p className="text-xs text-muted-foreground">
                        RMSE = {info.rmse?.toFixed(2)}
                      </p>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No models trained yet.</p>
            )}
          </div>
        </div>

        {/* Recent models */}
        <div className="card">
          <div className="flex items-center gap-2">
            <Zap size={16} className="text-accent" />
            <h3 className="text-sm font-semibold">Recent Model Activity</h3>
          </div>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="pb-2 pr-3">Column</th>
                  <th className="pb-2 pr-3">Type</th>
                  <th className="pb-2 pr-3">Ver</th>
                  <th className="pb-2 pr-3">Samples</th>
                  <th className="pb-2 pr-3">R²</th>
                  <th className="pb-2">Trained</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent_models.length > 0 ? (
                  stats.recent_models.map((m) => (
                    <tr key={m.id} className="border-b border-border last:border-0">
                      <td className="py-1.5 pr-3 font-medium">{m.column_type}</td>
                      <td className="py-1.5 pr-3">{m.model_type}</td>
                      <td className="py-1.5 pr-3 tabular-nums">v{m.version}</td>
                      <td className="py-1.5 pr-3 tabular-nums">{m.n_samples}</td>
                      <td className="py-1.5 pr-3 tabular-nums">
                        {m.r2 !== null ? m.r2.toFixed(3) : '—'}
                      </td>
                      <td className="py-1.5 text-muted-foreground">
                        {m.trained_at ? new Date(m.trained_at).toLocaleDateString() : '—'}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="py-4 text-center text-muted-foreground">
                      No models trained yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </main>
  );
}

function StatCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="card flex items-center gap-3">
      <div className={`shrink-0 ${color}`}>{icon}</div>
      <div>
        <p className="text-2xl font-bold tabular-nums">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  );
}
