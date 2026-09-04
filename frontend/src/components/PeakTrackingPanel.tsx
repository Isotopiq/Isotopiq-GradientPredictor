import { useState } from 'react';
import { GitMerge, Calculator, CheckCircle2, XCircle } from 'lucide-react';
import { methodsApi } from '@/api/methods';
import { toast } from 'sonner';
import type { TrackPeak, PeakTrackingResult } from '@/types';

interface ChromInput {
  id: string;
  peaks: TrackPeak[];
}

export function PeakTrackingPanel() {
  const [chromatograms, setChromatograms] = useState<ChromInput[]>([
    { id: 'A', peaks: [{ rt_min: 5.2, area: 100000, height: 50000, width_min: 0.15, compound_name: '' }] },
    { id: 'B', peaks: [{ rt_min: 5.3, area: 95000, height: 48000, width_min: 0.16, compound_name: '' }] },
  ]);
  const [rtTol, setRtTol] = useState(0.15);
  const [result, setResult] = useState<PeakTrackingResult | null>(null);
  const [loading, setLoading] = useState(false);

  const updatePeak = (ci: number, pi: number, field: keyof TrackPeak, value: string | number) => {
    const updated = [...chromatograms];
    updated[ci].peaks[pi] = { ...updated[ci].peaks[pi], [field]: value };
    setChromatograms(updated);
  };

  const addPeak = (ci: number) => {
    const updated = [...chromatograms];
    updated[ci].peaks.push({ rt_min: 0, area: 0, height: 0, width_min: 0, compound_name: '' });
    setChromatograms(updated);
  };

  const addChrom = () => {
    setChromatograms([...chromatograms, {
      id: String.fromCharCode(65 + chromatograms.length),
      peaks: [{ rt_min: 0, area: 0, height: 0, width_min: 0, compound_name: '' }],
    }]);
  };

  const handleTrack = async () => {
    const chromDict: Record<string, TrackPeak[]> = {};
    for (const c of chromatograms) {
      chromDict[c.id] = c.peaks.filter(p => p.rt_min > 0);
    }
    if (Object.values(chromDict).every(p => p.length === 0)) {
      toast.error('Enter at least one peak');
      return;
    }
    setLoading(true);
    try {
      const res = await methodsApi.peakTracking({
        chromatograms: chromDict,
        rt_tolerance_min: rtTol,
      });
      setResult(res);
      toast.success(`Found ${res.n_matched_groups} matched peak group(s)`);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Peak tracking failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card-scientific">
      <div className="flex items-center gap-2">
        <GitMerge className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold">Peak Tracking / Matching</h3>
      </div>

      <div className="mt-3 space-y-3">
        {chromatograms.map((chrom, ci) => (
          <div key={ci} className="rounded-md border border-border p-2">
            <div className="text-xs font-semibold">Chromatogram {chrom.id}</div>
            {chrom.peaks.map((peak, pi) => (
              <div key={pi} className="mt-1 flex gap-1">
                <input type="number" step="0.01" value={peak.rt_min}
                  onChange={(e) => updatePeak(ci, pi, 'rt_min', parseFloat(e.target.value) || 0)}
                  className="w-16 rounded border border-border bg-background px-1 py-0.5 text-xs" placeholder="RT" />
                <input type="number" step="1000" value={peak.area}
                  onChange={(e) => updatePeak(ci, pi, 'area', parseFloat(e.target.value) || 0)}
                  className="w-20 rounded border border-border bg-background px-1 py-0.5 text-xs" placeholder="Area" />
                <input type="text" value={peak.compound_name || ''}
                  onChange={(e) => updatePeak(ci, pi, 'compound_name', e.target.value)}
                  className="w-24 rounded border border-border bg-background px-1 py-0.5 text-xs" placeholder="Name" />
              </div>
            ))}
            <button onClick={() => addPeak(ci)} className="mt-1 text-[10px] text-accent hover:underline">+ Add peak</button>
          </div>
        ))}
        <button onClick={addChrom} className="text-[10px] text-accent hover:underline">+ Add chromatogram</button>
      </div>

      <div className="mt-2 flex items-center gap-2">
        <label className="text-xs text-muted-foreground">RT tolerance (min):</label>
        <input type="number" step="0.01" value={rtTol}
          onChange={(e) => setRtTol(parseFloat(e.target.value) || 0)}
          className="w-20 rounded border border-border bg-background px-1 py-0.5 text-xs" />
      </div>

      <button onClick={handleTrack} disabled={loading} className="btn-primary mt-2 flex items-center gap-1 text-xs">
        <Calculator className="h-3 w-3" /> {loading ? 'Tracking...' : 'Track Peaks'}
      </button>

      {result && (
        <div className="mt-3 space-y-2">
          <div className="text-xs font-semibold text-muted-foreground">
            {result.n_matched_groups} matched groups, {result.unmatched.length} unmatched peaks
          </div>

          {result.matches.map((match, i) => (
            <div key={i} className="rounded-md bg-green-500/10 p-2 text-xs">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-3 w-3 text-green-500" />
                <span className="font-semibold">Group {i + 1}</span>
                <span>RT: {match.mean_rt.toFixed(2)} ± {match.rt_std.toFixed(3)} min</span>
                <span className="ml-auto">Confidence: {(match.confidence * 100).toFixed(0)}%</span>
              </div>
              <div className="mt-1 text-[10px] text-muted-foreground">
                {match.peaks.map((p, j) => (
                  <span key={j} className="mr-2">
                    {p.chromatogram_id}: {p.rt_min.toFixed(2)}min ({p.area.toFixed(0)})
                  </span>
                ))}
              </div>
              {match.area_cv > 0 && (
                <div className="text-[10px] text-muted-foreground">
                  Area CV: {(match.area_cv * 100).toFixed(1)}%
                </div>
              )}
            </div>
          ))}

          {result.unmatched.length > 0 && (
            <div className="rounded-md bg-yellow-500/10 p-2 text-xs">
              <div className="flex items-center gap-2">
                <XCircle className="h-3 w-3 text-yellow-500" />
                <span className="font-semibold">Unmatched Peaks</span>
              </div>
              <div className="mt-1 text-[10px] text-muted-foreground">
                {result.unmatched.map((p, i) => (
                  <span key={i} className="mr-2">
                    {p.chromatogram_id}: {p.rt_min.toFixed(2)}min
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
