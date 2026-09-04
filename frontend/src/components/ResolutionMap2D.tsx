import { useState } from 'react';
import { Grid3x3, Calculator } from 'lucide-react';
import { methodsApi } from '@/api/methods';
import { toast } from 'sonner';
import type { ResolutionMap2D as ResMap2DType } from '@/types';

interface Props {
  smilesList: string[];
  methodParams?: {
    ph?: number;
    temperature?: number;
    flow_rate?: number;
    gradient_time?: number;
    percent_b_start?: number;
    percent_b_end?: number;
    column_type?: string;
  };
}

const VARIABLES = [
  { value: 'gradient_time', label: 'Gradient Time', min: 5, max: 60 },
  { value: 'ph', label: 'pH', min: 2, max: 10 },
  { value: 'temperature', label: 'Temperature', min: 20, max: 60 },
  { value: 'flow_rate', label: 'Flow Rate', min: 0.1, max: 1.0 },
  { value: 'percent_b_start', label: '%B Start', min: 2, max: 30 },
  { value: 'percent_b_end', label: '%B End', min: 60, max: 98 },
];

function rsColor(rs: number): string {
  if (rs >= 2.0) return '#10b981'; // green
  if (rs >= 1.5) return '#84cc16'; // lime
  if (rs >= 1.0) return '#f59e0b'; // amber
  if (rs >= 0.5) return '#f97316'; // orange
  return '#ef4444'; // red
}

