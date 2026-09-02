import { useQuery } from '@tanstack/react-query';
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
import { mlApi } from '@/api/ml';
import { CalibrationPlot } from '@/components/CalibrationPlot';
import { Skeleton } from '@/components/Skeleton';
import { EmptyState } from '@/components/EmptyState';

const PIE_COLORS = [
  'hsl(var(--chart-1))',
  'hsl(var(--chart-2))',
  'hsl(var(--chart-3))',
  'hsl(var(--chart-4))',
  'hsl(var(--chart-5))',
];

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

export function DashboardPage() {
  const { data: stats, isLoading } = useQuery<ModelStats>({
    queryKey: ['ml-stats'],
    queryFn: async () => {
      const { data } = await mlApi.stats();
      return data as ModelStats;
    },
  });

  const { data: calibration } = useQuery({
    queryKey: ['calibration'],
    queryFn: () => mlApi.calibration(),
  });

  if (isLoading) {
    return (
      <div className="mx-auto max-w-7xl p-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-5">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="mx-auto max-w-7xl p-6">
        <EmptyState
          icon={<BarChart3 size={24} />}
          title="Unable to load statistics"
          description="Make sure the backend is running and you're logged in."
        />
      </div>
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
    <div className="mx-auto max-w-7xl p-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Model statistics and performance overview</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-5">
        <StatCard icon={<Cpu size={18} />} label="Models" value={stats.totals.models} color="hsl(var(--chart-1))" />
        <StatCard icon={<FlaskConical size={18} />} label="Compounds" value={stats.totals.compounds} color="hsl(var(--chart-2))" />
        <StatCard icon={<Database size={18} />} label="Methods" value={stats.totals.methods} color="hsl(var(--chart-3))" />
        <StatCard icon={<Activity size={18} />} label="Runs" value={stats.totals.runs} color="hsl(var(--chart-4))" />
        <StatCard icon={<Target size={18} />} label="Predictions" value={stats.totals.predictions} color="hsl(var(--chart-5))" />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Confidence gauge */}
        <div className="card-scientific">
          <h3 className="text-sm font-semibold">Avg. Prediction Confidence</h3>
          <ResponsiveContainer width="100%" height={180} className="mt-2">
            <RadialBarChart
              innerRadius="60%"
              outerRadius="100%"
              data={[{ name: 'confidence', value: confidencePct, fill: 'hsl(var(--chart-1))' }]}
              startAngle={90}
              endAngle={-270}
            >
              <RadialBar dataKey="value" cornerRadius={8} fill="hsl(var(--chart-1))" background />
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
        <div className="card-scientific">
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
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[180px] items-center justify-center text-sm text-muted-foreground">
              No models trained yet
            </div>
          )}
        </div>

        {/* Models by column bar */}
        <div className="card-scientific">
          <h3 className="text-sm font-semibold">Models by Column Type</h3>
          {columnData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180} className="mt-2">
              <BarChart data={columnData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="name" fontSize={10} stroke="hsl(var(--muted-foreground))" />
                <YAxis fontSize={10} stroke="hsl(var(--muted-foreground))" allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Bar dataKey="models" fill="hsl(var(--chart-1))" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[180px] items-center justify-center text-sm text-muted-foreground">
              No models trained yet
            </div>
          )}
        </div>
      </div>

      {/* Best model per column + Recent activity */}
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="card-scientific">
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

        <div className="card-scientific">
          <div className="flex items-center gap-2">
            <Zap size={16} className="text-accent" />
            <h3 className="text-sm font-semibold">Recent Model Activity</h3>
          </div>
          <div className="mt-3 overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Column</th>
                  <th>Type</th>
                  <th>Ver</th>
                  <th>Samples</th>
                  <th>R²</th>
                  <th>Trained</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent_models.length > 0 ? (
                  stats.recent_models.map((m) => (
                    <tr key={m.id}>
                      <td className="font-medium">{m.column_type}</td>
                      <td>{m.model_type}</td>
                      <td className="tabular-nums">v{m.version}</td>
                      <td className="tabular-nums">{m.n_samples}</td>
                      <td className="tabular-nums">
                        {m.r2 !== null ? m.r2.toFixed(3) : '—'}
                      </td>
                      <td className="text-muted-foreground">
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

      {/* Calibration plot */}
      {calibration && calibration.n_points > 0 && (
        <div className="mt-6">
          <CalibrationPlot data={calibration} />
        </div>
      )}
    </div>
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
    <div className="stat-card" style={{ '--stat-color': color } as React.CSSProperties}>
      <div className="flex items-center gap-3 pt-1">
        <div className="shrink-0" style={{ color }}>{icon}</div>
        <div>
          <p className="text-2xl font-bold tabular-nums">{value}</p>
          <p className="text-xs text-muted-foreground">{label}</p>
        </div>
      </div>
    </div>
  );
}
