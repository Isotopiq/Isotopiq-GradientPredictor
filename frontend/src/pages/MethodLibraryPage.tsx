import { useState, useCallback, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Trash2, Download, Eye, FlaskConical, Plus, Share2, Copy, ChevronDown,
} from 'lucide-react';
import { methodsApi } from '@/api/methods';
import { apiClient } from '@/api/client';
import { GradientChart } from '@/components/GradientChart';
import { EmptyState } from '@/components/EmptyState';
import { Skeleton } from '@/components/Skeleton';
import { toast } from 'sonner';
import type { Method } from '@/types';

export function MethodLibraryPage() {
  const [selected, setSelected] = useState<Method | null>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const exportRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

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

  const handleExport = useCallback(async (id: string, format: string, ext: string) => {
    try {
      const resp = await apiClient.get(`/export/method/${id}`, {
        params: { format },
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
  }, []);

  const exportFormats = [
    { label: 'PDF Report', format: 'pdf', ext: 'pdf' },
    { label: 'CSV', format: 'csv', ext: 'csv' },
    { label: 'Agilent (.m)', format: 'agilent', ext: 'm' },
    { label: 'Waters (.mth)', format: 'waters', ext: 'mth' },
    { label: 'Thermo (.xml)', format: 'thermo', ext: 'xml' },
  ];

  return (
    <div className="mx-auto max-w-7xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Method Library</h1>
          <p className="text-sm text-muted-foreground">Saved LC methods</p>
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
                    <div>
                      <h2 className="text-sm font-bold">{selected.name || 'Unnamed Method'}</h2>
                      <p className="text-xs text-muted-foreground">
                        {selected.column_type} • {selected.is_shared ? 'Shared' : 'Private'}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      {/* Share button */}
                      <button
                        onClick={() => shareMutation.mutate(selected.id)}
                        className="btn-outline btn-sm"
                        disabled={shareMutation.isPending}
                      >
                        <Share2 size={14} className="mr-1" />
                        {selected.is_shared ? 'Copy Link' : 'Share'}
                      </button>

                      {/* Export dropdown */}
                      <div className="relative" ref={exportRef}>
                        <button
                          onClick={() => setExportOpen(!exportOpen)}
                          className="btn-outline btn-sm"
                        >
                          <Download size={14} className="mr-1" /> Export
                          <ChevronDown size={12} className="ml-1" />
                        </button>
                        {exportOpen && (
                          <div className="absolute right-0 top-10 z-50 w-48 overflow-hidden rounded-lg border border-border bg-card shadow-lg animate-slide-down">
                            {exportFormats.map((f) => (
                              <button
                                key={f.format}
                                onClick={() => handleExport(selected.id, f.format, f.ext)}
                                className="flex w-full items-center gap-2 px-3 py-2 text-xs hover:bg-muted"
                              >
                                <Download size={12} /> {f.label}
                              </button>
                            ))}
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
                    </div>
                  </div>

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
                </div>

                {selected.gradient_table && selected.gradient_table.length > 0 && (
                  <div className="card-scientific">
                    <h3 className="mb-3 text-sm font-semibold">Gradient Profile</h3>
                    <GradientChart gradientTable={selected.gradient_table} />
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
                          {selected.gradient_table.map((p, i) => (
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
                description="Click a method from the list to view details"
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
