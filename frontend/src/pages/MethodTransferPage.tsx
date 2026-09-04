import { useState } from 'react';
import { ArrowRightLeft, Calculator, Info } from 'lucide-react';
import { methodsApi } from '@/api/methods';
import { toast } from 'sonner';
import type { TransferColumnSpec, MethodTransferResult } from '@/types';

const PRESETS = [
  { name: 'HPLC → UHPLC', src: { length_mm: 150, inner_diameter_mm: 4.6, particle_size_um: 5.0 }, tgt: { length_mm: 50, inner_diameter_mm: 2.1, particle_size_um: 1.7 } },
  { name: 'UHPLC → HPLC', src: { length_mm: 50, inner_diameter_mm: 2.1, particle_size_um: 1.7 }, tgt: { length_mm: 150, inner_diameter_mm: 4.6, particle_size_um: 5.0 } },
  { name: 'HPLC 4.6 → 2.1mm', src: { length_mm: 150, inner_diameter_mm: 4.6, particle_size_um: 5.0 }, tgt: { length_mm: 150, inner_diameter_mm: 2.1, particle_size_um: 5.0 } },
];

export function MethodTransferPage() {
  const [srcCol, setSrcCol] = useState<TransferColumnSpec>({ length_mm: 150, inner_diameter_mm: 4.6, particle_size_um: 5.0, dwell_volume_ml: 1.0, dead_volume_ml: 0.6 });
  const [tgtCol, setTgtCol] = useState<TransferColumnSpec>({ length_mm: 50, inner_diameter_mm: 2.1, particle_size_um: 1.7, dwell_volume_ml: 0.2, dead_volume_ml: 0.15 });
  const [flowRate, setFlowRate] = useState(1.0);
  const [gradientTable, setGradientTable] = useState([
    { time_min: 0, percent_b: 5 },
    { time_min: 1, percent_b: 5 },
    { time_min: 20, percent_b: 95 },
    { time_min: 21, percent_b: 95 },
  ]);
  const [injVol, setInjVol] = useState(10);
  const [temp, setTemp] = useState(30);
  const [preserveRes, setPreserveRes] = useState(true);
  const [result, setResult] = useState<MethodTransferResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handleTransfer = async () => {
    setLoading(true);
    try {
      const res = await methodsApi.methodTransfer({
        source_column: srcCol,
        target_column: tgtCol,
        flow_rate_ml_min: flowRate,
        gradient_table: gradientTable.map((r) => ({ time_s: r.time_min * 60, percent_b: r.percent_b })),
        injection_volume_ul: injVol,
        temperature_c: temp,
        preserve_resolution: preserveRes,
      });
      setResult(res);
      toast.success('Method transferred successfully');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Transfer failed');
    } finally {
      setLoading(false);
    }
  };

  const applyPreset = (i: number) => {
    const p = PRESETS[i];
    setSrcCol({ ...srcCol, ...p.src });
    setTgtCol({ ...tgtCol, ...p.tgt });
  };

  const updateGradientRow = (i: number, field: 'time_min' | 'percent_b', value: number) => {
    setGradientTable((prev) => prev.map((r, idx) => idx === i ? { ...r, [field]: value } : r));
  };

  const addGradientRow = () => {
    const last = gradientTable[gradientTable.length - 1];
    setGradientTable([...gradientTable, { time_min: (last?.time_min || 0) + 1, percent_b: last?.percent_b || 50 }]);
  };

  const removeGradientRow = (i: number) => {
    if (gradientTable.length > 2) setGradientTable(gradientTable.filter((_, idx) => idx !== i));
  };

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-4">
      <div className="flex items-center gap-2">
        <ArrowRightLeft className="h-5 w-5 text-accent" />
        <h1 className="text-xl font-bold">Method Transfer Assistant</h1>
      </div>
      <p className="text-sm text-muted-foreground">
        Transfer chromatographic methods between columns and instruments with geometric scaling.
      </p>

      {/* Presets */}
      <div className="flex gap-2">
        {PRESETS.map((p, i) => (
          <button key={i} onClick={() => applyPreset(i)} className="btn-secondary text-xs">
            {p.name}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Source Column */}
        <div className="card-scientific">
          <h2 className="text-sm font-semibold">Source Column</h2>
          <div className="mt-2 space-y-2">
            <NumField label="Length (mm)" value={srcCol.length_mm} onChange={(v) => setSrcCol({ ...srcCol, length_mm: v })} />
            <NumField label="I.D. (mm)" value={srcCol.inner_diameter_mm} onChange={(v) => setSrcCol({ ...srcCol, inner_diameter_mm: v })} />
            <NumField label="Particle (μm)" value={srcCol.particle_size_um} onChange={(v) => setSrcCol({ ...srcCol, particle_size_um: v })} />
            <NumField label="Dwell Vol (mL)" value={srcCol.dwell_volume_ml || 0} onChange={(v) => setSrcCol({ ...srcCol, dwell_volume_ml: v })} />
            <NumField label="Dead Vol (mL)" value={srcCol.dead_volume_ml || 0} onChange={(v) => setSrcCol({ ...srcCol, dead_volume_ml: v })} />
          </div>
        </div>

        {/* Target Column */}
        <div className="card-scientific">
          <h2 className="text-sm font-semibold">Target Column</h2>
          <div className="mt-2 space-y-2">
            <NumField label="Length (mm)" value={tgtCol.length_mm} onChange={(v) => setTgtCol({ ...tgtCol, length_mm: v })} />
            <NumField label="I.D. (mm)" value={tgtCol.inner_diameter_mm} onChange={(v) => setTgtCol({ ...tgtCol, inner_diameter_mm: v })} />
            <NumField label="Particle (μm)" value={tgtCol.particle_size_um} onChange={(v) => setTgtCol({ ...tgtCol, particle_size_um: v })} />
            <NumField label="Dwell Vol (mL)" value={tgtCol.dwell_volume_ml || 0} onChange={(v) => setTgtCol({ ...tgtCol, dwell_volume_ml: v })} />
            <NumField label="Dead Vol (mL)" value={tgtCol.dead_volume_ml || 0} onChange={(v) => setTgtCol({ ...tgtCol, dead_volume_ml: v })} />
          </div>
        </div>
      </div>

      {/* Method parameters */}
      <div className="card-scientific">
        <h2 className="text-sm font-semibold">Source Method Parameters</h2>
        <div className="mt-2 grid grid-cols-3 gap-2">
          <NumField label="Flow (mL/min)" value={flowRate} onChange={setFlowRate} />
          <NumField label="Inj Vol (μL)" value={injVol} onChange={setInjVol} />
          <NumField label="Temp (°C)" value={temp} onChange={setTemp} />
        </div>
        <label className="mt-2 flex items-center gap-2 text-xs">
          <input type="checkbox" checked={preserveRes} onChange={(e) => setPreserveRes(e.target.checked)} />
          Preserve resolution (scale gradient time)
        </label>
      </div>

      {/* Source gradient table (editable, in minutes) */}
      <div className="card-scientific">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Source Gradient Table</h2>
          <button onClick={addGradientRow} className="btn-secondary text-xs">+ Add Row</button>
        </div>
        <table className="mt-2 w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="px-2 py-1 text-left">Time (min)</th>
              <th className="px-2 py-1 text-left">%B</th>
              <th className="px-2 py-1"></th>
            </tr>
          </thead>
          <tbody>
            {gradientTable.map((p, i) => (
              <tr key={i} className="border-b border-border/50">
                <td className="px-2 py-1">
                  <input type="number" step="0.1" min="0" value={p.time_min}
                    onChange={(e) => updateGradientRow(i, 'time_min', parseFloat(e.target.value) || 0)}
                    className="w-24 rounded border border-border bg-background px-1 py-0.5 text-xs" />
                </td>
                <td className="px-2 py-1">
                  <input type="number" step="0.1" min="0" max="100" value={p.percent_b}
                    onChange={(e) => updateGradientRow(i, 'percent_b', parseFloat(e.target.value) || 0)}
                    className="w-24 rounded border border-border bg-background px-1 py-0.5 text-xs" />
                </td>
                <td className="px-2 py-1">
                  <button onClick={() => removeGradientRow(i)} className="text-red-500 hover:text-red-700 text-xs">✕</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button onClick={handleTransfer} disabled={loading} className="btn-primary flex items-center gap-2 text-sm">
        <Calculator className="h-4 w-4" /> {loading ? 'Transferring...' : 'Transfer Method'}
      </button>

      {/* Results */}
      {result && (
        <div className="space-y-3">
          <div className="card-scientific">
            <h2 className="text-sm font-semibold">Transferred Method</h2>
            <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
              <div><span className="text-muted-foreground">Flow:</span> {result.flow_rate_ml_min.toFixed(3)} mL/min</div>
              <div><span className="text-muted-foreground">Inj Vol:</span> {result.injection_volume_ul.toFixed(2)} μL</div>
              <div><span className="text-muted-foreground">Temp:</span> {result.temperature_c}°C</div>
            </div>
            <div className="mt-2 text-xs">
              <span className="text-muted-foreground">Scaling factors:</span>
              <span className="ml-2">Flow ×{result.scaling_factors.flow_rate?.toFixed(3)}</span>
              <span className="ml-2">Grad ×{result.scaling_factors.gradient_time?.toFixed(3)}</span>
              <span className="ml-2">Inj ×{result.scaling_factors.injection_volume?.toFixed(3)}</span>
            </div>
          </div>

          {/* Transferred gradient table */}
          <div className="card-scientific">
            <h2 className="text-sm font-semibold">Transferred Gradient</h2>
            <table className="mt-2 w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-2 py-1 text-left">Time (min)</th>
                  <th className="px-2 py-1 text-left">%B</th>
                  <th className="px-2 py-1 text-left text-muted-foreground">Time (s)</th>
                </tr>
              </thead>
              <tbody>
                {result.gradient_table.map((p, i) => (
                  <tr key={i} className="border-b border-border/50">
                    <td className="px-2 py-1 font-medium">{(p.time_s / 60).toFixed(2)}</td>
                    <td className="px-2 py-1 font-medium">{p.percent_b.toFixed(1)}</td>
                    <td className="px-2 py-1 text-muted-foreground">{p.time_s.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Notes */}
          {result.notes.length > 0 && (
            <div className="card-scientific">
              <div className="flex items-center gap-2">
                <Info className="h-4 w-4 text-yellow-500" />
                <h2 className="text-sm font-semibold">Notes & Warnings</h2>
              </div>
              <ul className="mt-2 ml-4 list-disc space-y-1 text-xs text-muted-foreground">
                {result.notes.map((n, i) => <li key={i}>{n}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function NumField({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <label className="block">
      <span className="text-xs text-muted-foreground">{label}</span>
      <input type="number" step="0.01" value={value}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        className="mt-1 w-full rounded border border-border bg-background px-2 py-1 text-sm" />
    </label>
  );
}
