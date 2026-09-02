import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from 'recharts';

interface LearningCurveChartProps {
  versions: Array<{
    version: number;
    r2: number | null;
    rmse: number | null;
    n_samples: number;
    trained_at: string | null;
  }>;
}

export function LearningCurveChart({ versions }: LearningCurveChartProps) {
  if (versions.length === 0) {
    return (
      <div className="card-scientific py-8 text-center text-sm text-muted-foreground">
        No model versions available yet.
      </div>
    );
  }

  const data = versions.map((v) => ({
    version: `v${v.version}`,
    r2: v.r2 ?? 0,
    rmse: v.rmse ?? 0,
    n_samples: v.n_samples,
  }));

  // Check if latest version is worse than previous
  const lastTwo = versions.slice(-2);
  const isDeclining = lastTwo.length === 2 &&
    lastTwo[0].r2 != null && lastTwo[1].r2 != null &&
    lastTwo[1].r2 < lastTwo[0].r2;

  return (
    <div className="card-scientific">
      <div className="section-header mb-3">
        <div>
          <h2>Learning Curve</h2>
          <p>Model performance across versions</p>
        </div>
        {isDeclining && (
          <span className="badge badge-warning">
            Performance decline detected
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data} margin={{ top: 5, right: 30, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey="version" stroke="hsl(var(--muted-foreground))" fontSize={11} />
          <YAxis
            yAxisId="left"
            stroke="hsl(var(--chart-1))"
            fontSize={11}
            domain={[0, 1]}
            label={{ value: 'R²', angle: -90, position: 'insideLeft', fontSize: 11 }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke="hsl(var(--chart-4))"
            fontSize={11}
            label={{ value: 'RMSE', angle: 90, position: 'insideRight', fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
              fontSize: '12px',
            }}
          />
          <Legend wrapperStyle={{ fontSize: '11px' }} />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="r2"
            stroke="hsl(var(--chart-1))"
            strokeWidth={2}
            dot={{ r: 4 }}
            name="R²"
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="rmse"
            stroke="hsl(var(--chart-4))"
            strokeWidth={2}
            dot={{ r: 4 }}
            name="RMSE (s)"
          />
          <ReferenceLine yAxisId="left" y={0.9} stroke="hsl(var(--success))" strokeDasharray="4 4" label="Good fit" />
        </LineChart>
      </ResponsiveContainer>

      <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
        {versions.slice(-3).map((v, i) => (
          <div key={i} className="rounded-md border border-border p-2">
            <p className="font-semibold">v{v.version}</p>
            <p className="text-muted-foreground">R²: {v.r2?.toFixed(3) ?? '—'}</p>
            <p className="text-muted-foreground">{v.n_samples} samples</p>
          </div>
        ))}
      </div>
    </div>
  );
}
