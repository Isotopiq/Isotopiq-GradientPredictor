import { useEffect, useState } from 'react';
import { Trash2, Database } from 'lucide-react';
import { mlApi } from '@/api/ml';
import type { ModelArtifact } from '@/types';

export function ModelsPage() {
  const [models, setModels] = useState<ModelArtifact[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const data = await mlApi.listModels();
      setModels(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (id: string) => {
    try {
      await mlApi.deleteModel(id);
      await load();
    } catch {
      // ignore
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="mx-auto max-w-7xl px-4 py-3">
          <h1 className="text-lg font-bold">ML Models</h1>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6">
        {loading ? (
          <div className="card animate-pulse">
            <div className="h-4 w-32 rounded bg-muted" />
          </div>
        ) : models.length === 0 ? (
          <div className="card flex flex-col items-center gap-2 text-sm text-muted-foreground">
            <Database size={24} />
            <p>No trained models yet. Upload training data to get started.</p>
          </div>
        ) : (
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                  <th className="py-2 pr-4">Column</th>
                  <th className="py-2 pr-4">Model</th>
                  <th className="py-2 pr-4">Version</th>
                  <th className="py-2 pr-4">Samples</th>
                  <th className="py-2 pr-4">R²</th>
                  <th className="py-2 pr-4">RMSE</th>
                  <th className="py-2 pr-4">Trained</th>
                  <th className="py-2"></th>
                </tr>
              </thead>
              <tbody>
                {models.map((m) => (
                  <tr key={m.id} className="border-b border-border last:border-0">
                    <td className="py-2 pr-4 font-medium">{m.column_type}</td>
                    <td className="py-2 pr-4">{m.model_type}</td>
                    <td className="py-2 pr-4 tabular-nums">v{m.version}</td>
                    <td className="py-2 pr-4 tabular-nums">{m.n_samples}</td>
                    <td className="py-2 pr-4 tabular-nums">
                      {(m.train_metrics as Record<string, number>)?.r2?.toFixed(3) ?? '—'}
                    </td>
                    <td className="py-2 pr-4 tabular-nums">
                      {(m.train_metrics as Record<string, number>)?.rmse?.toFixed(2) ?? '—'}
                    </td>
                    <td className="py-2 pr-4 text-xs text-muted-foreground">
                      {new Date(m.trained_at).toLocaleDateString()}
                    </td>
                    <td className="py-2">
                      <button
                        onClick={() => handleDelete(m.id)}
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
        )}
      </main>
    </div>
  );
}
