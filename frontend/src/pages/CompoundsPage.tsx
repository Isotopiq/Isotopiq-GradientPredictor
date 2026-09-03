import { useState, useEffect, useRef, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Trash2, Search, Plus, FlaskConical, ChevronDown, X, Edit3, Check, Share2, Layers, ListPlus, FolderOpen, ArrowRight } from 'lucide-react';
import { compoundsApi } from '@/api/compounds';
import { compoundListsApi } from '@/api/compoundLists';
import { CompoundSearch } from '@/components/CompoundSearch';
import { MoleculeThumbnail } from '@/components/MoleculeViewer';
import { CompoundDetailModal } from '@/components/CompoundDetailModal';
import { EmptyState } from '@/components/EmptyState';
import { Skeleton } from '@/components/Skeleton';
import { toast } from 'sonner';
import type { Compound, CompoundList } from '@/types';

type Tab = 'compounds' | 'lists';

export function CompoundsPage() {
  const [tab, setTab] = useState<Tab>('compounds');
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [pasteSmiles, setPasteSmiles] = useState('');
  const [pasteName, setPasteName] = useState('');
  const [selectedCompound, setSelectedCompound] = useState<Compound | null>(null);
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

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { name?: string; cas?: string; is_shared?: boolean } }) =>
      compoundsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compounds'] });
      toast.success('Compound updated');
    },
    onError: () => toast.error('Failed to update compound'),
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
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Compound Library</h1>
          <p className="text-sm text-muted-foreground">
            Saved compounds and grouped lists for reuse with the predictor
          </p>
        </div>
        {tab === 'compounds' && (
          <button
            type="button"
            onClick={() => setShowAdd(!showAdd)}
            className="btn-primary btn-sm"
          >
            <Plus size={14} /> Add Compound
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="mb-4 flex gap-1 rounded-md bg-muted p-1 w-fit">
        <button
          onClick={() => setTab('compounds')}
          className={`flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-medium transition-colors ${
            tab === 'compounds' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground'
          }`}
        >
          <FlaskConical size={14} /> Compounds
        </button>
        <button
          onClick={() => setTab('lists')}
          className={`flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-medium transition-colors ${
            tab === 'lists' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground'
          }`}
        >
          <Layers size={14} /> Lists
        </button>
      </div>

      {/* ===== Compounds Tab ===== */}
      {tab === 'compounds' && (
        <>
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
                  onUpdate={(data) => updateMutation.mutate({ id: c.id, data })}
                  updating={updateMutation.isPending}
                  onStructureClick={() => setSelectedCompound(c)}
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
        </>
      )}

      {/* ===== Lists Tab ===== */}
      {tab === 'lists' && (
        <CompoundListsTab />
      )}

      {/* Compound detail modal */}
      <CompoundDetailModal
        compound={selectedCompound}
        onClose={() => setSelectedCompound(null)}
        onUseInPredictor={handleUseInPredictor}
      />
    </div>
  );
}

// ===== Compound Lists Tab =====

