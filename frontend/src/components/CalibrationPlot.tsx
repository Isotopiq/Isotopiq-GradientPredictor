import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Line,
  ComposedChart,
  Legend,
} from 'recharts';
import type { CalibrationData } from '@/types';

interface CalibrationPlotProps {
  data: CalibrationData;
}

export function CalibrationPlot({ data }: CalibrationPlotProps) {
  if (data.n_points === 0) {
    return (
      <div className="card-scientific py-8 text-center text-sm text-muted-foreground">
        No calibration data available. Log experimental runs with predictions to see calibration.
      </div>
    );
  }

  const { points, regression } = data;

  // Create scatter points
  const scatterData = points.map((p) => ({
    x: p.observed_rt_s,
    y: p.predicted_rt_s,
    label: p.compound_name || p.compound_smiles?.slice(0, 20),
    model: p.model_version,
  }));

  // Create regression line
  const maxRt = Math.max(...points.map((p) => Math.max(p.observed_rt_s, p.predicted_rt_s)));
  const regLine = [
    { x: 0, y: regression.intercept },
    { x: maxRt * 1.1, y: regression.intercept + regression.slope * maxRt * 1.1 },
  ];

  // Ideal y=x line
  const idealLine = [
    { x: 0, y: 0 },
    { x: maxRt * 1.1, y: maxRt * 1.1 },
  ];

  return (
    <div className="card-scientific">
      <div className="section-header mb-3">
        <div>
          <h2>Calibration Plot</h2>
          <p>Predicted vs observed retention time ({data.n_points} points)</p>
        </div>
        <div className="flex gap-2 text-xs">
          <span className="badge badge-info">R² = {Number.isFinite(regression.r2) ? regression.r2.toFixed(3) : '—'}</span>
          <span className="badge badge-warning">RMSE = {Number.isFinite(regression.rmse) ? regression.rmse.toFixed(1) : '—'}s</span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart margin={{ top: 20, right: 30, bottom: 20, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis
            type="number"
            dataKey="x"
            name="Observed RT"
            unit="s"
            stroke="hsl(var(--muted-foreground))"
            fontSize={11}
            domain={[0, maxRt * 1.1]}
            label={{ value: 'Observed RT (s)', position: 'insideBottom', offset: -10, fontSize: 11 }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Predicted RT"
            unit="s"
            stroke="hsl(var(--muted-foreground))"
            fontSize={11}
            domain={[0, maxRt * 1.1]}
            label={{ value: 'Predicted RT (s)', angle: -90, position: 'insideLeft', fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
              fontSize: '12px',
            }}
            formatter={(value, name) => {
              const v: number = typeof value === 'number' ? value : Array.isArray(value) ? Number(value[0]) : NaN;
              return [Number.isFinite(v) ? `${v.toFixed(1)}s` : '—', String(name)];
            }}
          />
          <Legend wrapperStyle={{ fontSize: '11px' }} />

          {/* Ideal y=x line */}
          <Line
            data={idealLine}
            dataKey="y"
            stroke="hsl(var(--success))"
            strokeWidth={1.5}
            strokeDasharray="6 4"
            dot={false}
            name="Ideal (y=x)"
            isAnimationActive={false}
          />

          {/* Regression line */}
          <Line
            data={regLine}
            dataKey="y"
            stroke="hsl(var(--chart-4))"
            strokeWidth={2}
            dot={false}
            name="Regression"
            isAnimationActive={false}
          />

          {/* Scatter points */}
          <Scatter
            data={scatterData}
            fill="hsl(var(--chart-1))"
            fillOpacity={0.6}
            name="Predictions"
          />
        </ComposedChart>
      </ResponsiveContainer>

      <p className="mt-2 text-xs text-muted-foreground">
        Points should cluster along the green dashed line (y=x) for well-calibrated predictions.
      </p>
    </div>
  );
}
