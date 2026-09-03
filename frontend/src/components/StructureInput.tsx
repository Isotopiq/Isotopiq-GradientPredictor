import { useState } from 'react';
import { Search, Upload, Pencil, FileText } from 'lucide-react';
import { compoundsApi } from '@/api/compounds';
import { CompoundSearch } from '@/components/CompoundSearch';
import { KetcherEditor } from '@/components/KetcherEditor';
import type { Compound } from '@/types';
import { cn } from '@/lib/utils';

type Tab = 'draw' | 'paste' | 'upload' | 'search';

interface StructureInputProps {
  onCompoundCreated: (compound: Compound) => void;
  onSmilesChange: (smiles: string) => void;
}

export function StructureInput({ onCompoundCreated, onSmilesChange }: StructureInputProps) {
  const [tab, setTab] = useState<Tab>('search');
  const [smiles, setSmiles] = useState('');
  const [inchi, setInchi] = useState('');
  const [molfile, setMolfile] = useState('');
  const [compoundName, setCompoundName] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const tabs: { id: Tab; label: string; icon: typeof Pencil }[] = [
    { id: 'search', label: 'Search', icon: Search },
    { id: 'draw', label: 'Draw', icon: Pencil },
    { id: 'paste', label: 'Paste', icon: FileText },
    { id: 'upload', label: 'Upload', icon: Upload },
  ];

  const handleCreate = async (e?: React.MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    setLoading(true);
    setError(null);
    try {
      const compound = await compoundsApi.create({
        smiles: smiles || undefined,
        inchi: inchi || undefined,
        molfile: molfile || undefined,
        name: compoundName,
      });
      onCompoundCreated(compound);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || 'Failed to create compound');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSelect = (result: { smiles: string; name?: string }) => {
    setSmiles(result.smiles);
    setCompoundName(result.name);
    onSmilesChange(result.smiles);
    setError(null);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    setMolfile(text);
  };

  return (
    <div className="card flex flex-col gap-3">
      <h3 className="text-sm font-semibold">Structure Input</h3>

      {/* Tabs */}
      <div className="flex gap-1 rounded-md bg-muted p-1">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              'flex flex-1 items-center justify-center gap-1 rounded px-2 py-1 text-xs font-medium transition-colors',
              tab === t.id ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground',
            )}
          >
            <t.icon size={12} />
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'search' && (
        <div className="flex flex-col gap-2">
          <label className="label">Search PubChem & ChemSpider</label>
          <CompoundSearch onSelect={handleSearchSelect} />
          {smiles && (
            <div className="rounded-md border border-border bg-muted/50 p-2">
              <p className="text-xs text-muted-foreground">Selected SMILES:</p>
              <p className="mt-0.5 break-all font-mono text-xs">{smiles}</p>
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            Real-time search across PubChem and ChemSpider databases.
          </p>
        </div>
      )}

      {tab === 'draw' && (
        <div className="flex flex-col gap-2">
          <div className="overflow-hidden rounded-md border border-border">
            <KetcherEditor
              smiles={smiles || undefined}
              onSmilesChange={(s) => {
                setSmiles(s);
                setCompoundName(undefined);
                onSmilesChange(s);
              }}
            />
          </div>
          {smiles && (
            <div className="rounded-md border border-border bg-muted/50 p-2">
              <p className="text-xs text-muted-foreground">Current SMILES:</p>
              <p className="mt-0.5 break-all font-mono text-xs">{smiles}</p>
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            Draw your molecule and the SMILES will be extracted automatically.
          </p>
        </div>
      )}

      {tab === 'paste' && (
        <div className="flex flex-col gap-2">
          <div>
            <label className="label">SMILES</label>
            <textarea
              className="input mt-1 h-20 font-mono text-xs"
              placeholder="e.g. CCO for ethanol"
              value={smiles}
              onChange={(e) => {
                setSmiles(e.target.value);
                setCompoundName(undefined);
                onSmilesChange(e.target.value);
              }}
            />
          </div>
          <div>
            <label className="label">InChI</label>
            <textarea
              className="input mt-1 h-20 font-mono text-xs"
              placeholder="InChI=1S/..."
              value={inchi}
              onChange={(e) => setInchi(e.target.value)}
            />
          </div>
        </div>
      )}

      {tab === 'upload' && (
        <div className="flex flex-col gap-2">
          <label className="label">Upload .mol or .sdf file</label>
          <input
            type="file"
            accept=".mol,.sdf"
            onChange={handleFileUpload}
            className="text-xs"
          />
          {molfile && (
            <p className="text-xs text-muted-foreground">
              File loaded ({molfile.length} chars)
            </p>
          )}
        </div>
      )}

      {error && <p className="text-xs text-destructive">{error}</p>}

      {/* Submit */}
      <button
        type="button"
        onClick={handleCreate}
        disabled={loading || (!smiles && !inchi && !molfile)}
        className="btn-primary w-full"
      >
        {loading ? 'Processing...' : 'Calculate Descriptors'}
      </button>
    </div>
  );
}
