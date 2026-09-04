import { useState } from 'react';
import { Triangle, Calculator } from 'lucide-react';
import { methodsApi } from '@/api/methods';
import { toast } from 'sonner';
import type { TernaryOptResult } from '@/types';

interface Props {
  smilesList: string[];
  methodParams?: {
    ph?: number;
    temperature?: number;
    flow_rate?: number;
    gradient_time?: number;
    column_type?: string;
  };
}

function rsColor(rs: number): string {
  if (rs >= 2.0) return '#10b981';
  if (rs >= 1.5) return '#84cc16';
  if (rs >= 1.0) return '#f59e0b';
  if (rs >= 0.5) return '#f97316';
  return '#ef4444';
}

// Convert ternary fractions to SVG coordinates (equilateral triangle)
function ternaryToSvg(frac_a: number, frac_b: number, frac_c: number, size: number): { x: number; y: number } {
  // A at top, B at bottom-left, C at bottom-right
  const x = frac_b * 0 + frac_c * size + frac_a * size / 2;
  const y = (1 - frac_a) * size * 0.866;
  return { x, y };
}

export function TernaryPlot({ smilesList, methodParams }: Props) {
  const [solventB, setSolventB] = useState('acn');
  const [solventC, setSolventC] = useState('meoh');
  const [mode, setMode] = useState('ternary');
  const [result, setResult] = useState<TernaryOptResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handleCompute = async () => {
    if (smilesList.length < 2) {
      toast.error('Need at least 2 compounds');
      return;
    }
    setLoading(true);
    try {
      const res = await methodsApi.ternaryOptimize({
        smiles_list: smilesList,
        solvent_b: solventB,
        solvent_c: solventC,
        mode,
        ph: methodParams?.ph,
        temperature_c: methodParams?.temperature,
        flow_rate_ml_min: methodParams?.flow_rate,
        gradient_time_min: methodParams?.gradient_time,
        column_type: methodParams?.column_type,
      });
      setResult(res);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Ternary optimization failed');
    } finally {
      setLoading(false);
    }
  };

  const triangleSize = 300;

  return (
    <div className="card-scientific">
      <div className="flex items-center gap-2">
        <Triangle className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold">Ternary Solvent Optimization</h3>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2">
        <label className="block">
          <span className="text-xs text-muted-foreground">Solvent B</span>
          <select value={solventB} onChange={(e) => setSolventB(e.target.value)}
            className="mt-1 w-full rounded border border-border bg-background px-1 py-1 text-xs">
            <option value="acn">Acetonitrile</option>
            <option value="meoh">Methanol</option>
            <option value="ipa">Isopropanol</option>
            <option value="thf">THF</option>
            <option value="acetone">Acetone</option>
          </select>
        </label>
        <label className="block">
          <span className="text-xs text-muted-foreground">Solvent C</span>
          <select value={solventC} onChange={(e) => setSolventC(e.target.value)}
            className="mt-1 w-full rounded border border-border bg-background px-1 py-1 text-xs">
            <option value="meoh">Methanol</option>
            <option value="acn">Acetonitrile</option>
            <option value="ipa">Isopropanol</option>
            <option value="thf">THF</option>
            <option value="acetone">Acetone</option>
          </select>
        </label>
        <label className="block">
          <span className="text-xs text-muted-foreground">Mode</span>
          <select value={mode} onChange={(e) => setMode(e.target.value)}
            className="mt-1 w-full rounded border border-border bg-background px-1 py-1 text-xs">
            <option value="ternary">Ternary (interior)</option>
            <option value="binary">Binary (perimeter)</option>
          </select>
        </label>
      </div>

      <button onClick={handleCompute} disabled={loading} className="btn-primary mt-2 flex items-center gap-1 text-xs">
        <Calculator className="h-3 w-3" /> {loading ? 'Optimizing...' : 'Optimize'}
      </button>

      {result && (
        <div className="mt-3">
          <div className="flex justify-center">
            <svg width={triangleSize + 80} height={triangleSize + 60}>
              {/* Triangle outline */}
              <polygon
                points={`${ternaryToSvg(1, 0, 0, triangleSize).x + 40},${ternaryToSvg(1, 0, 0, triangleSize).y + 20} ${ternaryToSvg(0, 1, 0, triangleSize).x + 40},${ternaryToSvg(0, 1, 0, triangleSize).y + 20} ${ternaryToSvg(0, 0, 1, triangleSize).x + 40},${ternaryToSvg(0, 0, 1, triangleSize).y + 20}`}
                fill="none"
                stroke="currentColor"
                strokeWidth={1}
                className="text-border"
              />

              {/* Plot points */}
              {result.points.map((p, i) => {
                const { x, y } = ternaryToSvg(p.frac_a, p.frac_b, p.frac_c, triangleSize);
                return (
                  <circle
                    key={i}
                    cx={x + 40}
                    cy={y + 20}
                    r={8}
                    fill={rsColor(p.min_rs)}
                    opacity={0.7}
                    stroke="#fff"
                    strokeWidth={0.5}
                  >
                    <title>{`A:${(p.frac_a*100).toFixed(0)}% B:${(p.frac_b*100).toFixed(0)}% C:${(p.frac_c*100).toFixed(0)}% Rs:${p.min_rs.toFixed(2)}`}</title>
                  </circle>
                );
              })}

              {/* Optimal point marker */}
              {result.optimal && (
                <circle
                  cx={ternaryToSvg(result.optimal.frac_a, result.optimal.frac_b, result.optimal.frac_c, triangleSize).x + 40}
                  cy={ternaryToSvg(result.optimal.frac_a, result.optimal.frac_b, result.optimal.frac_c, triangleSize).y + 20}
                  r={12}
                  fill="none"
                  stroke="#000"
                  strokeWidth={2}
                />
              )}

              {/* Corner labels */}
              <text x={ternaryToSvg(1, 0, 0, triangleSize).x + 40} y={ternaryToSvg(1, 0, 0, triangleSize).y + 10}
                fontSize={10} textAnchor="middle" className="text-muted-foreground">Water (A)</text>
              <text x={ternaryToSvg(0, 1, 0, triangleSize).x + 40} y={ternaryToSvg(0, 1, 0, triangleSize).y + 35}
                fontSize={10} textAnchor="middle" className="text-muted-foreground">{solventB.toUpperCase()} (B)</text>
              <text x={ternaryToSvg(0, 0, 1, triangleSize).x + 40} y={ternaryToSvg(0, 0, 1, triangleSize).y + 35}
                fontSize={10} textAnchor="middle" className="text-muted-foreground">{solventC.toUpperCase()} (C)</text>
            </svg>
          </div>

          {/* Color legend */}
          <div className="mt-2 flex items-center justify-center gap-2 text-[10px] text-muted-foreground">
            <span>Rs:</span>
            <span style={{ color: rsColor(0.3) }}>&lt;0.5</span>
            <span style={{ color: rsColor(0.7) }}>0.5-1.0</span>
            <span style={{ color: rsColor(1.2) }}>1.0-1.5</span>
            <span style={{ color: rsColor(1.7) }}>1.5-2.0</span>
            <span style={{ color: rsColor(2.5) }}>&gt;2.0</span>
          </div>

          {result.optimal && (
            <p className="mt-2 text-center text-xs">
              <span className="font-semibold">Optimal:</span> {(result.optimal.frac_a*100).toFixed(0)}% A / {(result.optimal.frac_b*100).toFixed(0)}% B / {(result.optimal.frac_c*100).toFixed(0)}% C (Rs={result.optimal.min_rs.toFixed(2)})
            </p>
          )}
        </div>
      )}
    </div>
  );
}
