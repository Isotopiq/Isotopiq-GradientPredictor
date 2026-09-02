import { useState, useEffect, useRef, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Trash2, Search, Plus, FlaskConical, ChevronDown, X } from 'lucide-react';
import { compoundsApi } from '@/api/compounds';
import { CompoundSearch } from '@/components/CompoundSearch';
import { MoleculeThumbnail } from '@/components/MoleculeViewer';
import { EmptyState } from '@/components/EmptyState';
import { Skeleton } from '@/components/Skeleton';
import { toast } from 'sonner';
import type { Compound } from '@/types';

export function CompoundsPage() {
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [pasteSmiles, setPasteSmiles] = useState('');
  const [pasteName, setPasteName] = useState('');
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const { data: compounds, isLoading } = useQuery({
    queryKey: ['compounds', debouncedSearch],
    queryFn: () => compoundsApi.list(debouncedSearch || undefined),
  });

  const createMutation = useMutation({
    mutationFn: (data: { smiles?: string; name?: string; lookup?: boolean }) =>
      compoundsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compounds'] });
      toast.success('Compound saved to library');
      setPasteSmiles('');
      setPasteName('');
    },
    onError: () => toast.error('Failed to save compound'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => compoundsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compounds'] });
      toast.success('Compound removed');
    },
    onError: () => toast.error('Failed to delete compound'),
  });

  const handleSearchSelect = (result: { smiles: string; name?: string }) => {
    setPasteSmiles(result.smiles);
    setPasteName(result.name || '');
  };

  const handleAddFromSearch = () => {
    if (!pasteSmiles.trim()) {
      toast.error('Select or paste a SMILES first');
      return;
    }
    createMutation.mutate({
      smiles: pasteSmiles.trim(),
      name: pasteName.trim() || undefined,
    });
  };

  const handleDelete = (id: string, name: string | null) => {
    if (confirm(`Remove "${name || 'this compound'}" from your library?`)) {
      deleteMutation.mutate(id);
    }
  };

  const handleUseInPredictor = (compound: Compound) => {
    const smi = compound.smiles || '';
    if (smi) {
      navigate(`/?smiles=${encodeURIComponent(smi)}`);
    }
  };

  return (
    <div className="mx-auto max-w-7xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Compound Library</h1>
          <p className="text-sm text-muted-foreground">
            Saved compounds with cached properties — no refetch needed when reused
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowAdd(!showAdd)}
          className="btn-primary btn-sm"
        >
          <Plus size={14} /> Add Compound
        </button>
      </div>

      {/* Add panel */}
      {showAdd && (
        <div className="card-scientific mb-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">Add Compound to Library</h3>
            <button onClick={() => setShowAdd(false)} className="text-muted-foreground hover:text-foreground">
              <X size={16} />
            </button>
          </div>
          <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2">
            {/* Search */}
            <div className="space-y-2">
              <label className="label">Search PubChem / ChemSpider</label>
              <CompoundSearch onSelect={handleSearchSelect} />
              {pasteSmiles && (
                <div className="rounded-md border border-border bg-muted/50 p-2">
                  <p className="text-xs text-muted-foreground">Selected:</p>
                  <p className="mt-0.5 break-all font-mono text-xs">{pasteSmiles}</p>
                  {pasteName && <p className="mt-1 text-xs font-medium">{pasteName}</p>}
                </div>
              )}
            </div>
            {/* Manual paste */}
            <div className="space-y-2">
              <label className="label">Or paste SMILES manually</label>
              <input
                className="input font-mono text-xs"
                placeholder="e.g. CN1C=NC2=C1C(=O)N(C(=O)N2C)C"
                value={pasteSmiles}
                onChange={(e) => setPasteSmiles(e.target.value)}
              />
              <label className="label">Name (optional)</label>
              <input
                className="input"
                placeholder="e.g. Caffeine"
                value={pasteName}
                onChange={(e) => setPasteName(e.target.value)}
              />
            </div>
          </div>
          <div className="mt-3 flex justify-end">
            <button
              type="button"
              onClick={handleAddFromSearch}
              disabled={!pasteSmiles.trim() || createMutation.isPending}
              className="btn-primary btn-sm"
            >
              {createMutation.isPending ? 'Saving...' : 'Save to Library'}
            </button>
          </div>
        </div>
      )}

      {/* Search bar */}
      <div className="mb-4 flex items-center gap-2">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            className="input pl-9"
            placeholder="Search by name, SMILES, or CAS..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <span className="text-xs text-muted-foreground">
          {compounds?.length ?? 0} compound{(compounds?.length ?? 0) !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Compound grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-40 w-full rounded-lg" />
          ))}
        </div>
      ) : compounds && compounds.length > 0 ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {compounds.map((c) => (
            <CompoundCard
              key={c.id}
              compound={c}
              onDelete={() => handleDelete(c.id, c.name)}
              onUse={() => handleUseInPredictor(c)}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<FlaskConical size={24} />}
          title="No compounds saved"
          description="Click 'Add Compound' to search PubChem or paste SMILES. Saved compounds retain all properties for instant reuse."
        />
      )}
    </div>
  );
}

function CompoundCard({
  compound,
  onDelete,
  onUse,
}: {
  compound: Compound;
  onDelete: () => void;
  onUse: () => void;
}) {
  return (
    <div className="card-scientific flex flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold">
            {compound.name || 'Unnamed compound'}
          </h3>
          <p className="truncate font-mono text-[10px] text-muted-foreground">
            {compound.smiles || '—'}
          </p>
        </div>
        {compound.source === 'pubchem' && (
          <span className="badge badge-info shrink-0 text-[10px]">PubChem</span>
        )}
      </div>

      <div className="flex items-center gap-3">
        {compound.smiles && (
          <MoleculeThumbnail smiles={compound.smiles} size={56} />
        )}
        <div className="flex-1 text-xs">
          <div className="flex justify-between border-b border-border py-0.5">
            <span className="text-muted-foreground">MW</span>
            <span className="tabular-nums font-medium">{compound.mw?.toFixed(1) ?? '—'}</span>
          </div>
          <div className="flex justify-between border-b border-border py-0.5">
            <span className="text-muted-foreground">logP</span>
            <span className="tabular-nums font-medium">{compound.logp?.toFixed(2) ?? '—'}</span>
          </div>
          <div className="flex justify-between py-0.5">
            <span className="text-muted-foreground">TPSA</span>
            <span className="tabular-nums font-medium">{compound.tpsa?.toFixed(0) ?? '—'}</span>
          </div>
        </div>
      </div>

      {compound.pka_values && compound.pka_values.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {compound.pka_values.map((pka, i) => (
            <span key={i} className="badge badge-warning text-[10px]">pKa {pka.toFixed(1)}</span>
          ))}
        </div>
      )}

      <div className="flex items-center gap-2 pt-1">
        <button
          type="button"
          onClick={onUse}
          className="btn-outline btn-sm flex-1"
          title="Open in predictor"
        >
          <FlaskConical size={12} /> Use in Predictor
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="btn-ghost btn-sm text-destructive hover:bg-destructive/10"
          title="Remove from library"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  );
}
