import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { getFeatureCategory } from '@/lib/featureDescriptions';
import type { FeatureImportance } from '@/types';

interface FeatureImportanceChartProps {
  data: FeatureImportance;
}

const categoryColors: Record<string, string> = {
  molecular: 'hsl(var(--chart-1))',
  method: 'hsl(var(--chart-3))',
  column: 'hsl(var(--chart-5))',
};

export function FeatureImportanceChart({ data }: FeatureImportanceChartProps) {
  if (!data.features || data.features.length === 0) {
    return (
      <div className="card-scientific py-8 text-center text-sm text-muted-foreground">
        Feature importance not available for this model type.
      </div>
    );
  }

  // Take top 15 features
  const topFeatures = data.features.slice(0, 15).map((f) => ({
    name: f.name,
    importance: f.importance,
    category: getFeatureCategory(f.name),
  }));

  return (
    <div className="card-scientific">
      <div className="section-header mb-3">
        <div>
          <h2>Feature Importance</h2>
          <p>{data.model_type} • {data.column_type} • v{data.version}</p>
        </div>
        <div className="flex gap-2 text-xs">
          <span className="badge badge-info">Molecular</span>
          <span className="badge badge-warning">Method</span>
          <span className="badge" style={{ background: 'hsl(var(--chart-5) / 0.1)', color: 'hsl(var(--chart-5))' }}>Column</span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <BarChart
          data={topFeatures}
          layout="vertical"
          margin={{ top: 5, right: 20, bottom: 5, left: 100 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
          <XAxis
            type="number"
            stroke="hsl(var(--muted-foreground))"
            fontSize={11}
            label={{ value: 'Importance', position: 'insideBottom', offset: -2, fontSize: 11 }}
          />
          <YAxis
            type="category"
            dataKey="name"
            stroke="hsl(var(--muted-foreground))"
            fontSize={10}
            width={100}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
              fontSize: '12px',
            }}
            formatter={(value) => {
              const v = typeof value === 'number' ? value : NaN;
              return [Number.isFinite(v) ? v.toFixed(4) : '—', 'Importance'];
            }}
          />
          <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
            {topFeatures.map((entry, idx) => (
              <Cell key={idx} fill={categoryColors[entry.category] ?? 'hsl(var(--muted-foreground))'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
