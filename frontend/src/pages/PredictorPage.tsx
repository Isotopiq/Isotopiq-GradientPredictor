import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Save, Check, Plus, Trash2, RefreshCw, Layers, AlertTriangle, ListPlus, FolderOpen, X, Edit3, Pencil, FileText, LayoutTemplate, Zap } from 'lucide-react';
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
  UserTemplateCreate,
} from '@/types';

interface CompoundEntry {
  id: string;
  smiles: string;
  name?: string;
  compound?: Compound;
}

const COLUMN_OPTIONS = [
  { value: '', label: 'Auto (heuristic recommendation)' },
  { value: 'C18', label: 'C18 — Standard reversed-phase (most retentive RP)' },
  { value: 'C8', label: 'C8 — Less retentive RP (faster elution)' },
  { value: 'C4', label: 'C4 — Short-chain RP (large molecules)' },
  { value: 'phenyl', label: 'Phenyl — π-π selectivity (aromatics)' },
  { value: 'PFP', label: 'PFP — Pentafluorophenyl (polarizable/halogenated)' },
  { value: 'HILIC', label: 'HILIC — Hydrophilic (polar analytes)' },
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
  const [showSaveMethod, setShowSaveMethod] = useState(false);
  const [methodName, setMethodName] = useState('');
  const [saveAsTemplate, setSaveAsTemplate] = useState(false);

  // Column override + multi-compound state
  const [columnChoice, setColumnChoice] = useState('');
  const [multiResult, setMultiResult] = useState<MultiCompoundSuggestion | null>(null);
  const [recalculating, setRecalculating] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
  const [autoAdjustGradient, setAutoAdjustGradient] = useState(false);

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

  const handleRenameCompound = (id: string, name: string) => {
    setCompounds((prev) => prev.map((e) => e.id === id ? { ...e, name } : e));
  };

  const handleRecalculate = async () => {
    // Build list of (originalIndex, smiles) so backend indices map back correctly
    const validEntries = compounds
      .map((c, i) => ({ idx: i, smiles: c.smiles }))
      .filter((e) => e.smiles && e.smiles.trim());
    const validSmiles = validEntries.map((e) => e.smiles);
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

  const handleOptimizeGradient = async () => {
    const validEntries = compounds
      .map((c, i) => ({ idx: i, smiles: c.smiles }))
      .filter((e) => e.smiles && e.smiles.trim());
    if (validEntries.length < 2) {
      toast.error('Add at least 2 compounds to optimize separation');
      return;
    }
    setOptimizing(true);
    try {
      const validSmiles = validEntries.map((e) => e.smiles);
      const result = await methodsApi.optimizeGradient(validSmiles, {
        column_type: columnChoice || undefined,
        gradient_time_min: gradientTime,
        flow_rate_ml_min: flowRate,
        ph,
        temperature_c: temperature,
      });
      setMultiResult(result);

      // Apply the optimized gradient parameters
      if (result.gradient?.gradient_table?.length > 0) {
        setGradientTable(result.gradient.gradient_table);
        setFlowRate(result.gradient.flow_rate_ml_min);
        setGradientTime(result.gradient.gradient_time_min);
      }

      // Update slider values to reflect the optimized configuration
      const opt = (result as { optimization?: { percent_b_start: number; percent_b_end: number; gradient_time_min: number; min_resolution: number; configurations_tested: number } }).optimization;
      if (opt) {
        toast.success(
          `Optimized: ${opt.percent_b_start}→${opt.percent_b_end}% B over ${opt.gradient_time_min} min — min Rs=${opt.min_resolution.toFixed(2)} (${opt.configurations_tested} configs tested)`,
        );
      } else if (result.co_elution_count > 0) {
        toast.warning(`${result.co_elution_count} co-elution risk(s) remain — review resolution matrix`);
      } else {
        toast.success('Gradient optimized — no co-elution risks');
      }
    } catch {
      toast.error('Failed to optimize gradient separation');
    } finally {
      setOptimizing(false);
    }
  };

  // Generate a chromatogram showing XIC peaks for all compounds in the method.
  // Re-simulates RTs when gradient/flow/pH/temperature parameters change so
  // that slider adjustments are reflected in real time.
  // Debounced so rapid slider dragging doesn't cancel in-flight API calls.
  useEffect(() => {
    const PEAK_COLORS = [
      '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
      '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
    ];

    // Temperature effect on peak width: higher temp → narrower peaks
    // (van Deemter B-term dominates at higher temp; ~2% per 10°C)
    const tempWidthFactor = Math.max(0.5, 1.0 - (temperature - 30) * 0.02);
    // Temperature effect on retention: higher temp → lower RT
    // (~1.5% per 10°C, typical for RP-LC)
    const tempRtFactor = Math.max(0.7, 1.0 - (temperature - 30) * 0.015);

    // pH effect on effective logD using a practical ionization model.
    // Uses the first (most significant) pKa value. Most LC-MS analytes with
    // a pKa are acidic (carboxylic acids, phenols), so we apply the acid
    // ionization penalty: penalty = log10(1 + 10^(pH - pKa)).
    // For basic pKa (> 7), apply the base penalty: log10(1 + 10^(pKa - pH)).
    // Penalty is capped at 3 to avoid extreme clamping.
    const adjustLogPForPh = (logp: number, pkaValues?: number[]): number => {
      if (!pkaValues || pkaValues.length === 0) return logp;
      const pka = pkaValues[0];
      const isAcidic = pka < 7;
      const delta = isAcidic ? ph - pka : pka - ph;
      if (delta <= 0) return logp; // non-ionizing direction, no penalty
      const penalty = Math.min(3, Math.log10(1 + Math.pow(10, delta)));
      return Math.max(-2, logp - penalty);
    };

    const totalTime = gradientTable.length > 0
      ? gradientTable[gradientTable.length - 1].time_s
      : 1800;

    let cancelled = false;

    const timer = setTimeout(async () => {
      try {
        let peaks: Array<{ rt_s: number; width_s?: number; height: number; label: string; color: string }>;

        if (multiResult && multiResult.per_compound.length > 0) {
          // Multi-compound: re-simulate RT for each compound with current params
          const validEntries = multiResult.per_compound.filter(
            (pc) => pc.predicted_rt_s != null && !pc.error,
          );
          if (validEntries.length === 0) return;

          // Re-simulate each compound's RT using the current gradient + flow + pH
          const simPeaks = await Promise.all(
            validEntries.map(async (pc, i) => {
              const entry = compounds[pc.index];
              const baseLogP = pc.logp ?? entry?.compound?.logp ?? 2.0;
              const effectiveLogP = adjustLogPForPh(baseLogP, pc.pka_values);
              try {
                const sim = await methodsApi.simulateGradient({
                  gradient_table: gradientTable,
                  flow_rate_ml_min: flowRate,
                  logp: effectiveLogP,
                  mw: pc.mw ?? entry?.compound?.mw ?? 200,
                  tpsa: pc.tpsa ?? entry?.compound?.tpsa ?? 0,
                  hbd: pc.hbd ?? 0,
                  hba: pc.hba ?? 0,
                  column_type: columnChoice || pc.column?.column_type || 'C18',
                });
                return {
                  rt_s: sim.predicted_rt_s * tempRtFactor,
                  width_s: (pc.peak_width_s || 10) * tempWidthFactor,
                  height: 1.0,
                  label: entry?.name || `Compound ${pc.index + 1}`,
                  color: PEAK_COLORS[i % PEAK_COLORS.length],
                };
              } catch {
                return {
                  rt_s: pc.predicted_rt_s! * tempRtFactor,
                  width_s: (pc.peak_width_s || 10) * tempWidthFactor,
                  height: 1.0,
                  label: entry?.name || `Compound ${pc.index + 1}`,
                  color: PEAK_COLORS[i % PEAK_COLORS.length],
                };
              }
            }),
          );
          peaks = simPeaks;
        } else {
          // Single-compound: re-simulate with pH-adjusted logP + temperature
          const baseLogP = suggestion?.descriptors.logp ?? activeCompound?.logp ?? 2.0;
          const pkaValues = suggestion?.pka_values ?? activeCompound?.pka_values ?? undefined;
          const effectiveLogP = adjustLogPForPh(baseLogP, pkaValues);
          try {
            const sim = await methodsApi.simulateGradient({
              gradient_table: gradientTable,
              flow_rate_ml_min: flowRate,
              logp: effectiveLogP,
              mw: suggestion?.descriptors.mw ?? activeCompound?.mw ?? 200,
              tpsa: suggestion?.descriptors.tpsa ?? activeCompound?.tpsa ?? 0,
              hbd: suggestion?.descriptors.hbd ?? 0,
              hba: suggestion?.descriptors.hba ?? 0,
              column_type: columnChoice || suggestion?.column.column_type || 'C18',
            });
            peaks = [{
              rt_s: sim.predicted_rt_s * tempRtFactor,
              width_s: undefined,
              height: 1.0,
              label: activeCompound?.name || 'Predicted',
              color: PEAK_COLORS[0],
            }];
          } catch {
            return;
          }
        }

        // Auto-adjust gradient time: if any peak RT exceeds the gradient end,
        // extend the gradient table to fit all peaks with a 10% margin.
        let effectiveTotalTime = totalTime;
        if (autoAdjustGradient && peaks.length > 0) {
          const maxRt = Math.max(...peaks.map((p) => p.rt_s));
          const gradientEnd = totalTime;
          if (maxRt > gradientEnd * 0.9) {
            // Extend gradient time to 110% of the latest peak RT
            const newTotalTime = Math.ceil((maxRt * 1.1) / 60) * 60; // round up to next minute
            effectiveTotalTime = newTotalTime;
            // Rebuild gradient table with extended time
            if (gradientTable.length >= 2) {
              const bStart = gradientTable[0].percent_b;
              const bEnd = gradientTable[gradientTable.length - 1].percent_b;
              const newTable = [
                { time_s: 0, percent_b: bStart },
                { time_s: 60, percent_b: bStart },
                { time_s: newTotalTime - 120, percent_b: bEnd },
                { time_s: newTotalTime, percent_b: bEnd },
              ];
              if (!cancelled) {
                setGradientTable(newTable);
                setGradientTime(newTotalTime / 60);
              }
            }
          }
        }

        const chromResult = await methodsApi.simulateChromatogram({
          peaks,
          total_time_s: effectiveTotalTime,
        });
        if (!cancelled) setChromatogram(chromResult);
      } catch {
        // silent
      }
    }, 500); // 500ms debounce — wait for slider to stop before API calls

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [multiResult, gradientTable, simResult, flowRate, ph, temperature, columnChoice, autoAdjustGradient]);

  const handleSaveMethod = async () => {
    if (gradientTable.length === 0 && !suggestion && !multiResult) {
      toast.error('Generate a method prediction first');
      return;
    }
    setSaving(true);
    try {
      const colType = suggestion?.column.column_type
        || multiResult?.per_compound?.find((pc) => !pc.error)?.column?.column_type
        || columnChoice || 'C18';
      const additive = suggestion?.additive.additive || '0.1% Formic Acid';
      const mobilePhaseA = suggestion?.gradient
        ? `Water + ${additive}`
        : 'Water + 0.1% Formic Acid';
      const mobilePhaseB = 'Acetonitrile';
      const name = methodName.trim() || (compounds.length > 1
        ? `Multi-compound method (${compounds.length} compounds)`
        : activeCompound?.name || 'Predicted Method');

      // Save as method
      const compoundSmiles = compounds
        .map((c) => c.smiles)
        .filter((s) => s && s.trim());
      await methodsApi.create({
        name,
        column_type: colType,
        ph,
        mobile_phase_a: mobilePhaseA,
        mobile_phase_b: mobilePhaseB,
        additive,
        flow_rate_ml_min: flowRate,
        temperature_c: temperature,
        gradient_table: gradientTable,
        compounds_smiles: compoundSmiles.length > 0 ? compoundSmiles : undefined,
      });

      // Optionally save as template too
      if (saveAsTemplate) {
        const bStart = gradientTable[0]?.percent_b ?? 5;
        const bEnd = gradientTable[gradientTable.length - 1]?.percent_b ?? 95;
        const gradTime = gradientTable.length >= 2
          ? (gradientTable[gradientTable.length - 1].time_s - gradientTable[0].time_s) / 60
          : gradientTime;
        const tmpl: UserTemplateCreate = {
          name: `${name} (template)`,
          category: 'Custom',
          description: `Saved from predictor — ${compounds.length} compound(s), ${colType} column`,
          column_type: colType,
          mobile_phase_a: mobilePhaseA,
          mobile_phase_b: mobilePhaseB,
          additive,
          ph,
          percent_b_start: bStart,
          percent_b_end: bEnd,
          gradient_time_min: gradTime,
          flow_rate_ml_min: flowRate,
          temperature_c: temperature,
        };
        try {
          await methodsApi.createUserTemplate(tmpl);
          toast.success('Method and template saved');
        } catch {
          toast.success('Method saved to library (template save failed)');
        }
      } else {
        toast.success('Method saved to library');
      }

      setSaved(true);
      setShowSaveMethod(false);
      setMethodName('');
      setSaveAsTemplate(false);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      toast.error('Failed to save method');
    } finally {
      setSaving(false);
    }
  };

  const handleOpenSaveMethod = () => {
    // Pre-fill a sensible name
    setMethodName(
      compounds.length > 1
        ? `Multi-compound method (${compounds.length} compounds)`
        : activeCompound?.name || 'Predicted Method',
    );
    setSaveAsTemplate(false);
    setShowSaveMethod(true);
  };

  const logp = suggestion?.descriptors.logp ?? activeCompound?.logp ?? 2.0;

  // Auto-fetch suggestion if SMILES is in URL, or load a compound list from sessionStorage
  useEffect(() => {
    // Check for a compound list ID stored by the Compounds page "Use in Predictor" action
    const storedListId = sessionStorage.getItem('predictor_load_list_id');
    if (storedListId) {
      sessionStorage.removeItem('predictor_load_list_id');
      (async () => {
        try {
          const list = await compoundListsApi.get(storedListId);
          loadListCompounds(list);
        } catch {
          // Fall back to URL smiles
          const urlSmiles = searchParams.get('smiles');
          if (urlSmiles) {
            setActiveSmiles(urlSmiles);
            fetchSuggestion(urlSmiles);
          }
        }
      })();
      return;
    }
    const urlSmiles = searchParams.get('smiles');
    if (urlSmiles) {
      setActiveSmiles(urlSmiles);
      fetchSuggestion(urlSmiles);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="mx-auto max-w-[1600px] p-4 lg:p-6">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">LC-MS Method Predictor</h1>
          <p className="text-sm text-muted-foreground">
            Predict chromatographic method parameters from molecular structure
          </p>
        </div>
        {(gradientTable.length > 0 || suggestion || multiResult) && (
          <button
            type="button"
            onClick={handleOpenSaveMethod}
            disabled={saving || saved}
            className={`btn-primary btn-sm ${saved ? 'bg-success' : ''}`}
          >
            {saved ? (
              <><Check size={14} /> Saved</>
            ) : saving ? (
              'Saving...'
            ) : (
              <><Save size={14} /> Save Method</>
            )}
          </button>
        )}
      </div>

      {/* Main layout: left input sidebar + right workflow area */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        {/* ===== LEFT SIDEBAR: Structure Input ===== */}
        <div className="xl:col-span-3 space-y-3">
          <StructureInput
            onCompoundCreated={handleCompoundCreated}
            onSmilesChange={setActiveSmiles}
          />

          {activeSmiles && (
            <div className="card-scientific">
              <h3 className="mb-2 text-sm font-semibold">2D Structure</h3>
              <MoleculeViewer smiles={activeSmiles} width={300} height={220} autoFit className="mx-auto w-full" />
            </div>
          )}

          <PropertyPanel
            compound={activeCompound}
            descriptors={suggestion?.descriptors}
            loading={suggesting}
          />
        </div>

        {/* ===== MAIN WORKFLOW AREA ===== */}
        <div className="xl:col-span-9 space-y-4">
          {/* --- Step 1: Compounds --- */}
          <div className="card-scientific">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent/10 text-xs font-bold text-accent">1</span>
                <h3 className="text-sm font-semibold">Compounds in Method</h3>
                {compounds.length > 0 && (
                  <span className="badge badge-info text-[10px]">{compounds.length} compound{compounds.length !== 1 ? 's' : ''}</span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleAddCompound}
                  disabled={!activeSmiles.trim()}
                  className="btn-outline btn-sm"
                  title="Add current compound to the method"
                >
                  <Plus size={14} /> Add Current
                </button>
              </div>
            </div>

            {compounds.length === 0 ? (
              <div className="mt-3 rounded-md border border-dashed border-border p-6 text-center">
                <Layers size={24} className="mx-auto mb-2 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">
                  No compounds added yet. Use the structure input on the left to search or draw a molecule,
                  then click "Add Current" to build your method.
                </p>
              </div>
            ) : (
              <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                {compounds.map((entry, i) => {
                  const pcEntry = multiResult?.per_compound?.find((pc) => pc.index === i);
                  const predictedRtMin = pcEntry?.predicted_rt_s != null
                    ? pcEntry.predicted_rt_s / 60
                    : null;
                  return (
                  <CompoundListEntry
                    key={entry.id}
                    entry={entry}
                    index={i}
                    predictedRtMin={predictedRtMin}
                    onRemove={() => handleRemoveCompound(entry.id)}
                    onRename={(name) => handleRenameCompound(entry.id, name)}
                  />
                  );
                })}
              </div>
            )}

            {/* Pick from library + Save/Load controls */}
            <div className="mt-3 grid grid-cols-1 gap-3 border-t border-border pt-3 sm:grid-cols-2">
              <div>
                <label className="label">Pick from saved library</label>
                <CompoundPicker
                  onSelect={handlePickSavedCompound}
                  placeholder="Search saved compounds..."
                  className="mt-1"
                />
              </div>
              <div className="flex items-end gap-2">
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
                      >
                        <FolderOpen size={12} /> Load
                      </button>
                      <button
                        type="button"
                        onClick={() => handleOpenEditList(list)}
                        className="btn-ghost btn-sm shrink-0"
                      >
                        <Edit3 size={12} />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteList(list)}
                        className="btn-ghost btn-sm shrink-0 text-destructive hover:bg-destructive/10"
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

          {/* --- Step 2: Method Configuration --- */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {/* Column + Recalculate */}
            <div className="card-scientific">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent/10 text-xs font-bold text-accent">2</span>
                <h3 className="text-sm font-semibold">Column & Optimization</h3>
              </div>
              <div className="mt-3 space-y-3">
                <div>
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
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleRecalculate}
                    disabled={recalculating || optimizing || compounds.length === 0}
                    className="btn-primary flex-1"
                  >
                    <RefreshCw size={14} className={recalculating ? 'animate-spin' : ''} />
                    {recalculating ? 'Recalculating...' : 'Recalculate'}
                  </button>
                  <button
                    type="button"
                    onClick={handleOptimizeGradient}
                    disabled={optimizing || recalculating || compounds.length < 2}
                    className="btn-outline"
                    title="Grid-search for the gradient parameters that maximize minimum resolution between all compounds"
                  >
                    <Zap size={14} className={optimizing ? 'animate-pulse' : ''} />
                    {optimizing ? 'Optimizing...' : 'Optimize Separation'}
                  </button>
                </div>
                <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoAdjustGradient}
                    onChange={(e) => setAutoAdjustGradient(e.target.checked)}
                    className="rounded border-border"
                  />
                  Auto-adjust gradient time to fit all peaks
                </label>
                <p className="text-xs text-muted-foreground">
                  "Recalculate" suggests a method for all compounds. "Optimize Separation" grid-searches %B start/end and gradient time to maximize resolution.
                </p>
              </div>
            </div>

            {/* Method Suggestion */}
            <MethodSuggestionCard suggestion={suggestion} loading={suggesting} />
          </div>

          {/* Parameter Sliders — full width row */}
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
          />

          {/* --- Step 3: Results --- */}
          {/* Resolution Analysis */}
          {multiResult && multiResult.resolution_matrix.length > 0 && (
            <div className="card-scientific">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent/10 text-xs font-bold text-accent">3</span>
                <h3 className="text-sm font-semibold">Resolution Analysis</h3>
                {multiResult.co_elution_count > 0 ? (
                  <span className="badge badge-warning text-[10px]">
                    {multiResult.co_elution_count} co-elution risk(s)
                  </span>
                ) : (
                  <span className="badge badge-success text-[10px]">All resolved</span>
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

          {/* Charts: Gradient + Chromatogram side by side */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <GradientChart
              gradientTable={gradientTable}
              predictedRtS={simResult?.predicted_rt_s}
              rtMarkers={chromatogram?.peaks?.map((p) => ({
                rt_s: p.rt_s,
                label: p.label,
                color: p.color || undefined,
              }))}
            />
            <ChromatogramPreview chromatogram={chromatogram} loading={suggesting} />
          </div>

          {/* pKa plot full width */}
          {activeSmiles && suggestion?.ionizable && (
            <PkaPlotter smiles={activeSmiles} />
          )}

          {/* Disclaimer */}
          <div className="pt-2">
            <DisclaimerTooltip />
          </div>
        </div>
      </div>

      {/* Save method dialog */}
      {showSaveMethod && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-lg rounded-xl border border-border bg-card p-6 shadow-2xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-semibold">Save LC-MS Method</h3>
              <button
                onClick={() => setShowSaveMethod(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X size={18} />
              </button>
            </div>

            {/* Method summary */}
            <div className="mb-4 rounded-md border border-border bg-muted/30 p-3 text-xs">
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                <div><span className="text-muted-foreground">Column:</span> {suggestion?.column.column_type || columnChoice || 'C18'}</div>
                <div><span className="text-muted-foreground">pH:</span> {ph.toFixed(1)}</div>
                <div><span className="text-muted-foreground">Flow:</span> {flowRate} mL/min</div>
                <div><span className="text-muted-foreground">Temp:</span> {temperature}°C</div>
                <div><span className="text-muted-foreground">Gradient:</span> {gradientTable[0]?.percent_b ?? '—'}→{gradientTable[gradientTable.length - 1]?.percent_b ?? '—'}% B</div>
                <div><span className="text-muted-foreground">Time:</span> {gradientTable.length >= 2 ? ((gradientTable[gradientTable.length - 1].time_s - gradientTable[0].time_s) / 60).toFixed(1) : gradientTime} min</div>
                <div><span className="text-muted-foreground">Compounds:</span> {compounds.length}</div>
                <div><span className="text-muted-foreground">Additive:</span> {suggestion?.additive.additive || '0.1% Formic Acid'}</div>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <label className="label">Method Name</label>
                <input
                  className="input mt-1"
                  placeholder="e.g. Caffeine metabolites RP method"
                  value={methodName}
                  onChange={(e) => setMethodName(e.target.value)}
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && methodName.trim()) handleSaveMethod();
                  }}
                />
              </div>
              <label className="flex items-center gap-2 rounded-md border border-border p-2.5 text-xs cursor-pointer hover:bg-muted/30">
                <input
                  type="checkbox"
                  checked={saveAsTemplate}
                  onChange={(e) => setSaveAsTemplate(e.target.checked)}
                  className="accent-accent"
                />
                <LayoutTemplate size={14} className="text-accent" />
                <span>Also save as reusable method template</span>
              </label>
            </div>

            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setShowSaveMethod(false)}
                className="btn-ghost btn-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveMethod}
                disabled={!methodName.trim() && compounds.length === 0 || saving}
                className="btn-primary btn-sm"
              >
                {saving ? 'Saving...' : (
                  <><Save size={12} /> Save Method{saveAsTemplate ? ' & Template' : ''}</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

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
    </div>
  );
}

function CompoundListEntry({
  entry,
  index,
  predictedRtMin,
  onRemove,
  onRename,
}: {
  entry: CompoundEntry;
  index: number;
  predictedRtMin: number | null;
  onRemove: () => void;
  onRename: (name: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState(entry.name || '');

  const handleSaveName = () => {
    onRename(editName.trim());
    setEditing(false);
  };

  const handleStartEdit = () => {
    setEditName(entry.name || '');
    setEditing(true);
  };

  return (
    <div className="group flex items-start gap-2 rounded-md border border-border p-2.5 transition-colors hover:border-accent/30">
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent/10 text-xs font-bold text-accent">
        {index + 1}
      </span>
      <div className="min-w-0 flex-1">
        {editing ? (
          <div className="flex items-center gap-1">
            <input
              className="input h-6 flex-1 text-xs"
              placeholder={`Compound ${index + 1}`}
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveName();
                if (e.key === 'Escape') setEditing(false);
              }}
              autoFocus
            />
            <button
              type="button"
              onClick={handleSaveName}
              className="rounded p-0.5 text-success hover:bg-success/10"
              title="Save name"
            >
              <Check size={12} />
            </button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="rounded p-0.5 text-muted-foreground hover:bg-muted"
              title="Cancel"
            >
              <X size={12} />
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-1">
              <p className="truncate text-xs font-medium">
                {entry.name || `Compound ${index + 1}`}
              </p>
              <button
                type="button"
                onClick={handleStartEdit}
                className="shrink-0 rounded p-0.5 text-muted-foreground opacity-0 transition-opacity hover:bg-muted group-hover:opacity-100"
                title="Edit name"
              >
                <Pencil size={10} />
              </button>
            </div>
            <p className="truncate font-mono text-[10px] text-muted-foreground">
              {entry.smiles.length > 50 ? entry.smiles.slice(0, 47) + '...' : entry.smiles}
            </p>
            {predictedRtMin != null && (
              <span className="mt-0.5 inline-block rounded bg-accent/5 px-1.5 py-0.5 text-[10px] font-medium tabular-nums text-accent">
                Predicted RT: {predictedRtMin.toFixed(2)} min
              </span>
            )}
          </>
        )}
      </div>
      <button
        type="button"
        onClick={onRemove}
        className="shrink-0 rounded p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
        title="Remove compound"
      >
        <Trash2 size={14} />
      </button>
    </div>
  );
}
