import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Save, Check, Plus, Trash2, RefreshCw, Layers, AlertTriangle, ListPlus, FolderOpen, X, Edit3 } from 'lucide-react';
import { StructureInput } from '@/components/StructureInput';
import { CompoundPicker } from '@/components/CompoundPicker';
import { PropertyPanel } from '@/components/PropertyPanel';
import { MethodSuggestionCard } from '@/components/MethodSuggestionCard';
import { GradientChart } from '@/components/GradientChart';
import { ChromatogramPreview } from '@/components/ChromatogramPreview';
import { ParameterSliders } from '@/components/ParameterSliders';
import { MoleculeViewer } from '@/components/MoleculeViewer';
import { PkaPlotter } from '@/components/PkaPlotter';
import { DisclaimerTooltip } from '@/components/DisclaimerTooltip';
import { methodsApi } from '@/api/methods';
import { compoundListsApi } from '@/api/compoundLists';
import { compoundsApi } from '@/api/compounds';
import { toast } from 'sonner';
import type {
  Compound,
  CompoundList,
  MethodSuggestion,
  MethodSuggestionRequest,
  GradientPoint,
  GradientSimulateResult,
  ChromatogramResult,
  MultiCompoundSuggestion,
} from '@/types';

interface CompoundEntry {
  id: string;
  smiles: string;
  name?: string;
  compound?: Compound;
}

const COLUMN_OPTIONS = [
  { value: '', label: 'Auto (heuristic)' },
  { value: 'C18', label: 'C18 — Reversed-phase' },
  { value: 'C8', label: 'C8 — Less retentive RP' },
  { value: 'C4', label: 'C4 — Short-chain RP' },
  { value: 'phenyl', label: 'Phenyl — π-π selectivity' },
  { value: 'PFP', label: 'PFP — Pentafluorophenyl' },
  { value: 'HILIC', label: 'HILIC — Polar analytes' },
  { value: 'ion_pair', label: 'Ion-pair — Charged analytes' },
];

let compoundIdCounter = 0;

