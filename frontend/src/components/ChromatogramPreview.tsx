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

// Distinct colors for multi-compound XIC peaks
const PEAK_COLORS = [
  '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
  '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
];

// Gaussian function matching the backend (FWHM -> sigma)
function gaussian(x: number, center: number, width: number, height: number): number {
  const sigma = width / (2.0 * Math.sqrt(2.0 * Math.log(2.0)));
  if (sigma <= 0) return 0;
  return height * Math.exp(-((x - center) ** 2) / (2.0 * sigma ** 2));
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
        Predicted chromatogram will appear here after recalculation.
      </div>
    );
  }

  const hasMultiplePeaks = chromatogram.peaks.length > 1;

  // Build per-peak XIC traces so each compound is visible as its own colored peak.
  // Each peak gets its own dataKey in the chart data, rendered as a separate Area.
  const timesMin = chromatogram.times.map((t) => t / 60);
  const peakTraces = chromatogram.peaks.map((p, i) => {
    const color = p.color || PEAK_COLORS[i % PEAK_COLORS.length];
    const key = `xic_${i}`;
    const values = chromatogram.times.map((t) =>
      gaussian(t, p.rt_s, p.width_s || 10, p.height || 1.0),
    );
    return { key, color, label: p.label || `Peak ${i + 1}`, rtMin: p.rt_s / 60, values };
  });

  // Build combined data: each time point has all XIC traces
  const data = timesMin.map((t, i) => {
    const row: Record<string, number> = { time: t };
    for (const trace of peakTraces) {
      row[trace.key] = trace.values[i];
    }
    return row;
  });

  return (
    <div className="card">
      <h3 className="text-sm font-semibold">
        Predicted Chromatogram (XIC)
        {hasMultiplePeaks && (
          <span className="ml-2 text-xs font-normal text-muted-foreground">
            ({chromatogram.peaks.length} compounds)
          </span>
        )}
      </h3>
      <ResponsiveContainer width="100%" height={220} className="mt-2">
        <AreaChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <defs>
            {peakTraces.map((trace) => (
              <linearGradient key={trace.key} id={`grad_${trace.key}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={trace.color} stopOpacity={0.5} />
                <stop offset="95%" stopColor={trace.color} stopOpacity={0} />
              </linearGradient>
            ))}
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
            formatter={(v: number, name: string) => {
              const trace = peakTraces.find((t) => `xic_${peakTraces.indexOf(t)}` === name || t.key === name);
              const label = trace?.label || name;
              return [Number.isFinite(v) ? v.toFixed(3) : '—', label];
            }}
            labelFormatter={(l) => `${Number(l).toFixed(1)} min`}
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '6px',
              fontSize: '12px',
            }}
          />
          {peakTraces.map((trace) => (
            <Area
              key={trace.key}
              type="monotone"
              dataKey={trace.key}
              stroke={trace.color}
              strokeWidth={1.8}
              fill={`url(#grad_${trace.key})`}
              connectNulls={false}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
      {chromatogram.peaks.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {peakTraces.map((trace, i) => (
            <span
              key={i}
              className="flex items-center gap-1 rounded bg-muted px-2 py-0.5 text-xs tabular-nums text-muted-foreground"
            >
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ backgroundColor: trace.color }}
              />
              {trace.label}: {trace.rtMin.toFixed(2)} min
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
