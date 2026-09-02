import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Upload, FileText, Layers, Download } from 'lucide-react';
import { methodsApi } from '@/api/methods';
import { parseCompoundCsv, parseSdf } from '@/lib/sdfParser';
import { MoleculeThumbnail } from '@/components/MoleculeViewer';
import { EmptyState } from '@/components/EmptyState';
import { toast } from 'sonner';
import type { MultiCompoundSuggestion } from '@/types';

interface ParsedCompound {
  name?: string;
  smiles: string;
  molfile?: string;
}

export function BatchAnalysisPage() {
  const [compounds, setCompounds] = useState<ParsedCompound[]>([]);
  const [results, setResults] = useState<MultiCompoundSuggestion | null>(null);
  const [fileName, setFileName] = useState('');

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);

    try {
      const content = await file.text();
      let parsed: ParsedCompound[] = [];

      if (file.name.toLowerCase().endsWith('.sdf')) {
        const records = parseSdf(content);
        parsed = records.map((r) => ({
          name: r.properties['Name'] || r.properties['name'] || undefined,
          smiles: r.properties['SMILES'] || r.properties['smiles'] || '',
          molfile: r.molfile,
        })).filter((p) => p.smiles || p.molfile);
      } else {
        // CSV
        const csvCompounds = parseCompoundCsv(content);
        parsed = csvCompounds
          .map((c) => ({ name: c.name, smiles: c.smiles }))
          .filter((p) => p.smiles?.trim());
      }

      if (parsed.length === 0) {
        toast.error('No valid compounds found in file');
        return;
      }

      setCompounds(parsed);
      setResults(null);
      toast.success(`Parsed ${parsed.length} compounds from ${file.name}`);
    } catch {
      toast.error('Failed to parse file');
    }
  };

  const suggestMutation = useMutation({
    mutationFn: (smilesList: string[]) => methodsApi.suggestMulti(smilesList),
    onSuccess: (data) => {
      setResults(data);
      toast.success('Multi-compound analysis complete');
    },
    onError: () => toast.error('Analysis failed — check SMILES validity'),
  });

  const exportResults = () => {
    if (!results) return;
    const rows = results.per_compound.map((c, i) => ({
      index: i + 1,
      smiles: c.smiles || '',
      column: (c.column as { column_type?: string })?.column_type || '',
      logp: c.logp ?? '',
      logd: c.logd ?? '',
      predicted_rt_s: c.predicted_rt_s ?? '',
      peak_width_s: c.peak_width_s ?? '',
    }));
    const headers = Object.keys(rows[0] || {});
    const csv = [
      headers.join(','),
      ...rows.map((r) => headers.map((h) => r[h as keyof typeof r]).join(',')),
    ].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'batch_analysis.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mx-auto max-w-6xl p-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold">Batch Compound Analysis</h1>
        <p className="text-sm text-muted-foreground">
          Upload multiple compounds via CSV or SDF and run multi-compound method optimization
        </p>
      </div>

      {/* Upload zone */}
      <div className="card-scientific mb-6">
        <label className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed border-border py-8 hover:border-accent hover:bg-muted/30">
          <Upload size={32} className="text-muted-foreground" />
          <p className="text-sm font-medium">
            Drop CSV or SDF file here, or click to browse
          </p>
          <p className="text-xs text-muted-foreground">
            CSV: name,smiles columns • SDF: standard format with SMILES property
          </p>
          <div className="mt-2 flex gap-3">
            <a
              href="/examples/batch_compounds_example.csv"
              download
              className="inline-flex items-center gap-1 text-xs text-accent hover:underline"
            >
              <Download size={11} /> Example CSV
            </a>
          </div>
          <input
            type="file"
            accept=".csv,.sdf,.txt"
            className="hidden"
            onChange={handleFileUpload}
          />
        </label>
        {fileName && (
          <p className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
            <FileText size={12} /> {fileName} — {compounds.length} compounds parsed
          </p>
        )}
      </div>

      {/* Parsed compounds table */}
      {compounds.length > 0 && (
        <div className="card-scientific mb-6">
          <div className="section-header mb-3">
            <div>
              <h2>Parsed Compounds ({compounds.length})</h2>
            </div>
            <button
              className="btn-primary btn-sm"
              onClick={() => suggestMutation.mutate(compounds.map((c) => c.smiles))}
              disabled={suggestMutation.isPending}
            >
              {suggestMutation.isPending ? 'Analyzing...' : 'Generate Suggestions'}
            </button>
          </div>

          <div className="max-h-60 overflow-y-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th></th>
                  <th>Name</th>
                  <th>SMILES</th>
                </tr>
              </thead>
              <tbody>
                {compounds.map((c, i) => (
                  <tr key={i}>
                    <td>
                      {c.smiles && <MoleculeThumbnail smiles={c.smiles} size={36} />}
                    </td>
                    <td className="font-medium">{c.name || `Compound ${i + 1}`}</td>
                    <td className="max-w-xs truncate font-mono text-xs">{c.smiles}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Results */}
      {results && (
        <div className="space-y-4">
          <div className="card-scientific">
            <div className="section-header mb-3">
              <div>
                <h2>Analysis Results</h2>
                <p>
                  {results.per_compound.length} compounds • {results.co_elution_count} co-elution risks detected
                </p>
              </div>
              <button className="btn-outline btn-sm" onClick={exportResults}>
                <Download size={14} className="mr-1" /> Export CSV
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>SMILES</th>
                    <th>Column</th>
                    <th>logP</th>
                    <th>logD</th>
                    <th>Pred RT (s)</th>
                    <th>Width (s)</th>
                  </tr>
                </thead>
                <tbody>
                  {results.per_compound.map((c, i) => (
                    <tr key={i}>
                      <td className="text-muted-foreground">{i + 1}</td>
                      <td className="max-w-xs truncate font-mono text-xs">
                        {(c.smiles as string) || '—'}
                      </td>
                      <td>
                        <span className="badge badge-info">
                          {(c.column as { column_type?: string })?.column_type || '—'}
                        </span>
                      </td>
                      <td>{(c.logp as number)?.toFixed(2) ?? '—'}</td>
                      <td>{(c.logd as number)?.toFixed(2) ?? '—'}</td>
                      <td>{(c.predicted_rt_s as number)?.toFixed(1) ?? '—'}</td>
                      <td>{(c.peak_width_s as number)?.toFixed(1) ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {results.resolution_matrix.length > 0 && (
            <div className="card-scientific">
              <h2 className="mb-3 text-base font-semibold">Resolution Matrix</h2>
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Pair</th>
                      <th>RT A (s)</th>
                      <th>RT B (s)</th>
                      <th>Resolution (Rs)</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.resolution_matrix.map((r, i) => {
                      const ra = r as { compound_a: number; compound_b: number; rt_a: number; rt_b: number; resolution: number; co_elution_risk: boolean };
                      return (
                        <tr key={i}>
                          <td>
                            #{ra.compound_a + 1} vs #{ra.compound_b + 1}
                          </td>
                          <td>{ra.rt_a?.toFixed(1)}</td>
                          <td>{ra.rt_b?.toFixed(1)}</td>
                          <td className="font-medium">{ra.resolution?.toFixed(2)}</td>
                          <td>
                            {ra.co_elution_risk ? (
                              <span className="badge badge-danger">Co-elution risk</span>
                            ) : (
                              <span className="badge badge-success">Resolved</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {compounds.length === 0 && !results && (
        <EmptyState
          icon={<Layers size={24} />}
          title="No compounds loaded"
          description="Upload a CSV or SDF file to start batch analysis"
        />
      )}
    </div>
  );
}
