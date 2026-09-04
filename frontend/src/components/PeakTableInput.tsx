import { useState } from 'react';
import { Table, Plus, Trash2, Upload } from 'lucide-react';
import { toast } from 'sonner';

export interface ManualPeak {
  rt_min: number;
  width_min: number;
  area: number;
  height: number;
  compound_name?: string;
}

interface Props {
  onPeaksSubmit: (peaks: ManualPeak[]) => void;
}

export function PeakTableInput({ onPeaksSubmit }: Props) {
  const [peaks, setPeaks] = useState<ManualPeak[]>([
    { rt_min: 0, width_min: 0, area: 0, height: 0, compound_name: '' },
  ]);
  const [pasteMode, setPasteMode] = useState(false);
  const [pasteText, setPasteText] = useState('');

  const updatePeak = (i: number, field: keyof ManualPeak, value: string | number) => {
    const updated = [...peaks];
    updated[i] = { ...updated[i], [field]: value };
    setPeaks(updated);
  };

  const addRow = () => {
    setPeaks([...peaks, { rt_min: 0, width_min: 0, area: 0, height: 0, compound_name: '' }]);
  };

  const removeRow = (i: number) => {
    setPeaks(peaks.filter((_, idx) => idx !== i));
  };

  const handleSubmit = () => {
    const valid = peaks.filter(p => p.rt_min > 0);
    if (valid.length === 0) {
      toast.error('Enter at least one peak with RT > 0');
      return;
    }
    onPeaksSubmit(valid);
    toast.success(`Submitted ${valid.length} peak(s)`);
  };

  const handlePaste = () => {
    // Parse pasted text: tab or comma separated, one peak per line
    // Format: RT, width, area, height, [name]
    const lines = pasteText.trim().split('\n');
    const parsed: ManualPeak[] = [];
    for (const line of lines) {
      const parts = line.split(/[\t,]/).map(s => s.trim());
      if (parts.length < 1) continue;
      const rt = parseFloat(parts[0]);
      if (isNaN(rt) || rt <= 0) continue;
      parsed.push({
        rt_min: rt,
        width_min: parseFloat(parts[1]) || 0,
        area: parseFloat(parts[2]) || 0,
        height: parseFloat(parts[3]) || 0,
        compound_name: parts[4] || '',
      });
    }
    if (parsed.length === 0) {
      toast.error('No valid peaks found in pasted text');
      return;
    }
    setPeaks(parsed);
    setPasteMode(false);
    setPasteText('');
    toast.success(`Parsed ${parsed.length} peak(s) from pasted text`);
  };

  return (
    <div className="card-scientific">
      <div className="flex items-center gap-2">
        <Table className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold">Manual Peak Table Entry</h3>
      </div>

      <div className="mt-2 flex gap-2">
        <button
          onClick={() => setPasteMode(!pasteMode)}
          className={`text-xs rounded-md px-2 py-1 ${pasteMode ? 'bg-accent text-white' : 'bg-muted text-muted-foreground'}`}
        >
          Paste Mode
        </button>
      </div>

      {pasteMode ? (
        <div className="mt-2 space-y-2">
          <p className="text-[10px] text-muted-foreground">
            Paste peak data (one per line): RT, width, area, height, [name]
            <br />Tab or comma separated.
          </p>
          <textarea
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            placeholder="5.23, 0.15, 1234567, 89000, Caffeine&#10;8.45, 0.20, 2345678, 78000, Aspirin"
            rows={6}
            className="w-full rounded border border-border bg-background px-2 py-1 font-mono text-xs"
          />
          <button onClick={handlePaste} className="btn-primary text-xs">Parse Pasted Data</button>
        </div>
      ) : (
        <div className="mt-2">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-1 py-1 text-left">RT (min)</th>
                  <th className="px-1 py-1 text-left">Width (min)</th>
                  <th className="px-1 py-1 text-left">Area</th>
                  <th className="px-1 py-1 text-left">Height</th>
                  <th className="px-1 py-1 text-left">Name</th>
                  <th className="px-1 py-1"></th>
                </tr>
              </thead>
              <tbody>
                {peaks.map((p, i) => (
                  <tr key={i} className="border-b border-border/50">
                    <td className="px-1 py-1">
                      <input type="number" step="0.01" value={p.rt_min}
                        onChange={(e) => updatePeak(i, 'rt_min', parseFloat(e.target.value) || 0)}
                        className="w-20 rounded border border-border bg-background px-1 py-0.5 text-xs" />
                    </td>
                    <td className="px-1 py-1">
                      <input type="number" step="0.001" value={p.width_min}
                        onChange={(e) => updatePeak(i, 'width_min', parseFloat(e.target.value) || 0)}
                        className="w-20 rounded border border-border bg-background px-1 py-0.5 text-xs" />
                    </td>
                    <td className="px-1 py-1">
                      <input type="number" step="1" value={p.area}
                        onChange={(e) => updatePeak(i, 'area', parseFloat(e.target.value) || 0)}
                        className="w-24 rounded border border-border bg-background px-1 py-0.5 text-xs" />
                    </td>
                    <td className="px-1 py-1">
                      <input type="number" step="1" value={p.height}
                        onChange={(e) => updatePeak(i, 'height', parseFloat(e.target.value) || 0)}
                        className="w-20 rounded border border-border bg-background px-1 py-0.5 text-xs" />
                    </td>
                    <td className="px-1 py-1">
                      <input type="text" value={p.compound_name || ''}
                        onChange={(e) => updatePeak(i, 'compound_name', e.target.value)}
                        className="w-24 rounded border border-border bg-background px-1 py-0.5 text-xs" />
                    </td>
                    <td className="px-1 py-1">
                      <button onClick={() => removeRow(i)} className="text-red-500 hover:text-red-700">
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button onClick={addRow} className="mt-1 flex items-center gap-1 text-xs text-accent hover:underline">
            <Plus className="h-3 w-3" /> Add row
          </button>
        </div>
      )}

      <button onClick={handleSubmit} className="btn-primary mt-2 flex items-center gap-1 text-xs">
        <Upload className="h-3 w-3" /> Submit Peaks
      </button>
    </div>
  );
}
