import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Trash2, Download, Eye, FlaskConical, Plus, Share2, Copy, ChevronDown,
  Pencil, Check, X, Zap,
} from 'lucide-react';
import { methodsApi } from '@/api/methods';
import { apiClient } from '@/api/client';
import { GradientChart } from '@/components/GradientChart';
import { ChromatogramPreview } from '@/components/ChromatogramPreview';
import { EmptyState } from '@/components/EmptyState';
import { Skeleton } from '@/components/Skeleton';
import { toast } from 'sonner';
import type { Method, GradientPoint, ChromatogramResult, MultiCompoundSuggestion } from '@/types';

const PEAK_COLORS = [
  '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
  '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
];

export function MethodLibraryPage() {
  const [selected, setSelected] = useState<Method | null>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const exportRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Chromatogram simulation state
  const [chromatogram, setChromatogram] = useState<ChromatogramResult | null>(null);
  const [multiResult, setMultiResult] = useState<MultiCompoundSuggestion | null>(null);
  const [simulating, setSimulating] = useState(false);

  // Edit mode state
  const [editing, setEditing] = useState(false);
  const [editFlowRate, setEditFlowRate] = useState(0.4);
  const [editPh, setEditPh] = useState(2.7);
  const [editTemperature, setEditTemperature] = useState(30);
  const [editGradientTable, setEditGradientTable] = useState<GradientPoint[]>([]);
  const [editName, setEditName] = useState('');
  const [saving, setSaving] = useState(false);

  const { data: methods, isLoading } = useQuery({
    queryKey: ['methods-library'],
    queryFn: () => methodsApi.list(),
  });

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) {
        setExportOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // When a method is selected, initialize edit state and simulate chromatogram
  useEffect(() => {
    if (selected) {
      setEditName(selected.name || '');
      setEditFlowRate(selected.flow_rate_ml_min ?? 0.4);
      setEditPh(selected.ph ?? 2.7);
      setEditTemperature(selected.temperature_c ?? 30);
      setEditGradientTable(selected.gradient_table ?? []);
      setEditing(false);
    } else {
      setChromatogram(null);
      setMultiResult(null);
    }
  }, [selected]);

  // Simulate chromatogram for the selected method
  // Re-runs when edit parameters change (if compounds are available)
  const compoundSmiles = useMemo(() => {
    return selected?.compounds_smiles?.filter((s) => s && s.trim()) ?? [];
  }, [selected]);

  useEffect(() => {
    if (!selected || compoundSmiles.length === 0 || !editGradientTable.length) {
      setChromatogram(null);
      setMultiResult(null);
      return;
    }

    let cancelled = false;
    setSimulating(true);

    const timer = setTimeout(async () => {
      try {
        // Get multi-compound suggestions for descriptors
        const result = await methodsApi.suggestMulti(compoundSmiles, {
          column_type: selected.column_type,
          flow_rate_ml_min: editFlowRate,
          gradient_time_min: editGradientTable.length >= 2
            ? (editGradientTable[editGradientTable.length - 1].time_s - editGradientTable[0].time_s) / 60
            : 20,
        });
        if (cancelled) return;
        setMultiResult(result);

        // Re-simulate RTs with current gradient + pH + temperature
        const totalTime = editGradientTable[editGradientTable.length - 1].time_s;
        const tempRtFactor = Math.max(0.7, 1.0 - (editTemperature - 30) * 0.015);
        const tempWidthFactor = Math.max(0.5, 1.0 - (editTemperature - 30) * 0.02);

        const adjustLogPForPh = (logp: number, pkaValues?: number[]): number => {
          if (!pkaValues || pkaValues.length === 0) return logp;
          const pka = pkaValues[0];
          const isAcidic = pka < 7;
          const delta = isAcidic ? editPh - pka : pka - editPh;
          if (delta <= 0) return logp;
          const penalty = Math.min(3, Math.log10(1 + Math.pow(10, delta)));
          return Math.max(-2, logp - penalty);
        };

        const validEntries = result.per_compound.filter(
          (pc) => pc.predicted_rt_s != null && !pc.error,
        );
        if (validEntries.length === 0) {
          setSimulating(false);
          return;
        }

        const peaks = await Promise.all(
          validEntries.map(async (pc, i) => {
            const effectiveLogP = adjustLogPForPh(pc.logp ?? 2.0, pc.pka_values);
            try {
              const sim = await methodsApi.simulateGradient({
                gradient_table: editGradientTable,
                flow_rate_ml_min: editFlowRate,
                logp: effectiveLogP,
                mw: pc.mw ?? 200,
                tpsa: pc.tpsa ?? 0,
                hbd: pc.hbd ?? 0,
                hba: pc.hba ?? 0,
                column_type: selected.column_type,
              });
              return {
                rt_s: sim.predicted_rt_s * tempRtFactor,
                width_s: (pc.peak_width_s || 10) * tempWidthFactor,
                height: 1.0,
                label: `Compound ${pc.index + 1}`,
                color: PEAK_COLORS[i % PEAK_COLORS.length],
              };
            } catch {
              return {
                rt_s: pc.predicted_rt_s! * tempRtFactor,
                width_s: (pc.peak_width_s || 10) * tempWidthFactor,
                height: 1.0,
                label: `Compound ${pc.index + 1}`,
                color: PEAK_COLORS[i % PEAK_COLORS.length],
              };
            }
          }),
        );

        if (cancelled) return;
        const chromResult = await methodsApi.simulateChromatogram({
          peaks,
          total_time_s: totalTime,
        });
        if (!cancelled) {
          setChromatogram(chromResult);
          setSimulating(false);
        }
      } catch {
        if (!cancelled) setSimulating(false);
      }
    }, 500);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [selected, compoundSmiles, editGradientTable, editFlowRate, editPh, editTemperature]);

  const deleteMutation = useMutation({
    mutationFn: (id: string) => methodsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['methods-library'] });
      setSelected(null);
      toast.success('Method deleted');
    },
    onError: () => toast.error('Failed to delete method'),
  });

  const shareMutation = useMutation({
    mutationFn: (id: string) => methodsApi.share(id),
    onSuccess: (method) => {
      setSelected(method);
      const url = `${window.location.origin}/shared/${method.share_token}`;
      navigator.clipboard.writeText(url).catch(() => {});
      toast.success('Share link copied to clipboard!');
    },
    onError: () => toast.error('Failed to share method'),
  });

  const unshareMutation = useMutation({
    mutationFn: (id: string) => methodsApi.unshare(id),
    onSuccess: (method) => {
      setSelected(method);
      queryClient.invalidateQueries({ queryKey: ['methods-library'] });
      toast.success('Share link disabled');
    },
    onError: () => toast.error('Failed to unshare method'),
  });

  const handleSaveEdit = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      // Rebuild gradient table if edited
      const bStart = editGradientTable[0]?.percent_b ?? 5;
      const bEnd = editGradientTable[editGradientTable.length - 1]?.percent_b ?? 95;
      const gradTime = editGradientTable.length >= 2
        ? (editGradientTable[editGradientTable.length - 1].time_s - editGradientTable[0].time_s) / 60
        : 20;

      // Use the update endpoint (create overwrites)
      await methodsApi.create({
        name: editName.trim() || selected.name || 'Unnamed Method',
        column_type: selected.column_type,
        ph: editPh,
        mobile_phase_a: selected.mobile_phase_a ?? undefined,
        mobile_phase_b: selected.mobile_phase_b ?? undefined,
        additive: selected.additive ?? undefined,
        flow_rate_ml_min: editFlowRate,
        temperature_c: editTemperature,
        gradient_table: editGradientTable,
        compounds_smiles: selected.compounds_smiles ?? undefined,
      });
      toast.success('Method saved as new version');
      queryClient.invalidateQueries({ queryKey: ['methods-library'] });
      setEditing(false);
    } catch {
      toast.error('Failed to save method');
    } finally {
      setSaving(false);
    }
  };

  const [includeChromatogram, setIncludeChromatogram] = useState(false);

  const handleExport = useCallback(async (id: string, format: string, ext: string, withChromatogram: boolean = false) => {
    const includeChroma = withChromatogram || includeChromatogram;
    try {
      const resp = await apiClient.get(`/export/method/${id}`, {
        params: { format, include_chromatogram: includeChroma ? 'true' : 'false' },
        responseType: 'blob',
      });
      const url = URL.createObjectURL(resp.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `method_${id}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`Exported as ${ext.toUpperCase()}`);
      setExportOpen(false);
    } catch {
      toast.error('Export failed');
    }
  }, [includeChromatogram]);

  const exportFormats = [
    { label: 'PDF Report', format: 'pdf', ext: 'pdf' },
    { label: 'PDF + Chromatogram', format: 'pdf', ext: 'pdf', withChromatogram: true },
    { label: 'CSV', format: 'csv', ext: 'csv' },
    { label: 'Agilent (.m)', format: 'agilent', ext: 'm' },
    { label: 'Waters (.mth)', format: 'waters', ext: 'mth' },
    { label: 'Thermo (.xml)', format: 'thermo', ext: 'xml' },
  ];

  // Update gradient table when %B start/end/time sliders change in edit mode
  const rebuildGradient = (bStart: number, bEnd: number, gTimeMin: number) => {
    const tTotal = gTimeMin * 60;
    setEditGradientTable([
      { time_s: 0, percent_b: bStart },
      { time_s: 60, percent_b: bStart },
      { time_s: tTotal - 120, percent_b: bEnd },
      { time_s: tTotal, percent_b: bEnd },
    ]);
  };

  const editBStart = editGradientTable[0]?.percent_b ?? 5;
  const editBEnd = editGradientTable[editGradientTable.length - 1]?.percent_b ?? 95;
  const editGradTime = editGradientTable.length >= 2
    ? (editGradientTable[editGradientTable.length - 1].time_s - editGradientTable[0].time_s) / 60
    : 20;

  return (
    <div className="mx-auto max-w-7xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Method Library</h1>
          <p className="text-sm text-muted-foreground">Saved LC methods with chromatogram preview</p>
        </div>
        <button onClick={() => navigate('/')} className="btn-outline btn-sm">
          <Plus size={14} className="mr-1" /> New Method
        </button>
      </div>

      {isLoading ? (
        <Skeleton className="h-64" />
      ) : !methods || methods.length === 0 ? (
        <EmptyState
          icon={<FlaskConical size={24} />}
          title="No saved methods yet"
          description="Use the Predictor to generate and save a method."
          action={
            <button onClick={() => navigate('/')} className="btn-primary btn-sm">
              Go to Predictor
            </button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Method list */}
          <div className="lg:col-span-1">
            <div className="card-scientific overflow-x-auto">
              <h2 className="mb-3 text-sm font-semibold">Methods ({methods.length})</h2>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Column</th>
                    <th>pH</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {methods.map((m) => (
                    <tr
                      key={m.id}
                      className="cursor-pointer"
                      onClick={() => setSelected(m)}
                      style={selected?.id === m.id ? { background: 'hsl(var(--muted))' } : undefined}
                    >
                      <td className="font-medium">{m.name || 'Unnamed'}</td>
                      <td>
                        <span className="badge badge-info">{m.column_type}</span>
                      </td>
                      <td className="tabular-nums">{m.ph?.toFixed(1) ?? '—'}</td>
                      <td>
                        {m.is_shared && <Share2 size={12} className="text-success" />}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Method detail */}
          <div className="lg:col-span-2">
            {selected ? (
              <div className="space-y-4">
                <div className="card-scientific">
                  <div className="section-header mb-4">
                    <div className="flex-1">
                      {editing ? (
                        <input
                          className="input"
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          placeholder="Method name"
                        />
                      ) : (
                        <>
                          <h2 className="text-sm font-bold">{selected.name || 'Unnamed Method'}</h2>
                          <p className="text-xs text-muted-foreground">
                            {selected.column_type} • {selected.is_shared ? 'Shared' : 'Private'}
                            {compoundSmiles.length > 0 && ` • ${compoundSmiles.length} compound(s)`}
                          </p>
                        </>
                      )}
                    </div>
                    <div className="flex gap-2">
                      {editing ? (
                        <>
                          <button
                            onClick={handleSaveEdit}
                            disabled={saving}
                            className="btn-primary btn-sm"
                          >
                            <Check size={14} className="mr-1" />
                            {saving ? 'Saving...' : 'Save'}
                          </button>
                          <button
                            onClick={() => {
                              setEditing(false);
                              // Reset edit state
                              setEditName(selected.name || '');
                              setEditFlowRate(selected.flow_rate_ml_min ?? 0.4);
                              setEditPh(selected.ph ?? 2.7);
                              setEditTemperature(selected.temperature_c ?? 30);
                              setEditGradientTable(selected.gradient_table ?? []);
                            }}
                            className="btn-outline btn-sm"
                          >
                            <X size={14} />
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={() => setEditing(true)}
                            className="btn-outline btn-sm"
                          >
                            <Pencil size={14} className="mr-1" /> Edit
                          </button>
                          {selected.is_shared ? (
                            <>
                              <button
                                onClick={() => shareMutation.mutate(selected.id)}
                                className="btn-outline btn-sm"
                                disabled={shareMutation.isPending}
                              >
                                <Share2 size={14} className="mr-1" />
                                Copy Link
                              </button>
                              <button
                                onClick={() => {
                                  if (confirm('Disable sharing? The existing share link will stop working.')) {
                                    unshareMutation.mutate(selected.id);
                                  }
                                }}
                                className="btn-outline btn-sm text-destructive"
                                disabled={unshareMutation.isPending}
                                title="Disable share link"
                              >
                                <X size={14} className="mr-1" />
                                Unshare
                              </button>
                            </>
                          ) : (
                            <button
                              onClick={() => shareMutation.mutate(selected.id)}
                              className="btn-outline btn-sm"
                              disabled={shareMutation.isPending}
                            >
                              <Share2 size={14} className="mr-1" />
                              Share
                            </button>
                          )}
                          <div className="relative" ref={exportRef}>
                            <button
                              onClick={() => setExportOpen(!exportOpen)}
                              className="btn-outline btn-sm"
                            >
                              <Download size={14} className="mr-1" /> Export
                              <ChevronDown size={12} className="ml-1" />
                            </button>
                            {exportOpen && (
                              <div className="absolute right-0 top-10 z-50 w-56 overflow-hidden rounded-lg border border-border bg-card shadow-lg animate-slide-down">
                                {exportFormats.map((f, idx) => (
                                  <button
                                    key={`${f.format}-${idx}`}
                                    onClick={() => handleExport(selected.id, f.format, f.ext, (f as { withChromatogram?: boolean }).withChromatogram === true)}
                                    className="flex w-full items-center gap-2 px-3 py-2 text-xs hover:bg-muted"
                                  >
                                    <Download size={12} /> {f.label}
                                  </button>
                                ))}
                                <div className="border-t border-border px-3 py-2">
                                  <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                                    <input
                                      type="checkbox"
                                      checked={includeChromatogram}
                                      onChange={(e) => setIncludeChromatogram(e.target.checked)}
                                      className="rounded border-border"
                                    />
                                    Include XIC chromatogram in all PDFs
                                  </label>
                                </div>
                              </div>
                            )}
                          </div>
                          <button
                            onClick={() => {
                              if (confirm('Delete this method?')) deleteMutation.mutate(selected.id);
                            }}
                            className="btn-outline btn-sm text-destructive"
                          >
                            <Trash2 size={14} />
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  {editing ? (
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="label">%B Start</label>
                          <div className="flex items-center gap-2">
                            <input
                              type="range"
                              min={0} max={50} step={1}
                              value={editBStart}
                              onChange={(e) => rebuildGradient(Number(e.target.value), editBEnd, editGradTime)}
                              className="flex-1"
                            />
                            <span className="text-xs tabular-nums w-12">{editBStart}%</span>
                          </div>
                        </div>
                        <div>
                          <label className="label">%B End</label>
                          <div className="flex items-center gap-2">
                            <input
                              type="range"
                              min={50} max={100} step={1}
                              value={editBEnd}
                              onChange={(e) => rebuildGradient(editBStart, Number(e.target.value), editGradTime)}
                              className="flex-1"
                            />
                            <span className="text-xs tabular-nums w-12">{editBEnd}%</span>
                          </div>
                        </div>
                        <div>
                          <label className="label">Gradient Time (min)</label>
                          <div className="flex items-center gap-2">
                            <input
                              type="range"
                              min={5} max={60} step={1}
                              value={editGradTime}
                              onChange={(e) => rebuildGradient(editBStart, editBEnd, Number(e.target.value))}
                              className="flex-1"
                            />
                            <span className="text-xs tabular-nums w-12">{editGradTime}m</span>
                          </div>
                        </div>
                        <div>
                          <label className="label">Flow Rate (mL/min)</label>
                          <div className="flex items-center gap-2">
                            <input
                              type="range"
                              min={0.1} max={2} step={0.05}
                              value={editFlowRate}
                              onChange={(e) => setEditFlowRate(Number(e.target.value))}
                              className="flex-1"
                            />
                            <span className="text-xs tabular-nums w-12">{editFlowRate}</span>
                          </div>
                        </div>
                        <div>
                          <label className="label">pH</label>
                          <div className="flex items-center gap-2">
                            <input
                              type="range"
                              min={2} max={11} step={0.1}
                              value={editPh}
                              onChange={(e) => setEditPh(Number(e.target.value))}
                              className="flex-1"
                            />
                            <span className="text-xs tabular-nums w-12">{editPh.toFixed(1)}</span>
                          </div>
                        </div>
                        <div>
                          <label className="label">Temperature (°C)</label>
                          <div className="flex items-center gap-2">
                            <input
                              type="range"
                              min={20} max={80} step={1}
                              value={editTemperature}
                              onChange={(e) => setEditTemperature(Number(e.target.value))}
                              className="flex-1"
                            />
                            <span className="text-xs tabular-nums w-12">{editTemperature}°</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <DetailRow label="Column" value={selected.column_type} />
                      <DetailRow label="pH" value={selected.ph?.toFixed(1) ?? '—'} />
                      <DetailRow label="Flow Rate" value={selected.flow_rate_ml_min ? `${selected.flow_rate_ml_min} mL/min` : '—'} />
                      <DetailRow label="Temperature" value={selected.temperature_c ? `${selected.temperature_c}°C` : '—'} />
                      <DetailRow label="Mobile Phase A" value={selected.mobile_phase_a ?? '—'} />
                      <DetailRow label="Mobile Phase B" value={selected.mobile_phase_b ?? '—'} />
                      <DetailRow label="Additive" value={selected.additive ?? '—'} />
                      <DetailRow label="Steps" value={selected.gradient_table ? `${selected.gradient_table.length}` : '—'} />
                    </div>
                  )}
                </div>

                {/* XIC Chromatogram Overlay */}
                {compoundSmiles.length > 0 ? (
                  <div className="card-scientific">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-semibold">
                        XIC Chromatogram Overlay
                        {compoundSmiles.length > 1 && (
                          <span className="ml-2 text-xs font-normal text-muted-foreground">
                            ({compoundSmiles.length} compounds)
                          </span>
                        )}
                      </h3>
                      {simulating && (
                        <span className="text-xs text-muted-foreground animate-pulse">Simulating...</span>
                      )}
                    </div>
                    <ChromatogramPreview
                      chromatogram={chromatogram}
                      loading={simulating}
                    />
                    {multiResult && multiResult.resolution_matrix.length > 0 && (
                      <div className="mt-3">
                        <h4 className="text-xs font-semibold mb-2">Resolution Matrix</h4>
                        <div className="overflow-x-auto">
                          <table className="data-table">
                            <thead>
                              <tr>
                                <th>Pair</th>
                                <th>RT A (min)</th>
                                <th>RT B (min)</th>
                                <th>Rs</th>
                                <th>Risk</th>
                              </tr>
                            </thead>
                            <tbody>
                              {multiResult.resolution_matrix.map((r, i) => (
                                <tr key={i}>
                                  <td>#{r.compound_a + 1} / #{r.compound_b + 1}</td>
                                  <td className="tabular-nums">{(r.rt_a / 60).toFixed(2)}</td>
                                  <td className="tabular-nums">{(r.rt_b / 60).toFixed(2)}</td>
                                  <td className="tabular-nums">{r.resolution.toFixed(2)}</td>
                                  <td>
                                    {r.co_elution_risk ? (
                                      <span className="badge badge-warning">Co-elution</span>
                                    ) : (
                                      <span className="badge badge-success">OK</span>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="card-scientific">
                    <p className="text-sm text-muted-foreground">
                      No compound data saved with this method. Save a method from the Predictor with compounds added to see the XIC chromatogram overlay.
                    </p>
                  </div>
                )}

                {editGradientTable.length > 0 && (
                  <div className="card-scientific">
                    <h3 className="mb-3 text-sm font-semibold">Gradient Profile</h3>
                    <GradientChart
                      gradientTable={editGradientTable}
                      rtMarkers={chromatogram?.peaks?.map((p) => ({
                        rt_s: p.rt_s,
                        label: p.label,
                        color: p.color || undefined,
                      }))}
                    />
                    <div className="mt-3 overflow-x-auto">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Step</th>
                            <th>Time (min)</th>
                            <th>%B</th>
                          </tr>
                        </thead>
                        <tbody>
                          {editGradientTable.map((p, i) => (
                            <tr key={i}>
                              <td className="text-muted-foreground">{i + 1}</td>
                              <td className="tabular-nums">{(p.time_s / 60).toFixed(2)}</td>
                              <td className="tabular-nums">{p.percent_b.toFixed(1)}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {selected.is_shared && selected.share_token && (
                  <div className="card-scientific-success">
                    <div className="flex items-center gap-2">
                      <Share2 size={16} className="text-success" />
                      <div className="flex-1">
                        <p className="text-sm font-medium">Shared Method</p>
                        <p className="text-xs text-muted-foreground">
                          Share link: {window.location.origin}/shared/{selected.share_token}
                        </p>
                      </div>
                      <button
                        onClick={() => {
                          navigator.clipboard
                            .writeText(`${window.location.origin}/shared/${selected.share_token}`)
                            .then(() => toast.success('Link copied'))
                            .catch(() => toast.error('Could not copy link'));
                        }}
                        className="btn-outline btn-sm"
                      >
                        <Copy size={12} className="mr-1" /> Copy
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <EmptyState
                icon={<Eye size={24} />}
                title="Select a method"
                description="Click a method from the list to view details and chromatogram"
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-border py-1.5">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
