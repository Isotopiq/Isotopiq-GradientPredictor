import { useState } from 'react';
import { Map, Calculator } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Legend } from 'recharts';
import { methodsApi } from '@/api/methods';
import { toast } from 'sonner';
import type { ResolutionMap1D as ResMap1DType } from '@/types';

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
  { value: 'gradient_time', label: 'Gradient Time (min)', min: 5, max: 60 },
  { value: 'ph', label: 'pH', min: 2, max: 10 },
  { value: 'temperature', label: 'Temperature (°C)', min: 20, max: 60 },
  { value: 'flow_rate', label: 'Flow Rate (mL/min)', min: 0.1, max: 1.0 },
  { value: 'percent_b_start', label: '%B Start', min: 2, max: 30 },
  { value: 'percent_b_end', label: '%B End', min: 60, max: 98 },
];

export function ResolutionMap1D({ smilesList, methodParams }: Props) {
  const [variable, setVariable] = useState('gradient_time');
  const [varMin, setVarMin] = useState(5);
  const [varMax, setVarMax] = useState(60);
  const [steps, setSteps] = useState(20);
  const [result, setResult] = useState<ResMap1DType | null>(null);
  const [loading, setLoading] = useState(false);

  const handleCompute = async () => {
    if (smilesList.length < 2) {
      toast.error('Need at least 2 compounds');
      return;
    }
    setLoading(true);
    try {
      const res = await methodsApi.resolutionMap1D({
        smiles_list: smilesList,
        variable,
        var_min: varMin,
        var_max: varMax,
        steps,
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
      toast.error(e?.response?.data?.detail || 'Failed to compute resolution map');
    } finally {
      setLoading(false);
    }
  };

  const chartData = result ? result.x_values.map((x, i) => {
    const row: Record<string, number> = { x };
    row['min_rs'] = result.min_rs[i];
    result.per_compound_rts.forEach((rts, ci) => {
      row[`C${ci + 1}`] = rts[i];
    });
    return row;
  }) : [];

  const varLabel = VARIABLES.find(v => v.value === variable)?.label || variable;

  return (
    <div className="card-scientific">
      <div className="flex items-center gap-2">
        <Map className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold">1D Resolution Map</h3>
      </div>

      <div className="mt-3 grid grid-cols-4 gap-2">
        <label className="col-span-2 block">
          <span className="text-xs text-muted-foreground">Variable</span>
          <select value={variable} onChange={(e) => {
            setVariable(e.target.value);
            const v = VARIABLES.find(v => v.value === e.target.value);
            if (v) { setVarMin(v.min); setVarMax(v.max); }
          }} className="mt-1 w-full rounded border border-border bg-background px-1 py-1 text-xs">
            {VARIABLES.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
          </select>
        </label>
        <label className="block">
          <span className="text-xs text-muted-foreground">Min</span>
          <input type="number" step="0.1" value={varMin}
            onChange={(e) => setVarMin(parseFloat(e.target.value) || 0)}
            className="mt-1 w-full rounded border border-border bg-background px-1 py-1 text-xs" />
        </label>
        <label className="block">
          <span className="text-xs text-muted-foreground">Max</span>
          <input type="number" step="0.1" value={varMax}
            onChange={(e) => setVarMax(parseFloat(e.target.value) || 0)}
            className="mt-1 w-full rounded border border-border bg-background px-1 py-1 text-xs" />
        </label>
      </div>

      <button onClick={handleCompute} disabled={loading} className="btn-primary mt-2 flex items-center gap-1 text-xs">
        <Calculator className="h-3 w-3" /> {loading ? 'Computing...' : 'Compute Map'}
      </button>

      {result && (
        <div className="mt-3">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="x" label={{ value: varLabel, position: 'bottom', fontSize: 10 }} tick={{ fontSize: 10 }} />
              <YAxis yAxisId="rs" label={{ value: 'Min Rs', angle: -90, position: 'insideLeft', fontSize: 10 }} tick={{ fontSize: 10 }} />
              <YAxis yAxisId="rt" orientation="right" label={{ value: 'RT (s)', angle: 90, position: 'insideRight', fontSize: 10 }} tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 10 }} />
              <ReferenceLine yAxisId="rs" y={1.5} stroke="#10b981" strokeDasharray="5 5" label={{ value: 'Rs=1.5', fontSize: 9, fill: '#10b981' }} />
              <ReferenceLine yAxisId="rs" y={1.0} stroke="#f59e0b" strokeDasharray="5 5" label={{ value: 'Rs=1.0', fontSize: 9, fill: '#f59e0b' }} />
              <Line yAxisId="rs" type="monotone" dataKey="min_rs" stroke="#ef4444" strokeWidth={2} dot={false} name="Min Rs" />
              {result.per_compound_rts.map((_, i) => (
                <Line key={i} yAxisId="rt" type="monotone" dataKey={`C${i + 1}`} stroke={`hsl(${i * 60}, 70%, 50%)`} strokeWidth={1} dot={false} name={`Compound ${i + 1} RT`} />
              ))}
            </LineChart>
          </ResponsiveContainer>
          {result.co_elution_points.length > 0 && (
            <p className="mt-1 text-[10px] text-red-500">
              {result.co_elution_points.length} co-elution point(s) detected (Rs &lt; 0.8)
            </p>
          )}
        </div>
      )}
    </div>
  );
}