export function PredictorPage() {
  const [searchParams] = useSearchParams();
  const [compounds, setCompounds] = useState<CompoundEntry[]>([]);
  const [activeSmiles, setActiveSmiles] = useState(searchParams.get('smiles') || '');
  const [activeCompound, setActiveCompound] = useState<Compound | null>(null);
  const [suggestion, setSuggestion] = useState<MethodSuggestion | null>(null);
  const [suggesting, setSuggesting] = useState(false);
  const [gradientTable, setGradientTable] = useState<GradientPoint[]>([]);
  const [simResult, setSimResult] = useState<GradientSimulateResult | null>(null);
  const [chromatogram, setChromatogram] = useState<ChromatogramResult | null>(null);
  const [flowRate, setFlowRate] = useState(0.4);
  const [gradientTime, setGradientTime] = useState(20);
  const [ph, setPh] = useState(2.7);
  const [temperature, setTemperature] = useState(30);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Column override + multi-compound state
  const [columnChoice, setColumnChoice] = useState('');
  const [multiResult, setMultiResult] = useState<MultiCompoundSuggestion | null>(null);
  const [recalculating, setRecalculating] = useState(false);

  // Compound list save/load state
  const queryClient = useQueryClient();
  const [showSaveList, setShowSaveList] = useState(false);
  const [showLoadList, setShowLoadList] = useState(false);
  const [listName, setListName] = useState('');
  const [listDescription, setListDescription] = useState('');
  const [editingListId, setEditingListId] = useState<string | null>(null);

  const { data: savedLists } = useQuery({
    queryKey: ['compound-lists'],
    queryFn: () => compoundListsApi.list(),
  });

  const saveListMutation = useMutation({
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
      setShowSaveList(false);
      setListName('');
      setListDescription('');
      setEditingListId(null);
      toast.success(editingListId ? 'Compound list updated' : 'Compound list saved');
    },
    onError: () => toast.error('Failed to save compound list'),
  });

  const deleteListMutation = useMutation({
    mutationFn: (id: string) => compoundListsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compound-lists'] });
      toast.success('Compound list deleted');
    },
    onError: () => toast.error('Failed to delete compound list'),
  });

  const handleSaveList = () => {
    if (!listName.trim()) {
      toast.error('Enter a list name');
      return;
    }
    // Collect compound IDs — prefer stored compound IDs, otherwise skip (SMILES-only entries)
    const compoundIds = compounds
      .map((c) => c.compound?.id)
      .filter((id): id is string => !!id);

    if (compoundIds.length === 0) {
      toast.error('Add compounds from the saved library first (compounds must have IDs)');
      return;
    }

    saveListMutation.mutate({
      name: listName.trim(),
      description: listDescription.trim() || undefined,
      compound_ids: compoundIds,
      id: editingListId || undefined,
    });
  };

  const handleOpenSaveList = () => {
    setEditingListId(null);
    setListName('');
    setListDescription('');
    setShowSaveList(true);
  };

  const handleOpenEditList = (list: CompoundList) => {
    setEditingListId(list.id);
    setListName(list.name);
    setListDescription(list.description || '');
    setShowSaveList(true);
    setShowLoadList(false);
    // Load the list's compounds into the current method
    loadListCompounds(list);
  };

  const loadListCompounds = async (list: CompoundList) => {
    if (!list.compound_ids || list.compound_ids.length === 0) {
      toast.info('This list has no compounds');
      return;
    }
    try {
      // Fetch all compounds in the list
      const fetched: Compound[] = [];
      for (const cid of list.compound_ids) {
        try {
          const c = await compoundsApi.get(cid);
          fetched.push(c);
        } catch {
          // Skip compounds that can't be fetched
        }
      }
      if (fetched.length === 0) {
        toast.error('Could not load any compounds from this list');
        return;
      }
      // Replace current compounds with the loaded list
      setCompounds(fetched.map((c) => ({
        id: `cmpd-${++compoundIdCounter}`,
        smiles: c.smiles || '',
        name: c.name || undefined,
        compound: c,
      })));
      // Set first as active
      const first = fetched[0];
      setActiveCompound(first);
      setActiveSmiles(first.smiles || '');
      if (first.smiles) {
        fetchSuggestion(first.smiles);
      }
      setMultiResult(null);
      toast.success(`Loaded "${list.name}" (${fetched.length} compounds)`);
    } catch {
      toast.error('Failed to load compound list');
    }
  };

  const handleLoadList = (list: CompoundList) => {
    loadListCompounds(list);
    setShowLoadList(false);
  };

  const handleDeleteList = (list: CompoundList) => {
    if (confirm(`Delete compound list "${list.name}"?`)) {
      deleteListMutation.mutate(list.id);
    }
  };

  const handleCompoundCreated = useCallback(async (c: Compound) => {
    setActiveCompound(c);
    setSaved(false);
    const smi = c.smiles || '';
    setActiveSmiles(smi);

    // Add to compound list (avoid duplicates by SMILES)
    setCompounds((prev) => {
      if (prev.some((e) => e.smiles === smi && smi)) return prev;
      return [...prev, {
        id: `cmpd-${++compoundIdCounter}`,
        smiles: smi,
        name: c.name || undefined,
        compound: c,
      }];
    });

    if (smi) {
      try {
        await fetchSuggestion(smi);
      } catch {
        // fetchSuggestion already shows a toast
      }
    }
  }, []);

  const fetchSuggestion = async (smi: string) => {
    setSuggesting(true);
    try {
      const req: MethodSuggestionRequest = {
        smiles: smi,
        column_type: columnChoice || undefined,
      };
      const sugg = await methodsApi.suggest(req);
      setSuggestion(sugg);
      setGradientTable(sugg.gradient.gradient_table);
      setFlowRate(sugg.gradient.flow_rate_ml_min);
      setGradientTime(sugg.gradient.gradient_time_min);
      setPh(sugg.ph.recommended_ph);
    } catch {
      toast.error('Failed to generate suggestion — check SMILES validity');
    } finally {
      setSuggesting(false);
    }
  };

  const handleAddCompound = () => {
    if (!activeSmiles.trim()) {
      toast.error('Enter or search a compound first');
      return;
    }
    if (compounds.some((e) => e.smiles === activeSmiles.trim())) {
      toast.error('Compound already in list');
      return;
    }
    setCompounds((prev) => [...prev, {
      id: `cmpd-${++compoundIdCounter}`,
      smiles: activeSmiles.trim(),
      name: activeCompound?.name || undefined,
      compound: activeCompound || undefined,
    }]);
    toast.success('Compound added to method');
  };

  const handlePickSavedCompound = (c: Compound) => {
    const smi = c.smiles || '';
    if (!smi) {
      toast.error('This compound has no SMILES');
      return;
    }
    if (compounds.some((e) => e.smiles === smi)) {
      toast.error('Compound already in list');
      return;
    }
    setCompounds((prev) => [...prev, {
      id: `cmpd-${++compoundIdCounter}`,
      smiles: smi,
      name: c.name || undefined,
      compound: c,
    }]);
    // Also set as active compound for display
    setActiveCompound(c);
    setActiveSmiles(smi);
    // Fetch suggestion for this compound
    fetchSuggestion(smi);
    toast.success(`Added "${c.name || 'compound'}" from library`);
  };

  const handleRemoveCompound = (id: string) => {
    setCompounds((prev) => prev.filter((e) => e.id !== id));
  };

  const handleRecalculate = async () => {
    const validSmiles = compounds
      .map((c) => c.smiles)
      .filter((s) => s && s.trim());
    if (validSmiles.length === 0) {
      toast.error('Add at least one compound to the list');
      return;
    }
    setRecalculating(true);
    try {
      const result = await methodsApi.suggestMulti(validSmiles, {
        column_type: columnChoice || undefined,
        gradient_time_min: gradientTime,
        flow_rate_ml_min: flowRate,
      });
      setMultiResult(result);

      // Update the gradient table and primary suggestion from the merged result
      if (result.gradient?.gradient_table?.length > 0) {
        setGradientTable(result.gradient.gradient_table);
        setFlowRate(result.gradient.flow_rate_ml_min);
        setGradientTime(result.gradient.gradient_time_min);
      }

      if (result.co_elution_count > 0) {
        toast.warning(`${result.co_elution_count} co-elution risk(s) detected — review resolution matrix`);
      } else {
        toast.success(`Optimized method for ${validSmiles.length} compound(s) — no co-elution risks`);
      }
    } catch {
      toast.error('Failed to recalculate method for compound set');
    } finally {
      setRecalculating(false);
    }
  };

  const handleSaveMethod = async () => {
    if (!suggestion && !multiResult) return;
    setSaving(true);
    try {
      const colType = suggestion?.column.column_type || columnChoice || 'C18';
      const additive = suggestion?.additive.additive || '0.1% formic acid';
      await methodsApi.create({
        name: compounds.length > 1
          ? `Multi-compound method (${compounds.length} compounds)`
          : activeCompound?.name || 'Predicted Method',
        column_type: colType,
        ph,
        mobile_phase_a: 'Water',
        mobile_phase_b: 'ACN',
        additive,
        flow_rate_ml_min: flowRate,
        temperature_c: temperature,
        gradient_table: gradientTable,
      });
      setSaved(true);
      toast.success('Method saved to library');
      setTimeout(() => setSaved(false), 3000);
    } catch {
      toast.error('Failed to save method');
    } finally {
      setSaving(false);
    }
  };

  const logp = suggestion?.descriptors.logp ?? activeCompound?.logp ?? 2.0;

  // Auto-fetch suggestion if SMILES is in URL
  useEffect(() => {
    const urlSmiles = searchParams.get('smiles');
    if (urlSmiles) {
      setActiveSmiles(urlSmiles);
      fetchSuggestion(urlSmiles);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="mx-auto max-w-7xl p-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold">LC-MS Method Predictor</h1>
        <p className="text-sm text-muted-foreground">
          Predict chromatographic method parameters from molecular structure
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left: structure input + properties + molecule viewer */}
        <div className="space-y-4">
          <StructureInput
            onCompoundCreated={handleCompoundCreated}
            onSmilesChange={setActiveSmiles}
          />

          {/* 2D Molecule Viewer */}
          {activeSmiles && (
            <div className="card-scientific">
              <h3 className="mb-2 text-sm font-semibold">2D Structure</h3>
              <MoleculeViewer smiles={activeSmiles} width={280} height={200} className="mx-auto" />
            </div>
          )}

          <PropertyPanel
            compound={activeCompound}
            descriptors={suggestion?.descriptors}
            loading={suggesting}
          />
        </div>

        {/* Center: compound list + method suggestion + charts + save */}
        <div className="space-y-4">
          {/* Compound List */}
          <div className="card-scientific">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers size={16} className="text-accent" />
                <h3 className="text-sm font-semibold">Compounds in Method</h3>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">{compounds.length} added</span>
                <button
                  type="button"
                  onClick={handleAddCompound}
                  disabled={!activeSmiles.trim()}
                  className="btn-outline btn-sm"
                  title="Add current compound to the method"
                >
                  <Plus size={14} /> Add
                </button>
              </div>
            </div>

            {compounds.length === 0 ? (
              <p className="mt-3 text-xs text-muted-foreground">
                No compounds added yet. Search or paste a structure above, then click "Add" to build a multi-compound method.
              </p>
            ) : (
              <div className="mt-3 space-y-2">
                {compounds.map((entry, i) => (
                  <div key={entry.id} className="flex items-center gap-2 rounded-md border border-border p-2">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent/10 text-xs font-bold text-accent">
                      {i + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-medium">
                        {entry.name || `Compound ${i + 1}`}
                      </p>
                      <p className="truncate font-mono text-[10px] text-muted-foreground">
                        {entry.smiles.length > 50 ? entry.smiles.slice(0, 47) + '...' : entry.smiles}
                      </p>
                    </div>
                    {/* Show predicted RT if multi-result available */}
                    {multiResult?.per_compound?.find((pc) => pc.index === i)?.predicted_rt_s != null && (
                      <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                        RT: {(multiResult.per_compound[i].predicted_rt_s! / 60).toFixed(2)} min
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={() => handleRemoveCompound(entry.id)}
                      className="shrink-0 rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                      title="Remove compound"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Pick from saved compound library */}
            <div className="mt-3 border-t border-border pt-3">
              <label className="label">Pick from saved library</label>
              <CompoundPicker
                onSelect={handlePickSavedCompound}
                placeholder="Search saved compounds..."
                className="mt-1"
              />
            </div>

            {/* Save / Load compound list */}
            <div className="mt-3 border-t border-border pt-3">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleOpenSaveList}
                  disabled={compounds.length === 0}
                  className="btn-outline btn-sm flex-1"
                  title="Save current compounds as a named list for reuse"
                >
                  <ListPlus size={14} /> Save as List
                </button>
                <button
                  type="button"
                  onClick={() => setShowLoadList(!showLoadList)}
                  className="btn-outline btn-sm flex-1"
                  title="Load a previously saved compound list"
                >
                  <FolderOpen size={14} /> Load List
                </button>
              </div>
            </div>
          </div>

          {/* Save list modal */}
          {showSaveList && (
            <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/70 p-4">
              <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-2xl">
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="text-sm font-semibold">
                    {editingListId ? 'Edit Compound List' : 'Save Compound List'}
                  </h3>
                  <button
                    onClick={() => { setShowSaveList(false); setEditingListId(null); }}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <X size={18} />
                  </button>
                </div>
                <div className="space-y-3">
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
                    {compounds.length} compound(s) will be saved in this list.
                    {compounds.filter((c) => !c.compound?.id).length > 0 && (
                      <span className="mt-1 block text-warning">
                        Note: {compounds.filter((c) => !c.compound?.id).length} compound(s) without a saved library entry will be skipped.
                      </span>
                    )}
                  </div>
                </div>
                <div className="mt-4 flex justify-end gap-2">
                  <button
                    onClick={() => { setShowSaveList(false); setEditingListId(null); }}
                    className="btn-ghost btn-sm"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveList}
                    disabled={!listName.trim() || saveListMutation.isPending}
                    className="btn-primary btn-sm"
                  >
                    {saveListMutation.isPending ? 'Saving...' : editingListId ? 'Update List' : 'Save List'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Load list dropdown */}
          {showLoadList && (
            <div className="card-scientific">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">Saved Compound Lists</h3>
                <button onClick={() => setShowLoadList(false)} className="text-muted-foreground hover:text-foreground">
                  <X size={16} />
                </button>
              </div>
              {savedLists && savedLists.length > 0 ? (
                <div className="mt-3 space-y-2">
                  {savedLists.map((list) => (
                    <div key={list.id} className="flex items-center gap-2 rounded-md border border-border p-2">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-medium">{list.name}</p>
                        <p className="text-[10px] text-muted-foreground">
                          {list.compound_ids.length} compound(s)
                          {list.description ? ` — ${list.description}` : ''}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleLoadList(list)}
                        className="btn-outline btn-sm shrink-0"
                        title="Load this list"
                      >
                        <FolderOpen size={12} /> Load
                      </button>
                      <button
                        type="button"
                        onClick={() => handleOpenEditList(list)}
                        className="btn-ghost btn-sm shrink-0"
                        title="Edit this list"
                      >
                        <Edit3 size={12} />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteList(list)}
                        className="btn-ghost btn-sm shrink-0 text-destructive hover:bg-destructive/10"
                        title="Delete this list"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-3 text-xs text-muted-foreground">
                  No saved compound lists yet. Add compounds and click "Save as List" to create one.
                </p>
              )}
            </div>
          )}

          {/* Column selector + recalculate */}
          <div className="card-scientific">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <div className="flex-1">
                <label className="label">Column Choice</label>
                <select
                  className="input mt-1"
                  value={columnChoice}
                  onChange={(e) => setColumnChoice(e.target.value)}
                >
                  {COLUMN_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                onClick={handleRecalculate}
                disabled={recalculating || compounds.length === 0}
                className="btn-primary btn-sm whitespace-nowrap"
              >
                <RefreshCw size={14} className={recalculating ? 'animate-spin' : ''} />
                {recalculating ? 'Recalculating...' : 'Recalculate Best Choices'}
              </button>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              Select a column or let the heuristic choose automatically. "Recalculate" optimizes the gradient for all compounds in the list.
            </p>
          </div>

          <MethodSuggestionCard suggestion={suggestion} loading={suggesting} />

          {/* Multi-compound resolution results */}
          {multiResult && multiResult.resolution_matrix.length > 0 && (
            <div className="card-scientific">
              <div className="flex items-center gap-2">
                <AlertTriangle size={16} className={multiResult.co_elution_count > 0 ? 'text-warning' : 'text-success'} />
                <h3 className="text-sm font-semibold">Resolution Analysis</h3>
                {multiResult.co_elution_count > 0 && (
                  <span className="badge badge-warning text-[10px]">
                    {multiResult.co_elution_count} co-elution risk(s)
                  </span>
                )}
              </div>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border text-left text-muted-foreground">
                      <th className="py-1.5 pr-3">Pair</th>
                      <th className="py-1.5 pr-3">RT A (min)</th>
                      <th className="py-1.5 pr-3">RT B (min)</th>
                      <th className="py-1.5 pr-3">Resolution (Rs)</th>
                      <th className="py-1.5">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {multiResult.resolution_matrix.map((pair, idx) => {
                      const a = multiResult.per_compound[pair.compound_a];
                      const b = multiResult.per_compound[pair.compound_b];
                      return (
                        <tr key={idx} className="border-b border-border/50">
                          <td className="py-1.5 pr-3 font-medium">
                            {a?.name || `#${pair.compound_a + 1}`} ↔ {b?.name || `#${pair.compound_b + 1}`}
                          </td>
                          <td className="py-1.5 pr-3 tabular-nums">{(pair.rt_a / 60).toFixed(2)}</td>
                          <td className="py-1.5 pr-3 tabular-nums">{(pair.rt_b / 60).toFixed(2)}</td>
                          <td className="py-1.5 pr-3 tabular-nums font-medium">
                            {pair.resolution.toFixed(2)}
                          </td>
                          <td className="py-1.5">
                            {pair.co_elution_risk ? (
                              <span className="badge badge-warning text-[10px]">Co-elution</span>
                            ) : (
                              <span className="badge badge-success text-[10px]">Resolved</span>
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

          <GradientChart
            gradientTable={gradientTable}
            predictedRtS={simResult?.predicted_rt_s}
          />
          <ChromatogramPreview chromatogram={chromatogram} loading={suggesting} />

          {/* pKa Plotter */}
          {activeSmiles && suggestion?.ionizable && <PkaPlotter smiles={activeSmiles} />}

          {/* Save method button */}
          {suggestion && (
            <button
              type="button"
              onClick={handleSaveMethod}
              disabled={saving || saved}
              className={`btn-primary w-full ${saved ? 'bg-success' : ''}`}
            >
              {saved ? (
                <>
                  <Check size={14} className="inline" /> Saved to Method Library
                </>
              ) : saving ? (
                'Saving...'
              ) : (
                <>
                  <Save size={14} className="inline" /> Save Method to Library
                </>
              )}
            </button>
          )}
        </div>

        {/* Right: parameter sliders */}
        <div>
          <ParameterSliders
            gradientTable={gradientTable}
            logp={logp}
            flowRate={flowRate}
            gradientTimeMin={gradientTime}
            ph={ph}
            temperature={temperature}
            onGradientChange={setGradientTable}
            onFlowRateChange={setFlowRate}
            onGradientTimeChange={setGradientTime}
            onPhChange={setPh}
            onTemperatureChange={setTemperature}
            onSimulateResult={setSimResult}
            onChromatogramResult={setChromatogram}
          />
        </div>
      </div>

      <div className="mt-4">
        <DisclaimerTooltip />
      </div>
    </div>
  );
}
