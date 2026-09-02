import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Trash2, Database, ChevronRight, BarChart3 } from 'lucide-react';
import { mlApi } from '@/api/ml';
import { FeatureImportanceChart } from '@/components/FeatureImportanceChart';
import { LearningCurveChart } from '@/components/LearningCurveChart';
import { EmptyState } from '@/components/EmptyState';
import { Skeleton } from '@/components/Skeleton';
import { toast } from 'sonner';
import type { ModelArtifact } from '@/types';

export function ModelsPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: models, isLoading } = useQuery({
    queryKey: ['ml-models'],
    queryFn: () => mlApi.listModels(),
  });

  const { data: selectedModel } = useQuery({
    queryKey: ['ml-model', selectedId],
    queryFn: () => mlApi.getModel(selectedId!),
    enabled: !!selectedId,
  });

  const { data: featureImportance } = useQuery({
    queryKey: ['feature-importance', selectedId],
    queryFn: () => mlApi.featureImportance(selectedId!),
    enabled: !!selectedId,
  });

  const { data: modelHistory } = useQuery({
    queryKey: ['model-history', selectedId],
    queryFn: () => mlApi.modelHistory(selectedId!),
    enabled: !!selectedId,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => mlApi.deleteModel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ml-models'] });
      setSelectedId(null);
      toast.success('Model deleted');
    },
    onError: () => toast.error('Failed to delete model'),
  });

  return (
    <div className="mx-auto max-w-7xl p-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold">ML Models</h1>
        <p className="text-sm text-muted-foreground">Trained retention prediction models</p>
      </div>

      {isLoading ? (
        <Skeleton className="h-64" />
      ) : !models || models.length === 0 ? (
        <EmptyState
          icon={<Database size={24} />}
          title="No trained models yet"
          description="Upload training data to get started"
        />
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Model list */}
          <div className="lg:col-span-1">
            <div className="card-scientific overflow-x-auto">
              <h2 className="mb-3 text-sm font-semibold">Models ({models.length})</h2>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Column</th>
                    <th>Type</th>
                    <th>Ver</th>
                    <th>R²</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {models.map((m: ModelArtifact) => (
                    <tr
                      key={m.id}
                      onClick={() => setSelectedId(m.id)}
                      className="cursor-pointer"
                      style={selectedId === m.id ? { background: 'hsl(var(--muted))' } : undefined}
                    >
                      <td className="font-medium">{m.column_type}</td>
                      <td>
                        <span className="badge badge-info">{m.model_type}</span>
                      </td>
                      <td className="tabular-nums">v{m.version}</td>
                      <td className="tabular-nums">
                        {(m.train_metrics as Record<string, number>)?.r2?.toFixed(3) ?? '—'}
                      </td>
                      <td>
                        <ChevronRight size={14} className="text-muted-foreground" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Model detail */}
          <div className="lg:col-span-2 space-y-4">
            {selectedModel ? (
              <>
                <div className="card-scientific">
                  <div className="section-header mb-3">
                    <div>
                      <h2 className="text-sm font-bold">
                        {selectedModel.column_type} • {selectedModel.model_type} v{selectedModel.version}
                      </h2>
                      <p className="text-xs text-muted-foreground">
                        {selectedModel.n_samples} samples • Trained {new Date(selectedModel.trained_at).toLocaleString()}
                      </p>
                    </div>
                    <button
                      onClick={() => deleteMutation.mutate(selectedModel.id)}
                      className="btn-outline btn-sm text-destructive"
                    >
                      <Trash2 size={14} className="mr-1" /> Delete
                    </button>
                  </div>

                  <div className="grid grid-cols-3 gap-3 text-center">
                    <MetricBox
                      label="R²"
                      value={(selectedModel.train_metrics as Record<string, number>)?.r2?.toFixed(3) ?? '—'}
                    />
                    <MetricBox
                      label="RMSE"
                      value={(selectedModel.train_metrics as Record<string, number>)?.rmse?.toFixed(2) ?? '—'}
                    />
                    <MetricBox
                      label="Samples"
                      value={String(selectedModel.n_samples)}
                    />
                  </div>
                </div>

                {modelHistory && modelHistory.versions.length > 0 && (
                  <LearningCurveChart versions={modelHistory.versions} />
                )}

                {featureImportance && (
                  <FeatureImportanceChart data={featureImportance} />
                )}
              </>
            ) : (
              <EmptyState
                icon={<BarChart3 size={24} />}
                title="Select a model"
                description="Click a model from the list to view detailed analytics"
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function MetricBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border p-3">
      <p className="text-lg font-bold tabular-nums">{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}