export function ResolutionMap2D({ smilesList, methodParams }: Props) {
  const [varX, setVarX] = useState('gradient_time');
  const [varY, setVarY] = useState('temperature');
  const [xMin, setXMin] = useState(5);
  const [xMax, setXMax] = useState(60);
  const [yMin, setYMin] = useState(20);
  const [yMax, setYMax] = useState(60);
  const [stepsX, setStepsX] = useState(10);
  const [stepsY, setStepsY] = useState(8);
  const [result, setResult] = useState<ResMap2DType | null>(null);
  const [loading, setLoading] = useState(false);

  const handleCompute = async () => {
    if (smilesList.length < 2) {
      toast.error('Need at least 2 compounds');
      return;
    }
    setLoading(true);
    try {
      const res = await methodsApi.resolutionMap2D({
        smiles_list: smilesList,
        var_x: varX, var_x_min: xMin, var_x_max: xMax, steps_x: stepsX,
        var_y: varY, var_y_min: yMin, var_y_max: yMax, steps_y: stepsY,
        ph: methodParams?.ph,
        temperature: methodParams?.temperature,
        flow_rate: methodParams?.flow_rate,
        gradient_time: methodParams?.gradient_time,
        percent_b_start: methodParams?.percent_b_start,
        percent_b_end: methodParams?.percent_b_end,
        column_type: methodParams?.column_type,
      });
      setResult(res);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to compute 2D map');
    } finally {
      setLoading(false);
    }
  };

  const varXLabel = VARIABLES.find(v => v.value === varX)?.label || varX;
  const varYLabel = VARIABLES.find(v => v.value === varY)?.label || varY;

  return (
    <div className="card-scientific">
      <div className="flex items-center gap-2">
        <Grid3x3 className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold">2D Resolution Map (Heatmap)</h3>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <div className="text-xs font-semibold text-muted-foreground">X Axis</div>
          <select value={varX} onChange={(e) => {
            setVarX(e.target.value);
            const v = VARIABLES.find(v => v.value === e.target.value);
            if (v) { setXMin(v.min); setXMax(v.max); }
          }} className="w-full rounded border border-border bg-background px-1 py-1 text-xs">
            {VARIABLES.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
          </select>
          <div className="flex gap-1">
            <input type="number" step="0.1" value={xMin} onChange={(e) => setXMin(parseFloat(e.target.value) || 0)}
              className="w-20 rounded border border-border bg-background px-1 py-0.5 text-xs" placeholder="min" />
            <input type="number" step="0.1" value={xMax} onChange={(e) => setXMax(parseFloat(e.target.value) || 0)}
              className="w-20 rounded border border-border bg-background px-1 py-0.5 text-xs" placeholder="max" />
            <input type="number" step="1" value={stepsX} onChange={(e) => setStepsX(parseInt(e.target.value) || 5)}
              className="w-16 rounded border border-border bg-background px-1 py-0.5 text-xs" placeholder="steps" />
          </div>
        </div>
        <div className="space-y-1">
          <div className="text-xs font-semibold text-muted-foreground">Y Axis</div>
          <select value={varY} onChange={(e) => {
            setVarY(e.target.value);
            const v = VARIABLES.find(v => v.value === e.target.value);
            if (v) { setYMin(v.min); setYMax(v.max); }
          }} className="w-full rounded border border-border bg-background px-1 py-1 text-xs">
            {VARIABLES.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
          </select>
          <div className="flex gap-1">
            <input type="number" step="0.1" value={yMin} onChange={(e) => setYMin(parseFloat(e.target.value) || 0)}
              className="w-20 rounded border border-border bg-background px-1 py-0.5 text-xs" placeholder="min" />
            <input type="number" step="0.1" value={yMax} onChange={(e) => setYMax(parseFloat(e.target.value) || 0)}
              className="w-20 rounded border border-border bg-background px-1 py-0.5 text-xs" placeholder="max" />
            <input type="number" step="1" value={stepsY} onChange={(e) => setStepsY(parseInt(e.target.value) || 5)}
              className="w-16 rounded border border-border bg-background px-1 py-0.5 text-xs" placeholder="steps" />
          </div>
        </div>
      </div>

      <button onClick={handleCompute} disabled={loading} className="btn-primary mt-2 flex items-center gap-1 text-xs">
        <Calculator className="h-3 w-3" /> {loading ? 'Computing...' : 'Compute Heatmap'}
      </button>

      {result && (
        <div className="mt-3">
          {/* Canvas-based heatmap */}
          <div className="overflow-x-auto">
            <svg
              width={Math.max(result.x_values.length * 40, 300)}
              height={Math.max(result.y_values.length * 30, 200)}
              className="border border-border"
            >
              {/* Y-axis label */}
              <text x={5} y={15} fontSize={10} fill="currentColor" className="text-muted-foreground">
                {varYLabel} →
              </text>
              {result.rs_grid.map((row, yi) =>
                row.map((rs, xi) => (
                  <g key={`${xi}-${yi}`}>
                    <rect
                      x={40 + xi * 40}
                      y={20 + yi * 30}
                      width={40}
                      height={30}
                      fill={rsColor(rs)}
                      opacity={0.8}
                      stroke="#fff"
                      strokeWidth={0.5}
                    />
                    <text
                      x={40 + xi * 40 + 20}
                      y={20 + yi * 30 + 18}
                      fontSize={9}
                      fill="#fff"
                      textAnchor="middle"
                    >
                      {rs.toFixed(1)}
                    </text>
                  </g>
                ))
              )}
              {/* X-axis labels */}
              {result.x_values.map((x, i) => (
                <text key={i} x={40 + i * 40 + 20} y={result.y_values.length * 30 + 35}
                  fontSize={8} fill="currentColor" textAnchor="middle" className="text-muted-foreground">
                  {x.toFixed(1)}
                </text>
              ))}
              {/* Y-axis labels */}
              {result.y_values.map((y, i) => (
                <text key={i} x={35} y={20 + i * 30 + 18}
                  fontSize={8} fill="currentColor" textAnchor="end" className="text-muted-foreground">
                  {y.toFixed(1)}
                </text>
              ))}
              {/* Optimal point marker */}
              {result.optimal_point && (
                <circle
                  cx={40 + result.x_values.indexOf(result.optimal_point.x) * 40 + 20}
                  cy={20 + result.y_values.indexOf(result.optimal_point.y) * 30 + 15}
                  r={8}
                  fill="none"
                  stroke="#000"
                  strokeWidth={2}
                />
              )}
            </svg>
          </div>
          <div className="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
            <span>Color:</span>
            <span style={{ color: rsColor(0.3) }}>Rs&lt;0.5</span>
            <span style={{ color: rsColor(0.7) }}>0.5-1.0</span>
            <span style={{ color: rsColor(1.2) }}>1.0-1.5</span>
            <span style={{ color: rsColor(1.7) }}>1.5-2.0</span>
            <span style={{ color: rsColor(2.5) }}>&gt;2.0</span>
          </div>
          {result.optimal_point && (
            <p className="mt-1 text-xs">
              <span className="font-semibold">Optimal:</span> {varXLabel}={result.optimal_point.x.toFixed(1)}, {varYLabel}={result.optimal_point.y.toFixed(1)} (Rs={result.optimal_point.rs.toFixed(2)})
            </p>
          )}
        </div>
      )}
    </div>
  );
}
