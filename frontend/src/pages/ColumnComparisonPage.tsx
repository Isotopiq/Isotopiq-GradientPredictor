import { useState, useEffect } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend } from 'recharts';
import { Columns, Calculator } from 'lucide-react';
import { columnsApi } from '@/api/columns';
import { toast } from 'sonner';
import type { TanakaParameters, ColumnComparisonResult } from '@/types';

const PARAM_LABELS: Record<string, string> = {
  k_pb: 'Hydrophobicity',
  alpha_ch2: 'Methylene Sel.',
  alpha_t_o: 'Shape Sel.',
  alpha_c_p: 'H-Bond',
  alpha_b_a_76: 'Ion Exch. (7.6)',
  alpha_b_a_27: 'Ion Exch. (2.7)',
};

export function ColumnComparisonPage() {
  const [reference, setReference] = useState<Record<string, TanakaParameters>>({});
  const [selectedA, setSelectedA] = useState<string>('C18_endcapped');
  const [selectedB, setSelectedB] = useState<string>('phenyl');
  const [customA, setCustomA] = useState<TanakaParameters | null>(null);
  const [customB, setCustomB] = useState<TanakaParameters | null>(null);
  const [result, setResult] = useState<ColumnComparisonResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    columnsApi.getTanakaReference().then(res => {
      setReference(res.reference_columns);
    }).catch(() => toast.error('Failed to load reference columns'));
  }, []);

  const colA = customA || reference[selectedA];
  const colB = customB || reference[selectedB];

  const handleCompare = async () => {
    if (!colA || !colB) {
      toast.error('Select two columns');
      return;
    }
    setLoading(true);
    try {
      const res = await columnsApi.compareColumns(colA, colB);
      setResult(res);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Comparison failed');
    } finally {
      setLoading(false);
    }
  };

  // Radar chart data
  const radarData = colA && colB ? Object.keys(PARAM_LABELS).map(key => ({
    parameter: PARAM_LABELS[key],
    columnA: (colA as any)[key] || 0,
    columnB: (colB as any)[key] || 0,
  })) : [];

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-4">
      <div className="flex items-center gap-2">
        <Columns className="h-5 w-5 text-accent" />
        <h1 className="text-xl font-bold">Tanaka Column Comparison</h1>
      </div>
      <p className="text-sm text-muted-foreground">
        Compare columns using the six Tanaka characterization parameters with radar plots and Column Distance Factor (CDF).
      </p>

      <div className="grid grid-cols-2 gap-4">
        <div className="card-scientific">
          <h2 className="text-sm font-semibold">Column A</h2>
          <select value={selectedA} onChange={(e) => { setSelectedA(e.target.value); setCustomA(null); }}
            className="mt-2 w-full rounded border border-border bg-background px-2 py-1 text-sm">
            {Object.entries(reference).map(([key, col]) => (
              <option key={key} value={key}>{col.column_name}</option>
            ))}
          </select>
        </div>
        <div className="card-scientific">
          <h2 className="text-sm font-semibold">Column B</h2>
          <select value={selectedB} onChange={(e) => { setSelectedB(e.target.value); setCustomB(null); }}
            className="mt-2 w-full rounded border border-border bg-background px-2 py-1 text-sm">
            {Object.entries(reference).map(([key, col]) => (
              <option key={key} value={key}>{col.column_name}</option>
            ))}
          </select>
        </div>
      </div>

      <button onClick={handleCompare} disabled={loading} className="btn-primary flex items-center gap-2 text-sm">
        <Calculator className="h-4 w-4" /> {loading ? 'Comparing...' : 'Compare Columns'}
      </button>

      {/* Radar Chart */}
      {colA && colB && (
        <div className="card-scientific">
          <h2 className="text-sm font-semibold">Tanaka Parameter Radar</h2>
          <ResponsiveContainer width="100%" height={350}>
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="parameter" tick={{ fontSize: 10 }} />
              <PolarRadiusAxis tick={{ fontSize: 9 }} />
              <Radar name={colA.column_name} dataKey="columnA" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
              <Radar name={colB.column_name} dataKey="columnB" stroke="#ef4444" fill="#ef4444" fillOpacity={0.3} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Comparison Result */}
      {result && (
        <div className="space-y-3">
          <div className="card-scientific">
            <h2 className="text-sm font-semibold">Comparison Metrics</h2>
            <div className="mt-2 grid grid-cols-3 gap-3 text-sm">
              <div className="rounded-md bg-muted/50 p-2 text-center">
                <div className="text-xs text-muted-foreground">CDF</div>
                <div className="text-lg font-bold">{result.cdf.toFixed(3)}</div>
              </div>
              <div className="rounded-md bg-muted/50 p-2 text-center">
                <div className="text-xs text-muted-foreground">Similarity</div>
                <div className="text-lg font-bold">{(result.similarity * 100).toFixed(1)}%</div>
              </div>
              <div className="rounded-md bg-muted/50 p-2 text-center">
                <div className="text-xs text-muted-foreground">Orthogonality</div>
                <div className="text-lg font-bold">{(result.orthogonality * 100).toFixed(1)}%</div>
              </div>
            </div>
          </div>

          <div className="card-scientific">
            <h2 className="text-sm font-semibold">Parameter Differences</h2>
            <table className="mt-2 w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-2 py-1 text-left">Parameter</th>
                  <th className="px-2 py-1 text-right">Column A</th>
                  <th className="px-2 py-1 text-right">Column B</th>
                  <th className="px-2 py-1 text-right">|Δ|</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(PARAM_LABELS).map(key => (
                  <tr key={key} className="border-b border-border/50">
                    <td className="px-2 py-1">{PARAM_LABELS[key]}</td>
                    <td className="px-2 py-1 text-right">{(result.column_a as any)[key].toFixed(3)}</td>
                    <td className="px-2 py-1 text-right">{(result.column_b as any)[key].toFixed(3)}</td>
                    <td className="px-2 py-1 text-right">{result.parameter_differences[key].toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card-scientific text-xs text-muted-foreground">
            <p><strong>Interpretation:</strong></p>
            <ul className="ml-4 mt-1 list-disc space-y-1">
              <li><strong>CDF &lt; 1:</strong> Columns are very similar — substitutable for most methods.</li>
              <li><strong>CDF 1-3:</strong> Moderate difference — may require method adjustment.</li>
              <li><strong>CDF &gt; 3:</strong> Very different columns — useful for orthogonal screening.</li>
              <li><strong>High orthogonality:</strong> Columns provide complementary selectivity — good for 2D-LC.</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
