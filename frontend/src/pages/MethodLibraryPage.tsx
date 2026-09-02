import { useEffect, useState, useCallback } from 'react';
import { Trash2, Download, Eye, FlaskConical, Plus } from 'lucide-react';
import { methodsApi } from '@/api/methods';
import { apiClient } from '@/api/client';
import type { Method } from '@/types';

export function MethodLibraryPage() {
  const [methods, setMethods] = useState<Method[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Method | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await methodsApi.list();
      setMethods(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this method? This cannot be undone.')) return;
    try {
      await methodsApi.delete(id);
      await load();
      if (selected?.id === id) setSelected(null);
    } catch {
      // ignore
    }
  };

  const handleExport = async (id: string, format: 'pdf' | 'csv') => {
    try {
      const resp = await apiClient.get(`/export/method/${id}`, {
        params: { format },
        responseType: 'blob',
      });
      const url = URL.createObjectURL(resp.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `method_${id}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // ignore
    }
  };

  return (
    <main className="mx-auto max-w-7xl px-4 py-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-bold">Method Library</h1>
        <button
          onClick={() => (window.location.href = '/')}
          className="btn-outline flex items-center gap-1.5 text-sm"
        >
          <Plus size={14} />
          New Method
        </button>
      </div>

      {loading ? (
        <div className="card animate-pulse">
          <div className="h-4 w-32 rounded bg-muted" />
        </div>
      ) : methods.length === 0 ? (
        <div className="card flex flex-col items-center gap-3 py-12 text-center">
          <FlaskConical size={32} className="text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            No saved methods yet. Use the Predictor to generate and save a method.
          </p>
          <button
            onClick={() => (window.location.href = '/')}
            className="btn-primary text-sm"
          >
            Go to Predictor
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {/* Method list */}
          <div className="lg:col-span-1">
            <div className="card overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs text-muted-foreground">
                    <th className="py-2 pr-3">Column</th>
                    <th className="py-2 pr-3">pH</th>
                    <th className="py-2 pr-3">Flow</th>
                    <th className="py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {methods.map((m) => (
                    <tr
                      key={m.id}
                      className={`cursor-pointer border-b border-border last:border-0 hover:bg-muted/50 ${
                        selected?.id === m.id ? 'bg-muted' : ''
                      }`}
                      onClick={() => setSelected(m)}
                    >
                      <td className="py-2 pr-3 font-medium">{m.column_type}</td>
                      <td className="py-2 pr-3 tabular-nums">{m.ph ?? '—'}</td>
                      <td className="py-2 pr-3 tabular-nums">
                        {m.flow_rate_ml_min ?? '—'}
                      </td>
                      <td className="py-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(m.id);
                          }}
                          className="text-muted-foreground hover:text-destructive"
                        >
                          <Trash2 size={14} />
                        </button>
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
              <div className="card space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold">Method Details</h3>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleExport(selected.id, 'csv')}
                      className="btn-outline flex items-center gap-1 text-xs"
                    >
                      <Download size={12} />
                      CSV
                    </button>
                    <button
                      onClick={() => handleExport(selected.id, 'pdf')}
                      className="btn-outline flex items-center gap-1 text-xs"
                    >
                      <Download size={12} />
                      PDF
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 text-sm">
                  <DetailRow label="Column" value={selected.column_type} />
                  <DetailRow label="pH" value={selected.ph?.toString() ?? '—'} />
                  <DetailRow
                    label="Flow Rate"
                    value={selected.flow_rate_ml_min ? `${selected.flow_rate_ml_min} mL/min` : '—'}
                  />
                  <DetailRow
                    label="Temperature"
                    value={selected.temperature_c ? `${selected.temperature_c}°C` : '—'}
                  />
                  <DetailRow label="Mobile Phase A" value={selected.mobile_phase_a ?? '—'} />
                  <DetailRow label="Mobile Phase B" value={selected.mobile_phase_b ?? '—'} />
                  <DetailRow label="Additive" value={selected.additive ?? '—'} />
                  <DetailRow
                    label="Gradient Points"
                    value={selected.gradient_table ? `${selected.gradient_table.length} steps` : '—'}
                  />
                </div>

                {selected.gradient_table && selected.gradient_table.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground">Gradient Program</p>
                    <table className="mt-1 w-full text-xs">
                      <thead>
                        <tr className="border-b border-border text-left text-muted-foreground">
                          <th className="py-1.5 pr-3">Time (min)</th>
                          <th className="py-1.5">%B</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selected.gradient_table.map((p, i) => (
                          <tr key={i} className="border-b border-border last:border-0">
                            <td className="py-1.5 pr-3 tabular-nums">
                              {(p.time_s / 60).toFixed(2)}
                            </td>
                            <td className="py-1.5 tabular-nums">{p.percent_b.toFixed(1)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ) : (
              <div className="card flex h-full flex-col items-center justify-center gap-2 text-center">
                <Eye size={32} className="text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  Select a method from the list to view details.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </main>
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
