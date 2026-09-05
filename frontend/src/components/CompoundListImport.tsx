import { useState, useRef, useCallback, useEffect } from 'react';
import {
  Upload,
  FileText,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Search,
  ChevronRight,
  ChevronLeft,
  X,
  FlaskConical,
} from 'lucide-react';
import { compoundListsApi } from '@/api/compoundLists';
import { MoleculeThumbnail } from '@/components/MoleculeViewer';
import { toast } from 'sonner';
import type {
  CSVCompoundEntry,
  CSVParseResult,
  ImportResolveStatus,
  ResolvedCompound,
} from '@/types';

type Step = 'upload' | 'preview' | 'resolving' | 'review' | 'finalizing';

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export function CompoundListImport({ open, onClose, onCreated }: Props) {
  const [step, setStep] = useState<Step>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [pasteText, setPasteText] = useState('');
  const [useLipidmaps, setUseLipidmaps] = useState(false);
  const [parseResult, setParseResult] = useState<CSVParseResult | null>(null);
  const [parsing, setParsing] = useState(false);
  const [resolveStatus, setResolveStatus] = useState<ImportResolveStatus | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [confirmedRows, setConfirmedRows] = useState<Set<number>>(new Set());
  const [manualSmiles, setManualSmiles] = useState<Record<number, string>>({});
  const [selectedCandidates, setSelectedCandidates] = useState<Record<number, number>>({});
  const [listName, setListName] = useState('');
  const [listDescription, setListDescription] = useState('');
  const [finalizing, setFinalizing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Reset state when dialog closes
  useEffect(() => {
    if (!open) {
      setStep('upload');
      setFile(null);
      setPasteText('');
      setUseLipidmaps(false);
      setParseResult(null);
      setResolveStatus(null);
      setJobId(null);
      setConfirmedRows(new Set());
      setManualSmiles({});
      setSelectedCandidates({});
      setListName('');
      setListDescription('');
      if (pollRef.current) {
        clearTimeout(pollRef.current);
        pollRef.current = null;
      }
    }
  }, [open]);

  // Poll for resolution status
  useEffect(() => {
    if (!jobId || step !== 'resolving') return;

    const poll = async () => {
      try {
        const status = await compoundListsApi.getResolveStatus(jobId);
        setResolveStatus(status);
        if (status.status === 'complete' || status.status === 'failed') {
          setStep('review');
          // Auto-select all resolved compounds
          const confirmed = new Set<number>();
          for (const r of status.results) {
            if (r.status === 'resolved' && r.smiles) {
              confirmed.add(r.row_index);
            }
          }
          setConfirmedRows(confirmed);
          return;
        }
        pollRef.current = setTimeout(poll, 1000);
      } catch {
        pollRef.current = setTimeout(poll, 2000);
      }
    };

    poll();
    return () => {
      if (pollRef.current) {
        clearTimeout(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [jobId, step]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f && f.name.endsWith('.csv')) {
      setFile(f);
    }
  }, []);

  const handleParse = async () => {
    if (!file && !pasteText.trim()) {
      toast.error('Please select a CSV file or paste CSV content');
      return;
    }
    setParsing(true);
    try {
      let result: CSVParseResult;
      if (file) {
        result = await compoundListsApi.parseCsv(file);
      } else {
        // Create a File from pasted text
        const blob = new Blob([pasteText], { type: 'text/csv' });
        const csvFile = new File([blob], 'pasted.csv', { type: 'text/csv' });
        result = await compoundListsApi.parseCsv(csvFile);
      }
      setParseResult(result);
      setStep('preview');
      toast.success(`Parsed ${result.total_rows} compound(s) from CSV`);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to parse CSV');
    } finally {
      setParsing(false);
    }
  };

  const handleStartResolve = async () => {
    if (!parseResult) return;
    setStep('resolving');
    setResolveStatus(null);
    try {
      const { job_id } = await compoundListsApi.startResolve(
        parseResult.entries,
        useLipidmaps,
      );
      setJobId(job_id);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to start resolution');
      setStep('preview');
    }
  };

  const toggleConfirm = (rowIndex: number) => {
    setConfirmedRows((prev) => {
      const next = new Set(prev);
      if (next.has(rowIndex)) {
        next.delete(rowIndex);
      } else {
        next.add(rowIndex);
      }
      return next;
    });
  };

  const confirmAllResolved = () => {
    if (!resolveStatus) return;
    const next = new Set(confirmedRows);
    for (const r of resolveStatus.results) {
      if (r.status === 'resolved' && r.smiles) {
        next.add(r.row_index);
      }
    }
    setConfirmedRows(next);
  };

  const deselectUnresolved = () => {
    if (!resolveStatus) return;
    const next = new Set(confirmedRows);
    for (const r of resolveStatus.results) {
      if (r.status !== 'resolved' || !r.smiles) {
        next.delete(r.row_index);
      }
    }
    setConfirmedRows(next);
  };

  const getSmilesForRow = (r: ResolvedCompound): string | null => {
    // Manual override takes priority
    const manual = manualSmiles[r.row_index];
    if (manual && manual.trim()) return manual.trim();

    // Selected candidate override
    const candIdx = selectedCandidates[r.row_index];
    if (candIdx !== undefined && r.candidates[candIdx]) {
      return r.candidates[candIdx].smiles;
    }

    return r.smiles ?? null;
  };

  const handleConfirm = async () => {
    if (!resolveStatus) return;
    if (!listName.trim()) {
      toast.error('Please enter a list name');
      return;
    }

    const compounds: { smiles: string; name?: string; cas?: string; source?: string }[] = [];
    for (const r of resolveStatus.results) {
      if (!confirmedRows.has(r.row_index)) continue;
      const smiles = getSmilesForRow(r);
      if (!smiles) continue;
      compounds.push({
        smiles,
        name: r.name,
        cas: r.cas || undefined,
        source: r.source === 'unresolved' && manualSmiles[r.row_index] ? 'manual' : r.source,
      });
    }

    if (compounds.length === 0) {
      toast.error('No compounds selected. Confirm at least one compound.');
      return;
    }

    setFinalizing(true);
    setStep('finalizing');
    try {
      const result = await compoundListsApi.confirmImport(
        listName,
        listDescription || undefined,
        compounds,
      );
      toast.success(
        `Created "${result.compound_list.name}" with ${compounds.length} compound(s) ` +
        `(${result.compounds_created} new, ${result.compounds_reused} reused)`,
      );
      onCreated();
      onClose();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to create compound list');
      setStep('review');
    } finally {
      setFinalizing(false);
    }
  };

  if (!open) return null;

  const status = resolveStatus;
  const results = status?.results || [];
  const confirmedCount = confirmedRows.size;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-lg border border-border bg-background shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-2">
            <FlaskConical className="h-5 w-5 text-accent" />
            <h2 className="text-sm font-semibold">Import Compound List from CSV</h2>
            {/* Step indicator */}
            <div className="ml-4 flex items-center gap-1 text-[10px] text-muted-foreground">
              {(['upload', 'preview', 'resolving', 'review', 'finalizing'] as Step[]).map((s, i) => (
                <span key={s} className={`flex items-center gap-1 ${step === s ? 'font-bold text-foreground' : ''}`}>
                  {i > 0 && <ChevronRight size={10} className="mx-0.5" />}
                  <span className="capitalize">{s === 'resolving' ? 'resolve' : s}</span>
                </span>
              ))}
            </div>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* Step 1: Upload */}
          {step === 'upload' && (
            <div className="space-y-4">
              <div
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
                className="rounded-lg border-2 border-dashed border-border p-8 text-center"
              >
                <Upload className="mx-auto h-10 w-10 text-muted-foreground" />
                <p className="mt-2 text-sm text-muted-foreground">
                  Drag & drop a CSV file here, or
                </p>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="btn-secondary btn-sm mt-2"
                >
                  <FileText size={14} /> Choose File
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,text/csv"
                  className="hidden"
                  onChange={handleFileSelect}
                />
                {file && (
                  <p className="mt-2 text-xs text-foreground">
                    Selected: <strong>{file.name}</strong> ({(file.size / 1024).toFixed(1)} KB)
                  </p>
                )}
              </div>

              <div className="text-center text-xs text-muted-foreground">— or paste CSV —</div>
              <textarea
                value={pasteText}
                onChange={(e) => setPasteText(e.target.value)}
                placeholder="compound,formula,,rt,charge&#10;PC(32:1),C40H80NO8P,,12.5,1&#10;..."
                className="h-32 w-full rounded border border-border bg-background px-3 py-2 font-mono text-xs"
              />

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="use-lipidmaps"
                  checked={useLipidmaps}
                  onChange={(e) => setUseLipidmaps(e.target.checked)}
                  className="rounded border-border"
                />
                <label htmlFor="use-lipidmaps" className="text-xs">
                  Query LipidMaps API for lipid compounds
                  <span className="ml-1 text-muted-foreground">
                    (slower but better resolution for lipid shorthand like PC(32:1))
                  </span>
                </label>
              </div>

              <div className="flex justify-end">
                <button
                  onClick={handleParse}
                  disabled={parsing || (!file && !pasteText.trim())}
                  className="btn-primary btn-sm"
                >
                  {parsing ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
                  Parse CSV
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Parse Preview */}
          {step === 'preview' && parseResult && (
            <div className="space-y-4">
              <div className="text-sm">
                Found <strong>{parseResult.total_rows}</strong> compounds.
                Detected columns: {Object.entries(parseResult.columns_detected).map(([k, v]) => (
                  <span key={k} className="ml-1 inline-block rounded bg-muted px-1.5 py-0.5 text-[10px]">
                    {k} → {v}
                  </span>
                ))}
              </div>
              <div className="max-h-[50vh] overflow-y-auto rounded border border-border">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-muted">
                    <tr>
                      <th className="px-2 py-1 text-left">#</th>
                      <th className="px-2 py-1 text-left">Name</th>
                      <th className="px-2 py-1 text-left">Formula</th>
                      <th className="px-2 py-1 text-right">RT</th>
                      <th className="px-2 py-1 text-right">Charge</th>
                      <th className="px-2 py-1 text-left">SMILES</th>
                    </tr>
                  </thead>
                  <tbody>
                    {parseResult.entries.slice(0, 100).map((e) => (
                      <tr key={e.row_index} className="border-b border-border/50">
                        <td className="px-2 py-1 text-muted-foreground">{e.row_index}</td>
                        <td className="px-2 py-1 font-medium">{e.name}</td>
                        <td className="px-2 py-1">{e.formula || '—'}</td>
                        <td className="px-2 py-1 text-right">{e.rt ?? '—'}</td>
                        <td className="px-2 py-1 text-right">{e.charge ?? '—'}</td>
                        <td className="px-2 py-1 truncate max-w-[200px] text-muted-foreground">
                          {e.smiles || '—'}
                        </td>
                      </tr>
                    ))}
                    {parseResult.entries.length > 100 && (
                      <tr>
                        <td colSpan={6} className="px-2 py-2 text-center text-muted-foreground">
                          ... and {parseResult.entries.length - 100} more
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between">
                <button onClick={() => setStep('upload')} className="btn-secondary btn-sm">
                  <ChevronLeft size={14} /> Back
                </button>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  {useLipidmaps && (
                    <span className="badge badge-info">LipidMaps enabled</span>
                  )}
                </div>
                <button onClick={handleStartResolve} className="btn-primary btn-sm">
                  Start Resolution <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Resolving (progress) */}
          {step === 'resolving' && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Loader2 className="h-5 w-5 animate-spin text-accent" />
                <span className="text-sm font-semibold">Resolving compounds...</span>
              </div>
              {status && (
                <>
                  <div className="w-full rounded-full bg-muted">
                    <div
                      className="rounded-full bg-accent transition-all"
                      style={{ width: `${status.progress_pct}%` }}
                    />
                  </div>
                  <div className="flex gap-4 text-xs">
                    <span>Processed: <strong>{status.processed}</strong> / {status.total}</span>
                    <span className="text-green-600">Resolved: <strong>{status.resolved}</strong></span>
                    <span className="text-yellow-600">Ambiguous: <strong>{status.ambiguous}</strong></span>
                    <span className="text-red-600">Unresolved: <strong>{status.unresolved}</strong></span>
                  </div>
                  {/* Live results table */}
                  <div className="max-h-[40vh] overflow-y-auto rounded border border-border">
                    <table className="w-full text-xs">
                      <thead className="sticky top-0 bg-muted">
                        <tr>
                          <th className="px-2 py-1 text-left">Name</th>
                          <th className="px-2 py-1 text-left">Status</th>
                          <th className="px-2 py-1 text-left">Source</th>
                          <th className="px-2 py-1 text-left">SMILES</th>
                        </tr>
                      </thead>
                      <tbody>
                        {results.map((r) => (
                          <tr key={r.row_index} className="border-b border-border/50">
                            <td className="px-2 py-1 font-medium">{r.name}</td>
                            <td className="px-2 py-1">
                              {r.status === 'resolved' && <CheckCircle2 size={12} className="text-green-500" />}
                              {r.status === 'ambiguous' && <AlertTriangle size={12} className="text-yellow-500" />}
                              {r.status === 'unresolved' && <XCircle size={12} className="text-red-500" />}
                              <span className="ml-1">{r.status}</span>
                            </td>
                            <td className="px-2 py-1">{r.source}</td>
                            <td className="px-2 py-1 truncate max-w-[200px] text-muted-foreground">
                              {r.smiles || '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Step 4: Review & Confirm */}
          {step === 'review' && status && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="text-sm">
                  Review resolved compounds. Confirm or reject each entry.
                </div>
                <div className="flex gap-2">
                  <button onClick={confirmAllResolved} className="btn-secondary btn-sm text-xs">
                    Select All Resolved
                  </button>
                  <button onClick={deselectUnresolved} className="btn-secondary btn-sm text-xs">
                    Deselect Unresolved
                  </button>
                </div>
              </div>

              <div className="max-h-[45vh] overflow-y-auto rounded border border-border">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-muted">
                    <tr>
                      <th className="px-2 py-1 text-center">✓</th>
                      <th className="px-2 py-1 text-left">Structure</th>
                      <th className="px-2 py-1 text-left">Name</th>
                      <th className="px-2 py-1 text-left">SMILES</th>
                      <th className="px-2 py-1 text-left">Formula</th>
                      <th className="px-2 py-1 text-right">MW</th>
                      <th className="px-2 py-1 text-left">Source</th>
                      <th className="px-2 py-1 text-left">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((r) => {
                      const smiles = getSmilesForRow(r);
                      const confirmed = confirmedRows.has(r.row_index);
                      return (
                        <tr
                          key={r.row_index}
                          className={`border-b border-border/50 ${confirmed ? 'bg-green-500/5' : ''}`}
                        >
                          <td className="px-2 py-1 text-center">
                            <input
                              type="checkbox"
                              checked={confirmed}
                              onChange={() => toggleConfirm(r.row_index)}
                              disabled={!smiles && !manualSmiles[r.row_index]}
                            />
                          </td>
                          <td className="px-2 py-1">
                            {smiles ? (
                              <MoleculeThumbnail smiles={smiles} size={48} />
                            ) : (
                              <div className="flex h-12 w-12 items-center justify-center rounded bg-muted text-muted-foreground">
                                ?
                              </div>
                            )}
                          </td>
                          <td className="px-2 py-1 font-medium">{r.name}</td>
                          <td className="px-2 py-1 max-w-[200px]">
                            {r.status === 'ambiguous' && r.candidates.length > 1 ? (
                              <select
                                value={selectedCandidates[r.row_index] ?? 0}
                                onChange={(e) => {
                                  setSelectedCandidates((prev) => ({
                                    ...prev,
                                    [r.row_index]: parseInt(e.target.value),
                                  }));
                                }}
                                className="w-full rounded border border-border bg-background px-1 py-0.5 text-[10px]"
                              >
                                {r.candidates.map((c, i) => (
                                  <option key={i} value={i}>
                                    {c.smiles.substring(0, 50)}
                                    {c.smiles.length > 50 ? '...' : ''}
                                  </option>
                                ))}
                              </select>
                            ) : r.status === 'unresolved' ? (
                              <input
                                type="text"
                                value={manualSmiles[r.row_index] || ''}
                                onChange={(e) => {
                                  setManualSmiles((prev) => ({
                                    ...prev,
                                    [r.row_index]: e.target.value,
                                  }));
                                }}
                                placeholder="Paste SMILES..."
                                className="w-full rounded border border-border bg-background px-1 py-0.5 text-[10px]"
                              />
                            ) : (
                              <span className="truncate text-muted-foreground" title={smiles || ''}>
                                {smiles || '—'}
                              </span>
                            )}
                          </td>
                          <td className="px-2 py-1">{r.formula || '—'}</td>
                          <td className="px-2 py-1 text-right tabular-nums">
                            {r.mw ? r.mw.toFixed(1) : '—'}
                          </td>
                          <td className="px-2 py-1">
                            <span className={`badge text-[9px] ${
                              r.source === 'pubchem' ? 'badge-info' :
                              r.source === 'lipidmaps' ? 'badge-success' :
                              r.source === 'manual' ? 'badge-info' :
                              'badge-warning'
                            }`}>
                              {r.source}
                            </span>
                          </td>
                          <td className="px-2 py-1">
                            {r.status === 'resolved' && <CheckCircle2 size={12} className="text-green-500" />}
                            {r.status === 'ambiguous' && <AlertTriangle size={12} className="text-yellow-500" />}
                            {r.status === 'unresolved' && <XCircle size={12} className="text-red-500" />}
                            {r.warnings.length > 0 && (
                              <span className="ml-1 text-[10px] text-muted-foreground" title={r.warnings.join('; ')}>
                                ⚠
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* List naming */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">List Name</label>
                  <input
                    value={listName}
                    onChange={(e) => setListName(e.target.value)}
                    placeholder="e.g. Lipid Positive XT v3"
                    className="input mt-1"
                  />
                </div>
                <div>
                  <label className="label">Description (optional)</label>
                  <input
                    value={listDescription}
                    onChange={(e) => setListDescription(e.target.value)}
                    placeholder="e.g. Lipidomics positive mode list"
                    className="input mt-1"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between">
                <button onClick={() => setStep('preview')} className="btn-secondary btn-sm">
                  <ChevronLeft size={14} /> Back
                </button>
                <span className="text-xs text-muted-foreground">
                  {confirmedCount} compound(s) selected
                </span>
                <button
                  onClick={handleConfirm}
                  disabled={confirmedCount === 0 || !listName.trim()}
                  className="btn-primary btn-sm"
                >
                  <CheckCircle2 size={14} /> Create List ({confirmedCount})
                </button>
              </div>
            </div>
          )}

          {/* Step 5: Finalizing */}
          {step === 'finalizing' && (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-accent" />
              <p className="mt-2 text-sm">Creating compound list...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
