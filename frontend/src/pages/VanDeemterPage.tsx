import { useEffect, useMemo, useState } from 'react';
import { Gauge, Calculator, Info, Search, X } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, ReferenceDot, Legend,
} from 'recharts';
import { methodsApi } from '@/api/methods';
import { columnsApi } from '@/api/columns';
import { toast } from 'sonner';
import type { ColumnSpec, VanDeemterResult } from '@/types';

const PARTICLE_TYPES = [
  { value: 'fully_porous', label: 'Fully porous' },
  { value: 'core_shell', label: 'Core-shell (SPP)' },
  { value: 'hybrid', label: 'Hybrid (BEH-type)' },
  { value: 'graphitic', label: 'Graphitic (PGC)' },
];

export function VanDeemterPage() {
  // Column state
  const [columnSearch, setColumnSearch] = useState('');
  const [columnOptions, setColumnOptions] = useState<ColumnSpec[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedColumn, setSelectedColumn] = useState<ColumnSpec | null>(null);
  const [lengthMm, setLengthMm] = useState(100);
  const [idMm, setIdMm] = useState(2.1);
  const [dpUm, setDpUm] = useState(1.7);
  const [particleType, setParticleType] = useState('fully_porous');

  // Conditions
  const [solventB, setSolventB] = useState('acetonitrile');
  const [fractionB, setFractionB] = useState(0.5);
  const [tempC, setTempC] = useState(40);
  const [mw, setMw] = useState(300);
  const [dmOverride, setDmOverride] = useState('');
  const [maxPressure, setMaxPressure] = useState(600);

  // Assessment / speed mode
  const [currentFlow, setCurrentFlow] = useState('');
  const [targetPlates, setTargetPlates] = useState('');

  const [result, setResult] = useState<VanDeemterResult | null>(null);
  const [loading, setLoading] = useState(false);

  // Debounced column search
  useEffect(() => {
    if (!columnSearch.trim()) {
      setColumnOptions([]);
      return;
    }
    const t = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await columnsApi.list({ search: columnSearch, limit: 15 });
        setColumnOptions(res.columns);
      } catch {
        setColumnOptions([]);
      } finally {
        setSearching(false);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [columnSearch]);

  const pickColumn = (c: ColumnSpec) => {
    setSelectedColumn(c);
    setColumnSearch(`${c.brand} ${c.name} — ${c.length_mm}×${c.inner_diameter_mm}mm, ${c.particle_size_um}µm`);
    setColumnOptions([]);
    setLengthMm(c.length_mm);
    setIdMm(c.inner_diameter_mm);
    setDpUm(c.particle_size_um);
    if (c.stationary_phase?.particle_type) {
      setParticleType(c.stationary_phase.particle_type);
    }
  };

  const clearColumn = () => {
    setSelectedColumn(null);
    setColumnSearch('');
  };

  const handleCompute = async () => {
    setLoading(true);
    try {
      const res = await methodsApi.vanDeemter({
        column_id: selectedColumn?.id,
        length_mm: lengthMm,
        inner_diameter_mm: idMm,
        particle_size_um: dpUm,
        particle_type: particleType,
        solvent_b: solventB,
        fraction_b: fractionB,
        temperature_c: tempC,
        analyte_mw: mw,
        dm_m2_s: dmOverride ? parseFloat(dmOverride) : undefined,
        current_flow_ml_min: currentFlow ? parseFloat(currentFlow) : undefined,
        max_pressure_bar: maxPressure,
        target_plates: targetPlates ? parseInt(targetPlates, 10) : undefined,
      });
      setResult(res);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Van Deemter analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const opt = result?.optimum_efficiency;
  const assessment = result?.current_assessment;

  const verdictClass = useMemo(() => {
    if (!assessment) return '';
    if (assessment.verdict === 'optimal') return 'badge badge-success';
    return 'badge badge-warning';
  }, [assessment]);

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4">
      <div className="flex items-center gap-2">
        <Gauge className="h-5 w-5 text-accent" />
        <h1 className="text-xl font-bold">Van Deemter Mapper</h1>
      </div>
      <p className="text-sm text-muted-foreground">
        Plate-height analysis and flow-rate optimization. Computes the optimal
        linear velocity u<sub>opt</sub> = √(b/c)·D<sub>m</sub>/d<sub>p</sub> for
        your column and analyte, maps optimal flow across column IDs, and
        checks backpressure via Kozeny-Carman.
      </p>

      {/* Column selection */}
      <div className="card-scientific">
        <h2 className="text-sm font-semibold">Column</h2>
        <div className="mt-2 space-y-2">
          <div className="relative">
            <div className="flex items-center gap-2">
              <Search className="h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                value={columnSearch}
                onChange={(e) => { setColumnSearch(e.target.value); setSelectedColumn(null); }}
                placeholder="Search column database (optional) — or enter dimensions below"
                className="w-full rounded border border-border bg-background px-2 py-1 text-sm"
              />
              {selectedColumn && (
                <button onClick={clearColumn} className="text-muted-foreground hover:text-foreground" title="Clear selection">
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
            {(columnOptions.length > 0 || searching) && (
              <div className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded border border-border bg-card shadow-lg">
                {searching && <div className="px-3 py-2 text-xs text-muted-foreground">Searching…</div>}
                {columnOptions.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => pickColumn(c)}
                    className="block w-full px-3 py-1.5 text-left text-xs hover:bg-muted"
                  >
                    <span className="font-medium">{c.brand} {c.name}</span>
                    <span className="text-muted-foreground">
                      {' '}— {c.length_mm}×{c.inner_diameter_mm} mm, {c.particle_size_um} µm
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <NumField label="Length (mm)" value={lengthMm} onChange={setLengthMm} />
            <NumField label="I.D. (mm)" value={idMm} onChange={setIdMm} step={0.1} />
            <NumField label="Particle (µm)" value={dpUm} onChange={setDpUm} step={0.1} />
            <label className="block">
              <span className="text-xs text-muted-foreground">Particle type</span>
              <select
                value={particleType}
                onChange={(e) => setParticleType(e.target.value)}
                className="mt-1 w-full rounded border border-border bg-background px-2 py-1 text-sm"
              >
                {PARTICLE_TYPES.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </label>
          </div>
        </div>
      </div>

      {/* Conditions */}
      <div className="card-scientific">
        <h2 className="text-sm font-semibold">Mobile Phase &amp; Analyte</h2>
        <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
          <label className="block">
            <span className="text-xs text-muted-foreground">Organic solvent (B)</span>
            <select
              value={solventB}
              onChange={(e) => setSolventB(e.target.value)}
              className="mt-1 w-full rounded border border-border bg-background px-2 py-1 text-sm"
            >
              <option value="acetonitrile">Acetonitrile</option>
              <option value="methanol">Methanol</option>
            </select>
          </label>
          <NumField label="%B (fraction 0–1)" value={fractionB} onChange={setFractionB} step={0.05} />
          <NumField label="Temperature (°C)" value={tempC} onChange={setTempC} step={1} />
          <NumField label="Analyte MW (Da)" value={mw} onChange={setMw} step={10} />
          <TextField
            label="Dₘ override (m²/s, optional)"
            value={dmOverride}
            onChange={setDmOverride}
            placeholder="auto via Wilke-Chang"
          />
          <NumField label="Max pressure (bar)" value={maxPressure} onChange={setMaxPressure} step={50} />
        </div>
      </div>

      {/* Assessment & speed mode */}
      <div className="card-scientific">
        <h2 className="text-sm font-semibold">Assessment &amp; Speed Mode</h2>
        <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
          <TextField
            label="Current flow (mL/min, optional)"
            value={currentFlow}
            onChange={setCurrentFlow}
            placeholder="e.g. 0.4"
          />
          <TextField
            label="Target plates N (optional)"
            value={targetPlates}
            onChange={setTargetPlates}
            placeholder="enables speed optimum"
          />
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          Speed mode finds the minimum hold-up time for the target plate count
          at your pressure limit, solving the kinetic-optimum relation
          u·H(u) = ΔP·d<sub>p</sub>²/(φ·η·ε·N) with column length free.
        </p>
      </div>

      <button onClick={handleCompute} disabled={loading} className="btn-primary flex items-center gap-2 text-sm">
        <Calculator className="h-4 w-4" /> {loading ? 'Computing…' : 'Compute Van Deemter Map'}
      </button>

      {result && opt && (
        <div className="space-y-3">
          {/* Optimum summary cards */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="card-scientific">
              <h2 className="text-sm font-semibold">Optimal Flow (max efficiency)</h2>
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                <div className="text-lg font-bold text-accent">
                  {opt.flow_ml_min.toFixed(3)} mL/min
                </div>
                <div className="text-right">
                  <div>u = {opt.u_mm_s.toFixed(2)} mm/s</div>
                  <div>H = {opt.h_um.toFixed(2)} µm</div>
                </div>
                <div><span className="text-muted-foreground">N:</span> {opt.n.toLocaleString()}</div>
                <div><span className="text-muted-foreground">t₀:</span> {opt.t0_s.toFixed(1)} s</div>
                <div><span className="text-muted-foreground">ΔP:</span> {opt.pressure_bar.toFixed(0)} bar</div>
                <div>
                  {opt.pressure_limited
                    ? <span className="badge badge-warning">pressure-capped</span>
                    : <span className="badge badge-success">unconstrained</span>}
                </div>
              </div>
            </div>

            {result.optimum_speed && result.optimum_speed.n > 0 && (
              <div className="card-scientific">
                <h2 className="text-sm font-semibold">
                  Speed Optimum (N = {result.optimum_speed.n.toLocaleString()})
                </h2>
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                  <div className="text-lg font-bold text-accent">
                    {result.optimum_speed.flow_ml_min.toFixed(3)} mL/min
                  </div>
                  <div className="text-right">
                    <div>u = {result.optimum_speed.u_mm_s.toFixed(2)} mm/s</div>
                    <div>H = {result.optimum_speed.h_um.toFixed(2)} µm</div>
                  </div>
                  <div><span className="text-muted-foreground">t₀:</span> {result.optimum_speed.t0_s.toFixed(1)} s</div>
                  <div><span className="text-muted-foreground">ΔP:</span> {result.optimum_speed.pressure_bar.toFixed(0)} bar</div>
                  <div className="col-span-2">
                    <span className="text-muted-foreground">Required length:</span>{' '}
                    {result.optimum_speed.required_length_mm?.toFixed(0)} mm
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Current flow assessment */}
          {assessment && (
            <div className="card-scientific">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold">
                  Current Flow Assessment — {assessment.flow_ml_min} mL/min
                </h2>
                <span className={verdictClass}>{assessment.verdict}</span>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
                <div><span className="text-muted-foreground">u:</span> {assessment.u_mm_s.toFixed(2)} mm/s ({assessment.velocity_ratio}× opt)</div>
                <div><span className="text-muted-foreground">Efficiency:</span> {assessment.efficiency_vs_optimum_pct}% of H<sub>min</sub></div>
                <div><span className="text-muted-foreground">N:</span> {assessment.n.toLocaleString()}</div>
                <div><span className="text-muted-foreground">ΔP:</span> {assessment.pressure_bar.toFixed(0)} bar</div>
              </div>
            </div>
          )}

          {/* Van Deemter curve */}
          <div className="card-scientific">
            <h2 className="text-sm font-semibold">Plate Height vs Flow Rate</h2>
            <div className="mt-1 text-xs text-muted-foreground">
              {result.column.label} — {result.column.length_mm}×{result.column.inner_diameter_mm} mm,
              {' '}{result.column.particle_size_um} µm, {result.particle_type};
              {' '}a={result.coefficients.a}, b={result.coefficients.b}, c={result.coefficients.c};
              {' '}D<sub>m</sub>={result.dm_m2_s.toExponential(2)} m²/s, η={result.viscosity_cp.toFixed(2)} cP,
              {' '}V₀={result.column.holdup_volume_ml.toFixed(3)} mL
            </div>
            <ResponsiveContainer width="100%" height={280} className="mt-2">
              <LineChart data={result.curve} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis
                  dataKey="flow_ml_min"
                  type="number"
                  domain={['dataMin', 'dataMax']}
                  tick={{ fontSize: 11 }}
                  label={{ value: 'Flow (mL/min)', position: 'insideBottom', offset: -2, fontSize: 11 }}
                />
                <YAxis
                  yAxisId="h"
                  tick={{ fontSize: 11 }}
                  label={{ value: 'H (µm)', angle: -90, position: 'insideLeft', fontSize: 11 }}
                />
                <YAxis
                  yAxisId="p"
                  orientation="right"
                  tick={{ fontSize: 11 }}
                  label={{ value: 'ΔP (bar)', angle: 90, position: 'insideRight', fontSize: 11 }}
                />
                <Tooltip
                  formatter={(v: number, name: string) => [
                    name === 'H (µm)' ? v.toFixed(2) : v.toFixed(0), name,
                  ]}
                  labelFormatter={(v: number) => `${v.toFixed(3)} mL/min`}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line
                  yAxisId="h" type="monotone" dataKey="h_um" name="H (µm)"
                  stroke="hsl(224, 76%, 48%)" strokeWidth={2} dot={false}
                />
                <Line
                  yAxisId="p" type="monotone" dataKey="pressure_bar" name="ΔP (bar)"
                  stroke="#94a3b8" strokeWidth={1.5} strokeDasharray="5 3" dot={false}
                />
                <ReferenceLine
                  yAxisId="h" x={opt.flow_ml_min}
                  stroke="hsl(224, 76%, 48%)" strokeDasharray="4 4"
                  label={{ value: 'optimum', position: 'top', fontSize: 10, fill: 'hsl(224, 76%, 48%)' }}
                />
                <ReferenceDot
                  yAxisId="h" x={opt.flow_ml_min} y={opt.h_um}
                  r={4} fill="hsl(224, 76%, 48%)" stroke="none"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Diameter map */}
          <div className="card-scientific">
            <h2 className="text-sm font-semibold">Flow Map Across Column IDs</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Optimal flow at fixed linear velocity (F ∝ d<sub>c</sub>²). At equal
              u, backpressure is identical across IDs for the same L and d<sub>p</sub>.
              {assessment && ' "Scaled" = your current flow geometrically rescaled.'}
            </p>
            <table className="mt-2 w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-2 py-1 text-left">I.D. (mm)</th>
                  <th className="px-2 py-1 text-left">Optimal flow (mL/min)</th>
                  <th className="px-2 py-1 text-left">u (mm/s)</th>
                  <th className="px-2 py-1 text-left">ΔP (bar)</th>
                  <th className="px-2 py-1 text-left">N</th>
                  {assessment && <th className="px-2 py-1 text-left">Scaled flow</th>}
                </tr>
              </thead>
              <tbody>
                {result.diameter_map.map((r) => (
                  <tr
                    key={r.inner_diameter_mm}
                    className={
                      'border-b border-border/50 ' +
                      (Math.abs(r.inner_diameter_mm - result.column.inner_diameter_mm) < 0.01
                        ? 'bg-accent/10 font-medium'
                        : '')
                    }
                  >
                    <td className="px-2 py-1">{r.inner_diameter_mm}</td>
                    <td className="px-2 py-1 font-medium">{r.optimal_flow_ml_min.toFixed(3)}</td>
                    <td className="px-2 py-1">{r.u_mm_s.toFixed(2)}</td>
                    <td className="px-2 py-1">{r.pressure_bar.toFixed(0)}</td>
                    <td className="px-2 py-1">{r.n.toLocaleString()}</td>
                    {assessment && (
                      <td className="px-2 py-1 text-muted-foreground">
                        {r.scaled_flow_ml_min != null ? r.scaled_flow_ml_min.toFixed(3) : '—'}
                      </td>
                    )}
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
                <h2 className="text-sm font-semibold">Notes &amp; Warnings</h2>
              </div>
              <ul className="mt-2 ml-4 list-disc space-y-1 text-xs text-muted-foreground">
                {result.notes.map((n, i) => <li key={i}>{n}</li>)}
              </ul>
            </div>
          )}

          <p className="text-xs text-muted-foreground">
            Model basis: reduced Van Deemter h = a + b/ν + c·ν with
            literature-typical coefficients; D<sub>m</sub> via Wilke-Chang;
            viscosity from Snyder &amp; Dolan App. IV tabulated data;
            pressure via Kozeny-Carman. Values are estimates — confirm
            critical methods empirically.
          </p>
        </div>
      )}
    </div>
  );
}

function NumField({ label, value, onChange, step = 0.01 }: {
  label: string; value: number; onChange: (v: number) => void; step?: number;
}) {
  return (
    <label className="block">
      <span className="text-xs text-muted-foreground">{label}</span>
      <input type="number" step={step} value={value}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        className="mt-1 w-full rounded border border-border bg-background px-2 py-1 text-sm" />
    </label>
  );
}

function TextField({ label, value, onChange, placeholder }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string;
}) {
  return (
    <label className="block">
      <span className="text-xs text-muted-foreground">{label}</span>
      <input type="text" inputMode="decimal" value={value} placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded border border-border bg-background px-2 py-1 text-sm" />
    </label>
  );
}
