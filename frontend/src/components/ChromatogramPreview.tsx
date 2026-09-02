import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { ChromatogramResult } from '@/types';

interface ChromatogramPreviewProps {
  chromatogram: ChromatogramResult | null;
  loading?: boolean;
}

export function ChromatogramPreview({ chromatogram, loading }: ChromatogramPreviewProps) {
  if (loading) {
    return (
      <div className="card animate-pulse">
        <div className="h-4 w-32 rounded bg-muted" />
        <div className="mt-2 h-[200px] w-full rounded bg-muted" />
      </div>
    );
  }

  if (!chromatogram) {
    return (
      <div className="card text-sm text-muted-foreground">
        Predicted chromatogram will appear here.
      </div>
    );
  }

  const data = chromatogram.times.map((t, i) => ({
    time: t / 60,
    intensity: chromatogram.intensities[i],
  }));

  return (
    <div className="card">
      <h3 className="text-sm font-semibold">Predicted Chromatogram</h3>
      <ResponsiveContainer width="100%" height={200} className="mt-2">
        <AreaChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <defs>
            <linearGradient id="peakGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="hsl(var(--accent))" stopOpacity={0.8} />
              <stop offset="95%" stopColor="hsl(var(--accent))" stopOpacity={0} />
            </linearGradient>
          </defs>
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
            label={{ value: 'Intensity', angle: -90, position: 'insideLeft', fontSize: 11 }}
            stroke="hsl(var(--muted-foreground))"
            fontSize={11}
          />
          <Tooltip
            formatter={(v: number) => [v.toFixed(3), 'Intensity']}
            labelFormatter={(l: number) => `${l.toFixed(1)} min`}
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '6px',
              fontSize: '12px',
            }}
          />
          <Area
            type="monotone"
            dataKey="intensity"
            stroke="hsl(var(--accent))"
            strokeWidth={1.5}
            fill="url(#peakGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
      {chromatogram.peaks.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {chromatogram.peaks.map((p, i) => (
            <span
              key={i}
              className="rounded bg-muted px-2 py-0.5 text-xs tabular-nums text-muted-foreground"
            >
              {p.label || `Peak ${i + 1}`}: {p.rt_s.toFixed(0)}s
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
