import { useState } from 'react';
import { GitBranch, Plus, Trash2, Calculator, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { methodsApi } from '@/api/methods';
import { toast } from 'sonner';
import type { CalibrationPoint, ModelSelectionResult } from '@/types';

export function ModelSelectionPanel() {
  const [points, setPoints] = useState<CalibrationPoint[]>([
    { gradient_time_min: 10, observed_rt_min: 0 },
    { gradient_time_min: 20, observed_rt_min: 0 },
    { gradient_time_min: 30, observed_rt_min: 0 },
    { gradient_time_min: 40, observed_rt_min: 0 },
  ]);
  const [threshold, setThreshold] = useState(0.75);
  const [result, setResult] = useState<ModelSelectionResult | null>(null);
  const [loading, setLoading] = useState(false);

  const updatePoint = (i: number, field: keyof CalibrationPoint, value: number) => {
    const updated = [...points];
    updated[i] = { ...updated[i], [field]: value };
    setPoints(updated);
  };

  const addPoint = () => setPoints([...points, { gradient_time_min: 0, observed_rt_min: 0 }]);
  const removePoint = (i: number) => setPoints(points.filter((_, idx) => idx !== i));

  const handleFit = async () => {
    const valid = points.filter(p => p.gradient_time_min > 0 && p.observed_rt_min > 0);
    if (valid.length < 2) {
      toast.error('Need at least 2 valid points');
      return;
    }
    setLoading(true);
    try {
      const res = await methodsApi.modelSelection(valid, threshold);
      setResult(res);
      toast.success(`Best model: ${res.best_model} (R²=${res.best_fit.r_squared.toFixed(4)})`);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Model fitting failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card-scientific">
      <div className="flex items-center gap-2">
        <GitBranch className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold">Model Selection</h3>
        <span className="text-[10px] text-muted-foreground">Linear / Quadratic / Log-Log</span>
      </div>

      <div className="mt-3">
        <div className="text-xs font-semibold text-muted-foreground mb-1">Calibration Points</div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border">
                <th className="px-1 py-1 text-left">Gradient Time (min)</th>
                <th className="px-1 py-1 text-left">Observed RT (min)</th>
                <th className="px-1 py-1"></th>
              </tr>
            </thead>
            <tbody>
              {points.map((p, i) => (
                <tr key={i} className="border-b border-border/50">
                  <td className="px-1 py-1">
                    <input type="number" step="0.1" value={p.gradient_time_min}
                      onChange={(e) => updatePoint(i, 'gradient_time_min', parseFloat(e.target.value) || 0)}
                      className="w-32 rounded border border-border bg-background px-1 py-0.5 text-xs" />
                  </td>
                  <td className="px-1 py-1">
                    <input type="number" step="0.01" value={p.observed_rt_min}
                      onChange={(e) => updatePoint(i, 'observed_rt_min', parseFloat(e.target.value) || 0)}
                      className="w-32 rounded border border-border bg-background px-1 py-0.5 text-xs" />
                  </td>
                  <td className="px-1 py-1">
                    <button onClick={() => removePoint(i)} className="text-red-500 hover:text-red-700">
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <button onClick={addPoint} className="mt-1 flex items-center gap-1 text-xs text-accent hover:underline">
          <Plus className="h-3 w-3" /> Add point
        </button>
      </div>

      <div className="mt-2 flex items-center gap-2">
        <label className="text-xs text-muted-foreground">Bad peaks threshold (min):</label>
        <input type="number" step="0.05" value={threshold}
          onChange={(e) => setThreshold(parseFloat(e.target.value) || 0)}
          className="w-20 rounded border border-border bg-background px-1 py-0.5 text-xs" />
      </div>

      <button onClick={handleFit} disabled={loading} className="btn-primary mt-2 flex items-center gap-1 text-xs">
        <Calculator className="h-3 w-3" /> {loading ? 'Fitting...' : 'Fit All Models'}
      </button>

      {result && (
        <div className="mt-3 space-y-2">
          <div className="rounded-md bg-green-500/10 p-2 text-xs">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-3 w-3 text-green-500" />
              <span className="font-semibold">Best: {result.best_model}</span>
              <span>R²={result.best_fit.r_squared.toFixed(4)}</span>
              <span>RMSE={result.best_fit.rmse.toFixed(4)}</span>
            </div>
            {result.best_quality.bad_peaks_count > 0 && (
              <div className="mt-1 flex items-center gap-1 text-yellow-600">
                <AlertTriangle className="h-3 w-3" />
                {result.best_quality.bad_peaks_count} bad peak(s) exceed threshold
              </div>
            )}
          </div>

          <div className="text-xs font-semibold text-muted-foreground">All Models</div>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border">
                <th className="px-1 py-1 text-left">Model</th>
                <th className="px-1 py-1 text-right">R²</th>
                <th className="px-1 py-1 text-right">RMSE</th>
                <th className="px-1 py-1 text-right">Bad Peaks</th>
              </tr>
            </thead>
            <tbody>
              {result.all_models.map((m) => (
                <tr key={m.model} className={`border-b border-border/50 ${m.model === result.best_model ? 'bg-green-500/5' : ''}`}>
                  <td className="px-1 py-1">{m.model}</td>
                  <td className="px-1 py-1 text-right">{m.fit.r_squared.toFixed(4)}</td>
                  <td className="px-1 py-1 text-right">{m.fit.rmse.toFixed(4)}</td>
                  <td className="px-1 py-1 text-right">{m.quality.bad_peaks_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
