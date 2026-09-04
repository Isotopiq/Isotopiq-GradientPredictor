import { useCallback, useEffect, useState, useRef } from 'react';
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
  const [washStep, setWashStep] = useState(true);
  const [washTimeMin, setWashTimeMin] = useState(0.5);      // time to drop from %B end to %B start
  const [reequilTimeMin, setReequilTimeMin] = useState(2.0); // hold at initial conditions

  // Track whether the current gradientTable change came from our own rebuild
  // to avoid the sync effect fighting with manual slider changes.
  const internalChange = useRef(false);

  // Rebuild gradient table from all current parameters
  const rebuildGradient = useCallback(
    (newBStart: number, newBEnd: number, newTimeMin: number, withWash: boolean, washMin: number, reequilMin: number) => {
      const tTotal = newTimeMin * 60;
      const table: GradientPoint[] = [
        { time_s: 0, percent_b: newBStart },
        { time_s: 60, percent_b: newBStart },
        { time_s: tTotal - 120, percent_b: newBEnd },
        { time_s: tTotal, percent_b: newBEnd },
      ];
      if (withWash) {
        // Wash step: linear drop from %B end back to %B start
        const washEndS = tTotal + washMin * 60;
        table.push({ time_s: washEndS, percent_b: newBStart });
        // Re-equilibration: hold at initial %B
        const reequilEndS = washEndS + reequilMin * 60;
        table.push({ time_s: reequilEndS, percent_b: newBStart });
      }
      internalChange.current = true;
      onGradientChange(table);
    },
    [onGradientChange],
  );

  // Sync bStart/bEnd/washStep when gradient table is set externally (e.g. from suggestion or loaded method).
  // Skips when the change came from our own rebuild to avoid feedback loops.
  useEffect(() => {
    if (internalChange.current) {
      internalChange.current = false;
      return;
    }
    if (gradientTable.length < 2) return;
    const first = gradientTable[0];
    const last = gradientTable[gradientTable.length - 1];
    // Detect wash step: last point's %B matches first point's %B and there are >4 points
    const hasWash = gradientTable.length > 4 && Math.abs(last.percent_b - first.percent_b) < 0.1;
    setBStart(first.percent_b);
    if (hasWash) {
      // Points: [start, start-hold, end, end-hold, wash-return, reequil-hold]
      const endIdx = 3;
      setBEnd(gradientTable[endIdx]?.percent_b ?? gradientTable[2]?.percent_b ?? 95);
      const tTotal = gradientTable[3]?.time_s ?? gradientTable[2]?.time_s ?? 1200;
      const washReturnS = gradientTable[4]?.time_s ?? tTotal;
      const reequilEndS = gradientTable[5]?.time_s ?? washReturnS;
      setWashTimeMin(Math.max(0.1, (washReturnS - tTotal) / 60));
      setReequilTimeMin(Math.max(0.1, (reequilEndS - washReturnS) / 60));
      setWashStep(true);
    } else {
      // Table has no wash step — since wash is on by default, rebuild with wash added
      const newBEnd = gradientTable[gradientTable.length - 1].percent_b;
      const tTotal = gradientTable[gradientTable.length - 1].time_s;
      const newTimeMin = Math.max(5, tTotal / 60);
      setBEnd(newBEnd);
      setWashStep(true);
      // Rebuild with wash enabled using the loaded gradient's parameters
      rebuildGradient(first.percent_b, newBEnd, newTimeMin, true, washTimeMin, reequilTimeMin);
    }
  }, [gradientTable]);

  // Debounced simulation — gradient RT prediction only.
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
    rebuildGradient(v, bEnd, gradientTimeMin, washStep, washTimeMin, reequilTimeMin);
  };

  const handleBEnd = (v: number) => {
    setBEnd(v);
    rebuildGradient(bStart, v, gradientTimeMin, washStep, washTimeMin, reequilTimeMin);
  };

  const handleGradientTime = (v: number) => {
    onGradientTimeChange(v);
    rebuildGradient(bStart, bEnd, v, washStep, washTimeMin, reequilTimeMin);
  };

  const handleWashToggle = (enabled: boolean) => {
    setWashStep(enabled);
    rebuildGradient(bStart, bEnd, gradientTimeMin, enabled, washTimeMin, reequilTimeMin);
  };

  const handleWashTime = (v: number) => {
    setWashTimeMin(v);
    rebuildGradient(bStart, bEnd, gradientTimeMin, washStep, v, reequilTimeMin);
  };

  const handleReequilTime = (v: number) => {
    setReequilTimeMin(v);
    rebuildGradient(bStart, bEnd, gradientTimeMin, washStep, washTimeMin, v);
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

      {/* Wash / re-equilibration step toggle + duration controls */}
      <div className="border-t border-border pt-3">
        <label className="flex items-center justify-between cursor-pointer">
          <div>
            <span className="text-xs font-medium">Wash & Re-equilibrate</span>
            <p className="text-[10px] text-muted-foreground">
              {washStep
                ? `Returns to ${bStart}% B, re-equilibrates column`
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

        {washStep && (
          <div className="mt-3 space-y-3">
            <SliderRow
              label="Wash Duration"
              value={washTimeMin}
              min={0.1}
              max={5}
              step={0.1}
              unit="min"
              onChange={handleWashTime}
            />
            <SliderRow
              label="Re-equilibration"
              value={reequilTimeMin}
              min={0.5}
              max={10}
              step={0.5}
              unit="min"
              onChange={handleReequilTime}
            />
            <div className="rounded-md bg-muted/40 p-2 text-[10px] text-muted-foreground">
              <strong>Gradient program:</strong> {bStart}% B → {bEnd}% B over {gradientTimeMin} min →
              wash to {bStart}% B over {washTimeMin.toFixed(1)} min →
              hold {reequilTimeMin.toFixed(1)} min (re-equilibration)
              <br />
              <strong>Total run time:</strong> {(gradientTimeMin + washTimeMin + reequilTimeMin).toFixed(1)} min
            </div>
          </div>
        )}
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
          {value.toFixed(step < 1 ? (step <= 0.1 ? 1 : 2) : 0)}
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
