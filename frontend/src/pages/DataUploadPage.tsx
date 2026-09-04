import { useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Upload, FileText, Beaker, Zap, ChevronDown, ChevronRight,
  AlertCircle, CheckCircle2, Loader2, Settings2, X, Plus, Trash2,
  Edit3, TrendingUp,
} from 'lucide-react';
import { DataUpload } from '@/components/DataUpload';
import { CompoundPicker } from '@/components/CompoundPicker';
import { mlApi } from '@/api/ml';
import { methodImportApi } from '@/api/methodImport';
import { compoundsApi } from '@/api/compounds';
import { InfoTooltip } from '@/components/InfoTooltip';
import { PeakTableInput } from '@/components/PeakTableInput';
import { PeakTrackingPanel } from '@/components/PeakTrackingPanel';
import { toast } from 'sonner';
import type { Compound } from '@/types';
import type {
  ParsedMethod as ParsedMethodType,
  ExtractPeaksResponse as ExtractPeaksResponseType,
  TrainFromPeaksResponse as TrainFromPeaksResponseType,
  ModelSummary,
} from '@/api/methodImport';

interface SelectedCompound {
  id: string;
  name: string | null;
  smiles: string | null;
}

// Editable method conditions — initialized from parsed .meth, user can override
interface EditableConditions {
  flow_rate_ml_min: string;
  column_temp_c: string;
  percent_b_start: string;
  percent_b_end: string;
  gradient_time_min: string;
  ph: string;
}

export function DataUploadPage() {
  const [searchParams] = useSearchParams();
  const preselectedColumn = searchParams.get('column');

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold">Data Upload & Model Training</h1>
        <p className="text-sm text-muted-foreground">
          Upload experimental run data to train retention prediction models. Choose between
          manual CSV upload or automated import from instrument method + mzXML files.
        </p>
      </div>

      <div className="space-y-6">
        <MethodImportSection defaultColumn={preselectedColumn || 'C18'} />
        <CsvUploadSection defaultColumn={preselectedColumn || undefined} />
      </div>
    </div>
  );
}

// --- Method Import Section (.meth + mzXML pipeline) ---