function CompoundListsTab() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showEditor, setShowEditor] = useState(false);
  const [editingList, setEditingList] = useState<CompoundList | null>(null);
  const [listName, setListName] = useState('');
  const [listDescription, setListDescription] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [searchCompounds, setSearchCompounds] = useState('');

  const { data: lists, isLoading: listsLoading } = useQuery({
    queryKey: ['compound-lists'],
    queryFn: () => compoundListsApi.list(),
  });

  const { data: allCompounds } = useQuery({
    queryKey: ['compounds', ''],
    queryFn: () => compoundsApi.list(),
  });

  const saveMutation = useMutation({
    mutationFn: (data: { name: string; description?: string; compound_ids: string[]; id?: string }) => {
      if (data.id) {
        return compoundListsApi.update(data.id, {
          name: data.name,
          description: data.description,
          compound_ids: data.compound_ids,
        });
      }
      return compoundListsApi.create({
        name: data.name,
        description: data.description,
        compound_ids: data.compound_ids,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compound-lists'] });
      toast.success(editingList ? 'Compound list updated' : 'Compound list created');
      resetEditor();
    },
    onError: () => toast.error('Failed to save compound list'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => compoundListsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compound-lists'] });
      toast.success('Compound list deleted');
    },
    onError: () => toast.error('Failed to delete compound list'),
  });

  const resetEditor = () => {
    setShowEditor(false);
    setEditingList(null);
    setListName('');
    setListDescription('');
    setSelectedIds(new Set());
    setSearchCompounds('');
  };

  const handleOpenCreate = () => {
    resetEditor();
    setShowEditor(true);
  };

  const handleOpenEdit = (list: CompoundList) => {
    setEditingList(list);
    setListName(list.name);
    setListDescription(list.description || '');
    setSelectedIds(new Set(list.compound_ids));
    setSearchCompounds('');
    setShowEditor(true);
  };

  const handleSave = () => {
    if (!listName.trim()) {
      toast.error('Enter a list name');
      return;
    }
    if (selectedIds.size === 0) {
      toast.error('Select at least one compound');
      return;
    }
    saveMutation.mutate({
      name: listName.trim(),
      description: listDescription.trim() || undefined,
      compound_ids: Array.from(selectedIds),
      id: editingList?.id,
    });
  };

  const handleDelete = (list: CompoundList) => {
    if (confirm(`Delete compound list "${list.name}"?`)) {
      deleteMutation.mutate(list.id);
    }
  };

  const handleSendToPredictor = async (list: CompoundList) => {
    if (!list.compound_ids || list.compound_ids.length === 0) {
      toast.error('This list has no compounds');
      return;
    }
    // Fetch first compound's SMILES to pass via URL, and store the list ID
    // so the predictor can load all compounds
    try {
      const first = await compoundsApi.get(list.compound_ids[0]);
      const smi = first.smiles || '';
      // Store the list ID in sessionStorage so the predictor can pick it up
      sessionStorage.setItem('predictor_load_list_id', list.id);
      navigate(`/?smiles=${encodeURIComponent(smi)}`);
      toast.success(`Loading "${list.name}" (${list.compound_ids.length} compounds) into predictor`);
    } catch {
      toast.error('Failed to load compounds from list');
    }
  };

  const toggleCompound = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const filteredCompounds = allCompounds?.filter((c) => {
    if (!searchCompounds) return true;
    const q = searchCompounds.toLowerCase();
    return (
      (c.name || '').toLowerCase().includes(q) ||
      (c.smiles || '').toLowerCase().includes(q) ||
      (c.cas || '').toLowerCase().includes(q)
    );
  }) || [];

  // Fetch compound details for list cards
  const { data: listCompoundDetails } = useQuery({
    queryKey: ['list-compound-details', lists?.map((l) => l.id).join(',')],
    queryFn: async () => {
      if (!lists) return {};
      const details: Record<string, Compound[]> = {};
      for (const list of lists) {
        const comps: Compound[] = [];
        for (const cid of list.compound_ids.slice(0, 20)) {
          try {
            const c = await compoundsApi.get(cid);
            comps.push(c);
          } catch { /* skip */ }
        }
        details[list.id] = comps;
      }
      return details;
    },
    enabled: !!lists && lists.length > 0,
  });

  return (
    <div>
      {!showEditor && (
        <div className="mb-4 flex justify-end">
          <button onClick={handleOpenCreate} className="btn-primary btn-sm">
            <ListPlus size={14} /> New List
          </button>
        </div>
      )}

      {/* List Editor */}
      {showEditor && (
        <div className="card-scientific mb-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">
              {editingList ? 'Edit Compound List' : 'Create Compound List'}
            </h3>
            <button onClick={resetEditor} className="text-muted-foreground hover:text-foreground">
              <X size={16} />
            </button>
          </div>

          <div className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-3">
            {/* Left: list info + compound picker */}
            <div className="lg:col-span-1 space-y-3">
              <div>
                <label className="label">List Name</label>
                <input
                  className="input mt-1"
                  placeholder="e.g. Caffeine metabolites"
                  value={listName}
                  onChange={(e) => setListName(e.target.value)}
                  autoFocus
                />
              </div>
              <div>
                <label className="label">Description (optional)</label>
                <input
                  className="input mt-1"
                  placeholder="Brief description..."
                  value={listDescription}
                  onChange={(e) => setListDescription(e.target.value)}
                />
              </div>
              <div className="rounded-md border border-border bg-muted/30 p-2 text-xs text-muted-foreground">
                <span className="font-medium text-foreground">{selectedIds.size}</span> compound(s) selected
              </div>

              {/* Compound search filter */}
              <div>
                <label className="label">Filter compounds</label>
                <div className="relative mt-1">
                  <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <input
                    className="input pl-8 text-xs"
                    placeholder="Search name, SMILES, CAS..."
                    value={searchCompounds}
                    onChange={(e) => setSearchCompounds(e.target.value)}
                  />
                </div>
              </div>
            </div>

            {/* Right: compound selection grid */}
            <div className="lg:col-span-2">
              <label className="label">Select compounds to include</label>
              {filteredCompounds.length === 0 ? (
                <p className="mt-2 text-xs text-muted-foreground">
                  No compounds available. Add compounds to your library first.
                </p>
              ) : (
                <div className="mt-2 max-h-[400px] space-y-1.5 overflow-y-auto rounded-md border border-border p-2">
                  {filteredCompounds.map((c) => {
                    const isSelected = selectedIds.has(c.id);
                    return (
                      <label
                        key={c.id}
                        className={`flex cursor-pointer items-center gap-2 rounded-md border p-2 text-xs transition-colors ${
                          isSelected ? 'border-accent/40 bg-accent/5' : 'border-border hover:bg-muted/30'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleCompound(c.id)}
                          className="accent-accent shrink-0"
                        />
                        {c.smiles && (
                          <MoleculeThumbnail smiles={c.smiles} size={36} />
                        )}
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-medium">{c.name || 'Unnamed'}</p>
                          <p className="truncate font-mono text-[10px] text-muted-foreground">
                            {c.smiles?.slice(0, 40)}{c.smiles && c.smiles.length > 40 ? '...' : ''}
                          </p>
                        </div>
                        {c.mw && (
                          <span className="shrink-0 text-[10px] tabular-nums text-muted-foreground">
                            {c.mw.toFixed(0)} Da
                          </span>
                        )}
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          <div className="mt-4 flex justify-end gap-2">
            <button onClick={resetEditor} className="btn-ghost btn-sm">Cancel</button>
            <button
              onClick={handleSave}
              disabled={!listName.trim() || selectedIds.size === 0 || saveMutation.isPending}
              className="btn-primary btn-sm"
            >
              {saveMutation.isPending ? 'Saving...' : editingList ? 'Update List' : 'Create List'}
            </button>
          </div>
        </div>
      )}

      {/* Lists grid */}
      {listsLoading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-48 w-full rounded-lg" />)}
        </div>
      ) : lists && lists.length > 0 ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {lists.map((list) => {
            const details = listCompoundDetails?.[list.id] || [];
            return (
              <div key={list.id} className="card-scientific flex flex-col gap-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate text-sm font-semibold">{list.name}</h3>
                    {list.description && (
                      <p className="truncate text-xs text-muted-foreground">{list.description}</p>
                    )}
                  </div>
                  <span className="badge badge-info text-[10px] shrink-0">
                    {list.compound_ids.length} compound{list.compound_ids.length !== 1 ? 's' : ''}
                  </span>
                </div>

                {/* Compound thumbnails preview */}
                {details.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {details.slice(0, 6).map((c) => (
                      <div key={c.id} className="rounded border border-border p-0.5" title={c.name || c.smiles || ''}>
                        {c.smiles && <MoleculeThumbnail smiles={c.smiles} size={32} />}
                      </div>
                    ))}
                    {details.length > 6 && (
                      <span className="flex h-9 w-9 items-center justify-center rounded border border-border text-[10px] text-muted-foreground">
                        +{list.compound_ids.length - 6}
                      </span>
                    )}
                  </div>
                )}

                {/* Compound names */}
                {details.length > 0 && (
                  <div className="text-xs text-muted-foreground">
                    {details.slice(0, 3).map((c) => c.name || 'Unnamed').join(', ')}
                    {details.length > 3 && ` +${details.length - 3} more`}
                  </div>
                )}

                <div className="flex items-center gap-2 pt-1 mt-auto">
                  <button
                    onClick={() => handleSendToPredictor(list)}
                    className="btn-primary btn-sm flex-1"
                    title="Load all compounds into the predictor"
                  >
                    <ArrowRight size={12} /> Use in Predictor
                  </button>
                  <button
                    onClick={() => handleOpenEdit(list)}
                    className="btn-ghost btn-sm"
                    title="Edit list"
                  >
                    <Edit3 size={14} />
                  </button>
                  <button
                    onClick={() => handleDelete(list)}
                    className="btn-ghost btn-sm text-destructive hover:bg-destructive/10"
                    title="Delete list"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <EmptyState
          icon={<Layers size={24} />}
          title="No compound lists yet"
          description="Create grouped lists of compounds for reuse with the predictor. Click 'New List' to select compounds from your library and save them as a named group."
        />
      )}
    </div>
  );
}

function CompoundCard({
  compound,
  onDelete,
  onUse,
  onUpdate,
  updating,
  onStructureClick,
}: {
  compound: Compound;
  onDelete: () => void;
  onUse: () => void;
  onUpdate: (data: { name?: string; cas?: string; is_shared?: boolean }) => void;
  updating: boolean;
  onStructureClick: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState(compound.name || '');
  const [editCas, setEditCas] = useState(compound.cas || '');

  const handleSaveEdit = () => {
    onUpdate({
      name: editName.trim() || undefined,
      cas: editCas.trim() || undefined,
    });
    setEditing(false);
  };

  const handleCancelEdit = () => {
    setEditName(compound.name || '');
    setEditCas(compound.cas || '');
    setEditing(false);
  };

  const handleToggleShare = () => {
    onUpdate({ is_shared: !compound.is_shared });
  };

  return (
    <div className="card-scientific flex flex-col gap-2">
      {editing ? (
        /* Edit mode */
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">Edit Compound</h3>
            <button onClick={handleCancelEdit} className="text-muted-foreground hover:text-foreground">
              <X size={16} />
            </button>
          </div>
          <div>
            <label className="label">Name</label>
            <input
              className="input mt-1 text-xs"
              placeholder="e.g. Caffeine"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              autoFocus
            />
          </div>
          <div>
            <label className="label">CAS Number</label>
            <input
              className="input mt-1 text-xs"
              placeholder="e.g. 58-08-2"
              value={editCas}
              onChange={(e) => setEditCas(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={handleCancelEdit} className="btn-ghost btn-sm">Cancel</button>
            <button onClick={handleSaveEdit} disabled={updating} className="btn-primary btn-sm">
              <Check size={12} /> Save
            </button>
          </div>
        </div>
      ) : (
        /* Display mode */
        <>
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <h3 className="truncate text-sm font-semibold">
                {compound.name || 'Unnamed compound'}
              </h3>
              <p className="truncate font-mono text-[10px] text-muted-foreground">
                {compound.smiles || '—'}
              </p>
              {compound.cas && (
                <p className="text-[10px] text-muted-foreground">CAS: {compound.cas}</p>
              )}
            </div>
            <div className="flex shrink-0 items-center gap-1">
              {compound.source === 'pubchem' && (
                <span className="badge badge-info text-[10px]">PubChem</span>
              )}
              {compound.is_shared && (
                <span className="badge badge-success text-[10px]" title="Shared with all users">
                  <Share2 size={8} className="mr-0.5" /> Shared
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3">
            {compound.smiles && (
              <MoleculeThumbnail
                smiles={compound.smiles}
                size={72}
                onClick={onStructureClick}
              />
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
            <div className="flex flex-wrap items-center gap-1">
              <span
                className="text-[10px] text-muted-foreground"
                title="pKa values are estimated using functional-group SMARTS matching with literature-typical values. Compounds with the same functional groups will show the same estimated pKa. These are approximations, not experimentally measured values."
              >
                pKa (est.):
              </span>
              {compound.pka_values.map((pka, i) => (
                <span key={i} className="badge badge-warning text-[10px]">{pka.toFixed(1)}</span>
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
              onClick={() => setEditing(true)}
              className="btn-ghost btn-sm"
              title="Edit compound details"
            >
              <Edit3 size={14} />
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
        </>
      )}
    </div>
  );
}
