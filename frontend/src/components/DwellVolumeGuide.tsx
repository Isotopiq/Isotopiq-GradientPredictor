import { useState } from 'react';
import { Beaker, Calculator, Info } from 'lucide-react';

interface Props {
  onDwellVolumeCalculated?: (vol: number) => void;
  onDeadVolumeCalculated?: (vol: number) => void;
}

export function DwellVolumeGuide({ onDwellVolumeCalculated, onDeadVolumeCalculated }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [mode, setMode] = useState<'dwell' | 'dead'>('dwell');

  // Dwell volume inputs
  const [flowRate, setFlowRate] = useState(2.0);
  const [gradientTime, setGradientTime] = useState(20);
  const [midpointTime, setMidpointTime] = useState(10.85);

  // Dead volume inputs
  const [uracilRt, setUracilRt] = useState(1.5);
  const [deadFlowRate, setDeadFlowRate] = useState(0.4);

  // Results
  const [dwellResult, setDwellResult] = useState<{ volume: number; time: number } | null>(null);
  const [deadResult, setDeadResult] = useState<number | null>(null);

  const calcDwell = () => {
    const dwellTime = midpointTime - gradientTime / 2;
    const volume = dwellTime * flowRate;
    setDwellResult({ volume, time: dwellTime });
    onDwellVolumeCalculated?.(volume);
  };

  const calcDead = () => {
    const volume = uracilRt * deadFlowRate;
    setDeadResult(volume);
    onDeadVolumeCalculated?.(volume);
  };

  return (
    <div className="card-scientific">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 text-left"
      >
        <Beaker className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold">Dwell & Dead Volume Measurement Guide</h3>
        <span className="ml-auto text-xs text-muted-foreground">{expanded ? '▼' : '▶'}</span>
      </button>

      {expanded && (
        <div className="mt-3 space-y-4">
          {/* Mode selector */}
          <div className="flex gap-2">
            <button
              onClick={() => setMode('dwell')}
              className={`rounded-md px-3 py-1 text-xs font-medium ${mode === 'dwell' ? 'bg-accent text-white' : 'bg-muted text-muted-foreground'}`}
            >
              Dwell Volume
            </button>
            <button
              onClick={() => setMode('dead')}
              className={`rounded-md px-3 py-1 text-xs font-medium ${mode === 'dead' ? 'bg-accent text-white' : 'bg-muted text-muted-foreground'}`}
            >
              Dead Volume
            </button>
          </div>

          {mode === 'dwell' && (
            <div className="space-y-3">
              <div className="rounded-md bg-muted/50 p-3 text-xs text-muted-foreground">
                <div className="mb-1 flex items-center gap-1 font-semibold text-foreground">
                  <Info className="h-3 w-3" /> Step-by-step procedure
                </div>
                <ol className="ml-4 list-decimal space-y-1">
                  <li>Remove the analytical column; connect capillary tubing (1m × 0.125mm PEEK) in its place.</li>
                  <li>Set A: water, B: water + 0.1% acetone. Detector at 265 nm.</li>
                  <li>Run a 0→100% B gradient over {gradientTime} min at {flowRate} mL/min.</li>
                  <li>Measure the midpoint time between the initial and final baselines.</li>
                  <li>Calculate: tD = midpoint − gradient_time/2, VD = tD × F</li>
                </ol>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <label className="block">
                  <span className="text-xs text-muted-foreground">Flow (mL/min)</span>
                  <input type="number" step="0.1" min="0" value={flowRate}
                    onChange={(e) => setFlowRate(parseFloat(e.target.value) || 0)}
                    className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm" />
                </label>
                <label className="block">
                  <span className="text-xs text-muted-foreground">Gradient (min)</span>
                  <input type="number" step="1" min="0" value={gradientTime}
                    onChange={(e) => setGradientTime(parseFloat(e.target.value) || 0)}
                    className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm" />
                </label>
                <label className="block">
                  <span className="text-xs text-muted-foreground">Midpoint (min)</span>
                  <input type="number" step="0.01" min="0" value={midpointTime}
                    onChange={(e) => setMidpointTime(parseFloat(e.target.value) || 0)}
                    className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm" />
                </label>
              </div>

              <button onClick={calcDwell} className="btn-primary flex items-center gap-1 text-xs">
                <Calculator className="h-3 w-3" /> Calculate Dwell Volume
              </button>

              {dwellResult && (
                <div className="rounded-md bg-green-500/10 p-2 text-sm">
                  <span className="font-semibold">Dwell Time:</span> {dwellResult.time.toFixed(2)} min<br />
                  <span className="font-semibold">Dwell Volume:</span> {dwellResult.volume.toFixed(3)} mL
                </div>
              )}
            </div>
          )}

          {mode === 'dead' && (
            <div className="space-y-3">
              <div className="rounded-md bg-muted/50 p-3 text-xs text-muted-foreground">
                <div className="mb-1 flex items-center gap-1 font-semibold text-foreground">
                  <Info className="h-3 w-3" /> Step-by-step procedure
                </div>
                <ol className="ml-4 list-decimal space-y-1">
                  <li>Install the analytical column you will use for analysis.</li>
                  <li>Inject a void marker (uracil for RP, thiourea for HILIC).</li>
                  <li>Run isocratic at typical flow rate; record the retention time.</li>
                  <li>Calculate: Vdead = tR × F</li>
                </ol>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <label className="block">
                  <span className="text-xs text-muted-foreground">Uracil RT (min)</span>
                  <input type="number" step="0.01" min="0" value={uracilRt}
                    onChange={(e) => setUracilRt(parseFloat(e.target.value) || 0)}
                    className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm" />
                </label>
                <label className="block">
                  <span className="text-xs text-muted-foreground">Flow (mL/min)</span>
                  <input type="number" step="0.01" min="0" value={deadFlowRate}
                    onChange={(e) => setDeadFlowRate(parseFloat(e.target.value) || 0)}
                    className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm" />
                </label>
              </div>

              <button onClick={calcDead} className="btn-primary flex items-center gap-1 text-xs">
                <Calculator className="h-3 w-3" /> Calculate Dead Volume
              </button>

              {deadResult !== null && (
                <div className="rounded-md bg-green-500/10 p-2 text-sm">
                  <span className="font-semibold">Dead Volume:</span> {deadResult.toFixed(3)} mL
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