function MethodImportSection({ defaultColumn }: { defaultColumn: string }) {
  const [methFile, setMethFile] = useState<File | null>(null);
  const [mzxmlFiles, setMzxmlFiles] = useState<File[]>([]);
  const [selectedCompounds, setSelectedCompounds] = useState<SelectedCompound[]>([]);
  const [columnType, setColumnType] = useState(defaultColumn);
  const [modelType, setModelType] = useState('xgboost');
  const [mzTolerancePpm, setMzTolerancePpm] = useState(10);
  const [minSnr, setMinSnr] = useState(3);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [parsedMethod, setParsedMethod] = useState<ParsedMethodType | null>(null);
  const [parsingMeth, setParsingMeth] = useState(false);
  const [editingConditions, setEditingConditions] = useState(false);
  const [conditions, setConditions] = useState<EditableConditions>({
    flow_rate_ml_min: '',
    column_temp_c: '',
    percent_b_start: '',
    percent_b_end: '',
    gradient_time_min: '',
    ph: '',
  });

  const [peakResults, setPeakResults] = useState<ExtractPeaksResponseType | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [training, setTraining] = useState(false);
  const [trainResult, setTrainResult] = useState<TrainFromPeaksResponseType | null>(null);

  // Incremental training state
  const [incrementalMode, setIncrementalMode] = useState(false);
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);

  const { data: existingModels } = useQuery({
    queryKey: ['method-import-models', columnType],
    queryFn: () => methodImportApi.listModels(columnType),
    enabled: incrementalMode,
  });

  const handleMethFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setMethFile(f);
    setParsedMethod(null);
    setParsingMeth(true);
    try {
      const result = await methodImportApi.parseMeth(f);
      setParsedMethod(result);
      // Initialize editable conditions from parsed values
      setConditions({
        flow_rate_ml_min: result.flow_rate_ml_min?.toString() || '',
        column_temp_c: result.column_temp_c?.toString() || '',
        percent_b_start: result.percent_b_start?.toString() || '',
        percent_b_end: result.percent_b_end?.toString() || '',
        gradient_time_min: result.gradient_time_min?.toString() || '',
        ph: '',
      });
      toast.success(`Parsed method: ${result.method_name || 'Unknown'} — ${result.gradient_table.length} gradient steps`);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(msg || 'Failed to parse .meth file');
    } finally {
      setParsingMeth(false);
    }
  };

  const handleMzxmlFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    setMzxmlFiles((prev) => [...prev, ...files]);
    setPeakResults(null);
    setTrainResult(null);
  };

  const handleRemoveMzxmlFile = (idx: number) => {
    setMzxmlFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const handlePickCompound = (c: Compound) => {
    if (selectedCompounds.some((sc) => sc.id === c.id)) {
      toast.error('Compound already selected');
      return;
    }
    setSelectedCompounds((prev) => [...prev, {
      id: c.id,
      name: c.name,
      smiles: c.smiles,
    }]);
  };

  const handleRemoveCompound = (id: string) => {
    setSelectedCompounds((prev) => prev.filter((sc) => sc.id !== id));
  };

  const buildOverrides = () => {
    const overrides: Record<string, number | undefined> = {};
    if (conditions.flow_rate_ml_min) overrides.override_flow = parseFloat(conditions.flow_rate_ml_min);
    if (conditions.column_temp_c) overrides.override_temp = parseFloat(conditions.column_temp_c);
    if (conditions.percent_b_start) overrides.override_percent_b_start = parseFloat(conditions.percent_b_start);
    if (conditions.percent_b_end) overrides.override_percent_b_end = parseFloat(conditions.percent_b_end);
    if (conditions.gradient_time_min) overrides.override_gradient_time = parseFloat(conditions.gradient_time_min);
    if (conditions.ph) overrides.override_ph = parseFloat(conditions.ph);
    return overrides;
  };

  const handleExtractPeaks = async () => {
    if (mzxmlFiles.length === 0) {
      toast.error('Select at least one mzXML file');
      return;
    }
    if (selectedCompounds.length === 0) {
      toast.error('Add at least one compound');
      return;
    }
    setExtracting(true);
    setPeakResults(null);
    setTrainResult(null);
    try {
      const result = await methodImportApi.extractPeaks(
        mzxmlFiles,
        selectedCompounds.map((sc) => sc.id),
        {
          methFile: methFile || undefined,
          mz_tolerance_ppm: mzTolerancePpm,
          min_snr: minSnr,
        },
      );
      setPeakResults(result);
      const detected = result.results.filter((r) => r.peaks.length > 0).length;
      const total = result.results.length;
      if (detected > 0) {
        toast.success(`Peaks detected for ${detected}/${total} compounds across ${result.mzxml_summaries.length} file(s)`);
      } else {
        toast.warning(`No peaks detected for any of the ${total} compounds — try adjusting m/z tolerance or SNR`);
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(msg || 'Failed to extract peaks');
    } finally {
      setExtracting(false);
    }
  };

  const handleTrain = async () => {
    if (mzxmlFiles.length === 0 || selectedCompounds.length === 0) return;
    if (incrementalMode && !selectedModelId) {
      toast.error('Select an existing model to improve');
      return;
    }
    setTraining(true);
    setTrainResult(null);
    try {
      const result = await methodImportApi.trainFromPeaks(
        mzxmlFiles,
        selectedCompounds.map((sc) => sc.id),
        {
          methFile: methFile || undefined,
          column_type: columnType,
          model_type: modelType,
          mz_tolerance_ppm: mzTolerancePpm,
          min_snr: minSnr,
          existing_artifact_id: incrementalMode ? selectedModelId || undefined : undefined,
          ...buildOverrides(),
        },
      );
      setTrainResult(result);
      if (result.incremental) {
        toast.success(
          `Model improved: ${result.n_new_samples} new + ${result.existing_samples_loaded || 0} existing = ${result.n_samples} total samples`,
        );
      } else {
        toast.success(`Model trained: ${result.n_samples} samples from ${result.compounds_used.length} compounds`);
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(msg || 'Training failed');
    } finally {
      setTraining(false);
    }
  };

  return (
    <div className="card-scientific space-y-4">
      <div className="flex items-center gap-2">
        <Beaker size={18} className="text-accent" />
        <h3 className="text-sm font-semibold">Instrument Method + mzXML Import</h3>
        <InfoTooltip
          title="Automated Import"
          content="Upload a Thermo Chromeleon .meth file to auto-import chromatography conditions (gradient, flow, temperature, solvents). Then upload the corresponding mzXML file(s) and select compounds — the app will extract ion chromatograms, detect peaks, and generate training data automatically. All imported values are editable."
        />
      </div>

      {/* Step 1: Upload .meth file */}
      <div>
        <label className="label flex items-center gap-1.5">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-accent/10 text-[10px] font-bold text-accent">1</span>
          Instrument Method File (.meth)
        </label>
        <div className="mt-1 flex items-center gap-2">
          <label className="btn-outline cursor-pointer text-xs">
            <Upload size={14} />
            Choose .meth file
            <input type="file" accept=".meth" onChange={handleMethFile} className="hidden" />
          </label>
          {methFile && (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <FileText size={12} />
              {methFile.name}
              {parsingMeth && <Loader2 size={12} className="animate-spin" />}
            </span>
          )}
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          Thermo Chromeleon .meth file — chromatography conditions are auto-imported and fully editable.
        </p>
      </div>

      {/* Parsed method display with edit capability */}
      {parsedMethod && (
        <div className="rounded-md border border-border bg-muted/30 p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">Imported Conditions</span>
            <button
              onClick={() => setEditingConditions(!editingConditions)}
              className="flex items-center gap-1 text-xs text-accent hover:underline"
            >
              <Edit3 size={10} />
              {editingConditions ? 'Done editing' : 'Edit values'}
            </button>
          </div>

          {editingConditions ? (
            /* Editable conditions grid */
            <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
              <EditableField
                label="Flow Rate (ml/min)"
                value={conditions.flow_rate_ml_min}
                onChange={(v) => setConditions((p) => ({ ...p, flow_rate_ml_min: v }))}
                placeholder="0.260"
              />
              <EditableField
                label="Column Temp (°C)"
                value={conditions.column_temp_c}
                onChange={(v) => setConditions((p) => ({ ...p, column_temp_c: v }))}
                placeholder="50"
              />
              <EditableField
                label="%B Start"
                value={conditions.percent_b_start}
                onChange={(v) => setConditions((p) => ({ ...p, percent_b_start: v }))}
                placeholder="35"
              />
              <EditableField
                label="%B End"
                value={conditions.percent_b_end}
                onChange={(v) => setConditions((p) => ({ ...p, percent_b_end: v }))}
                placeholder="95"
              />
              <EditableField
                label="Gradient Time (min)"
                value={conditions.gradient_time_min}
                onChange={(v) => setConditions((p) => ({ ...p, gradient_time_min: v }))}
                placeholder="27"
              />
              <EditableField
                label="pH"
                value={conditions.ph}
                onChange={(v) => setConditions((p) => ({ ...p, ph: v }))}
                placeholder="2.7"
              />
            </div>
          ) : (
            /* Read-only display */
            <>
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
                <MethodField label="Flow Rate" value={parsedMethod.flow_rate_ml_min ? `${parsedMethod.flow_rate_ml_min} ml/min` : '—'} />
                <MethodField label="Column Temp" value={parsedMethod.column_temp_c ? `${parsedMethod.column_temp_c}°C` : '—'} />
                <MethodField label="Gradient Time" value={parsedMethod.gradient_time_min ? `${parsedMethod.gradient_time_min} min` : '—'} />
                <MethodField label="Method End" value={parsedMethod.method_end_time_min ? `${parsedMethod.method_end_time_min} min` : '—'} />
              </div>
              {parsedMethod.solvent_a && (
                <div className="mt-2 text-xs">
                  <span className="text-muted-foreground">Solvent A: </span>
                  <span className="font-medium">{parsedMethod.solvent_a}</span>
                </div>
              )}
              {parsedMethod.solvent_b && (
                <div className="mt-1 text-xs">
                  <span className="text-muted-foreground">Solvent B: </span>
                  <span className="font-medium">{parsedMethod.solvent_b}</span>
                </div>
              )}
            </>
          )}

          {parsedMethod.gradient_table.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-medium text-muted-foreground">Gradient Table:</p>
              <div className="mt-1 max-h-32 overflow-y-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border text-left text-muted-foreground">
                      <th className="py-1 pr-3">Time (min)</th>
                      <th className="py-1 pr-3">%B</th>
                      <th className="py-1 pr-3">Flow (ml/min)</th>
                      <th className="py-1">Curve</th>
                    </tr>
                  </thead>
                  <tbody>
                    {parsedMethod.gradient_table.map((row, i) => (
                      <tr key={i} className="border-b border-border/50">
                        <td className="py-1 pr-3 tabular-nums">{row.time_min.toFixed(2)}</td>
                        <td className="py-1 pr-3 tabular-nums">{row.percent_b ?? '—'}</td>
                        <td className="py-1 pr-3 tabular-nums">{row.flow_rate_ml_min ?? '—'}</td>
                        <td className="py-1 tabular-nums">{row.curve ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          {parsedMethod.warnings.length > 0 && (
            <div className="mt-2 flex items-start gap-1 text-xs text-warning">
              <AlertCircle size={12} className="mt-0.5 shrink-0" />
              <span>{parsedMethod.warnings.join('; ')}</span>
            </div>
          )}
        </div>
      )}

      {/* Step 2: Upload mzXML files (multiple) */}
      <div>
        <label className="label flex items-center gap-1.5">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-accent/10 text-[10px] font-bold text-accent">2</span>
          mzXML Data File(s)
        </label>
        <div className="mt-1 flex items-center gap-2">
          <label className="btn-outline cursor-pointer text-xs">
            <Upload size={14} />
            Add mzXML file(s)
            <input
              type="file"
              accept=".mzxml,.mzXML"
              multiple
              onChange={handleMzxmlFiles}
              className="hidden"
            />
          </label>
          {mzxmlFiles.length > 0 && (
            <span className="text-xs text-muted-foreground">{mzxmlFiles.length} file(s) selected</span>
          )}
        </div>
        {mzxmlFiles.length > 0 && (
          <div className="mt-2 space-y-1">
            {mzxmlFiles.map((f, i) => (
              <div key={i} className="flex items-center gap-2 rounded-md border border-border p-1.5">
                <FileText size={12} className="shrink-0 text-accent" />
                <span className="flex-1 truncate text-xs">{f.name}</span>
                <span className="text-[10px] text-muted-foreground">{(f.size / 1024 / 1024).toFixed(1)} MB</span>
                <button
                  onClick={() => handleRemoveMzxmlFile(i)}
                  className="rounded p-0.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                  title="Remove file"
                >
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Step 3: Select compounds */}
      <div>
        <label className="label flex items-center gap-1.5">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-accent/10 text-[10px] font-bold text-accent">3</span>
          Select Compounds for Peak Extraction
        </label>
        <CompoundPicker
          onSelect={handlePickCompound}
          placeholder="Search saved compounds to add..."
          className="mt-1"
        />
        {selectedCompounds.length > 0 && (
          <div className="mt-2 space-y-1">
            {selectedCompounds.map((sc) => (
              <div key={sc.id} className="flex items-center gap-2 rounded-md border border-border p-1.5">
                <Beaker size={12} className="shrink-0 text-accent" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-medium">{sc.name || 'Unnamed'}</p>
                  <p className="truncate font-mono text-[10px] text-muted-foreground">{sc.smiles || '—'}</p>
                </div>
                <button
                  onClick={() => handleRemoveCompound(sc.id)}
                  className="text-xs text-destructive hover:underline"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Advanced settings */}
      <div>
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          {showAdvanced ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          <Settings2 size={12} />
          Advanced Settings
        </button>
        {showAdvanced && (
          <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div>
              <label className="label">Column Type</label>
              <select className="input mt-1 text-xs" value={columnType} onChange={(e) => setColumnType(e.target.value)}>
                <option value="C18">C18</option>
                <option value="phenyl">Phenyl</option>
                <option value="HILIC">HILIC</option>
                <option value="ion_pair">Ion Pair</option>
              </select>
            </div>
            <div>
              <label className="label">Model Type</label>
              <select className="input mt-1 text-xs" value={modelType} onChange={(e) => setModelType(e.target.value)}>
                <option value="xgboost">XGBoost</option>
                <option value="lightgbm">LightGBM</option>
                <option value="ensemble">Ensemble</option>
                <option value="sklearn">sklearn</option>
              </select>
            </div>
            <div>
              <label className="label">m/z Tolerance (ppm)</label>
              <input
                type="number"
                className="input mt-1 text-xs"
                value={mzTolerancePpm}
                onChange={(e) => setMzTolerancePpm(Number(e.target.value))}
                min={1}
                max={100}
              />
            </div>
            <div>
              <label className="label">Min SNR</label>
              <input
                type="number"
                className="input mt-1 text-xs"
                value={minSnr}
                onChange={(e) => setMinSnr(Number(e.target.value))}
                min={1}
                max={20}
              />
            </div>
          </div>
        )}
      </div>

      {/* Incremental training toggle */}
      <div className="rounded-md border border-border bg-muted/20 p-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setIncrementalMode(!incrementalMode);
              if (incrementalMode) setSelectedModelId(null);
            }}
            className="flex items-center gap-1.5 text-xs font-medium"
          >
            <TrendingUp size={14} className={incrementalMode ? 'text-accent' : 'text-muted-foreground'} />
            Improve existing model
          </button>
          <InfoTooltip
            title="Incremental Training"
            content="Enable this to add new data to an existing model. The app will load the previous model's training data, merge it with the new peaks, and retrain. This improves the model over time as more data becomes available."
          />
        </div>
        {incrementalMode && (
          <div className="mt-2">
            {existingModels && existingModels.length > 0 ? (
              <select
                className="input mt-1 text-xs"
                value={selectedModelId || ''}
                onChange={(e) => setSelectedModelId(e.target.value || null)}
              >
                <option value="">Select a model to improve...</option>
                {existingModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.column_type} — {m.model_type} v{m.version} ({m.n_samples} samples, {new Date(m.trained_at).toLocaleDateString()})
                  </option>
                ))}
              </select>
            ) : (
              <p className="text-xs text-muted-foreground">
                {existingModels ? 'No existing models found for this column type.' : 'Loading models...'}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Extract peaks button */}
      <button
        onClick={handleExtractPeaks}
        disabled={extracting || mzxmlFiles.length === 0 || selectedCompounds.length === 0}
        className="btn-outline w-full"
      >
        {extracting ? (
          <><Loader2 size={14} className="animate-spin" /> Extracting Peaks...</>
        ) : (
          <><Zap size={14} /> Extract Peaks from mzXML ({mzxmlFiles.length} file(s))</>
        )}
      </button>

      {/* Peak results */}
      {peakResults && (
        <div className="space-y-3">
          <div className="rounded-md border border-border bg-muted/30 p-3">
            {peakResults.mzxml_summaries.map((s, i) => (
              <p key={i} className="text-xs font-medium">
                {s.filename}: {s.num_scans} scans ({s.num_ms1_scans} MS1)
                {s.polarity && ` | ${s.polarity}`}
              </p>
            ))}
          </div>

          {peakResults.results.map((r, i) => (
            <div key={i} className={`rounded-md border p-3 ${r.peaks.length > 0 ? 'border-success/30 bg-success/5' : 'border-border bg-muted/20'}`}>
              <div className="flex items-center gap-2">
                {r.peaks.length > 0 ? (
                  <CheckCircle2 size={14} className="text-success" />
                ) : (
                  <AlertCircle size={14} className="text-muted-foreground" />
                )}
                <span className="text-xs font-medium">{r.compound_name || r.smiles || `Compound ${i + 1}`}</span>
                {r.target_mz && (
                  <span className="text-[10px] text-muted-foreground">m/z: {r.target_mz.toFixed(4)}</span>
                )}
              </div>
              {r.peaks.length > 0 ? (
                <div className="mt-2 space-y-1">
                  {r.peaks.map((peak, j) => (
                    <div key={j} className="flex items-center gap-3 text-xs">
                      <span className="tabular-nums font-medium text-success">
                        RT: {peak.retention_time_min.toFixed(2)} min
                      </span>
                      <span className="text-muted-foreground">
                        Intensity: {peak.intensity.toExponential(2)}
                      </span>
                      {peak.signal_to_noise && (
                        <span className="text-muted-foreground">SNR: {peak.signal_to_noise.toFixed(1)}</span>
                      )}
                      {peak.peak_width_s && (
                        <span className="text-muted-foreground">Width: {peak.peak_width_s.toFixed(1)}s</span>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-1 text-xs text-muted-foreground">{r.error || 'No peaks detected'}</p>
              )}
            </div>
          ))}

          {/* Train button */}
          {peakResults.results.some((r) => r.peaks.length > 0) && (
            <button
              onClick={handleTrain}
              disabled={training || (incrementalMode && !selectedModelId)}
              className="btn-primary w-full"
            >
              {training ? (
                <><Loader2 size={14} className="animate-spin" /> Training Model...</>
              ) : incrementalMode ? (
                <><TrendingUp size={14} /> Improve Existing Model</>
              ) : (
                <><Zap size={14} /> Train Model from Detected Peaks</>
              )}
            </button>
          )}
        </div>
      )}

      {/* Training result */}
      {trainResult && (
        <div className="rounded-md border border-success/30 bg-success/10 p-3 text-xs">
          <p className="font-medium text-success">
            {trainResult.incremental ? 'Model improved' : 'Model trained'}: {trainResult.n_samples} samples
          </p>
          <div className="mt-2 space-y-0.5">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Artifact ID</span>
              <span className="font-mono text-[10px]">{trainResult.artifact_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Column Type</span>
              <span>{trainResult.column_type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Model Type</span>
              <span>{trainResult.model_type}</span>
            </div>
            {trainResult.incremental && (
              <>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">New samples</span>
                  <span className="tabular-nums">{trainResult.n_new_samples}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Existing samples loaded</span>
                  <span className="tabular-nums">{trainResult.existing_samples_loaded || 0}</span>
                </div>
              </>
            )}
            {trainResult.compounds_used.length > 0 && (
              <div className="mt-1">
                <span className="text-muted-foreground">Compounds with peaks: </span>
                <span>{trainResult.compounds_used.join(', ')}</span>
              </div>
            )}
            {trainResult.compounds_no_peaks.length > 0 && (
              <div className="mt-0.5">
                <span className="text-muted-foreground">No peaks: </span>
                <span>{trainResult.compounds_no_peaks.join(', ')}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* F11: CSV/TXT Chromatogram Import */}
      <CsvChromatogramImport />

      {/* F12: Manual Peak Table Entry */}
      <PeakTableInput onPeaksSubmit={(peaks) => {
        toast.success(`Received ${peaks.length} manual peaks — use for calibration`);
      }} />

      {/* F14: Peak Tracking / Matching */}
      <PeakTrackingPanel />

    </div>
  );
}

// F11: CSV/TXT Chromatogram Import Section
function CsvChromatogramImport() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    time_min: number[];
    intensity: number[];
    detector: string;
    wavelength_nm: number | null;
    sample_name: string;
    n_points: number;
    peaks: Array<{ rt_min: number; height: number; width_min: number; area: number; index: number }>;
  } | null>(null);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  };

  const handleParse = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const res = await methodImportApi.parseChromatogramCsv(file);
      setResult(res);
      toast.success(`Parsed ${res.n_points} points, ${res.peaks.length} peaks detected`);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to parse chromatogram');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="mb-3 flex items-center gap-2">
        <FileText size={16} className="text-accent" />
        <h3 className="text-sm font-semibold">CSV/TXT Chromatogram Import</h3>
      </div>
      <p className="mb-3 text-xs text-muted-foreground">
        Import chromatogram data from Agilent, Chromeleon, Empower, or generic CSV/TXT exports.
        Supports time/intensity columns with auto-detection of format.
      </p>
      <div className="flex gap-2">
        <label className="btn-secondary cursor-pointer text-xs">
          Choose CSV/TXT file
          <input type="file" accept=".csv,.txt,.CSV,.TXT" onChange={handleFile} className="hidden" />
        </label>
        {file && (
          <button onClick={handleParse} disabled={loading} className="btn-primary text-xs">
            {loading ? 'Parsing...' : `Parse ${file.name}`}
          </button>
        )}
      </div>

      {result && (
        <div className="mt-3 space-y-2">
          <div className="rounded-md bg-muted/30 p-2 text-xs">
            <div className="flex gap-4">
              <span><strong>Points:</strong> {result.n_points}</span>
              <span><strong>Detector:</strong> {result.detector}</span>
              {result.wavelength_nm && <span><strong>λ:</strong> {result.wavelength_nm} nm</span>}
              <span><strong>Sample:</strong> {result.sample_name}</span>
            </div>
          </div>
          {result.peaks.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-muted-foreground">Detected Peaks ({result.peaks.length})</div>
              <table className="mt-1 w-full text-xs">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-1 py-1 text-left">RT (min)</th>
                    <th className="px-1 py-1 text-right">Height</th>
                    <th className="px-1 py-1 text-right">Width (min)</th>
                    <th className="px-1 py-1 text-right">Area</th>
                  </tr>
                </thead>
                <tbody>
                  {result.peaks.map((p, i) => (
                    <tr key={i} className="border-b border-border/50">
                      <td className="px-1 py-1">{p.rt_min.toFixed(3)}</td>
                      <td className="px-1 py-1 text-right">{p.height.toFixed(1)}</td>
                      <td className="px-1 py-1 text-right">{p.width_min.toFixed(4)}</td>
                      <td className="px-1 py-1 text-right">{p.area.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MethodField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-muted-foreground">{label}: </span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

function EditableField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="label text-[10px]">{label}</label>
      <input
        type="text"
        className="input mt-0.5 text-xs"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}

// --- CSV Upload Section (existing functionality) ---

function CsvUploadSection({ defaultColumn }: { defaultColumn?: string }) {
  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <ChevronRight size={16} className="text-muted-foreground" />
        <h3 className="text-sm font-semibold">Manual CSV Upload</h3>
      </div>
      <DataUpload onTrained={() => {}} defaultColumn={defaultColumn} />
    </div>
  );
}
