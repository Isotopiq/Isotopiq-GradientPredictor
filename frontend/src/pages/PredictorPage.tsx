import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Save, Check } from 'lucide-react';
import { StructureInput } from '@/components/StructureInput';
import { PropertyPanel } from '@/components/PropertyPanel';
import { MethodSuggestionCard } from '@/components/MethodSuggestionCard';
import { GradientChart } from '@/components/GradientChart';
import { ChromatogramPreview } from '@/components/ChromatogramPreview';
import { ParameterSliders } from '@/components/ParameterSliders';
import { MoleculeViewer } from '@/components/MoleculeViewer';
import { PkaPlotter } from '@/components/PkaPlotter';
import { DisclaimerTooltip } from '@/components/DisclaimerTooltip';
import { methodsApi } from '@/api/methods';
import { toast } from 'sonner';
import type {
  Compound,
  MethodSuggestion,
  MethodSuggestionRequest,
  GradientPoint,
  GradientSimulateResult,
  ChromatogramResult,
} from '@/types';

export function PredictorPage() {
  const [searchParams] = useSearchParams();
  const [compound, setCompound] = useState<Compound | null>(null);
  const [smiles, setSmiles] = useState(searchParams.get('smiles') || '');
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

  const handleCompoundCreated = async (c: Compound) => {
    setCompound(c);
    setSaved(false);
    if (c.smiles) {
      setSmiles(c.smiles);
      await fetchSuggestion(c.smiles);
    }
  };

  const fetchSuggestion = async (smi: string) => {
    setSuggesting(true);
    try {
      const req: MethodSuggestionRequest = { smiles: smi };
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

  const handleSaveMethod = async () => {
    if (!suggestion) return;
    setSaving(true);
    try {
      await methodsApi.create({
        name: compound?.name || 'Predicted Method',
        column_type: suggestion.column.column_type,
        ph,
        mobile_phase_a: 'Water',
        mobile_phase_b: 'ACN',
        additive: suggestion.additive.additive,
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

  const logp = suggestion?.descriptors.logp ?? compound?.logp ?? 2.0;

  // Auto-fetch suggestion if SMILES is in URL
  useEffect(() => {
    const urlSmiles = searchParams.get('smiles');
    if (urlSmiles) {
      setSmiles(urlSmiles);
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
            onSmilesChange={setSmiles}
          />

          {/* 2D Molecule Viewer */}
          {smiles && (
            <div className="card-scientific">
              <h3 className="mb-2 text-sm font-semibold">2D Structure</h3>
              <MoleculeViewer smiles={smiles} width={280} height={200} className="mx-auto" />
            </div>
          )}

          <PropertyPanel
            compound={compound}
            descriptors={suggestion?.descriptors}
            loading={suggesting}
          />
        </div>

        {/* Center: method suggestion + charts + save */}
        <div className="space-y-4">
          <MethodSuggestionCard suggestion={suggestion} loading={suggesting} />
          <GradientChart
            gradientTable={gradientTable}
            predictedRtS={simResult?.predicted_rt_s}
          />
          <ChromatogramPreview chromatogram={chromatogram} loading={suggesting} />

          {/* pKa Plotter */}
          {smiles && suggestion?.ionizable && <PkaPlotter smiles={smiles} />}

          {/* Save method button */}
          {suggestion && (
            <button
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
