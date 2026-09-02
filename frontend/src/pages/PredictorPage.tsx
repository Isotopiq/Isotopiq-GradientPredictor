import { useState } from 'react';
import { StructureInput } from '@/components/StructureInput';
import { PropertyPanel } from '@/components/PropertyPanel';
import { MethodSuggestionCard } from '@/components/MethodSuggestionCard';
import { GradientChart } from '@/components/GradientChart';
import { ChromatogramPreview } from '@/components/ChromatogramPreview';
import { ParameterSliders } from '@/components/ParameterSliders';
import { DisclaimerTooltip } from '@/components/DisclaimerTooltip';
import { methodsApi } from '@/api/methods';
import type {
  Compound,
  MethodSuggestion,
  MethodSuggestionRequest,
  GradientPoint,
  GradientSimulateResult,
  ChromatogramResult,
} from '@/types';

export function PredictorPage() {
  const [compound, setCompound] = useState<Compound | null>(null);
  const [smiles, setSmiles] = useState('');
  const [suggestion, setSuggestion] = useState<MethodSuggestion | null>(null);
  const [suggesting, setSuggesting] = useState(false);
  const [gradientTable, setGradientTable] = useState<GradientPoint[]>([]);
  const [simResult, setSimResult] = useState<GradientSimulateResult | null>(null);
  const [chromatogram, setChromatogram] = useState<ChromatogramResult | null>(null);
  const [flowRate, setFlowRate] = useState(0.4);
  const [gradientTime, setGradientTime] = useState(20);
  const [ph, setPh] = useState(2.7);
  const [temperature, setTemperature] = useState(30);

  const handleCompoundCreated = async (c: Compound) => {
    setCompound(c);
    if (c.smiles) {
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
      // ignore
    } finally {
      setSuggesting(false);
    }
  };

  const logp = suggestion?.descriptors.logp ?? compound?.logp ?? 2.0;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Left: structure input + properties */}
        <div className="space-y-4">
          <StructureInput
            onCompoundCreated={handleCompoundCreated}
            onSmilesChange={setSmiles}
          />
          <PropertyPanel
            compound={compound}
            descriptors={suggestion?.descriptors}
            loading={suggesting}
          />
        </div>

        {/* Center: method suggestion + charts */}
        <div className="space-y-4">
          <MethodSuggestionCard suggestion={suggestion} loading={suggesting} />
          <GradientChart
            gradientTable={gradientTable}
            predictedRtS={simResult?.predicted_rt_s}
          />
          <ChromatogramPreview chromatogram={chromatogram} loading={suggesting} />
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
    </main>
  );
}
