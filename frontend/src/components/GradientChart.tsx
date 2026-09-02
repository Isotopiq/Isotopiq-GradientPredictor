import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { GradientPoint } from '@/types';

interface GradientChartProps {
  gradientTable: GradientPoint[] | null;
  predictedRtS?: number | null;
}

export function GradientChart({ gradientTable, predictedRtS }: GradientChartProps) {
  if (!gradientTable || gradientTable.length === 0) {
    return (
      <div className="card text-sm text-muted-foreground">
        Gradient profile will appear here.
      </div>
    );
  }

  const data = gradientTable.map((p) => ({
    time: p.time_s / 60, // convert to minutes for display
    percentB: p.percent_b,
  }));

  return (
    <div className="card">
      <h3 className="text-sm font-semibold">Gradient Profile</h3>
      <ResponsiveContainer width="100%" height={200} className="mt-2">
        <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
          <XAxis
            dataKey="time"
            type="number"
            domain={['dataMin', 'dataMax']}
            tickFormatter={(v) => `${v.toFixed(1)}`}
            label={{ value: 'Time (min)', position: 'insideBottom', offset: -5, fontSize: 11 }}
            stroke="hsl(var(--muted-foreground))"
            fontSize={11}
          />
          <YAxis
            domain={[0, 100]}
            label={{ value: '%B', angle: -90, position: 'insideLeft', fontSize: 11 }}
            stroke="hsl(var(--muted-foreground))"
            fontSize={11}
          />
          <Tooltip
            formatter={(v) => {
              const n = typeof v === 'number' ? v : NaN;
              return [Number.isFinite(n) ? `${n.toFixed(1)}%` : '—', '%B'];
            }}
            labelFormatter={(l) => `${Number(l).toFixed(1)} min`}
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '6px',
              fontSize: '12px',
            }}
          />
          <Line
            type="linear"
            dataKey="percentB"
            stroke="hsl(var(--accent))"
            strokeWidth={2}
            dot={{ r: 3, fill: 'hsl(var(--accent))' }}
          />
          {predictedRtS && (
            <ReferenceLine
              x={predictedRtS / 60}
              stroke="hsl(var(--warning))"
              strokeDasharray="5 5"
              label={{ value: 'RT', fontSize: 10, fill: 'hsl(var(--warning))' }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
