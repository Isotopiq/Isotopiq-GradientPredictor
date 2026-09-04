import { useState } from 'react';
import { Activity, Calculator, Droplet } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceArea, ReferenceLine, Legend } from 'recharts';
import { methodsApi } from '@/api/methods';
import { toast } from 'sonner';
import type { PhDistribution, PhSuitabilityMap } from '@/types';

interface Props {
  activeSmiles: string;
  compoundsSmiles: string[];
}

export function PhSelectorPanel({ activeSmiles, compoundsSmiles }: Props) {
  const [distribution, setDistribution] = useState<PhDistribution | null>(null);
  const [suitability, setSuitability] = useState<PhSuitabilityMap | null>(null);
  const [loading, setLoading] = useState(false);

  const handleDistribution = async () => {
    if (!activeSmiles) {
      toast.error('Enter a compound first');
      return;
    }
    setLoading(true);
    try {
      const result = await methodsApi.phDistribution(activeSmiles);
      setDistribution(result);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to compute pH distribution');
    } finally {
      setLoading(false);
    }
  };

  const handleSuitability = async () => {
    const smiles = compoundsSmiles.filter(s => s && s.trim());
    if (smiles.length === 0) {
      toast.error('Add at least one compound');
      return;
    }
    setLoading(true);
    try {
      const result = await methodsApi.phSuitability(smiles);
      setSuitability(result);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to compute pH suitability');
    } finally {
      setLoading(false);
    }
  };

  // Build chart data for ionic distribution
  const distChartData = distribution ? distribution.ph_values.map((ph, i) => {
    const row: Record<string, number> = { ph };
    distribution.pka_sites.forEach((_, idx) => {
      row[`Site ${idx + 1}`] = distribution.species_fractions[i]?.[idx] ?? 0;
    });
    row['net_charge'] = distribution.net_charges[i];
    return row;
  }) : [];

  // Build chart data for suitability
  const suitChartData = suitability ? suitability.ph_values.map((ph, i) => ({
    ph,
    min_logd: suitability.min_logd[i],
    zone: suitability.zones[i],
  })) : [];

  return (
    <div className="card-scientific">
      <div className="flex items-center gap-2">
        <Activity className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold">pH Selector & Ionic Forms</h3>
      </div>

      <div className="mt-3 flex gap-2">
        <button onClick={handleDistribution} disabled={loading} className="btn-secondary text-xs">
          <Calculator className="mr-1 inline h-3 w-3" /> Ionic Distribution
        </button>
        <button onClick={handleSuitability} disabled={loading} className="btn-secondary text-xs">
          <Droplet className="mr-1 inline h-3 w-3" /> Suitability Map
        </button>
      </div>

      {/* Ionic Distribution Chart */}
      {distribution && (
        <div className="mt-3">
          <div className="text-xs font-semibold text-muted-foreground mb-1">Ionic Species Distribution</div>
          {distribution.pka_sites.length === 0 ? (
            <p className="text-xs text-muted-foreground">No ionizable groups detected.</p>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={distChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="ph" label={{ value: 'pH', position: 'bottom', fontSize: 10 }} tick={{ fontSize: 10 }} />
                  <YAxis label={{ value: 'Fraction', angle: -90, position: 'insideLeft', fontSize: 10 }} tick={{ fontSize: 10 }} domain={[0, 1]} />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: 10 }} />
                  {distribution.pka_sites.map((site, idx) => (
                    <ReferenceLine key={idx} x={site.pka} stroke="#ef4444" strokeDasharray="5 5"
                      label={{ value: `pKa ${site.pka.toFixed(1)}`, fontSize: 9, fill: '#ef4444' }} />
                  ))}
                  {distribution.pka_sites.map((_, idx) => (
                    <Line key={idx} type="monotone" dataKey={`Site ${idx + 1}`} stroke={`hsl(${idx * 60}, 70%, 50%)`} strokeWidth={2} dot={false} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
              <div className="mt-1 text-[10px] text-muted-foreground">
                {distribution.pka_sites.length} ionizable site(s) detected
              </div>
            </>
          )}
        </div>
      )}

      {/* Suitability Map */}
      {suitability && (
        <div className="mt-3">
          <div className="text-xs font-semibold text-muted-foreground mb-1">pH Suitability Map</div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={suitChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="ph" label={{ value: 'pH', position: 'bottom', fontSize: 10 }} tick={{ fontSize: 10 }} />
              <YAxis label={{ value: 'min logD', angle: -90, position: 'insideLeft', fontSize: 10 }} tick={{ fontSize: 10 }} />
              <Tooltip />
              {/* Zone backgrounds */}
              {suitability.recommended_phs.map((ph, i) => (
                <ReferenceLine key={i} x={ph} stroke="#10b981" strokeWidth={2}
                  label={{ value: `pH ${ph.toFixed(1)}`, fontSize: 9, fill: '#10b981', position: 'top' }} />
              ))}
              <Line type="monotone" dataKey="min_logd" stroke="#3b82f6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>

          {/* Zone summary */}
          <div className="mt-2 flex gap-2 text-[10px]">
            <span className="rounded bg-green-500/20 px-2 py-0.5 text-green-700">
              Suitable: {suitability.zones.filter(z => z === 'suitable').length}
            </span>
            <span className="rounded bg-yellow-500/20 px-2 py-0.5 text-yellow-700">
              Acceptable: {suitability.zones.filter(z => z === 'acceptable').length}
            </span>
            <span className="rounded bg-red-500/20 px-2 py-0.5 text-red-700">
              Prohibited: {suitability.zones.filter(z => z === 'prohibited').length}
            </span>
          </div>

          {/* Buffer suggestions */}
          {suitability.buffer_suggestions.length > 0 && (
            <div className="mt-2">
              <div className="text-xs font-semibold text-muted-foreground mb-1">Recommended Buffers</div>
              <div className="space-y-1">
                {suitability.buffer_suggestions.map((buf, i) => (
                  <div key={i} className="rounded-md bg-muted/50 p-2 text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{buf.name}</span>
                      <span className="text-muted-foreground">pKa {buf.pKa}</span>
                      {buf.ms_compatible ? (
                        <span className="badge badge-success text-[9px]">MS-compatible</span>
                      ) : (
                        <span className="badge badge-warning text-[9px]">Non-volatile</span>
                      )}
                    </div>
                    <div className="text-[10px] text-muted-foreground">{buf.recipe}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
