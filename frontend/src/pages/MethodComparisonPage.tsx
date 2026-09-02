import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { GitCompare, Download } from 'lucide-react';
import { methodsApi } from '@/api/methods';
import { EmptyState } from '@/components/EmptyState';
import { GradientChart } from '@/components/GradientChart';

export function MethodComparisonPage() {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const { data: methods } = useQuery({
    queryKey: ['methods-for-compare'],
    queryFn: () => methodsApi.list(100),
  });

  const selectedMethods = (methods || []).filter((m) => selectedIds.includes(m.id));

  const toggleMethod = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : prev.length < 3 ? [...prev, id] : prev,
    );
  };

  // Build overlaid gradient chart data
  const overlaidData: Array<Record<string, number>> = [];
  const colors = ['hsl(var(--chart-1))', 'hsl(var(--chart-2))', 'hsl(var(--chart-3))'];

  if (selectedMethods.length > 0) {
    const maxTime = Math.max(
      ...selectedMethods.map((m) => {
        const gt = m.gradient_table || [];
        return gt.length > 0 ? gt[gt.length - 1].time_s : 0;
      }),
    );
    const steps = 100;
    for (let i = 0; i <= steps; i++) {
      const t = (i / steps) * maxTime;
      const row: Record<string, number> = { time: t / 60 };
      selectedMethods.forEach((m, idx) => {
        const gt = m.gradient_table || [];
        // Interpolate %B at time t
        let pctB = gt[0]?.percent_b ?? 0;
        for (let j = 0; j < gt.length - 1; j++) {
          if (t >= gt[j].time_s && t <= gt[j + 1].time_s) {
            const ratio = (t - gt[j].time_s) / (gt[j + 1].time_s - gt[j].time_s || 1);
            pctB = gt[j].percent_b + ratio * (gt[j + 1].percent_b - gt[j].percent_b);
            break;
          }
          if (t > gt[gt.length - 1].time_s) {
            pctB = gt[gt.length - 1].percent_b;
          }
        }
        row[`method${idx}`] = pctB;
      });
      overlaidData.push(row);
    }
  }

  const exportComparison = () => {
    const rows = selectedMethods.map((m) => ({
      name: m.name || 'Unnamed',
      column: m.column_type,
      ph: m.ph ?? '',
      flow: m.flow_rate_ml_min ?? '',
      temp: m.temperature_c ?? '',
      additive: m.additive ?? '',
    }));
    if (rows.length === 0) return;
    const headers = Object.keys(rows[0]);
    const csv = [headers.join(','), ...rows.map((r) => headers.map((h) => r[h as keyof typeof r]).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'method_comparison.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mx-auto max-w-6xl p-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold">Method Comparison</h1>
        <p className="text-sm text-muted-foreground">
          Select up to 3 methods to compare side-by-side
        </p>
      </div>

      {/* Method selector */}
      <div className="card-scientific mb-6">
        <h2 className="mb-3 text-sm font-semibold">Select Methods</h2>
        <div className="max-h-48 overflow-y-auto space-y-1">
          {(methods || []).map((m) => (
            <label
              key={m.id}
              className="flex cursor-pointer items-center gap-2 rounded-md p-2 hover:bg-muted"
            >
              <input
                type="checkbox"
                checked={selectedIds.includes(m.id)}
                onChange={() => toggleMethod(m.id)}
                disabled={!selectedIds.includes(m.id) && selectedIds.length >= 3}
                className="rounded accent-accent"
              />
              <span className="text-sm font-medium">{m.name || 'Unnamed'}</span>
              <span className="badge badge-muted">{m.column_type}</span>
              {m.ph && <span className="text-xs text-muted-foreground">pH {m.ph}</span>}
            </label>
          ))}
        </div>
      </div>

      {selectedMethods.length === 0 ? (
        <EmptyState
          icon={<GitCompare size={24} />}
          title="No methods selected"
          description="Select methods above to compare them side-by-side"
        />
      ) : (
        <div className="space-y-4">
          {/* Overlaid gradient chart */}
          <div className="card-scientific">
            <div className="section-header mb-3">
              <div>
                <h2>Overlaid Gradient Comparison</h2>
              </div>
              <button className="btn-outline btn-sm" onClick={exportComparison}>
                <Download size={14} className="mr-1" /> Export
              </button>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={overlaidData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="time"
                  type="number"
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={11}
                  label={{ value: 'Time (min)', position: 'insideBottom', offset: -2, fontSize: 11 }}
                />
                <YAxis
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={11}
                  domain={[0, 100]}
                  label={{ value: '%B', angle: -90, position: 'insideLeft', fontSize: 11 }}
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
                {selectedMethods.map((m, idx) => (
                  <Line
                    key={m.id}
                    type="monotone"
                    dataKey={`method${idx}`}
                    stroke={colors[idx]}
                    strokeWidth={2}
                    dot={false}
                    name={m.name || `Method ${idx + 1}`}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Side-by-side parameter cards */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {selectedMethods.map((m, idx) => (
              <div
                key={m.id}
                className="card-scientific"
                style={{ borderLeftColor: colors[idx] }}
              >
                <h3 className="text-sm font-semibold">{m.name || `Method ${idx + 1}`}</h3>
                <div className="mt-3 space-y-2 text-xs">
                  <ParamRow label="Column" value={m.column_type} />
                  <ParamRow label="pH" value={m.ph?.toFixed(1)} />
                  <ParamRow label="Flow" value={`${m.flow_rate_ml_min?.toFixed(2)} mL/min`} />
                  <ParamRow label="Temp" value={`${m.temperature_c?.toFixed(0)} °C`} />
                  <ParamRow label="Additive" value={m.additive} />
                  <ParamRow label="Mobile A" value={m.mobile_phase_a} />
                  <ParamRow label="Mobile B" value={m.mobile_phase_b} />
                </div>
                <div className="mt-3">
                  <GradientChart gradientTable={m.gradient_table || []} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ParamRow({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="flex justify-between border-b border-border pb-1 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value || '—'}</span>
    </div>
  );
}
