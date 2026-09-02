import { useCallback, useEffect, useState } from 'react';
import { methodsApi } from '@/api/methods';
import type { GradientPoint, GradientSimulateResult, ChromatogramResult } from '@/types';

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
  onChromatogramResult: (result: ChromatogramResult) => void;
}

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
  onChromatogramResult,
}: ParameterSlidersProps) {
  const [bStart, setBStart] = useState(5);
  const [bEnd, setBEnd] = useState(95);

  // Rebuild gradient table when key params change
  const rebuildGradient = useCallback(
    (newBStart: number, newBEnd: number, newTimeMin: number) => {
      const tTotal = newTimeMin * 60;
      const table: GradientPoint[] = [
        { time_s: 0, percent_b: newBStart },
        { time_s: 60, percent_b: newBStart },
        { time_s: tTotal - 120, percent_b: newBEnd },
        { time_s: tTotal, percent_b: newBEnd },
      ];
      onGradientChange(table);
    },
    [onGradientChange],
  );

  // Debounced simulation
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

        const chromResult = await methodsApi.simulateChromatogram({
          peaks: [
            {
              rt_s: simResult.predicted_rt_s,
              height: 1.0,
              label: 'Predicted',
            },
          ],
          total_time_s: gradientTable[gradientTable.length - 1]?.time_s || 1500,
        });
        onChromatogramResult(chromResult);
      } catch {
        // Silent fail for live updates
      }
    }, 400);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gradientTable, flowRate, logp]);

  const handleBStart = (v: number) => {
    setBStart(v);
    rebuildGradient(v, bEnd, gradientTimeMin);
  };

  const handleBEnd = (v: number) => {
    setBEnd(v);
    rebuildGradient(bStart, v, gradientTimeMin);
  };

  const handleGradientTime = (v: number) => {
    onGradientTimeChange(v);
    rebuildGradient(bStart, bEnd, v);
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
