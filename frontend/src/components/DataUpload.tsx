import { useState, useCallback } from 'react';
import { Upload, FileText, Download } from 'lucide-react';
import { mlApi } from '@/api/ml';
import { InfoTooltip } from '@/components/InfoTooltip';
import { toast } from 'sonner';

interface DataUploadProps {
  onTrained: () => void;
  defaultColumn?: string;
}

export function DataUpload({ onTrained, defaultColumn }: DataUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [columnType, setColumnType] = useState(defaultColumn || 'C18');
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
      toast.success(`Model trained: v${res.version} (${res.n_samples} samples)`);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || 'Training failed');
      toast.error(msg || 'Training failed');
    } finally {
      setLoading(false);
    }
  }, [file, columnType, modelType, onTrained]);

  return (
    <div className="card-scientific space-y-4">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold">Upload Training Data</h3>
        <InfoTooltip
          title="Training Data Upload"
          content="Upload a CSV file with historical LC-MS runs to train a retention time prediction model. Each row should contain the compound SMILES, method conditions, and the observed retention time. The model learns to predict retention time for new compounds under similar conditions."
        />
      </div>

      <div>
        <div className="flex items-center gap-1.5">
          <label className="label">CSV File</label>
          <InfoTooltip
            title="CSV Format"
            content="The CSV must have columns: smiles, column_type, ph, percent_b_start, percent_b_end, gradient_time_min, flow_ml_min, temperature_c, observed_rt_s. The observed_rt_s is the measured retention time in seconds — this is what the model learns to predict."
          />
        </div>
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
        <a
          href="/examples/training_data_example.csv"
          download
          className="mt-1 inline-flex items-center gap-1 text-xs text-accent hover:underline"
        >
          <Download size={11} /> Download example CSV
        </a>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="flex items-center gap-1.5">
            <label className="label">Column Type</label>
            <InfoTooltip
              title="Column Type"
              content="Select the HPLC column chemistry you're training for. Models are trained per column type — a C18 model won't work for HILIC. Choose the column that matches your training data. If your data contains multiple column types, filter the CSV to one type before uploading."
            />
          </div>
          <select
            className="input mt-1"
            value={columnType}
            onChange={(e) => setColumnType(e.target.value)}
          >
            <option value="C18">C18 (reversed-phase)</option>
            <option value="phenyl">Phenyl (reversed-phase)</option>
            <option value="HILIC">HILIC (hydrophilic)</option>
            <option value="ion_pair">Ion Pair</option>
          </select>
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <label className="label">Model Type</label>
            <InfoTooltip
              title="Model Type Selection"
              content="XGBoost: Best general-purpose choice. High accuracy, handles non-linear relationships well, good with mixed feature types. Recommended for most cases. LightGBM: Faster training, similar accuracy to XGBoost. Good for larger datasets (>1000 samples). Ensemble (XGB+LGBM): Averages both models. Most robust — reduces overfitting and gives better uncertainty estimates. Use when you want maximum reliability. sklearn GBM: Baseline model, simpler and more interpretable. Use for comparison or when XGBoost/LightGBM aren't available."
            />
          </div>
          <select
            className="input mt-1"
            value={modelType}
            onChange={(e) => setModelType(e.target.value)}
          >
            <option value="xgboost">XGBoost (recommended)</option>
            <option value="lightgbm">LightGBM (faster)</option>
            <option value="ensemble">Ensemble (most robust)</option>
            <option value="sklearn">sklearn GBM (baseline)</option>
          </select>
        </div>
      </div>

      {/* Training tips */}
      <div className="rounded-md border border-border bg-muted/30 p-3">
        <p className="text-xs font-medium text-muted-foreground">When to use each model:</p>
        <ul className="mt-1.5 space-y-1 text-xs text-muted-foreground">
          <li>• <span className="font-medium">XGBoost</span> — default choice, best accuracy/speed balance</li>
          <li>• <span className="font-medium">LightGBM</span> — large datasets (&gt;1000 rows), faster training</li>
          <li>• <span className="font-medium">Ensemble</span> — maximum robustness, best uncertainty estimates</li>
          <li>• <span className="font-medium">sklearn GBM</span> — interpretable baseline for comparison</li>
        </ul>
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
