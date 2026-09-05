import { useState, useEffect, useMemo } from 'react';
import { Atom, Info, AlertTriangle, CheckCircle2, Zap } from 'lucide-react';
import { methodsApi } from '@/api/methods';
import type {
  RetentionModelsRegistry,
  AutoSelectResult,
} from '@/types';

interface Props {
  columnType: string;
  columnId: string | null;
  hasCalibration: boolean;
  percentBRange: number;
  selectedMechanism: string | null;
  selectedModel: string | null;
  onMechanismChange: (mechanism: string | null) => void;
  onModelChange: (model: string | null) => void;
}

export function RetentionModelSelector({
  columnType,
  columnId,
  hasCalibration,
  percentBRange,
  selectedMechanism,
  selectedModel,
  onMechanismChange,
  onModelChange,
}: Props) {
  const [registry, setRegistry] = useState<RetentionModelsRegistry | null>(null);
  const [autoResult, setAutoResult] = useState<AutoSelectResult | null>(null);
  const [loading, setLoading] = useState(false);

  // Load registry once
  useEffect(() => {
    methodsApi.getRetentionModels().then(setRegistry).catch(() => {});
  }, []);

  // Auto-select when inputs change (if user hasn't manually overridden)
  const isAutoMechanism = selectedMechanism === null || selectedMechanism === 'auto';
  const isAutoModel = selectedModel === null || selectedModel === 'auto';

  useEffect(() => {
    if (isAutoMechanism || isAutoModel) {
      setLoading(true);
      methodsApi
        .autoSelectRetentionModel({
          column_type: columnType,
          column_id: columnId || undefined,
          has_calibration: hasCalibration,
          percent_b_range: percentBRange,
          mechanism: isAutoMechanism ? undefined : selectedMechanism || undefined,
        })
        .then((result) => {
          setAutoResult(result);
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [columnType, columnId, hasCalibration, percentBRange, selectedMechanism, isAutoMechanism, isAutoModel]);

  const effectiveMechanism = isAutoMechanism ? autoResult?.mechanism : selectedMechanism;
  const effectiveModel = isAutoModel ? autoResult?.selected_model : selectedModel;

  const applicableModels = useMemo(() => {
    if (!registry || !effectiveMechanism) return [];
    return Object.values(registry.models).filter((m) =>
      m.applicable_mechanisms.includes(effectiveMechanism),
    );
  }, [registry, effectiveMechanism]);

  const currentModelInfo = registry?.models[effectiveModel || ''];
  const currentMechanismInfo = registry?.mechanisms[effectiveMechanism || ''];

  return (
    <div className="card-scientific">
      <div className="flex items-center gap-2">
        <Atom className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold">Retention Mechanism & Model</h3>
        {loading && <span className="text-[10px] text-muted-foreground">computing...</span>}
      </div>

      {/* Mechanism selector */}
      <div className="mt-3">
        <label className="label">Retention Mechanism</label>
        <select
          value={selectedMechanism || 'auto'}
          onChange={(e) => {
            const v = e.target.value;
            onMechanismChange(v === 'auto' ? null : v);
            // Reset model to auto when mechanism changes
            onModelChange(null);
          }}
          className="input mt-1 text-xs"
        >
          <option value="auto">Auto (auto-select based on parameters)</option>
          {registry &&
            Object.values(registry.mechanisms).map((m) => (
              <option key={m.key} value={m.key}>
                {m.label}
              </option>
            ))}
        </select>
        {currentMechanismInfo && (
          <p className="mt-1 text-[10px] text-muted-foreground">{currentMechanismInfo.description}</p>
        )}
      </div>

      {/* Model selector */}
      <div className="mt-3">
        <label className="label">Retention Model</label>
        <select
          value={selectedModel || 'auto'}
          onChange={(e) => {
            const v = e.target.value;
            onModelChange(v === 'auto' ? null : v);
          }}
          className="input mt-1 text-xs"
        >
          <option value="auto">Auto (auto-select based on data availability)</option>
          {applicableModels.map((m) => (
            <option key={m.key} value={m.key}>
              {m.label}
            </option>
          ))}
        </select>
        {currentModelInfo && (
          <div className="mt-1 space-y-1">
            <p className="font-mono text-[10px] text-foreground">{currentModelInfo.equation}</p>
            <p className="text-[10px] text-muted-foreground">
              <Info size={10} className="inline" /> Requires: {currentModelInfo.requires}
            </p>
            {currentModelInfo.reference && (
              <p className="text-[10px] text-muted-foreground">
                Ref: {currentModelInfo.reference}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Auto-selection rationale */}
      {autoResult && (isAutoMechanism || isAutoModel) && (
        <div className="mt-3 rounded-md bg-accent/10 p-2 text-xs">
          <div className="flex items-center gap-1 font-semibold text-accent">
            <Zap size={12} />
            Auto-Selected
          </div>
          <div className="mt-1 space-y-0.5">
            <div>
              <strong>Mechanism:</strong> {autoResult.mechanism_info.label}
            </div>
            <div>
              <strong>Model:</strong> {autoResult.selected_model_info.label}
            </div>
            <div className="text-[10px] text-muted-foreground">
              {autoResult.selected_model_info.equation}
            </div>
          </div>
        </div>
      )}

      {/* Applicability warnings */}
      {effectiveModel && effectiveMechanism && registry && (
        <>
          {!registry.models[effectiveModel]?.applicable_mechanisms.includes(effectiveMechanism) && (
            <div className="mt-2 flex items-center gap-1 rounded-md bg-yellow-500/10 p-2 text-xs text-yellow-700">
              <AlertTriangle size={12} />
              This model is not typically applicable to the selected mechanism.
            </div>
          )}
          {effectiveModel === 'pirm' && !columnId && (
            <div className="mt-2 flex items-center gap-1 rounded-md bg-yellow-500/10 p-2 text-xs text-yellow-700">
              <AlertTriangle size={12} />
              PIRM requires a commercial column selection. Falling back to heuristic.
            </div>
          )}
          {effectiveModel === 'lss_fit' && !hasCalibration && (
            <div className="mt-2 flex items-center gap-1 rounded-md bg-yellow-500/10 p-2 text-xs text-yellow-700">
              <AlertTriangle size={12} />
              LSS Fit requires ≥2 calibration runs. Falling back to heuristic LSS.
            </div>
          )}
          {effectiveModel === 'ml_trained' && (
            <div className="mt-2 flex items-center gap-1 rounded-md bg-yellow-500/10 p-2 text-xs text-yellow-700">
              <AlertTriangle size={12} />
              No trained ML model found for this column type. Falling back to heuristic.
            </div>
          )}
          {effectiveMechanism === 'size_exclusion' && (
            <div className="mt-2 flex items-center gap-1 rounded-md bg-blue-500/10 p-2 text-xs text-blue-700">
              <Info size={12} />
              SEC separates by molecular size, not retention factor. No k model applies.
            </div>
          )}
          {effectiveMechanism === 'ion_exchange' && (
            <div className="mt-2 flex items-center gap-1 rounded-md bg-blue-500/10 p-2 text-xs text-blue-700">
              <Info size={12} />
              IEX retention depends on ionic strength, not organic modifier %.
            </div>
          )}
        </>
      )}

      {/* Status indicator */}
      {effectiveModel && (
        <div className="mt-2 flex items-center gap-1 text-[10px] text-muted-foreground">
          <CheckCircle2 size={10} className="text-green-500" />
          Active: {effectiveMechanism} / {effectiveModel}
        </div>
      )}
    </div>
  );
}
