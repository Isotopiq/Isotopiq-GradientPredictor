import { useState, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Upload, FileText, Download, FlaskConical, Beaker, Zap, ChevronDown, ChevronRight,
  AlertCircle, CheckCircle2, Loader2, Settings2,
} from 'lucide-react';
import { DataUpload } from '@/components/DataUpload';
import { CompoundPicker } from '@/components/CompoundPicker';
import { GradientChart } from '@/components/GradientChart';
import { mlApi } from '@/api/ml';
import { methodImportApi } from '@/api/methodImport';
import { compoundsApi } from '@/api/compounds';
import { InfoTooltip } from '@/components/InfoTooltip';
import { toast } from 'sonner';
import type { Compound } from '@/types';

// Types from methodImport API
import type { ParsedMethod as ParsedMethodType, ExtractPeaksResponse as ExtractPeaksResponseType, TrainFromPeaksResponse as TrainFromPeaksResponseType } from '@/api/methodImport';

interface SelectedCompound {
  id: string;
  name: string | null;
  smiles: string | null;
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
  const [mzxmlFile, setMzxmlFile] = useState<File | null>(null);
  const [selectedCompounds, setSelectedCompounds] = useState<SelectedCompound[]>([]);
  const [columnType, setColumnType] = useState(defaultColumn);
  const [modelType, setModelType] = useState('xgboost');
  const [mzTolerancePpm, setMzTolerancePpm] = useState(10);
  const [minSnr, setMinSnr] = useState(3);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [parsedMethod, setParsedMethod] = useState<ParsedMethodType | null>(null);
  const [parsingMeth, setParsingMeth] = useState(false);
  const [peakResults, setPeakResults] = useState<ExtractPeaksResponseType | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [training, setTraining] = useState(false);
  const [trainResult, setTrainResult] = useState<TrainFromPeaksResponseType | null>(null);

  const handleMethFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setMethFile(f);
    setParsedMethod(null);
    setParsingMeth(true);
    try {
      const result = await methodImportApi.parseMeth(f);
      setParsedMethod(result);
      toast.success(`Parsed method: ${result.method_name || 'Unknown'} — ${result.gradient_table.length} gradient steps`);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(msg || 'Failed to parse .meth file');
    } finally {
      setParsingMeth(false);
    }
  };

  const handleMzxmlFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      setMzxmlFile(f);
      setPeakResults(null);
      setTrainResult(null);
    }
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

  const handleExtractPeaks = async () => {
    if (!mzxmlFile) {
      toast.error('Select an mzXML file first');
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
        mzxmlFile,
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
        toast.success(`Peaks detected for ${detected}/${total} compounds`);
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
    if (!mzxmlFile || selectedCompounds.length === 0) return;
    setTraining(true);
    setTrainResult(null);
    try {
      const result = await methodImportApi.trainFromPeaks(
        mzxmlFile,
        selectedCompounds.map((sc) => sc.id),
        {
          methFile: methFile || undefined,
          column_type: columnType,
          model_type: modelType,
          mz_tolerance_ppm: mzTolerancePpm,
          min_snr: minSnr,
        },
      );
      setTrainResult(result);
      toast.success(`Model trained: ${result.n_samples} samples from ${result.compounds_used.length} compounds`);
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
          content="Upload a Thermo Chromeleon .meth file to auto-import chromatography conditions (gradient, flow, temperature, solvents). Then upload the corresponding mzXML file and select compounds — the app will extract ion chromatograms, detect peaks, and generate training data automatically."
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
          Thermo Chromeleon .meth file — chromatography conditions are auto-imported.
        </p>
      </div>

      {/* Parsed method display */}
      {parsedMethod && (
        <div className="rounded-md border border-border bg-muted/30 p-3">
          <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
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

      {/* Step 2: Upload mzXML file */}
      <div>
        <label className="label flex items-center gap-1.5">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-accent/10 text-[10px] font-bold text-accent">2</span>
          mzXML Data File
        </label>
        <div className="mt-1 flex items-center gap-2">
          <label className="btn-outline cursor-pointer text-xs">
            <Upload size={14} />
            Choose mzXML file
            <input type="file" accept=".mzxml,.mzXML" onChange={handleMzxmlFile} className="hidden" />
          </label>
          {mzxmlFile && (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <FileText size={12} />
              {mzxmlFile.name}
            </span>
          )}
        </div>
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
                <FlaskConical size={12} className="shrink-0 text-accent" />
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

      {/* Extract peaks button */}
      <button
        onClick={handleExtractPeaks}
        disabled={extracting || !mzxmlFile || selectedCompounds.length === 0}
        className="btn-outline w-full"
      >
        {extracting ? (
          <><Loader2 size={14} className="animate-spin" /> Extracting Peaks...</>
        ) : (
          <><Zap size={14} /> Extract Peaks from mzXML</>
        )}
      </button>

      {/* Peak results */}
      {peakResults && (
        <div className="space-y-3">
          <div className="rounded-md border border-border bg-muted/30 p-3">
            <p className="text-xs font-medium">
              mzXML: {peakResults.mzxml_summary.num_scans} scans ({peakResults.mzxml_summary.num_ms1_scans} MS1)
            </p>
            <p className="text-xs text-muted-foreground">
              RT range: {peakResults.mzxml_summary.rt_start_s?.toFixed(1)}s — {peakResults.mzxml_summary.rt_end_s?.toFixed(1)}s
              {peakResults.mzxml_summary.polarity && ` | ${peakResults.mzxml_summary.polarity}`}
            </p>
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
              disabled={training}
              className="btn-primary w-full"
            >
              {training ? (
                <><Loader2 size={14} className="animate-spin" /> Training Model...</>
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
            Model trained: {trainResult.n_samples} samples
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
