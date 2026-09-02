import { useQuery } from '@tanstack/react-query';
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
  Area,
} from 'recharts';
import { compoundsApi } from '@/api/compounds';
import { Skeleton } from '@/components/Skeleton';
import { EmptyState } from '@/components/EmptyState';
import { Activity } from 'lucide-react';

interface PkaPlotterProps {
  smiles: string;
}

export function PkaPlotter({ smiles }: PkaPlotterProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['pka-plot', smiles],
    queryFn: () => compoundsApi.pkaPlot(smiles),
    enabled: !!smiles,
    staleTime: 300000, // 5 min cache
  });

  if (isLoading) return <SkeletonCard />;
  if (error || !data)
    return (
      <EmptyState
        icon={<Activity size={24} />}
        title="No pKa data available"
        description="Unable to compute ionization profile for this compound."
      />
    );

  const hasSites = data.sites.length > 0;
  const chartData = data.fractions.map((f) => ({
    ph: f.ph,
    fraction_ionized: f.fraction_ionized * 100,
    logd: f.logd,
  }));

  return (
    <div className="card-scientific">
      <div className="section-header mb-3">
        <div>
          <h2>pKa & Ionization Profile</h2>
          <p>Predicted ionization state and logD across pH range</p>
        </div>
      </div>

      {hasSites ? (
        <div className="mb-3 flex flex-wrap gap-2">
          {data.sites.map((site, i) => (
            <span
              key={i}
              className={`badge ${
                site.acid_base === 'acid' ? 'badge-warning' : 'badge-info'
              }`}
            >
              pKa {site.pka.toFixed(1)} ({site.acid_base})
            </span>
          ))}
          <span className="badge badge-success">
            Recommended pH: {data.recommended_ph.toFixed(1)}
          </span>
        </div>
      ) : (
        <p className="mb-3 text-sm text-muted-foreground">
          No ionizable sites detected — compound is neutral across the pH range.
        </p>
      )}

      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis
            dataKey="ph"
            type="number"
            domain={[0, 14]}
            ticks={[0, 2, 4, 6, 7, 8, 10, 12, 14]}
            stroke="hsl(var(--muted-foreground))"
            fontSize={11}
            label={{ value: 'pH', position: 'insideBottom', offset: -2, fontSize: 11 }}
          />
          <YAxis
            yAxisId="left"
            stroke="hsl(var(--chart-1))"
            fontSize={11}
            domain={[0, 100]}
            label={{ value: '% Ionized', angle: -90, position: 'insideLeft', fontSize: 11 }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke="hsl(var(--chart-3))"
            fontSize={11}
            label={{ value: 'logD', angle: 90, position: 'insideRight', fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
              fontSize: '12px',
            }}
            formatter={(value: number, name: string) => [
              name === 'fraction_ionized' ? `${value.toFixed(1)}%` : value.toFixed(2),
              name === 'fraction_ionized' ? '% Ionized' : 'logD',
            ]}
            labelFormatter={(label: number) => `pH ${label.toFixed(1)}`}
          />
          <Legend wrapperStyle={{ fontSize: '11px' }} />

          <Area
            yAxisId="left"
            type="monotone"
            dataKey="fraction_ionized"
            stroke="hsl(var(--chart-1))"
            fill="hsl(var(--chart-1))"
            fillOpacity={0.15}
            strokeWidth={2}
            name="% Ionized"
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="logd"
            stroke="hsl(var(--chart-3))"
            strokeWidth={2}
            dot={false}
            name="logD"
          />

          {data.pka_values.map((pka) => (
            <ReferenceLine
              key={pka}
              xAxisId={0}
              x={pka}
              stroke="hsl(var(--warning))"
              strokeDasharray="4 4"
              label={{ value: `pKa ${pka}`, fontSize: 10, fill: 'hsl(var(--warning))' }}
            />
          ))}
          <ReferenceLine
            xAxisId={0}
            x={data.recommended_ph}
            stroke="hsl(var(--success))"
            strokeWidth={2}
            label={{ value: 'Rec pH', fontSize: 10, fill: 'hsl(var(--success))' }}
          />
        </ComposedChart>
      </ResponsiveContainer>

      <p className="mt-2 text-xs text-muted-foreground">
        Estimates based on functional-group SMARTS heuristics. Verify experimentally for critical work.
      </p>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="card-scientific">
      <Skeleton className="h-5 w-40" />
      <Skeleton className="mt-3 h-4 w-full" />
      <Skeleton className="mt-2 h-[280px] w-full" />
    </div>
  );
}
