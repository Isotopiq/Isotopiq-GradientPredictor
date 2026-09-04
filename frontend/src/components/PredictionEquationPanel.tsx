import { useState, useEffect, useRef } from 'react';
import { TrendingUp, Plus, Trash2, Calculator, AlertTriangle, CheckCircle2, Download } from 'lucide-react';
import { methodsApi } from '@/api/methods';
import { toast } from 'sonner';
import type { KnownCompoundRT, PredictionEquation, PredictionResult } from '@/types';

interface Props {
  /** SMILES strings from the parent compound list — auto-populates the table */
  compoundsSmiles?: string[];
  /** Optional compound names aligned with compoundsSmiles */
  compoundNames?: string[];
  /** Optional predicted RT values (in minutes) aligned with compoundsSmiles */
  compoundRts?: (number | null)[];
}

export function PredictionEquationPanel({ compoundsSmiles, compoundNames, compoundRts }: Props) {
  const [compounds, setCompounds] = useState<KnownCompoundRT[]>([
    { smiles: '', rt_min: 0, ph: 2.7 },
    { smiles: '', rt_min: 0, ph: 2.7 },
    { smiles: '', rt_min: 0, ph: 2.7 },
    { smiles: '', rt_min: 0, ph: 2.7 },
    { smiles: '', rt_min: 0, ph: 2.7 },
  ]);
  const [equation, setEquation] = useState<PredictionEquation | null>(null);
  const [building, setBuilding] = useState(false);
  const [newSmiles, setNewSmiles] = useState('');
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [predicting, setPredicting] = useState(false);
  // Track whether the user has manually edited RT values so we don't overwrite them
  const userEditedRTs = useRef<Set<number>>(new Set());

  // Auto-populate SMILES and predicted RTs from the parent compound list.
  // Preserves any RT values the user has already entered manually.
  useEffect(() => {
    if (!compoundsSmiles || compoundsSmiles.length === 0) return;

    setCompounds((prev) => {
      // Build a lookup of existing SMILES → RT to preserve user-entered values
      const existingRtBySmiles = new Map<string, number>();
      for (const c of prev) {
        if (c.smiles && c.rt_min > 0) {
          existingRtBySmiles.set(c.smiles, c.rt_min);
        }
      }

      // Map the incoming compound list to table rows, using predicted RTs as defaults
      const newRows: KnownCompoundRT[] = compoundsSmiles.map((smi, i) => ({
        smiles: smi,
        rt_min: existingRtBySmiles.get(smi) || (compoundRts?.[i] ?? 0),
        ph: prev[0]?.ph ?? 2.7,
      }));

      // If we have fewer than 5 rows, pad with empty rows
      while (newRows.length < 5) {
        newRows.push({ smiles: '', rt_min: 0, ph: prev[0]?.ph ?? 2.7 });
      }

      return newRows;
    });
  }, [compoundsSmiles, compoundRts]);

  const updateCompound = (i: number, field: keyof KnownCompoundRT, value: string | number) => {
    const updated = [...compounds];
    updated[i] = { ...updated[i], [field]: value };
    setCompounds(updated);
  };

  const addRow = () => {
    setCompounds([...compounds, { smiles: '', rt_min: 0, ph: 2.7 }]);
  };

  const removeRow = (i: number) => {
    if (compounds.length <= 5) {
      toast.error('Need at least 5 compounds');
      return;
    }
    setCompounds(compounds.filter((_, idx) => idx !== i));
  };

  const handleLoadFromMethod = () => {
    if (!compoundsSmiles || compoundsSmiles.length === 0) {
      toast.error('No compounds in the method — add compounds first');
      return;
    }
    setCompounds((prev) => {
      const existingRtBySmiles = new Map<string, number>();
      for (const c of prev) {
        if (c.smiles && c.rt_min > 0) {
          existingRtBySmiles.set(c.smiles, c.rt_min);
        }
      }
      const newRows: KnownCompoundRT[] = compoundsSmiles.map((smi, i) => ({
        smiles: smi,
        rt_min: existingRtBySmiles.get(smi) || (compoundRts?.[i] ?? 0),
        ph: prev[0]?.ph ?? 2.7,
      }));
      while (newRows.length < 5) {
        newRows.push({ smiles: '', rt_min: 0, ph: prev[0]?.ph ?? 2.7 });
      }
      return newRows;
    });
    toast.success(`Loaded ${compoundsSmiles.length} compound(s) from method`);
  };

  const handleBuild = async () => {
    const valid = compounds.filter(c => c.smiles.trim() && c.rt_min > 0);
    if (valid.length < 5) {
      toast.error(`Need at least 5 compounds with SMILES and RT, got ${valid.length}`);
      return;
    }
    setBuilding(true);
    try {
      const eq = await methodsApi.buildPredictionEquation(valid);
      setEquation(eq);
      setPrediction(null);
      toast.success(`Equation built: R=${eq.r.toFixed(3)}, R²=${eq.r_squared.toFixed(3)}, StD=${eq.std_dev.toFixed(2)} min`);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Failed to build equation';
      toast.error(msg);
    } finally {
      setBuilding(false);
    }
  };

  const handlePredict = async () => {
    if (!equation) return;
    if (!newSmiles.trim()) {
      toast.error('Enter a SMILES to predict');
      return;
    }
    setPredicting(true);
    try {
      const result = await methodsApi.predictRT({
        equation,
        smiles: newSmiles,
        ph: compounds[0]?.ph || 2.7,
      });
      setPrediction(result);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Prediction failed';
      toast.error(msg);
    } finally {
      setPredicting(false);
    }
  };

  return (
    <div className="card-scientific">
      <div className="flex items-center gap-2">
        <TrendingUp className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold">Prediction Equation Mode</h3>
        <span className="text-[10px] text-muted-foreground">Build RT equation from ≥5 known compounds</span>
      </div>

      {/* Load from method button */}
      {compoundsSmiles && compoundsSmiles.length > 0 && (
        <button
          onClick={handleLoadFromMethod}
          className="mt-2 flex items-center gap-1 text-xs text-accent hover:underline"
        >
          <Download className="h-3 w-3" /> Load {compoundsSmiles.length} compound(s) from method
        </button>
      )}

      {/* Known compounds table */}
      <div className="mt-3">
        <div className="text-xs font-semibold text-muted-foreground mb-1">
          Known Compounds ({compounds.length})
          {compoundNames && compoundNames.length > 0 && (
            <span className="ml-2 text-[10px] text-muted-foreground/70">
              (names shown where available)
            </span>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border">
                <th className="px-1 py-1 text-left">SMILES</th>
                <th className="px-1 py-1 text-right">RT (min)</th>
                <th className="px-1 py-1 text-right">pH</th>
                <th className="px-1 py-1"></th>
              </tr>
            </thead>
            <tbody>
              {compounds.map((c, i) => {
                const name = compoundNames?.[i];
                return (
                  <tr key={i} className="border-b border-border/50">
                    <td className="px-1 py-1">
                      <input
                        type="text"
                        value={c.smiles}
                        onChange={(e) => updateCompound(i, 'smiles', e.target.value)}
                        placeholder="SMILES"
                        title={name || undefined}
                        className="w-full rounded border border-border bg-background px-1 py-0.5 text-xs"
                      />
                      {name && (
                        <span className="text-[9px] text-muted-foreground">{name}</span>
                      )}
                    </td>
                    <td className="px-1 py-1">
                      <input
                        type="number"
                        step="0.01"
                        value={c.rt_min}
                        onChange={(e) => updateCompound(i, 'rt_min', parseFloat(e.target.value) || 0)}
                        className="w-20 rounded border border-border bg-background px-1 py-0.5 text-xs text-right"
                      />
                    </td>
                    <td className="px-1 py-1">
                      <input
                        type="number"
                        step="0.1"
                        value={c.ph}
                        onChange={(e) => updateCompound(i, 'ph', parseFloat(e.target.value) || 0)}
                        className="w-16 rounded border border-border bg-background px-1 py-0.5 text-xs text-right"
                      />
                    </td>
                    <td className="px-1 py-1">
                      <button onClick={() => removeRow(i)} className="text-red-500 hover:text-red-700">
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <button onClick={addRow} className="mt-1 flex items-center gap-1 text-xs text-accent hover:underline">
          <Plus className="h-3 w-3" /> Add row
        </button>
      </div>

      <button
        onClick={handleBuild}
        disabled={building}
        className="btn-primary mt-3 flex items-center gap-1 text-xs"
      >
        <Calculator className="h-3 w-3" />
        {building ? 'Building...' : 'Build Equation'}
      </button>

      {/* Equation results */}
      {equation && (
        <div className="mt-3 space-y-2">
          <div className="rounded-md bg-muted/50 p-2 text-xs">
            <div className="flex gap-4">
              <span><strong>R:</strong> {equation.r.toFixed(4)}</span>
              <span><strong>R²:</strong> {equation.r_squared.toFixed(4)}</span>
              <span><strong>StD:</strong> {equation.std_dev.toFixed(3)} min</span>
              <span><strong>n:</strong> {equation.n}</span>
            </div>
            <div className="mt-1 font-mono text-[10px]">
              RT = {equation.intercept.toFixed(4)}
              {equation.descriptor_names.map(name => (
                <span key={name}>
                  {' + '}{equation.coefficients[name]?.toFixed(6)} × {name}
                </span>
              ))}
            </div>
          </div>

          {/* Predict new compound */}
          <div className="border-t border-border pt-2">
            <div className="text-xs font-semibold text-muted-foreground mb-1">Predict New Compound</div>
            <div className="flex gap-2">
              <input
                type="text"
                value={newSmiles}
                onChange={(e) => setNewSmiles(e.target.value)}
                placeholder="Enter SMILES to predict RT"
                className="flex-1 rounded border border-border bg-background px-2 py-1 text-xs"
              />
              <button
                onClick={handlePredict}
                disabled={predicting}
                className="btn-secondary text-xs"
              >
                {predicting ? '...' : 'Predict'}
              </button>
            </div>
          </div>

          {/* Prediction result */}
          {prediction && (
            <div className={`rounded-md p-2 text-xs ${prediction.in_applicability_domain ? 'bg-green-500/10' : 'bg-yellow-500/10'}`}>
              <div className="flex items-center gap-2">
                {prediction.in_applicability_domain ? (
                  <CheckCircle2 className="h-3 w-3 text-green-500" />
                ) : (
                  <AlertTriangle className="h-3 w-3 text-yellow-500" />
                )}
                <span className="font-semibold">Predicted RT:</span>
                <span>{prediction.predicted_rt_min.toFixed(2)} min</span>
                <span className="text-muted-foreground">
                  (CI: {prediction.confidence_interval_lower.toFixed(2)} – {prediction.confidence_interval_upper.toFixed(2)})
                </span>
              </div>
              {prediction.extrapolation_warnings.length > 0 && (
                <ul className="mt-1 ml-5 list-disc text-[10px] text-yellow-600">
                  {prediction.extrapolation_warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
