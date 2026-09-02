import { useState, useCallback } from 'react';
import { Upload, FileText } from 'lucide-react';
import { mlApi } from '@/api/ml';

interface DataUploadProps {
  onTrained: () => void;
}

export function DataUpload({ onTrained }: DataUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [columnType, setColumnType] = useState('C18');
  const [modelType, setModelType] = useState('xgboost');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    artifact_id: string;
    version: number;
    n_samples: number;
    metrics: Record<string, number>;
  } | null>(null);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  };

  const handleTrain = useCallback(async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await mlApi.trainFromCsv(file, columnType, modelType);
      setResult(res);
      onTrained();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || 'Training failed');
    } finally {
      setLoading(false);
    }
  }, [file, columnType, modelType, onTrained]);

  return (
    <div className="card space-y-4">
      <h3 className="text-sm font-semibold">Upload Training Data</h3>

      <div>
        <label className="label">CSV File</label>
        <div className="mt-1 flex items-center gap-2">
          <label className="btn-outline cursor-pointer text-xs">
            <Upload size={14} />
            Choose file
            <input type="file" accept=".csv" onChange={handleFile} className="hidden" />
          </label>
          {file && (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <FileText size={12} />
              {file.name}
            </span>
          )}
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          Columns: smiles, column_type, ph, percent_b_start, percent_b_end,
          gradient_time_min, flow_ml_min, temperature_c, observed_rt_s
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Column Type</label>
          <select
            className="input mt-1"
            value={columnType}
            onChange={(e) => setColumnType(e.target.value)}
          >
            <option value="C18">C18</option>
            <option value="phenyl">Phenyl</option>
            <option value="HILIC">HILIC</option>
            <option value="ion_pair">Ion Pair</option>
          </select>
        </div>
        <div>
          <label className="label">Model Type</label>
          <select
            className="input mt-1"
            value={modelType}
            onChange={(e) => setModelType(e.target.value)}
          >
            <option value="xgboost">XGBoost</option>
            <option value="lightgbm">LightGBM</option>
            <option value="ensemble">Ensemble (XGB+LGBM)</option>
            <option value="sklearn">sklearn GBM</option>
          </select>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {result && (
        <div className="rounded-md border border-success/30 bg-success/10 p-3 text-xs">
          <p className="font-medium text-success">
            Model trained: v{result.version} ({result.n_samples} samples)
          </p>
          {result.metrics && (
            <div className="mt-2 space-y-0.5">
              {Object.entries(result.metrics)
                .filter(([k]) => !['feature_names', 'n_samples'].includes(k))
                .map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-muted-foreground">{k}</span>
                    <span className="tabular-nums">{typeof v === 'number' ? v.toFixed(4) : v}</span>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

      <button onClick={handleTrain} disabled={loading || !file} className="btn-primary w-full">
        {loading ? 'Training...' : 'Train Model'}
      </button>
    </div>
  );
}
