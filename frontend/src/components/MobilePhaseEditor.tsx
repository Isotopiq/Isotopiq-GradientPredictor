import { useState } from 'react';
import { Droplet, Calculator, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { methodsApi } from '@/api/methods';
import { toast } from 'sonner';
import type { BufferCalcResult, MobilePhaseCheckResult } from '@/types';

const ACIDS = [
  { value: 'formic_acid', label: 'Formic acid' },
  { value: 'acetic_acid', label: 'Acetic acid' },
  { value: 'trifluoroacetic_acid', label: 'TFA' },
  { value: 'phosphoric_acid', label: 'Phosphoric acid' },
];
const SALTS = [
  { value: 'ammonium_formate', label: 'Ammonium formate' },
  { value: 'ammonium_acetate', label: 'Ammonium acetate' },
  { value: 'ammonium_bicarbonate', label: 'Ammonium bicarbonate' },
];
const BASES = [
  { value: 'ammonia', label: 'Ammonia' },
];

const ALL_BUFFERS = [...ACIDS, ...SALTS, ...BASES];

export function MobilePhaseEditor() {
  const [buffer, setBuffer] = useState('formic_acid');
  const [concentration, setConcentration] = useState(0.1);
  const [unit, setUnit] = useState('percent');
  const [solventA, setSolventA] = useState('water');
  const [solventB, setSolventB] = useState('acn');
  const [bufferResult, setBufferResult] = useState<BufferCalcResult | null>(null);
  const [compatResult, setCompatResult] = useState<MobilePhaseCheckResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handleCalculate = async () => {
    setLoading(true);
    try {
      const result = await methodsApi.calculateBuffer(buffer, concentration, unit);
      setBufferResult(result);
      // Also check compatibility
      const compat = await methodsApi.checkMobilePhase({
        solvent_a: solventA, solvent_b: solventB,
        buffer, buffer_percent: concentration, buffer_unit: unit,
      });
      setCompatResult(compat);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Calculation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card-scientific">
      <div className="flex items-center gap-2">
        <Droplet className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold">Mobile Phase Editor</h3>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3">
        <label className="block">
          <span className="text-xs text-muted-foreground">Solvent A</span>
          <select value={solventA} onChange={(e) => setSolventA(e.target.value)}
            className="mt-1 w-full rounded border border-border bg-background px-1 py-1 text-xs">
            <option value="water">Water</option>
            <option value="acn">Acetonitrile</option>
            <option value="meoh">Methanol</option>
          </select>
        </label>
        <label className="block">
          <span className="text-xs text-muted-foreground">Solvent B</span>
          <select value={solventB} onChange={(e) => setSolventB(e.target.value)}
            className="mt-1 w-full rounded border border-border bg-background px-1 py-1 text-xs">
            <option value="acn">Acetonitrile</option>
            <option value="meoh">Methanol</option>
            <option value="ipa">Isopropanol</option>
            <option value="thf">THF</option>
          </select>
        </label>
      </div>

      <div className="mt-2 grid grid-cols-3 gap-2">
        <label className="col-span-1 block">
          <span className="text-xs text-muted-foreground">Buffer/Additive</span>
          <select value={buffer} onChange={(e) => setBuffer(e.target.value)}
            className="mt-1 w-full rounded border border-border bg-background px-1 py-1 text-xs">
            <optgroup label="Acids">
              {ACIDS.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
            </optgroup>
            <optgroup label="Salts">
              {SALTS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
            </optgroup>
            <optgroup label="Bases">
              {BASES.map(b => <option key={b.value} value={b.value}>{b.label}</option>)}
            </optgroup>
          </select>
        </label>
        <label className="block">
          <span className="text-xs text-muted-foreground">Concentration</span>
          <input type="number" step="0.01" value={concentration}
            onChange={(e) => setConcentration(parseFloat(e.target.value) || 0)}
            className="mt-1 w-full rounded border border-border bg-background px-1 py-1 text-xs" />
        </label>
        <label className="block">
          <span className="text-xs text-muted-foreground">Unit</span>
          <select value={unit} onChange={(e) => setUnit(e.target.value)}
            className="mt-1 w-full rounded border border-border bg-background px-1 py-1 text-xs">
            <option value="percent">% (v/v)</option>
            <option value="mM">mM</option>
          </select>
        </label>
      </div>

      <button onClick={handleCalculate} disabled={loading} className="btn-primary mt-2 flex items-center gap-1 text-xs">
        <Calculator className="h-3 w-3" /> {loading ? 'Calculating...' : 'Calculate pH & Compatibility'}
      </button>

      {bufferResult && (
        <div className="mt-3 space-y-2">
          <div className={`rounded-md p-2 text-xs ${bufferResult.ms_compatible ? 'bg-green-500/10' : 'bg-yellow-500/10'}`}>
            <div className="flex items-center gap-2">
              {bufferResult.ms_compatible ? (
                <CheckCircle2 className="h-3 w-3 text-green-500" />
              ) : (
                <AlertTriangle className="h-3 w-3 text-yellow-500" />
              )}
              <span className="font-semibold">{bufferResult.buffer_name}</span>
              <span className="ml-auto text-lg font-bold">pH ≈ {bufferResult.estimated_ph}</span>
            </div>
            <div className="mt-1 text-muted-foreground">{bufferResult.recipe}</div>
            <div className="text-muted-foreground">Concentration: {bufferResult.concentration_mM.toFixed(1)} mM</div>
          </div>

          {bufferResult.warnings.length > 0 && (
            <ul className="ml-4 list-disc text-[10px] text-yellow-600">
              {bufferResult.warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          )}

          {compatResult && compatResult.warnings.length > 0 && (
            <div className="rounded-md bg-yellow-500/10 p-2 text-[10px]">
              <div className="font-semibold text-yellow-600">Compatibility Warnings:</div>
              <ul className="ml-4 list-disc">
                {compatResult.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
