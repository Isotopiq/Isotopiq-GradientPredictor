import { useCallback, useEffect, useState } from 'react';
import { methodsApi } from '@/api/methods';
import type { GradientPoint, GradientSimulateResult } from '@/types';

interface ParameterSlidersProps {
  gradientTable: GradientPoint[];
  logp: number;
  flowRate: number;
  gradientTimeMin: number;
  ph: number;
  temperature: number;
  onGradientChange: (table: GradientPoint[]) => void;
  onFlowRateChange: (v: number) => void;
  onGradientTimeChange: (v: number) => void;
  onPhChange: (v: number) => void;
  onTemperatureChange: (v: number) => void;
  onSimulateResult: (result: GradientSimulateResult) => void;
}

// Default re-equilibration time after the wash step returns to initial conditions
const WASH_RETURN_TIME_S = 30;   // 0.5 min to drop from %B end to %B start
const REEQUILIBRATION_TIME_S = 120; // 2 min hold at initial conditions

export function ParameterSliders({
  gradientTable,
  logp,
  flowRate,
  gradientTimeMin,
  ph,
  temperature,
  onGradientChange,
  onFlowRateChange,
  onGradientTimeChange,
  onPhChange,
  onTemperatureChange,
  onSimulateResult,
}: ParameterSlidersProps) {
  const [bStart, setBStart] = useState(5);
  const [bEnd, setBEnd] = useState(95);
  const [washStep, setWashStep] = useState(false);

  // Rebuild gradient table when key params change
  const rebuildGradient = useCallback(
    (newBStart: number, newBEnd: number, newTimeMin: number, withWash: boolean) => {
      const tTotal = newTimeMin * 60;
      const table: GradientPoint[] = [
        { time_s: 0, percent_b: newBStart },
        { time_s: 60, percent_b: newBStart },
        { time_s: tTotal - 120, percent_b: newBEnd },
        { time_s: tTotal, percent_b: newBEnd },
      ];
      if (withWash) {
        // Wash step: return to initial %B, then re-equilibrate
        table.push({ time_s: tTotal + WASH_RETURN_TIME_S, percent_b: newBStart });
        table.push({ time_s: tTotal + WASH_RETURN_TIME_S + REEQUILIBRATION_TIME_S, percent_b: newBStart });
      }
      onGradientChange(table);
    },
    [onGradientChange],
  );

  // Sync bStart/bEnd/washStep when gradient table is set externally (e.g. from suggestion)
  useEffect(() => {
    if (gradientTable.length < 2) return;
    const first = gradientTable[0];
    const last = gradientTable[gradientTable.length - 1];
    // Detect wash step: if the last point's %B matches the first point's %B
    // and there are more than 4 points, it's a wash step
    const hasWash = gradientTable.length > 4 && Math.abs(last.percent_b - first.percent_b) < 0.1;
    setBStart(first.percent_b);
    // %B end is the highest point (or the point before the wash return)
    const endIdx = hasWash ? gradientTable.length - 3 : gradientTable.length - 1;
    setBEnd(gradientTable[endIdx].percent_b);
    setWashStep(hasWash);
  }, [gradientTable]);

  // Debounced simulation — gradient RT prediction only.
  // Chromatogram generation is handled by the parent page so it can show
  // per-compound XIC traces for all compounds in the method.
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (gradientTable.length < 2) return;
      try {
        const simResult = await methodsApi.simulateGradient({
          gradient_table: gradientTable,
          flow_rate_ml_min: flowRate,
          logp,
        });
        onSimulateResult(simResult);
      } catch {
        // Silent fail for live updates
      }
    }, 400);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gradientTable, flowRate, logp]);

  const handleBStart = (v: number) => {
    setBStart(v);
    rebuildGradient(v, bEnd, gradientTimeMin, washStep);
  };

  const handleBEnd = (v: number) => {
    setBEnd(v);
    rebuildGradient(bStart, v, gradientTimeMin, washStep);
  };

  const handleGradientTime = (v: number) => {
    onGradientTimeChange(v);
    rebuildGradient(bStart, bEnd, v, washStep);
  };

  const handleWashToggle = (enabled: boolean) => {
    setWashStep(enabled);
    rebuildGradient(bStart, bEnd, gradientTimeMin, enabled);
  };

  return (
    <div className="card space-y-4">
      <h3 className="text-sm font-semibold">Method Parameters</h3>

      <SliderRow
        label="%B Start"
        value={bStart}
        min={0}
        max={50}
        step={1}
        unit="%"
        onChange={handleBStart}
      />
      <SliderRow
        label="%B End"
        value={bEnd}
        min={50}
        max={100}
        step={1}
        unit="%"
        onChange={handleBEnd}
      />
      <SliderRow
        label="Gradient Time"
        value={gradientTimeMin}
        min={5}
        max={60}
        step={1}
        unit="min"
        onChange={handleGradientTime}
      />
      <SliderRow
        label="Flow Rate"
        value={flowRate}
        min={0.1}
        max={2.0}
        step={0.05}
        unit="mL/min"
        onChange={onFlowRateChange}
      />
      <SliderRow
        label="pH"
        value={ph}
        min={2}
        max={11}
        step={0.1}
        onChange={onPhChange}
      />
      <SliderRow
        label="Temperature"
        value={temperature}
        min={20}
        max={80}
        step={1}
        unit="°C"
        onChange={onTemperatureChange}
      />

      {/* Wash / re-equilibration step toggle */}
      <div className="border-t border-border pt-3">
        <label className="flex items-center justify-between cursor-pointer">
          <div>
            <span className="text-xs font-medium">Wash & Re-equilibrate</span>
            <p className="text-[10px] text-muted-foreground">
              {washStep
                ? `Returns to ${bStart}% B after gradient, holds ${(REEQUILIBRATION_TIME_S / 60).toFixed(1)} min`
                : 'Drop back to initial %B and re-equilibrate column'}
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={washStep}
            onClick={() => handleWashToggle(!washStep)}
            className={`relative h-5 w-9 shrink-0 rounded-full transition-colors ${washStep ? 'bg-accent' : 'bg-muted'}`}
          >
            <span
              className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${washStep ? 'translate-x-4' : 'translate-x-0.5'}`}
            />
          </button>
        </label>
      </div>
    </div>
  );
}

function SliderRow({
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit?: string;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium tabular-nums">
          {value.toFixed(step < 1 ? 2 : 0)}
          {unit ? ` ${unit}` : ''}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="mt-1 w-full accent-accent"
      />
    </div>
  );
}
